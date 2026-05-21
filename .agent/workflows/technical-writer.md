---
description: Technical documentation and API documentation workflow
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Technical documentation and API documentation workflow
---

# /docs - Technical Writer Workflow

## Trigger
Use when: writing READMEs, API documentation, user guides, or technical specifications.

## Mindset
- **Audience first** - who is reading this and what do they need?
- **Show, don't tell** - examples > explanations
- **Keep it fresh** - outdated docs are worse than no docs
- **Progressive disclosure** - start simple, go deep when needed

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all documentation generation, API documentation, and changelog management tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human Technical Writer)**: 10-11 hours
- **AI Generated**: 23 min
- **User Time**: 25 min (review results)

### Auto-Generate API Documentation

**AI Input**: FastAPI route definitions

```python
# {{PATH_API_ROUTES}}/members.py
@router.post("/members", response_model=MemberResponse, status_code=201)
async def create_member(
    member: MemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new gym member."""
    if not current_user.has_permission("create_member"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check for duplicate email
    existing = db.query(Member).filter(Member.email == member.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_member = Member(**member.dict())
    db.add(new_member)
    db.commit()
    return new_member
```

**AI Auto-Generated Documentation** (8 min):

````markdown
## Create Member

Create a new gym member in the system.

### Endpoint
`POST /api/members`

### Authentication
**Required**: Yes (Bearer token)

**Permissions**: User must have `create_member` permission

### Request

**Headers**:
| Header | Value | Required |
|--------|-------|----------|
| Authorization | Bearer {access_token} | Yes |
| Content-Type | application/json | Yes |

**Body** (JSON):
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "date_of_birth": "1990-05-15",
  "emergency_contact": {
    "name": "Jane Doe",
    "phone": "+1234567891"
  }
}
```

**Schema**: `MemberCreate`
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| first_name | string | Yes | 1-50 characters |
| last_name | string | Yes | 1-50 characters |
| email | string (email) | Yes | Valid email format, unique |
| phone | string | No | Phone number format |
| date_of_birth | date | Yes | ISO 8601 format, age ≥16 |
| emergency_contact | object | No | See EmergencyContact schema |

### Response

**Success (201 Created)**:
```json
{
  "id": 123,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "date_of_birth": "1990-05-15",
  "status": "active",
  "created_at": "2023-12-15T10:30:00Z",
  "emergency_contact": {
    "name": "Jane Doe",
    "phone": "+1234567891"
  }
}
```

**Error Responses**:

| Status Code | Error | Cause | Solution |
|-------------|-------|-------|----------|
| 400 | Email already registered | Duplicate email in database | Use different email or update existing member |
| 401 | Invalid authentication credentials | Missing or invalid token | Obtain valid token via POST /api/token |
| 403 | Insufficient permissions | User lacks create_member permission | Contact administrator for permission |
| 422 | Validation error | Invalid request body | Check field constraints in schema |

**Example Error (400)**:
```json
{
  "detail": "Email already registered"
}
```

### Examples

**cURL**:
```bash
curl -X POST https://api.example.com/api/members \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "date_of_birth": "1990-05-15"
  }'
```

**Python (requests)**:
```python
import requests

url = "https://api.example.com/api/members"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp...",
    "Content-Type": "application/json"
}
payload = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "date_of_birth": "1990-05-15"
}

response = requests.post(url, json=payload, headers=headers)
if response.status_code == 201:
    member = response.json()
    print(f"Created member: {member['id']}")
else:
    print(f"Error: {response.json()['detail']}")
```

**JavaScript (fetch)**:
```javascript
const response = await fetch('https://api.example.com/api/members', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    first_name: 'John',
    last_name: 'Doe',
    email: 'john.doe@example.com',
    phone: '+1234567890',
    date_of_birth: '1990-05-15'
  })
});

const member = await response.json();
console.log('Created member:', member.id);
```

### Business Logic

**Validation Rules**:
- Email must be unique across all members
- Age must be ≥16 years (calculated from date_of_birth)
- Phone number format validated if provided

**Side Effects**:
- Member automatically assigned "active" status
- Welcome email sent to member.email (async)
- Audit log entry created

**Related Endpoints**:
- `GET /api/members/{id}` - Retrieve member details
- `PUT /api/members/{id}` - Update member
- `DELETE /api/members/{id}` - Soft-delete member
````

### Auto-Generate README.md

**AI Input**: Project structure + package.json/requirements.txt

**AI Auto-Generated README** (5 min):

```markdown
# Gym Management System

A comprehensive gym management system with member management, contract tracking, check-ins, PT session booking, and point-of-sale functionality.

## Quick Start

```bash
# Clone repository
git clone https://github.com/yourorg/gym-management-system.git
cd gym-management-system

# Install dependencies
poetry install

# Set up database
alembic upgrade head

# Run application
{{CAPABILITIES_RUN_BACKEND}}
```

Visit http://localhost:8000/docs for API documentation.

## Features

- **Member Management**: Register, update, and track gym members
- **Contract Management**: Create and manage membership contracts
- **Check-in System**: Track member check-ins with access control
- **PT Session Booking**: Schedule personal training sessions
- **Point of Sale**: Sell products and services
- **Staff Management**: Role-based access control for staff
- **Equipment Tracking**: Monitor gym equipment inventory

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose)
- **Testing**: Pytest + Playwright
- **Frontend**: Streamlit (admin dashboard)
- **Deployment**: AWS (EC2 + RDS)

## Project Structure

```
{{PATH_PROJECT_ROOT}}/
├── {{PATH_SOURCE_ROOT}}/
│   ├── api/              # FastAPI routes
│   ├── domain/           # Business logic & models
│   ├── infrastructure/   # Database & external services
│   └── repositories/     # Data access layer
├── {{PATH_TEST_ROOT}}/                # Unit, integration, E2E tests
├── bdd/                  # BDD feature files
├── {{PATH_DOCS}}/                 # Documentation
├── migrations/           # Alembic database migrations
└── .agent/workflows/     # Development workflows
```

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Poetry (dependency management)

### Setup

1. **Create virtual environment**:
   ```bash
   poetry install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Initialize database**:
   ```bash
   {{CAPABILITIES_DB_MIGRATE}}
   {{CAPABILITIES_DB_SEED}}
   ```

4. **Run tests**:
   ```bash
   {{CAPABILITIES_TEST_RUN_ALL}}
   ```

5. **Start server**:
   ```bash
   {{CAPABILITIES_RUN_BACKEND}}
   ```

## Configuration

**Environment Variables** (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://localhost/gym_app |
| SECRET_KEY | JWT signing key | (required) |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiration | 15 |
| REFRESH_TOKEN_EXPIRE_DAYS | Refresh token expiration | 7 |

## API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
{{CAPABILITIES_TEST_RUN_ALL}}

# Run with coverage
{{CAPABILITIES_TEST_COVERAGE}} --cov-report=html

# Run specific test types
{{CAPABILITIES_TEST_RUN_UNIT}}
{{CAPABILITIES_TEST_RUN_INTEGRATION}}
{{CAPABILITIES_TEST_RUN_UI}}
```

## Deployment

See [DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) for AWS deployment instructions.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Run tests (`{{CAPABILITIES_TEST_RUN_ALL}}`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details
```

### Auto-Generate CHANGELOG.md

**AI Input**: Git commit history

```bash
# AI analyzes git log since last release
git log v1.2.0..HEAD --pretty=format:"%h|%s|%an|%ad" --date=short
```

**AI Auto-Generated Changelog** (2 min):

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- PT session booking feature (#142)
  - Members can view trainer availability
  - Book sessions through mobile app
  - Trainers can manage availability blocks
  - Email notifications for bookings/cancellations
- Performance optimizations (#156)
  - Database connection pool increased to 50
  - Eager loading for member contracts
  - Composite index on checkins table
- Security enhancements (#158)
  - Fixed SQL injection in member search
  - Added JWT signature verification
  - Updated dependencies (requests, pillow, sqlalchemy)

### Changed
- Improved check-in validation logic (#145)
- Updated FastAPI to 0.104.1 (#150)
- Optimized member contract queries (N+1 fix) (#156)

### Fixed
- Memory leak in checkin history endpoint (#159)
- Token validation not checking signature (#158)
- Duplicate email validation on member creation (#148)

### Security
- **CRITICAL**: Fixed authentication bypass vulnerability (#158)
- **HIGH**: Fixed SQL injection in search endpoints (#158)
- Updated 6 dependencies with known vulnerabilities (#158)

## [1.2.0] - 2023-12-10

### Added
- Product management module (#134)
  - CRUD operations for gym products
  - Product categories and pricing
  - Inventory tracking

### Changed
- Migrated to Pydantic V2 (#138)
- Updated database schema for soft deletes (#140)

### Fixed
- Contract expiry status sync (#137)
- Dashboard metrics calculation (#139)

## [1.1.0] - 2023-11-25

### Added
- Equipment management (#120)
- Workout tracking for members (#125)
- Staff role-based permissions (#128)

### Fixed
- Check-in duplicate prevention (#122)
- Session timeout issues (#126)
```

### Confidence-Based Review

**AI auto-commits** (confidence ≥0.95):
- API docs from FastAPI routes (structure is clear)
- README from project structure
- Changelog from git commits (factual)

**User review required** (confidence <0.95):
- Business context and examples (AI may misunderstand domain)
- Complex workflows or edge cases
- Marketing copy or user-facing explanations

---

## Phase 1: Audience Analysis **Skill**: /technical-writer

1. Identify the reader:

| Audience | Needs | Tone | Detail Level |
|----------|-------|------|--------------|
| New developer | Getting started | Friendly | Step-by-step |
| API consumer | Endpoints, params | Precise | Reference |
| End user | How to use features | Simple | Task-based |
| Ops team | Deployment, config | Technical | Exhaustive |

2. Define the document purpose:
   - [ ] What question does this answer?
   - [ ] What action should the reader take after reading?
   - [ ] What can be omitted?

---

## Phase 2: Document Structure **Skill**: /technical-writer

3. README.md template:
```markdown
# Project Name

Brief description (1-2 sentences)

## Quick Start
Minimal steps to get running

## Features
- Feature 1
- Feature 2

## Installation
Detailed setup instructions

## Usage
Common use cases with examples

## Configuration
Environment variables and options

## Contributing
How to contribute

## License
License information
```

4. Update CHANGELOG.md:
   - [ ] Add entry under `[Unreleased]` or new version header.
   - [ ] Categorize: Added, Changed, Deprecated, Removed, Fixed, Security.

4. Update Static Documentation (Gatekeeper):
   > [!IMPORTANT]
   > Swagger/OpenAPI is NOT enough. You must update static files that developers read.
   - [ ] Check if `docs/api/API.md` exists. If yes, update it with new endpoints.
   - [ ] Check if `README.md` needs updates (new features, setup steps).
   - [ ] Check if `docs/technical/Technical_Specification.md` needs updates (data models, architecture).

5. API documentation template (for docs/api/API.md):
```markdown
## Endpoint Name

Brief description

### Request
`METHOD /path`

**Headers**
| Header | Value | Required |
|--------|-------|----------|
| Authorization | Bearer {token} | Yes |

**Parameters**
| Name | Type | Description | Required |
|------|------|-------------|----------|
| id | integer | Resource ID | Yes |

**Body**
\`\`\`json
{
  "field": "value"
}
\`\`\`

### Response

**Success (200)**
\`\`\`json
{
  "data": {...}
}
\`\`\`

**Error (4xx)**
\`\`\`json
{
  "error": "message"}
\`\`\`

### Examples

**cURL**:
\`\`\`bash
curl -X POST https://api.example.com/members \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR..." \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890"
  }'
\`\`\`

**Python (requests)**:
\`\`\`python
import requests

url = "https://api.example.com/members"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR...",
    "Content-Type": "application/json"
}
payload = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890"
}

response = requests.post(url, json=payload, headers=headers)

if response.status_code == 201:
    member = response.json()
    print(f"Created member: {member['id']}")
else:
    print(f"Error: {response.status_code} - {response.json()['detail']}")
\`\`\`

**JavaScript (fetch)**:
\`\`\`javascript
const url = "https://api.example.com/members";
const headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR...",
    "Content-Type": "application/json"
};
const payload = {
    first_name: "John",
    last_name: "Doe",
    email: "john.doe@example.com",
    phone: "+1234567890"
};

fetch(url, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(payload)
})
.then(response => {
    if (!response.ok) {
        throw new Error(\`HTTP error! status: \${response.status}\`);
    }
    return response.json();
})
.then(data => console.log("Created member:", data.id))
.catch(error => console.error("Error:", error));
\`\`\`

### Error Responses

**Validation Error (422)**:
\`\`\`json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
\`\`\`

**Authentication Error (401)**:
\`\`\`json
{
  "detail": "Invalid authentication credentials"
}
\`\`\`

**Authorization Error (403)**:
\`\`\`json
{
  "detail": "Not enough permissions"
}
\`\`\`
```

4.5. **Authentication Flow Documentation**:

```markdown
## Authentication

### Overview
The API uses JWT (JSON Web Token) for authentication. You must obtain an access token before making authenticated requests.

### Token Lifecycle
- **Access Token**: Valid for 15 minutes
- **Refresh Token**: Valid for 7 days

### Getting a Token

**Endpoint**: \`POST /api/token\`

**Request**:
\`\`\`bash
curl -X POST https://api.example.com/api/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=YourSecurePassword"
\`\`\`

**Response (200 OK)**:
\`\`\`json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp...",
  "token_type": "bearer",
  "expires_in": 900
}
\`\`\`

### Using the Token

Include the access token in the \`Authorization\` header:

\`\`\`bash
curl https://api.example.com/api/members \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp..."
\`\`\`

### Refreshing the Token

When the access token expires, use the refresh token to get a new one:

**Endpoint**: \`POST /api/refresh\`

\`\`\`bash
curl -X POST https://api.example.com/api/refresh \
  -H "Authorization: Bearer <refresh_token>"
\`\`\`

**Response (200 OK)**:
\`\`\`json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp...",
  "token_type": "bearer",
  "expires_in": 900
}
\`\`\`

### Error Handling

| Status Code | Error | Solution |
|-------------|-------|----------|
| 401 | Invalid credentials | Check username/password |
| 401 | Token expired | Use refresh token |
| 401 | Invalid token | Re-authenticate |
| 422 | Missing credentials | Provide username and password |

### Security Best Practices
- Store tokens securely (never in localStorage)
- Use HTTPS for all API requests
- Implement token rotation
- Set reasonable expiration times
```

---

## Phase 2.5: Diagrams and Visualizations **Skill**: /technical-writer

5. **Mermaid Diagram Templates**:

Use Mermaid for version-controllable, text-based diagrams.

**A. Flowcharts** (Process Logic):
````markdown
\`\`\`mermaid
flowchart TD
    A[User requests member data] --> B{Authenticated?}
    B -->|No| C[Return 401]
    B -->|Yes| D{Authorized?}
    D -->|No| E[Return 403]
    D -->|Yes| F[Query Database]
    F --> G{Member exists?}
    G -->|No| H[Return 404]
    G -->|Yes| I[Return member data]
\`\`\`
````

**B. Sequence Diagrams** (API Interactions):
````markdown
\`\`\`mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant DB as Database
    participant R as Redis Cache

    C->>A: POST /api/token (username, password)
    A->>DB: Verify credentials
    DB-->>A: User found
    A->>R: Store session token
    R-->>A: Token cached
    A-->>C: 200 OK (access_token, refresh_token)

    Note over C,A: Subsequent authenticated requests
    C->>A: GET /api/members (Bearer token)
    A->>R: Verify token in cache
    R-->>A: Token valid
    A->>DB: SELECT * FROM members
    DB-->>A: Members data
    A-->>C: 200 OK (members list)
\`\`\`
````

**C. Entity Relationship Diagrams** (Database Schema):
````markdown
\`\`\`mermaid
erDiagram
    MEMBER ||--o{ CONTRACT : has
    MEMBER ||--o{ CHECKIN : performs
    MEMBER ||--o{ WORKOUT_SESSION : logs
    CONTRACT ||--o{ TRANSACTION : generates
    STAFF ||--o{ PT_SESSION : conducts
    MEMBER ||--o{ PT_SESSION : books

    MEMBER {
        int id PK
        string first_name
        string last_name
        string email UK
        date dob
        string status
        boolean is_deleted
    }

    CONTRACT {
        int id PK
        int member_id FK
        date start_date
        date end_date
        string contract_type
        decimal price
    }
\`\`\`
````

**D. Architecture Diagrams** (System Overview):
````markdown
\`\`\`mermaid
graph TB
    subgraph "Client Layer"
        UI[Streamlit UI]
        Kiosk[Kiosk App]
    end

    subgraph "API Layer"
        FastAPI[FastAPI Server]
        Auth[Auth Middleware]
    end

    subgraph "Service Layer"
        MemberSvc[Member Service]
        ContractSvc[Contract Service]
        CheckinSvc["Check-in Service"]
    end

    subgraph "Data Layer"
        Repo[Repositories]
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis Cache)]
    end

    UI --> FastAPI
    Kiosk --> FastAPI
    FastAPI --> Auth
    Auth --> MemberSvc
    Auth --> ContractSvc
    Auth --> CheckinSvc
    MemberSvc --> Repo
    ContractSvc --> Repo
    CheckinSvc --> Repo
    Repo --> PostgreSQL
    Auth --> Redis
\`\`\`
````

**E. State Diagrams** (Feature States):
````markdown
\`\`\`mermaid
stateDiagram-v2
    [*] --> Active: Contract created
    Active --> Suspended: Payment failed
    Active --> Expired: End date reached
    Suspended --> Active: Payment received
    Suspended --> Cancelled: Grace period expired
    Expired --> Renewed: Renew contract
    Expired --> [*]
    Cancelled --> [*]
    Renewed --> Active
\`\`\`
````

**Diagram Best Practices**:
- [ ] Keep diagrams simple (max 10-15 nodes)
- [ ] Use consistent colors/styles across all diagrams
- [ ] Add legend if using custom notation
- [ ] Quote node labels containing special characters: `id["Label (Info)"]`
- [ ] Avoid HTML tags in labels

---

## Phase 3: Writing Guidelines **Skill**: /technical-writer

6. Style rules:
   - [ ] Use active voice ("Run the command" not "The command should be run")
   - [ ] Use present tense ("The API returns" not "The API will return")
   - [ ] Use second person ("You can configure" not "Users can configure")
   - [ ] Keep sentences short (< 25 words)
   - [ ] One idea per paragraph

7. Code examples:
   - [ ] Always tested and working
   - [ ] Include expected output
   - [ ] Use realistic values (not "foo", "bar")
   - [ ] Include error handling where relevant

8. Formatting:
   - [ ] Headers follow hierarchy (H1 > H2 > H3)
   - [ ] Use tables for structured data
   - [ ] Use code blocks with language hints
   - [ ] Use admonitions for warnings/tips

---

## Phase 4: Review and Maintenance **Skill**: /technical-writer

9. Quality checklist:
   - [ ] All code examples run successfully
   - [ ] Links are valid
   - [ ] No spelling/grammar errors
   - [ ] Consistent terminology
   - [ ] Accurate to current codebase

10. Maintenance strategy:
   - [ ] Add "Last updated" timestamp
   - [ ] Link to source code where relevant
   - [ ] Create GitHub issue for docs that need updating
   - [ ] Include in PR checklist: "Did you update docs?"

---

## Phase 4.5: Documentation Testing **Skill**: /technical-writer

11. **Automated Documentation Tests**:

**A. Link Checking**:
```bash
# Install linkchecker
pip install linkchecker

# Check all links in documentation
{{CAPABILITIES_DOCS_LINKCHECK}} {{PATH_DOCS}}/ --check-extern

# Generate report
{{CAPABILITIES_DOCS_LINKCHECK}} {{PATH_DOCS}}/ --check-extern --output=html > link_report.html
```

**B. Markdown Linting**:
```bash
# Install markdownlint
npm install -g markdownlint-cli

# Lint all markdown files
{{CAPABILITIES_DOCS_LINT}}

# Fix automatically where possible
{{CAPABILITIES_DOCS_LINT}} --fix
```

**C. Code Example Testing**:
```python
# Test all code examples in documentation
# tests/test_docs_examples.py

import subprocess
import re
from pathlib import Path

def test_api_examples():
    """Extract and test all cURL commands from API docs."""
    api_doc = Path("docs/api/API.md").read_text()

    # Extract cURL commands
    curl_pattern = r"```bash\n(curl .+?)\n```"
    commands = re.findall(curl_pattern, api_doc, re.DOTALL)

    for cmd in commands:
        # Execute command (requires local server running)
        result = subprocess.run(
            cmd.replace("\\", ""),
            shell=True,
            capture_output=True,
            text=True
        )

        # Assert command succeeded or returned expected status
        assert result.returncode in [0, 1], f"Command failed: {cmd}"
```

**D. Spelling and Grammar Check**:
```bash
# Install vale
brew install vale  # macOS
# or download from: https://github.com/errata-ai/vale/releases

# Create .vale.ini config
cat > .vale.ini << EOF
StylesPath = styles
MinAlertLevel = suggestion

[*.md]
BasedOnStyles = Vale, write-good
EOF

# Run vale
{{CAPABILITIES_DOCS_SPELLCHECK}} {{PATH_DOCS}}/ --output=line

# Generate JSON report
{{CAPABILITIES_DOCS_SPELLCHECK}} {{PATH_DOCS}}/ --output=JSON > spelling_report.json
```

**E. Readability Scoring**:
```bash
# Install textstat
pip install textstat

# Check readability
python -c "
import textstat
from pathlib import Path

doc = Path('docs/README.md').read_text()
flesch_score = textstat.flesch_reading_ease(doc)

print(f'Flesch Reading Ease: {flesch_score}')
print(f'Target: 60-70 (easily understood by 13-15 year olds)')

if flesch_score < 60:
    print('⚠️  Documentation may be too complex')
"
```

**F. CI/CD Integration**:
```yaml
# .github/workflows/docs.yml
name: Documentation Quality
on: [push, pull_request]

jobs:
  docs-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check Links
        run: |
          pip install linkchecker
          linkchecker docs/ --check-extern

      - name: Lint Markdown
        run: |
          {{CAPABILITIES_DOCS_LINT}}

      - name: Check Spelling
        uses: rojopolis/spellcheck-github-actions@0.34.0
        with:
          source_files: docs/**/*.md
```

---

## Anti-patterns to Avoid
- ❌ Wall of text without structure
- ❌ Outdated code examples
- ❌ Assuming reader knowledge (define terms)
- ❌ Missing the "why" (only explaining "how")
- ❌ Screenshots without alt text

---

## Phase 5: Issue Lifecycle & Project Board **Skill**: /project-manager

**Goal**: Track documentation tasks from draft to publish.

12. **Start Work**:
    - Move Issue to "In Progress".
    - `{{CAPABILITIES_GITHUB_ISSUE_MANAGER}}` update-phase --issue <ID> --phase implementation

13. **Content Review**:
    - Create PR with doc changes.
    - Move to "Technical Review" (or "Content Review").
    - `{{CAPABILITIES_GITHUB_ISSUE_MANAGER}}` add-tech-review --issue <ID> --pr <PR#>

14. **Troubleshooting**:
    - If card status fails to update (e.g., stuck in "Todo"), see `.github/GITHUB_OPERATIONS.md`.
