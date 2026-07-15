# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, finale, or under the License.

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Any
from pydantic import BaseModel
from fastapi import HTTPException
from origami_router import state

logger = logging.getLogger(__name__)


class PipelineContext(BaseModel):
    model: str
    prompt: str
    context_summary: Optional[str] = None
    span: Any = None
    
    # Internal Pipeline Metadata
    threat_detected: bool = False
    matched_attack: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    confidence: float = 0.0
    action_taken: Optional[str] = None
    sanitized_prompt: str = ""


class PipelineResult(BaseModel):
    route: str
    context: PipelineContext


class PipelineStep(ABC):
    @abstractmethod
    async def process(self, ctx: PipelineContext) -> Optional[PipelineResult]:
        """
        Processes context step. Returns PipelineResult if pipeline terminates early, else None.
        """
        pass


class OpsSecPreFilterStep(PipelineStep):
    """
    Evaluates Operational Security (OpsSec) vector attack rules before routing.
    """
    async def process(self, ctx: PipelineContext) -> Optional[PipelineResult]:
        if state.ops_sec_analyzer is None:
            return None

        threat = await state.ops_sec_analyzer.analyze_prompt(ctx.prompt)
        ctx.confidence = threat.confidence
        ctx.sanitized_prompt = threat.sanitized_prompt

        if threat.is_threat:
            ctx.threat_detected = True
            ctx.matched_attack = threat.matched_attack
            ctx.category = threat.category
            ctx.severity = threat.severity
            ctx.action_taken = state.ops_sec_analyzer.rules.config.default_action

            if ctx.span:
                ctx.span.set_attribute("router.ops_sec_threat", True)
                ctx.span.set_attribute("router.ops_sec_attack", ctx.matched_attack or "")
                ctx.span.set_attribute("router.ops_sec_confidence", ctx.confidence)
                ctx.span.set_attribute("router.ops_sec_action", ctx.action_taken)

            if ctx.action_taken == "block":
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Security Alert: Prompt vector attack detected and blocked.",
                        "threat": threat.model_dump(),
                    },
                )
            elif ctx.action_taken == "slim":
                ctx.prompt = threat.sanitized_prompt

        return None


class FastTierStep(PipelineStep):
    """
    Fast-Tier Optimization: Tries high-speed Ember per-example embedding router first.
    """
    async def process(self, ctx: PipelineContext) -> Optional[PipelineResult]:
        if ctx.model != "ember" and "ember" in state.active_routers:
            ember_router = state.active_routers["ember"]
            try:
                threshold_cfg = getattr(ember_router, "ember_config", None)
                if threshold_cfg:
                    threshold_val = threshold_cfg.confidence_threshold
                    outcome, confidence = await ember_router.route_detailed(ctx.prompt, context_summary=ctx.context_summary)
                    
                    if confidence >= threshold_val:
                        if ctx.span:
                            ctx.span.set_attribute("router.fast_tier_hit", True)
                            ctx.span.set_attribute("router.fast_tier_confidence", confidence)
                            ctx.span.set_attribute("router.outcome", outcome)
                        return PipelineResult(route=outcome, context=ctx)
                    else:
                        if ctx.span:
                            ctx.span.set_attribute("router.fast_tier_hit", False)
                            ctx.span.set_attribute("router.fast_tier_confidence", confidence)
            except Exception as e:
                logger.warning("Fast-Tier pre-routing step failed: %s", e)

        return None


class TargetProviderStep(PipelineStep):
    """
    Primary routing dispatch to target model specialist router.
    """
    async def process(self, ctx: PipelineContext) -> Optional[PipelineResult]:
        model_name = ctx.model.lower()
        target_router = state.active_routers.get(model_name)

        if not target_router:
            if ctx.span:
                ctx.span.set_attribute("error", True)
                ctx.span.set_attribute("error.message", f"Router not configured for model: {ctx.model}")
            raise HTTPException(status_code=400, detail=f"Unsupported model: {ctx.model}")

        try:
            outcome = await target_router.route(ctx.prompt, context_summary=ctx.context_summary)
        except Exception as e:
            if ctx.span:
                ctx.span.set_attribute("error", True)
                ctx.span.set_attribute("error.message", str(e))
            raise HTTPException(status_code=500, detail=f"Routing failed: {e}")

        if ctx.span:
            ctx.span.set_attribute("router.outcome", outcome)

        return PipelineResult(route=outcome, context=ctx)


class RoutingPipeline:
    """
    Orchestrates decoupled, step-by-step pipeline execution for request queries.
    """
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps

    async def execute(self, ctx: PipelineContext) -> PipelineResult:
        for step in self.steps:
            res = await step.process(ctx)
            if res is not None:
                return res
        raise HTTPException(status_code=500, detail="Routing pipeline completed without producing an outcome.")
