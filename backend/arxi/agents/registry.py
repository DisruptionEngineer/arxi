from pathlib import Path

import yaml


class AgentRegistry:
    def __init__(self, agents: dict):
        self.agents = agents

    @classmethod
    def from_yaml(cls, path: str) -> "AgentRegistry":
        content = Path(path).read_text()
        data = yaml.safe_load(content)
        return cls(agents=data.get("agents", {}))

    def get(self, key: str) -> dict | None:
        return self.agents.get(key)

    def list_agents(self) -> list[dict]:
        return [{"key": k, **v} for k, v in self.agents.items()]
