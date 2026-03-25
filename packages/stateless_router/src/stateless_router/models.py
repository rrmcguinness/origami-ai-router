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

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class AgentDefinition(BaseModel):
    name: str
    description: str
    instructions: Optional[str] = None
    examples: List[str] = Field(default_factory=list)
    salience: int = 0  # Higher value means higher priority for the prompt! 💋

class RoutingRules(BaseModel):
    agents: List[AgentDefinition]
    global_rules: List[str] = Field(default_factory=list)
    output_schema_instruction: str = 'Respond ONLY with valid JSON: { "route": "AgentName" }'

    def to_system_prompt(self) -> str:
        """
        Converts the structured rules into a flattened system prompt.
        Agents are sorted by salience (descending) to break ties. 🏎️💨
        """
        prompt = "You are a stateless routing agent. Analyze the user's prompt and route it correctly.\n\nAGENTS:\n"
        
        # Sort by salience (descending) 💋
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
