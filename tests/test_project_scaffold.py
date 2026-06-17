from pathlib import Path

import agent_tui


def test_package_imports_expected_v1_modules() -> None:
    """The package exposes the V1 module boundaries from issue #1."""
    assert Path(agent_tui.__file__).parent.name == "agent_tui"
    assert {"cli", "config", "agent", "llm", "safety"}.issubset(set(agent_tui.__all__))


def test_minimal_test_command_runs() -> None:
    """A minimal passing test proves pytest is configured correctly."""
    assert True
