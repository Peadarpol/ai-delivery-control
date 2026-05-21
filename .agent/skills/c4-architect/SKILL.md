---
name: c4-architect
description: Expert skill for creating C4 model architecture diagrams (Context, Container, Component) using Mermaid and structured markdown documentation.
---

# C4 Architect Skill

## Overview
This skill enables the generation of comprehensive software architecture documentation following the **C4 model** (Context, Containers, Components, Code). It focuses on visualizing the system's static structure at different levels of abstraction using **Mermaid C4** syntax.

## Capabilities
1.  **Context Diagrams (Level 1)**: Visualize the system's interactions with users and external systems.
2.  **Container Diagrams (Level 2)**: Zoom in to show high-level technical building blocks (Web Apps, APIs, Databases).
3.  **Component Diagrams (Level 3)**: Decompose containers into logical components (Controllers, Services, Repositories).
4.  **Code Diagrams (Level 4)**: Represent UML class diagrams or entity relationships (ERD).

## Workflow

### Phase 1: Context Level (The "Big Picture")
**Goal**: Document who uses the system and what external systems it integrates with.
**Actions**:
- Identify all user personas: **Customer** (self-service portal), **Staff** (admin dashboard), **Manager** (reports), **System Admin** (platform config).
- Identify external systems: **Payment Gateway** (credit card processing), **Cloud Storage** (invoice/report storage), **Email Service** (transactional messaging), **Reverse Proxy** (load balancing/routing).
- Generate a `System Context Diagram` using `C4Context`.

### Phase 2: Container Level (High-Level Tech)
**Goal**: Show the deployable units and data flow.
**Actions**:
- Containers in scope: **Frontend Application** (web browser dashboard), **Mobile App** (user self-service), **Backend API** (port 8000), **Relational Database** (managed DB instance), **Object Storage** (media/exports), **Reverse Proxy** (SSL termination/routing).
- Document protocols: HTTPS (proxy → web frontend/API), JSON/HTTP (frontend → API), SQL/ORM (API → DB), API/SDK (API → Storage).
- Generate a `Container Diagram` using `C4Container`.

### Phase 3: Component Level (Internal Structure)
**Goal**: Show how the Backend API container is structured internally.
**Actions**:
- Analyse `src/` directory — layers of the system (e.g. Clean Architecture, Domain Driven Design).
- **Presentation**: routers, controllers, event listeners, templates.
- **Application**: use cases, services, DTOs, data access interfaces.
- **Domain**: pure business entities, value objects, domain rules.
- **Infrastructure**: database ORM implementations, third-party adapters (auth, payment).
- Generate a `Component Diagram` using `C4Component`.

## Mermaid Syntax Guide

### Context Diagram Example
```mermaid
C4Context
    title System Context — SaaS Platform

    Person(customer, "Customer", "Uses self-service portals and interfaces.")
    Person(staff, "Staff / Manager", "Manages records, schedules, and operations.")
    Person(sysadmin, "System Admin", "Configures platform, plans, and system rules.")

    System(app, "Application System", "Multi-tenant SaaS platform (API + Frontend).")

    System_Ext(payment, "Payment Gateway", "Card payment processing API.")
    System_Ext(storage, "Object Storage", "Invoice and report file storage.")
    System_Ext(email, "Email Service", "Transactional email delivery.")
    System_Ext(proxy, "Reverse Proxy", "Reverse proxy and routing.")

    Rel(customer, app, "Uses self-service functions", "HTTPS")
    Rel(staff, app, "Admin workflows and reports", "HTTPS")
    Rel(sysadmin, app, "Platform config", "HTTPS")
    Rel(app, payment, "Processes card payments", "HTTPS API")
    Rel(app, storage, "Stores documents / exports", "API")
    Rel(app, email, "Sends transactional emails", "SMTP/API")
    Rel(proxy, app, "Routes external traffic", "HTTP")
```

### Container Diagram Example
```mermaid
C4Container
    title Container Diagram — Application Architecture

    Person(staff, "Staff / Manager", "Admin dashboard interface")
    Person(customer, "Customer", "User interface / mobile portal")

    Container(proxy, "Reverse Proxy", "nginx", "Reverse proxy, routes external traffic to backend or frontend apps")
    Container(frontend, "Frontend Application", "Framework Client", "Web application for administrative and customer workflows")
    Container(api, "Backend API", "FastAPI / Node", "REST API — business logic, RBAC, background tasks")
    ContainerDb(database, "Relational Database", "PostgreSQL", "Stores application data, accounts, settings, audit logs")
    Container(storage, "Object Storage", "AWS S3 / GCP Cloud Storage", "File assets, exports, invoices")

    Rel(staff, proxy, "HTTPS")
    Rel(customer, proxy, "HTTPS")
    Rel(proxy, frontend, "HTTP", "Internal routing")
    Rel(proxy, api, "HTTP", "Internal routing")
    Rel(frontend, api, "JSON/HTTP")
    Rel(api, database, "SQL", "Database connection")
    Rel(api, storage, "API", "Storage SDK")
```

### Component Diagram Example
```mermaid
C4Component
    title Component Diagram — Backend Container (Clean Architecture)

    Container_Boundary(api_container, "Backend API") {
        Component(routers, "Controllers / Routers", "API framework routing", "HTTP endpoints — route only, no business logic")
        Component(deps, "Dependency Injector", "DI engine", "Injects services, repositories, and auth context")
        Component(services, "Application Services", "Service layer classes", "Use cases, workflow logic, transactions")
        Component(interfaces, "Repository Interfaces", "Interface / Protocols", "Abstraction of data access layer")
        Component(domain, "Domain Entities", "Plain Python / JS", "Pure business entities, domain models and invariants")
        Component(repos, "Repositories", "ORM Implementation", "Implements repository interfaces for specific database")
        Component(models, "ORM Models", "ORM library", "Database schema mapping/table classes")
        Component(eventbus, "Event Bus", "Pub/Sub", "Decouples side effects from core application flow")
    }

    Rel(routers, deps, "Uses")
    Rel(deps, services, "Injects dependencies")
    Rel(services, interfaces, "Uses interfaces")
    Rel(interfaces, repos, "Implemented by")
    Rel(repos, models, "Queries/Mutates")
    Rel(services, domain, "Uses/Returns entities")
    Rel(services, eventbus, "Publishes events")
```

## Instructions for Agent
When asked to perform architectural work:
1.  **Analyze**: Read the codebase to understand the current structure.
2.  **Plan**: Identify the level of detail required (Context -> Container -> Component).
3.  **Generate**: Create a markdown artifact (e.g., `docs/architecture/c4-context.md`) containing the Mermaid diagram and supporting text.
4.  **Verify**: Ensure the diagram accurately reflects the code.

## Output Templates

### Context Document Template
```markdown
# System Context

## Overview
[Description of the system]

## Personas
- **[Name]**: [Description]

## External Systems
- **[Name]**: [Description]

## Diagram
[Insert Mermaid C4Context]
```
