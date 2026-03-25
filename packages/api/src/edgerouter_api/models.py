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

from __future__ import annotations
import os
import toml
from abc import ABC
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from .utils import deep_merge


class AgentDefinition(BaseModel):
    name: str
    description: str
    instructions: Optional[str] = None
    examples: List[str] = Field(default_factory=list)
    salience: int = 0  # Higher value means higher priority for the prompt!

class RoutingRules(BaseModel):
    agents: List[AgentDefinition]
    global_rules: List[str] = Field(default_factory=list)
    output_schema_instruction: str = 'Respond ONLY with valid JSON: { "route": "AgentName" }'

    def to_system_prompt(self) -> str:
        """
        Converts the structured rules into a flattened system prompt.
        Agents are sorted by salience (descending) to break ties.
        """
        prompt = "You are a stateless routing agent. Analyze the user's prompt and route it correctly.\n\nAGENTS:\n"
        
        # Sort by salience (descending)
        sorted_agents = sorted(self.agents, key=lambda a: a.salience, reverse=True)
        
        for agent in sorted_agents:
            prompt += f"- {agent.name}: {agent.description}\n"
            if agent.instructions:
                prompt += f"  Instruction: {agent.instructions}\n"
            if agent.examples:
                prompt += f"  Examples: {', '.join(agent.examples)}\n"
        
        if self.global_rules:
            prompt += "\nRULES:\n"
            for rule in self.global_rules:
                prompt += f"- {rule}\n"
        
        prompt += f"\nOUTPUT:\n{self.output_schema_instruction}"
        return prompt


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

class GeminiModel:
    def get_generative_config(self) -> GenerationConfig:
        return GenerationConfig(
                temperature=self.temperature,
                top_p=self.topP,
                top_k=self.topK,
                max_output_tokens=self.maxTokens,
                response_mime_type=self.outputFormat)

    def get_model(self, system_instructions: str) -> GenerativeModel:
        return GenerativeModel(model_name=self.model, system_instruction=system_instructions)

