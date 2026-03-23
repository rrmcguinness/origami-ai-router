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

'''
Copyright 2024 Google, LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import logging
import os
import warnings
from typing import Optional

# Suppress known deprecation warning in OTel GCP exporter BEFORE importing it
warnings.filterwarnings("ignore", category=DeprecationWarning, module="opentelemetry.exporter.cloud_trace")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

from opentelemetry import _logs
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.cloud_logging import CloudLoggingExporter

from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from .config import Config
from .api import TomlClass

logger = logging.getLogger(__name__)

# Suppress known deprecation warning in OTel GCP exporter BEFORE importing it
warnings.filterwarnings("ignore", category=DeprecationWarning, module="opentelemetry.exporter.cloud_trace")

_INITIALIZED = False

class TelemetryConfig(TomlClass):
    service_name: str = "exitpass"
    use_gcp: bool = True
    project_id: Optional[str] = None

def init_otel(config: Config = None):
    """
    Initializes OpenTelemetry Tracer and Logger Providers.
    """
    global _INITIALIZED
    if _INITIALIZED:
        logger.debug("OpenTelemetry already initialized")
        return

    if config is None:
        config = Config()

    otel_cfg_dict = getattr(config.baseConfig, 'telemetry', {})
    otel_cfg = TelemetryConfig(otel_cfg_dict)

    if not otel_cfg.project_id:
        app_cfg = getattr(config.baseConfig, 'application', None)
        if app_cfg:
            otel_cfg.project_id = getattr(app_cfg, 'google_project_id', getattr(app_cfg, 'projectId', None))

    logger.info(f"Initializing OpenTelemetry for service: {otel_cfg.service_name} (Project: {otel_cfg.project_id})")

    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: otel_cfg.service_name,
        "deployment.environment": os.environ.get("RUNTIME_ENV", "local"),
    })

    # Initialize Tracer
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    if otel_cfg.use_gcp:
        logger.info(f"Using CloudTraceSpanExporter for project: {otel_cfg.project_id or 'Inferred'}")
        trace_exporter = CloudTraceSpanExporter(project_id=otel_cfg.project_id or None)
        tracer_provider.add_span_processor(BatchSpanProcessor(
            trace_exporter,
            max_queue_size=16384,
            max_export_batch_size=4096
        ))
    else:
        logger.info("GCP telemetry disabled, using NoOp/Default providers for tracing")

    # Initialize Logger
    logger_provider = LoggerProvider(resource=resource)
    _logs.set_logger_provider(logger_provider)

    if otel_cfg.use_gcp:
        logger.info(f"Using CloudLoggingExporter for project: {otel_cfg.project_id or 'Inferred'}")
        log_exporter = CloudLoggingExporter(project_id=otel_cfg.project_id or None)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(
            log_exporter,
            max_queue_size=16384,
            max_export_batch_size=4096
        ))
    else:
        logger.info("GCP telemetry disabled, using NoOp/Default providers for logging")

    _INITIALIZED = True
    logger.info("OpenTelemetry initialization complete")

def get_tracer(name: str = __name__):
    """
    Gets a tracer instance. Auto-initializes if necessary.
    """
    if not _INITIALIZED:
        init_otel()
    return trace.get_tracer(name)

def get_logger(name: str = __name__):
    """
    Gets a logger instance. Auto-initializes if necessary.
    """
    if not _INITIALIZED:
        init_otel()
    return _logs.get_logger(name)

def flush_otel():
    """
    Forces a flush of any pending telemetry data.
    """
    if _INITIALIZED:
        try:
            tp = trace.get_tracer_provider()
            if hasattr(tp, 'force_flush'):
                tp.force_flush()
                
            lp = _logs.get_logger_provider()
            if hasattr(lp, 'force_flush'):
                lp.force_flush()
        except Exception as e:
            logger.error(f"Error flushing OpenTelemetry data: {e}")
