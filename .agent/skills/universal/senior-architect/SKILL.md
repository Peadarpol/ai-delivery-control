---
name: senior-architect
description: Comprehensive software architecture skill for designing scalable systems using Clean Architecture/DDD. Includes dependency analysis for layer enforcement.
skill_type: universal
version: 1.0.0
---

# Senior Architect

## Overview

Maintain structural integrity using Clean Architecture and Domain-Driven Design (DDD). This skill provides tools to verify that dependencies flow towards the domain and that layers remain isolated.

## Main Capabilities

This skill provides automated structural verification for the project:

```bash
# Script: Dependency Analyzer
# Checks for layer violations (e.g., domain importing infrastructure)
python .agent/skills/senior-architect/scripts/dependency_analyzer.py src/
```

## Architecture Layers

| Layer | Responsibility | Allowed Dependencies |
| :--- | :--- | :--- |
| **Domain** | Business logic, Entities, Aggregates | None (External libraries only) |
| **Application** | Use cases, Services, DTOs, **IUnitOfWork** | Domain |
| **Infrastructure** | Database, External APIs, **UnitOfWorkImpl** | Domain, Application |
| **Presentation** | UI, API | Application, Domain |

## Dependency Rules

1. **Inner Circle First**: Nothing in the `domain/` directory should import from `application/`, `infrastructure/`, or `presentation/`.
2. **Persistence Ignorance**: Entities should not know how they are stored (No DB-specific ORM imports in `domain/`).
3. **Repository Pattern**: Infrastructure implements interfaces defined in the domain/application layers.

## Best Practices

- **Bounded Contexts**: Keep related models within their functional modules.
- **DTOs vs Entities**: Always use Pydantic DTOs for data transfer across layer boundaries.
- **Protocol-Based Type Safety**: Use domain protocols to decouple the service layer from concrete model implementations. This ensures type safety and compliance.
- **Strict Exception Handling**: Refuse any architecture where broad exceptions are suppressed or ignored. Ensure all exception blocks are accompanied by a `raise`.
- **Unit of Work Pattern**: Use `IUnitOfWork` (in application layer) to group multiple operations into a single transaction. Services should depend on `IUnitOfWork`, not individual repositories.
- **Dependency Injection**: Use framework-specific dependency injection to inject `IUnitOfWork` into services.
- **Event-Driven Decoupling**: Services focus on *Decision Making* and *State Changes*. Side effects (Notifications, Analytics, Integrations) belong in *Event Handlers*.
- **Layer Rule**: Handlers live in the application layer and subscribe in the infrastructure event bus layer.

## New Architectural Enforcement (2026)

- **Linter**: Use `python .agent/skills/senior-architect/scripts/architecture_checks.py` for automated boundary checks.
- **DTO Isolation**: Strictly enforce that `domain/` and `application/` are free of `presentation/` and web framework imports.
- **Mypy Strictness**: Use static checks for the domain and application layers.
- **Async Safety**: Use proper event loop policy management in test configurations.

## Troubleshooting

If the `dependency_analyzer.py` reports a violation:
1. Identify the file and the "forbidden" import.
2. If it's a cross-layer dependency, consider introducing an **Interface/Protocol** in the inner layer and implementing it in the outer layer.
3. If it's a circular dependency within a layer, refactor shared logic into a `common` or `utils` module.
4. If a Service is importing another Service purely for a side effect, refactor to use a **Domain Event** instead.
