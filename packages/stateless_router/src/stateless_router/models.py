from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class AgentDefinition(BaseModel):
    name: str
    description: str
    examples: List[str] = Field(default_factory=list)

class RoutingRules(BaseModel):
    agents: List[AgentDefinition]
    global_rules: List[str] = Field(default_factory=list)
    output_schema_instruction: str = 'Respond ONLY with valid JSON: { "route": "AgentName" }'

    def to_system_prompt(self) -> str:
        """
        Converts the structured rules into a flattened system prompt.
        """
        prompt = "You are a stateless routing agent. Analyze the user's prompt and route it correctly.\n\nAGENTS:\n"
        for agent in self.agents:
            prompt += f"- {agent.name}: {agent.description}\n"
            if agent.examples:
                prompt += f"  Examples: {', '.join(agent.examples)}\n"
        
        if self.global_rules:
            prompt += "\nRULES:\n"
            for rule in self.global_rules:
                prompt += f"- {rule}\n"
        
        prompt += f"\nOUTPUT:\n{self.output_schema_instruction}"
        return prompt
