"""Fixture schema module — whitelisted in .agent/config.yaml's schema_hardening.whitelist.

Fixture-only. Deliberately uses the un-hardened `BaseModel` shape that
enforce_hardened_schemas.py flags, so its presence on the whitelist is meaningful
rather than decorative.
"""


class FixtureAlpha:  # stands in for a `class FixtureAlpha(BaseModel):` declaration
    """Placeholder for a legacy, whitelist-exempt schema."""

    table_name = "fixture_table_alpha"
