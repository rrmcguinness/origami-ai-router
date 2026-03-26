# Copyright 2026 Google LLC

from __future__ import annotations
import os
import tomllib
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

ENV_TOML = ".env.toml"
ENV_LOCAL_TOML = ".env.local.toml"
RUNTIME_ENV = "RUNTIME_ENV"


class TomlClass:
    def __init__(self, d: Dict[str, Any] = None):
        if d is not None:
            for k, v in d.items():
                logger.debug("creating value for property: %s", k)
                setattr(self, k, v)
                
    def updateValues(self, d: Dict[str, Any] = None):
        if d is not None:
            for k, v in d.items():
                logger.debug("overriding value for property: %s", k)
                setattr(self, k, v)
                
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in vars(self).items() if not k.startswith('_')}


class TelemetryConfig(TomlClass):
    service_name: str = "default_service"
    project_id: str = ""
    use_gcp: bool = True

class ServerRouter(TomlClass):
    name: str = ""
    provider: str = ""
    config_path: str = ""
    model_path: str = ""
    n_threads: int = 0

class LoadTestConfig(TomlClass):
    total_requests: int = 0
    concurrent_clients: int = 0

class APIServer(TomlClass):
    host: str = "0.0.0.0"
    port: int = 8000
    model_path: str = ""
    n_threads: int = 0
    routers: dict[str, ServerRouter]

    def __init__(self, d: Dict[str, Any] = None):
        super().__init__(d)
        self.routers = {}
        if d is not None and "routers" in d:
            routers_data = d.get("routers")
            if isinstance(routers_data, list):
                for r_data in routers_data:
                    r = ServerRouter(r_data)
                    self.routers[r.name] = r

    def updateValues(self, d: Dict[str, Any] = None):
        super().updateValues(d)
        if d is not None and "routers" in d:
            routers_data = d.get("routers")
            if isinstance(routers_data, list):
                for r_data in routers_data:
                    name = r_data.get("name")
                    if name and name in self.routers:
                        self.routers[name].updateValues(r_data)
                    elif name:
                        r = ServerRouter(r_data)
                        self.routers[name] = r

    def get_router(self, name: str) -> ServerRouter | None:
        return self.routers.get(name)

class Application(TomlClass):
    name: str = ""
    projectId: str = ""
    location: str = ""
    threadPoolSize: int = 0
    google_project_id: str = ""
    rules_file: str = "rules.toml"

class AIModel(TomlClass):
    model_name: str = ""
    temperature: float = 0.0
    top_p: float = 0.0
    top_k: int = 0
    max_tokens: int = 0
    output_format: str = ""
    instructions: str = ""
    api_key: str = ""

class AIModels(TomlClass):
    models: dict[str, AIModel]

    def __init__(self, d: Dict[str, Any] = None):
        self.models = {}
        if d is not None:
            for k, v in d.items():
                model = AIModel(v)
                self.models[k] = model
                setattr(self, k, model)
                
    def updateValues(self, d: Dict[str, Any] = None):
        if d is not None:
            for k, v in d.items():
                if k in self.models:
                    self.models[k].updateValues(v)
                else:
                    model = AIModel(v)
                    self.models[k] = model
                    setattr(self, k, model)

    def get_model(self, name: str) -> AIModel | None:
        return self.models.get(name)

    def set_model(self, name: str, model: AIModel):
        self.models[name] = model
        setattr(self, name, model)
    

class Embedding(TomlClass):
    model: str = ""
    max_requests_per_minute: int = 0

class Embeddings(TomlClass):
    values: dict[str, Embedding] = None

class Config:
    application: Application
    api_server: APIServer
    ai_models: AIModels
    embeddings: Embeddings
    server: APIServer
    load_test: LoadTestConfig

    @staticmethod
    def get_env_file_name(fileName: str, env: str = None) -> str | None:
        if not fileName:
            return None
            
        env_to_use = env if env else os.environ.get(RUNTIME_ENV, None)
        if not env_to_use:
            return None
            
        directory = os.path.dirname(fileName)
        base = os.path.basename(fileName)
        
        if base == ".env.toml":
            tFile = os.path.join(directory, f".env.{env_to_use}.toml")
            if os.path.isfile(tFile):
                return tFile
                
        parts = fileName.split('.')
        if len(parts) >= 2:
            parts.insert(-1, env_to_use)
            tFile = ".".join(parts)
            if os.path.isfile(tFile):
                return tFile
                
        return None
    
    def __init__(self, file: str = None):
        if file is None:
            file = ENV_TOML
        self._config_file = file
        
        with open(file, "rb") as f:
            print("Loading configuration from file: ", file)
            data = tomllib.load(f)
            self.application = Application(data.get("application"))
            self.server = APIServer(data.get("server", data.get("server")))
            self.ai_models = AIModels(data.get("ai_models"))
            self.embeddings = Embeddings(data.get("embeddings"))
            self.telemetry = TelemetryConfig(data.get("telemetry"))
            self.load_test = LoadTestConfig(data.get("load_test"))

        runtime_env = os.environ.get(RUNTIME_ENV, None)

        # Load environment specific overrides
        if runtime_env is not None and runtime_env != 'local':
            self.load_overrides(runtime_env)

        # Always load local if available (overrides environment specific overrides)
        self.load_overrides("local")


    def load_overrides(self, env: str):
        env_file_name = Config.get_env_file_name(self._config_file, env)
        if env_file_name is not None:
            with open(env_file_name, "rb") as f:
                print("Loading environment config file: ", env_file_name)
                data = tomllib.load(f)
                if data.get("application"):
                    self.application.updateValues(data.get("application"))
                if data.get("server") or data.get("server"):
                    self.server.updateValues(data.get("server", data.get("server")))
                if data.get("ai_models"):
                    self.ai_models.updateValues(data.get("ai_models"))
                if data.get("embeddings"):
                    self.embeddings.updateValues(data.get("embeddings"))
                if data.get("load_test"):
                    self.load_test.updateValues(data.get("load_test"))


from pydantic import BaseModel

class RouterConfig(BaseModel):
    query_instruction: str = ""
    enable_per_example: bool = True
    confidence_threshold: float = 0.5


