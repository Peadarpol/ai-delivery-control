---
name: testing-patterns
description: Pytest testing patterns, factory functions, mocking strategies, and TDD workflow. Use when writing unit tests, creating test factories, following TDD red-green-refactor cycle, or determining test coverage priorities.
requires-context: [docs/decisions/business_rules.md, docs/architecture/ARCHITECTURE.md]
---

# Testing Patterns and Utilities — Application Edition

## Testing Philosophy

**Test-Driven Development (TDD):**
- Write failing test FIRST.
- Implement minimal code to pass.
- Refactor after green.
- Never write production code without a failing test.
- See `test-driven-development` skill for the full Iron Law and Red-Green-Refactor cycle.

**Behavior-Driven Testing:**
- Test behavior, not implementation.
- Focus on public APIs (Services/Routers) and business requirements.
- Avoid testing implementation details (private methods).
- Use descriptive test names: `test_<action>_<condition>_<expected_outcome>`.

**Factory Pattern:**
- Create `get_mock_x(**overrides)` functions.
- Provide sensible defaults.
- Keep tests DRY and maintainable.

---

## Coverage Priority Order

When deciding what to test next, work through this priority stack:

| Priority | Target | Coverage Goal |
|----------|--------|---------------|
| 🔴 1 | Critical business logic (domain constraints, RBAC, payments) | 90%+ |
| 🟠 2 | Complex algorithms and state machines (workflows, state transitions) | 85%+ |
| 🟡 3 | Edge cases that have previously caused bugs (see `golden_dataset.yaml`) | 100% of known cases |
| 🔵 4 | Project invariant checks (no broad `except`, UoW commit, tenant isolation) | All new services |
| 🟢 5 | Public API surfaces (FastAPI routers) | 80%+ |
| 💡 6 | Utility and helper functions | 70%+ |

**Overall target**: ≥80% coverage on `src/` ([BUSINESS_RULE_PLACEHOLDER]). Coverage below 70% blocks merge.

---

## Factory Pattern

Use simple factory functions to create consistent test data without duplication.

```python
from pydantic import BaseModel
from src.domain.enums.user_roles import UserRole

class User(BaseModel):
    id: int
    name: str
    role: UserRole   # Always use the enum, never raw strings

def get_mock_user(**overrides) -> User:
    defaults = {
        "id": 1,
        "name": "John Doe",
        "role": UserRole.STAFF,
    }
    return User(**{**defaults, **overrides})

# Usage in tests
def test_manager_access_allowed():
    user = get_mock_user(role=UserRole.GYM_MANAGER)
    assert user.role == UserRole.GYM_MANAGER
```

> **Tip**: For complex SQLAlchemy models with relationships, use `factory_boy`
> to manage persistence and FK constraints automatically.

---

## Stateful Testing with FakeUnitOfWork

Prefer `FakeUnitOfWork` over deep repository mocking for service-layer tests.
This verifies actual state transitions rather than mock call counts.

```python
# tests/unit/services/test_booking_service.py
from tests.utils.fake_unit_of_work import FakeUnitOfWork
from src.application.services.booking_service import BookingService
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta

future_date = datetime.now(timezone.utc) + timedelta(hours=3)

def test_cancel_booking_success():
    # Arrange
    uow = FakeUnitOfWork()
    uow.sessions.entities[1] = SimpleNamespace(id=1, schedule_time=future_date)
    uow.sessions.create_booking(SimpleNamespace(session_id=1, member_id=101))
    service = BookingService(uow=uow)

    # Act
    service.cancel_booking(booking_id=1)

    # Assert
    assert uow.sessions.get_booking_by_id(1).status == "cancelled"
    assert uow.committed is True   # ← Always verify the commit happened
```

**Always assert `uow.committed is True`** after a successful write operation.
A service that fails to commit is silently discarding work.

---

## Mocking Patterns

Use `unittest.mock` / `pytest-mock` to isolate tests from external dependencies.

```python
# Mocking a service dependency
def test_member_service_sends_welcome_email(mocker):
    mock_bus = mocker.MagicMock()
    uow = FakeUnitOfWork()
    service = MemberService(uow=uow, bus=mock_bus)

    service.create_member(MemberCreate(email="j@example.com", ...))

    mock_bus.publish.assert_called_once()
    event = mock_bus.publish.call_args[0][0]
    assert event.member_email == "j@example.com"
```

**Rules:**
- Mock external dependencies (email, payment gateway, S3) — not the code under test.
- Use `FakeUnitOfWork` rather than mocking individual repositories.
- Verify mock interactions only when the interaction itself is the behaviour being tested.

---

## Branch Isolation in Integration Tests

All integration tests that write to the database must use a scoped `branch_id`
to prevent cross-tenant data leakage between test cases.

```python
# conftest.py
@pytest.fixture
def test_branch(db_session):
    branch = Branch(name="Test Branch", business_id=1)
    db_session.add(branch)
    db_session.commit()
    return branch

@pytest.fixture
def scoped_uow(db_session, test_branch):
    """UnitOfWork pre-scoped to the test branch."""
    uow = UnitOfWork(db_session)
    uow.set_branch_context(test_branch.id)
    return uow
```

Never share `branch_id=1` across all tests — isolation prevents false passes
caused by data left behind by a previous test.

---

## Testing Business Invariants

Key project invariants that **must** have dedicated tests:

```python
# [BUSINESS_RULE_PLACEHOLDER]: No entity overlap / conflict
def test_create_entity_raises_when_conflict_exists():
    uow = FakeUnitOfWork()
    uow.entities.entities[1] = active_entity_fixture()
    service = EntityService(uow=uow)
    with pytest.raises(EntityConflictError):
        service.create_entity(conflicting_entity_data())

# [BUSINESS_RULE_PLACEHOLDER]: Numeric values stored precisely
def test_transaction_stores_precise_value():
    tx = TransactionCreate(amount_cents=1999, ...)
    assert isinstance(tx.amount_cents, int)
    assert tx.amount_cents == 1999

# [BUSINESS_RULE_PLACEHOLDER]: Soft-delete, never hard-delete
def test_delete_entity_sets_is_deleted_flag():
    uow = FakeUnitOfWork()
    uow.entities.entities[1] = entity_fixture()
    service = EntityService(uow=uow)
    service.delete_entity(1)
    assert uow.entities.entities[1].is_deleted is True  # NOT removed from store

# RBAC: require_permission blocks unauthorised access
def test_endpoint_returns_403_for_insufficient_role(client, token):
    response = client.delete("/entities/1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

# Exception handling: broad except must re-raise
def test_service_does_not_swallow_infrastructure_error(mocker):
    uow = FakeUnitOfWork()
    uow.entities.get_by_id = mocker.MagicMock(side_effect=DatabaseError("db down"))
    service = EntityService(uow=uow)
    with pytest.raises(Exception):   # must propagate, not be swallowed
        service.get_entity(1)
```

---

## Mutation Testing (High-Confidence QA)

Mutation testing verifies that tests actually catch bugs. Surviving mutants
indicate weak assertions.

**Tool**: `mutmut`

```bash
# Target critical business logic only (fast feedback)
mutmut run --paths-to-mutate src/application/services/some_service.py

# View surviving mutants
mutmut results

# Inspect a specific survivor
mutmut show 42
```

**Target**: mutation score ≥ 80% on `src/application/services/`.
If a mutant survives, write a new test case specifically targeting the
mutated logic before marking the feature complete.

---

## Test Structure (Pytest)

```python
import pytest
from tests.utils.fake_unit_of_work import FakeUnitOfWork

class TestMemberService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.uow = FakeUnitOfWork()
        self.service = MemberService(uow=self.uow)

    def test_get_member_not_found_raises_error(self):
        self.uow.members.entities = {}   # empty store
        with pytest.raises(MemberNotFoundError):
            self.service.get_member(999)

    def test_create_member_commits_and_returns_dto(self):
        result = self.service.create_member(
            MemberCreate(first_name="Jo", last_name="Doe", email="jo@example.com", ...)
        )
        assert result.email == "jo@example.com"
        assert self.uow.committed is True
```

---

## Test Type Selection

| Type | When to use | Speed |
|------|-------------|-------|
| Unit (FakeUoW) | Service-layer logic, business rules, state transitions | Fast |
| Unit (mock) | Adapter boundaries (email, payment gateway, S3) | Fast |
| Integration | Repository → DB round-trips, Alembic migrations, multi-service flows | Medium |
| API / TestClient | FastAPI router wiring, auth header propagation, status codes | Medium |
| BDD / Gherkin | High-value user journeys (member check-in, contract creation) | Medium |
| Performance | p95 latency benchmarks (≥ weekly, not on every commit) | Slow |

---

## Best Practices

1. **Arrange-Act-Assert** — keep steps visually distinct.
2. **One behaviour per test** — avoid god tests that assert many unrelated things.
3. **Stateful verification** — prefer `FakeUnitOfWork` state assertions over mock call counts.
4. **Always assert `uow.committed`** after write operations.
5. **No `time.sleep()`** — use `anyio` timeouts or condition-based waiting (see `systematic-debugging/condition-based-waiting.md`).
6. **No production data** — use factories and fixtures; never seed from a real database.
7. **Enum types in factories** — use `UserRole.STAFF`, not `"staff"`.
8. **Mutation score target** — ≥80% on critical services.

## Running Tests

```bash
# Full suite
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing

# Specific test file
pytest tests/unit/services/test_member_service.py -v

# Mutation tests (critical services only)
mutmut run --paths-to-mutate src/application/services/some_service.py
```
