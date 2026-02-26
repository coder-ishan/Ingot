"""AGENT-05 enforcement and registry population tests."""
import ast
from pathlib import Path

AGENT_NAMES = ["orchestrator", "scout", "research", "matcher", "writer", "outreach", "analyst"]
AGENTS_DIR = Path(__file__).parent.parent / "src" / "ingot" / "agents"


def test_all_agents_in_registry():
    """Importing ingot.agents triggers self-registration of all 6 non-Orchestrator agents."""
    import ingot.agents  # noqa: F401 — triggers all register_agent() calls
    from ingot.agents.registry import AGENT_REGISTRY
    for name in ["scout", "research", "matcher", "writer", "outreach", "analyst"]:
        assert name in AGENT_REGISTRY, f"Agent '{name}' not in AGENT_REGISTRY"


def test_agent05_no_cross_agent_imports():
    """AGENT-05: No agent module imports from another agent module."""
    agent_modules = {f.stem for f in AGENTS_DIR.glob("*.py") if not f.stem.startswith("_")}

    violations = []
    for agent_file in AGENTS_DIR.glob("*.py"):
        if agent_file.stem.startswith("_"):
            continue
        tree = ast.parse(agent_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    # Check if importing from ingot.agents.<another_agent_module>
                    parts = node.module.split(".")
                    if (
                        len(parts) >= 3
                        and parts[0] == "ingot"
                        and parts[1] == "agents"
                        and parts[2] in agent_modules
                        and parts[2] != agent_file.stem
                        and parts[2] not in ("base", "registry", "exceptions")
                    ):
                        violations.append(
                            f"{agent_file.stem} imports from ingot.agents.{parts[2]}"
                        )

    assert not violations, f"AGENT-05 violated: {violations}"
