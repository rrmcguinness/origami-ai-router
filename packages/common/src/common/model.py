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

from typing import Dict, List, Any
from .api import TomlClass

from vertexai.vision_models import Image, MultiModalEmbeddingModel, MultiModalEmbeddingResponse
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, GenerationConfig


class Application(TomlClass):
    projectId: str
    location: str
    apiKey: str
    threadPoolSize: int
    root_gcs_bucket: str


class Server(TomlClass):
    host: str = "0.0.0.0"
    port: int = 8000
    model_path: str = ""
    n_threads: int = 0  # 0 will be treated as cores-1 in the implementation


class Embedding(TomlClass):
    model: str
    maxRequestPerMinute: int

class embeddings(TomlClass):
    values: dict[str, Embedding]

class Model(TomlClass):
    model: str
    temperature: float
    topP: float
    topK: float
    maxTokens: int
    outputFormat: str
    instructions: str

    def get_generative_config(self) -> GenerationConfig:
        return GenerationConfig(
                temperature=self.temperature,
                top_p=self.topP,
                top_k=self.topK,
                max_output_tokens=self.maxTokens,
                response_mime_type=self.outputFormat)

    def get_model(self, system_instructions: str) -> GenerativeModel:
        return GenerativeModel(model_name=self.model, system_instruction=system_instructions)
    

class Gemini(TomlClass):
    values: dict[str, Model]


RETRIEVAL_TASK = "RETRIEVAL_DOCUMENT"

class EmbeddingClient:
    def __init__(self, config: Any):
        vertexai.init(
            project=config.application.project_id, 
            location=config.application.location)
        
        model = TextEmbeddingModel.from_pretrained(config.vertex_ai.embedding.text_embedding_model)
        multiModel =  MultiModalEmbeddingModel.from_pretrained(config.vertex_ai.embedding.multimodal_embedding_model)
        self.embedding_model = model
        self.mult_modal_model = multiModel
    
    def get_text_embeddings(self, text: str) -> List[float]:        
        input = [TextEmbeddingInput(text, RETRIEVAL_TASK)]
        embeddings = self.embedding_model.get_embeddings(input)
        return embeddings[0].values
    
    def get_multi_modal_embeddings( self, text: str, imageBytes: bytes | None = None) -> MultiModalEmbeddingResponse:
        img = None if imageBytes == None or len(imageBytes) == 0 else Image(image_bytes=imageBytes)
        return self.mult_modal_model.get_embeddings(image=img, contextual_text=text, dimension=1408)


class BaseConfig:
    def __init__(self, args: Dict[str, any]=None):
        if args is not None:
            for k, v in args.items():
                if isinstance(v, dict):
                    setattr(self, k, BaseConfig(v))
                else:
                    setattr(self, k, v)

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def __contains__(self, item):
        return hasattr(self, item)

    def items(self):
        return vars(self).items()

    def get(self, item, default=None):
        return getattr(self, item, default)
