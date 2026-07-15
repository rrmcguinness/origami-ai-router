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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from opentelemetry.propagate import extract
from origami_api.config import Config
from origami_router import state
from origami_router.pipeline import (
    RoutingPipeline,
    PipelineContext,
    OpsSecPreFilterStep,
    FastTierStep,
    TargetProviderStep,
)
from origami_common.otel import get_tracer

logger = logging.getLogger(__name__)
router = APIRouter()


class RouteRequest(BaseModel):
    model: str
    prompt: str
    context_summary: Optional[str] = None


class RouteResponse(BaseModel):
    route: str


class ProtectedRouteResponse(BaseModel):
    route: str
    threat_detected: bool
    matched_attack: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    confidence: float = 0.0
    action_taken: Optional[str] = None
    sanitized_prompt: str


async def ensure_state_initialized():
    """Ensures routers and telemetry are active in dynamic test execution environments."""
    if state.tracer is None:
        state.tracer = get_tracer("edgerouter_service")

    if not state.active_routers:
        if state.config is None:
            state.config = Config()
        shared_executor = state.get_executor()
        rules_path = getattr(state.config.application, "rules_routing", "rules_router.toml")
        if not os.path.exists(rules_path) and os.path.exists("rules_router.toml"):
            rules_path = "rules_router.toml"
        rules = state.load_rules(rules_path)
        server_cfg = getattr(state.config, "server", None)
        await state.setup_routers(server_cfg, rules, shared_executor)

        if getattr(state.config.application, "enable_ops_sec", False) and state.ops_sec_analyzer is None:
            ops_sec_path = getattr(state.config.application, "rules_ops_sec", "rules_ops_sec.toml")
            state.setup_ops_sec(ops_sec_path, shared_executor)


@router.post("/route", response_model=RouteResponse)
async def route_query(request: RouteRequest, req: Request):
    """
    Main routing endpoint.
    Orchestrates routing via a decoupled RoutingPipeline step chain.
    """
    await ensure_state_initialized()
    ctx = extract(req.headers)

    with state.tracer.start_as_current_span(
        "origami_router.api_route",
        attributes={"router.model_requested": request.model},
        context=ctx
    ) as span:
        pipeline_ctx = PipelineContext(
            model=request.model,
            prompt=request.prompt,
            context_summary=request.context_summary,
            span=span,
            sanitized_prompt=request.prompt,
        )

        pipeline = RoutingPipeline([
            OpsSecPreFilterStep(),
            FastTierStep(),
            TargetProviderStep(),
        ])

        result = await pipeline.execute(pipeline_ctx)
        return RouteResponse(route=result.route)


@router.post("/route/protected", response_model=ProtectedRouteResponse)
async def route_query_protected(request: RouteRequest, req: Request):
    """
    Dedicated protected routing endpoint.
    Executes OpsSec vector attack evaluation pre-filter and outputs comprehensive security metadata.
    """
    await ensure_state_initialized()
    
    if state.ops_sec_analyzer is None:
        shared_executor = state.get_executor()
        ops_sec_path = getattr(state.config.application, "rules_ops_sec", "rules_ops_sec.toml")
        state.setup_ops_sec(ops_sec_path, shared_executor)

    ctx = extract(req.headers)

    with state.tracer.start_as_current_span(
        "origami_router.protected_route",
        attributes={"router.model_requested": request.model},
        context=ctx
    ) as span:
        pipeline_ctx = PipelineContext(
            model=request.model,
            prompt=request.prompt,
            context_summary=request.context_summary,
            span=span,
            sanitized_prompt=request.prompt,
        )

        pipeline = RoutingPipeline([
            OpsSecPreFilterStep(),
            FastTierStep(),
            TargetProviderStep(),
        ])

        result = await pipeline.execute(pipeline_ctx)
        c = result.context

        return ProtectedRouteResponse(
            route=result.route,
            threat_detected=c.threat_detected,
            matched_attack=c.matched_attack,
            category=c.category,
            severity=c.severity,
            confidence=c.confidence,
            action_taken=c.action_taken,
            sanitized_prompt=c.sanitized_prompt,
        )


@router.post("/admin/rules/reload")
async def reload_rules_endpoint(routing_rules_path: Optional[str] = None, ops_sec_rules_path: Optional[str] = None):
    """
    Administrative endpoint for dynamic zero-downtime hot-swapping of routing & security rules.
    """
    try:
        res = await state.reload_rules_and_routers(routing_rules_path, ops_sec_rules_path)
        return res
    except Exception as e:
        logger.error("Failed to hot-reload rules: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hot-reload failed: {e}")
