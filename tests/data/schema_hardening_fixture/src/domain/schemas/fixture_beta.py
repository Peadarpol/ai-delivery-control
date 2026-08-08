"""Fixture schema module — whitelisted in .agent/config.yaml's schema_hardening.whitelist.

Fixture-only. Second whitelisted module, present so the whitelist has more than one
member and a partial drop is distinguishable from a total one.
"""


class FixtureBeta:  # stands in for a `class FixtureBeta(BaseModel):` declaration
    """Placeholder for a second legacy, whitelist-exempt schema."""

    table_name = "fixture_table_beta"
