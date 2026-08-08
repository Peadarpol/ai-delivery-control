"""
tests/integration/test_contract_runner.py — Integration test for contract_test_runner.py (Tier 4, D1)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
agent_scripts = PROJECT_ROOT / ".agent" / "scripts"
if str(agent_scripts) not in sys.path:
    sys.path.insert(0, str(agent_scripts))

from contract_test_runner import main as runner_main, run_contract_test
import yaml


def test_dream_proposal_staleness_contract():
    """Verify that dream_proposal_staleness contract test executes and passes clean."""
    config_path = PROJECT_ROOT / ".agent" / "config" / "producer_consumer_contracts.yaml"
    assert config_path.exists(), "producer_consumer_contracts.yaml missing"

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    contracts = data.get("contracts", [])
    staleness_contract = next((c for c in contracts if c.get("name") == "dream_proposal_staleness"), None)
    assert staleness_contract is not None, "dream_proposal_staleness contract definition missing"

    passed, msg, timestamps = run_contract_test(staleness_contract, verbose=True)
    assert passed, f"Contract test failed with message:\n{msg}"
    assert "NOW_MINUS_25D" in timestamps
    assert "Open proposals :" in msg
