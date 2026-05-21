#!/usr/bin/env python3
"""
Fixture Generator

Generates pytest fixtures from SQLAlchemy models.

Usage:
    poetry run python .agent/skills/python-testing/scripts/generate_fixtures.py Member Contract
"""

import sys
from pathlib import Path


def generate_fixture_code(model_name: str) -> str:
    """Generate fixture code for a model."""
    snake_name = "".join(
        f"_{c.lower()}" if c.isupper() and i > 0 else c.lower()
        for i, c in enumerate(model_name)
    )

    return f'''
@pytest.fixture
def {snake_name}(db_session, branch) -> {model_name}:
    """Create a test {model_name}."""
    {snake_name} = {model_name}(
        branch_id=branch.id,
        # Add required fields here
    )
    db_session.add({snake_name})
    db_session.commit()
    db_session.refresh({snake_name})
    return {snake_name}


@pytest.fixture
def {snake_name}_factory(db_session, branch):
    """Factory fixture for creating multiple {model_name} instances."""
    created = []

    def _create(**kwargs):
        defaults = {{
            "branch_id": branch.id,
            # Add default field values here
        }}
        defaults.update(kwargs)

        obj = {model_name}(**defaults)
        db_session.add(obj)
        db_session.commit()
        db_session.refresh(obj)
        created.append(obj)
        return obj

    yield _create

    # Cleanup
    for obj in created:
        db_session.delete(obj)
    db_session.commit()
'''


def generate_conftest_template(model_names: list) -> str:
    """Generate complete conftest.py with fixtures."""
    header = '''"""
Generated pytest fixtures for test models.

Usage:
    Copy relevant fixtures to tests/conftest.py
"""

import pytest
from datetime import datetime, date
from decimal import Decimal

# Import your models
# from src.infrastructure.database.models import Member, Contract, Branch

'''

    fixtures = []

    # Base fixtures
    fixtures.append('''
@pytest.fixture
def db_session():
    """Database session fixture - implement based on your DB setup."""
    # Option 1: Use test database
    # from src.infrastructure.database.connection import get_test_session
    # session = get_test_session()

    # Option 2: Use in-memory SQLite
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    # engine = create_engine("sqlite:///:memory:")
    # Session = sessionmaker(bind=engine)
    # session = Session()

    # yield session
    # session.rollback()
    # session.close()
    pass


@pytest.fixture
def branch(db_session):
    """Create a test branch for multi-tenancy."""
    # branch = Branch(name="Test Branch", gym_business_id=1)
    # db_session.add(branch)
    # db_session.commit()
    # return branch
    pass
''')

    for model_name in model_names:
        fixtures.append(generate_fixture_code(model_name))

    return header + "\n".join(fixtures)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_fixtures.py ModelName1 ModelName2 ...")
        print("\nExample:")
        print("  python generate_fixtures.py Member Contract Invoice")
        print("\nThis will generate pytest fixtures for the specified models.")
        return

    model_names = sys.argv[1:]

    print("=" * 60)
    print("PYTEST FIXTURE GENERATOR")
    print("=" * 60)
    print(f"\nGenerating fixtures for: {', '.join(model_names)}")

    output = generate_conftest_template(model_names)

    # Write to file
    output_file = Path("generated_fixtures.py")
    output_file.write_text(output)

    print(f"\n✅ Generated fixtures saved to: {output_file}")
    print("\nCopy the relevant fixtures to your tests/conftest.py")

    # Also print to console
    print("\n" + "-" * 60)
    print("GENERATED CODE:")
    print("-" * 60)
    print(output)


if __name__ == "__main__":
    main()
