"""
Unit tests for configuration migration from v1.2.0.1 to v1.3.0.
"""

from pathlib import Path
import tempfile
import pytest

from bootstrap.migrations.v1_2_0_1_to_v1_3_0 import MigrationV1_2_0_1_to_V1_3_0

@pytest.fixture
def temp_config_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        # Seed it with a mini valid config.yaml
        config_path.write_text("""# Mini config
project:
  name: "test-proj"
framework:
  version: "1.2.0.1"
spec_gate:
  specs_path: docs/planning/specs/
""", encoding="utf-8")
        yield config_path

def test_migration_v1_2_0_1_to_v1_3_0_success(temp_config_file):
    migrator = MigrationV1_2_0_1_to_V1_3_0()
    
    # Run upgrade migration
    migrator.migrate(temp_config_file)
    
    content = temp_config_file.read_text(encoding="utf-8")
    assert 'version: "1.3.0"' in content
    assert "traceability:" in content
    assert "specs_path: docs/planning/specs/" in content
    assert "acceptance_gate:" in content
    assert "base_branch: main" in content
    
    # A second migrate() call on an already-migrated file triggers the version-match guard
    with pytest.raises(ValueError, match="expected version"):
        migrator.migrate(temp_config_file)
    
    # Run downgrade migration
    migrator.downgrade(temp_config_file)
    content_down = temp_config_file.read_text(encoding="utf-8")
    assert 'version: "1.2.0.1"' in content_down
    assert "traceability:" not in content_down
    assert "acceptance_gate:" not in content_down
