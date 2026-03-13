from pathlib import Path
from arxi.agents.registry import AgentRegistry

AGENTS_YAML = str(Path(__file__).parent.parent.parent / "agents.yaml")

def test_load_agents():
    registry = AgentRegistry.from_yaml(AGENTS_YAML)
    assert "intake-agent" in registry.agents
    agent = registry.get("intake-agent")
    assert agent["name"] == "Rx Intake Agent"
    assert agent["human_gate"] == "pharmacist_review"

def test_agent_not_found():
    registry = AgentRegistry.from_yaml(AGENTS_YAML)
    assert registry.get("nonexistent") is None
