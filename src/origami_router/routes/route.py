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

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from opentelemetry.propagate import extract
from origami_api.config import Config
from origami_router import state
from origami_common.otel import get_tracer

router = APIRouter()

class RouteRequest(BaseModel):
    model: str
    prompt: str
    context_summary: Optional[str] = None

class RouteResponse(BaseModel):
    route: str

@router.post("/route", response_model=RouteResponse)
async def route_query(request: RouteRequest, req: Request):
    """
    Main routing endpoint.
    Participates in OTel span if provided in headers, otherwise starts a new one.
    """
    if state.tracer is None:
        state.tracer = get_tracer("edgerouter_service")
    
    # In test environments, startup_event might not have fired
    if not state.active_routers:
        if state.config is None:
            state.config = Config()
        
        shared_executor = state.get_executor()
        rules_path = "rules.toml"
        rules = state.load_rules(rules_path)
        server_cfg = getattr(state.config, "server", None)
        await state.setup_routers(server_cfg, rules, shared_executor)

    ctx = extract(req.headers)

    with state.tracer.start_as_current_span(
        "origami_router.api_route",
        attributes={"router.model_requested": request.model},
        context=ctx
    ) as span:
        
        model_name = request.model.lower()
        target_router = state.active_routers.get(model_name)
        
        if not target_router:
            span.set_attribute("error", True)
            span.set_attribute("error.message", f"Router not configured for model: {request.model}")
            raise HTTPException(status_code=400, detail=f"Unsupported model: {request.model}")

        # Fast-Tier Optimization: Try EmberRouter first if it's available and not the primary target
        if request.model != "ember" and "ember" in state.active_routers:
            ember_router = state.active_routers["ember"]
            try:
                # We need to access ember_config to get the threshold
                threshold = getattr(ember_router, "ember_config", None)
                if threshold:
                    threshold_val = threshold.confidence_threshold
                    outcome, confidence = await ember_router.route_detailed(request.prompt, context_summary=request.context_summary)
                    
                    if confidence >= threshold_val:
                        span.set_attribute("router.fast_tier_hit", True)
                        span.set_attribute("router.fast_tier_confidence", confidence)
                        span.set_attribute("router.outcome", outcome)
                        return RouteResponse(route=outcome)
                    else:
                        span.set_attribute("router.fast_tier_hit", False)
                        span.set_attribute("router.fast_tier_confidence", confidence)
            except Exception as e:
                logger.warning("Fast-Tier pre-routing failed: %s", e)

        # Execute routing via the primary target router
        try:
            outcome = await target_router.route(request.prompt, context_summary=request.context_summary)
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            raise HTTPException(status_code=500, detail=f"Routing failed: {e}")
            
        span.set_attribute("router.outcome", outcome)
        return RouteResponse(route=outcome)
