---
description: Performance analysis, profiling, and optimization
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Performance analysis, profiling, and optimization
---

# /perf - Performance Engineer Workflow

## Trigger
Use when: optimizing slow code, analyzing bottlenecks, load testing, or improving resource efficiency.

## Mindset
- **Measure first** - never optimize without data
- **80/20 rule** - 20% of code causes 80% of slowness
- **User-perceived performance** - latency matters more than throughput
- **Premature optimization is evil** - correctness > performance until proven otherwise

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all performance analysis, profiling, and optimization tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human)**: 4 hours
- **AI Automated**: 50 min
- **User Time**: 15 min (review results)

### Automated Profiling Pipeline

**AI Auto-Executes** (no user approval needed):

```bash
# Step 1: CPU Profiling (Flamegraph) - 2 min
{{CAPABILITIES_PERF_PROFILE_FLAMEGRAPH}} -o profile.svg --duration 60 --rate 100 -- {{CAPABILITIES_RUN_BACKEND}}

# Step 2: Memory Profiling - 3 min
{{CAPABILITIES_PERF_MEMORY_PROFILE}} {{PATH_API_ROUTES}}/members.py

# Step 3: Database Query Profiling (5 min)
# AI enables query logging
export SQLALCHEMY_ECHO=true
# AI collects slow query log
tail -f /var/log/postgresql/slow_queries.log

# Step 4: API Endpoint Timing (10 min)
# AI instruments FastAPI middleware
# Collects response time for all endpoints
```

**AI Profiling Report** (auto-generated):
```markdown
## Performance Profiling Report

**Test Duration**: 60 seconds
**Environment**: Staging (simulated production load)

### CPU Hotspots

| Function | % Time | Self Time | Cumulative Time | Calls |
|----------|--------|-----------|------------------|-------|
| `get_member_contracts()` | 34.2% | 12.5s | 20.5s | 1,234 |
| `validate_token()` | 18.7% | 6.8s | 6.8s | 5,678 |
| `calculate_membership_fee()` | 12.3% | 4.5s | 9.2s | 2,345 |

**AI Analysis**:
- 🔴 `get_member_contracts()` has N+1 query problem (34% CPU time)
- 🟡 `validate_token()` called 5,678 times (opportunity for caching)
- 🟢 Most other functions performing well

### Memory Usage

| Endpoint | Peak Memory | Memory Leak | Status |
|----------|-------------|-------------|---------|
| `/api/members` | 145 MB | No | ✅ |
| `/api/contracts` | 312 MB | No | ✅ |
| `/api/workouts` | 89 MB | No | ✅ |
| `/api/checkins` | 523 MB | ⚠️ Possible | ⚠️ Investigate |

**AI Analysis**:
- 🔴 `/api/checkins` using 523 MB for 1000 records (should be ~150 MB)
- Possible memory leak in checkin history pagination

### Database Performance

**Slow Queries** (>100ms):

1. **Query**: `SELECT * FROM members m LEFT JOIN contracts c ON m.id = c.member_id`
   - **Time**: 245ms
   - **Calls**: 1,234
   - **Issue**: Missing index on `contracts.member_id`
   - **AI Fix**: Create index (already proposed in DBA workflow)

2. **Query**: `SELECT COUNT(*) FROM checkins WHERE member_id = ?`
   - **Time**: 156ms
   - **Calls**: 2,345
   - **Issue**: Sequential scan on 45,000 rows
   - **AI Fix**: Add composite index on `(member_id, created_at)`
```

### Load Testing Automation

**AI Auto-Executes** (30 min):

```bash
# k6 Load Test - Automatically configured by AI

import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '5m', target: 50 },   // Ramp up to 50 users
    { duration: '10m', target: 50 },  // Stay at 50 users
    { duration: '5m', target: 100 },  // Ramp to 100 users
    { duration: '10m', target: 100 }, // Stay at 100 users
    { duration: '5m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p95<200', 'p99<500'], // 95% <200ms, 99% <500ms
    http_req_failed: ['rate<0.01'],            // Error rate <1%
  },
};

export default function () {
  // AI-generated realistic test scenarios

  // Scenario 1: Member check-in (40% of traffic)
  let checkin = http.post('{{URL_BACKEND_LOCAL}}/api/checkins', {
    member_id: Math.floor(Math.random() * 1000) + 1
  });
  check(checkin, { 'checkin status is 201': (r) => r.status === 201 });

  // Scenario 2: View member contracts (30% of traffic)
  let contracts = http.get(`{{URL_BACKEND_LOCAL}}/api/members/${Math.floor(Math.random() * 1000) + 1}/contracts`);
  check(contracts, { 'contracts status is 200': (r) => r.status === 200 });

  // Scenario 3: Search members (20% of traffic)
  let search = http.get('{{URL_BACKEND_LOCAL}}/api/members?name=john');
  check(search, { 'search status is 200': (r) => r.status === 200 });

  sleep(1);
}
```

### Auto-Optimization Execution

**AI Auto-Applies** (confidence ≥0.90):

```markdown
## 🚀 Applied Performance Optimizations

**1. Database Connection Pool** (Confidence: 0.98)
- Increased pool_size: 10 → 50
- Increased max_overflow: 10 → 20
- **Impact**: Eliminated connection wait time

**2. Eager Loading for Contracts** (Confidence: 0.95)
```python
# Before
def get_member_contracts(member_id: int):
    member = db.query(Member).get(member_id)
    return member.contracts  # Lazy load

# After (AI applied)
def get_member_contracts(member_id: int):
    member = db.query(Member).options(
        joinedload(Member.contracts)
    ).get(member_id)
    return member.contracts
```
**Impact**: 101 queries → 1 query

**3. Added Composite Index** (Confidence: 0.92)
```sql
CREATE INDEX idx_checkins_member_created
ON checkins(member_id, created_at);
```
**Impact**: Checkin queries 156ms → 8ms

**Committed**: `perf: apply automated performance optimizations`
```

### User Approval Required

**Medium/Low Confidence** (user decides):

```markdown
## ⚠️ Performance Optimizations - User Decision Needed

**1. Implement Redis Token Caching** (Confidence: 0.72)

**Pros**:
- 15% reduction in API latency
- Reduces database load (no token lookup per request)

**Cons**:
- New dependency (Redis)
- Additional infrastructure cost (~$15/month)
- Adds complexity

**AI Recommendation**: Implement if token validation is a bottleneck (currently 18.7% CPU)

**Your Decision**: [Approve] [Defer] [Reject]

---

**2. Investigate Memory Leak in `/api/checkins`** (Confidence: 0.55)

**Issue**: Memory usage 523 MB for 1000 records (expected ~150 MB)

**AI Analysis**: Unable to determine root cause automatically
- Possible causes: Unclosed DB sessions, circular references, large object caching

**AI Recommendation**: Manual investigation required (AI can assist with memory dump analysis)

**Your Decision**: [Investigate Now] [Monitor for 1 week] [Accept]
```

---

## Phase 1: Performance Assessment **Skill**: /performance-optimization

1. **Establish Baseline Metrics**:

| Metric | Current (Measure First!) | Target | Acceptable Range | Measurement Method |
|--------|--------------------------|--------|------------------|-------------------|
| **Latency** | | | | |
| p50 response time | ? | < 100ms | 80-150ms | k6 load test |
| p95 response time | ? | < 200ms | 150-300ms | k6 load test |
| p99 response time | ? | < 500ms | 300-800ms | k6 load test |
| **Throughput** | | | | |
| Requests/second | ? | > 100 req/s | 80-150 req/s | k6 load test |
| Concurrent users | ? | > 50 users | 40-80 users | k6/Locust |
| **Resources** | | | | |
| Memory usage (idle) | ? | < 100MB | 80-150MB | `docker stats` |
| Memory usage (load) | ? | < 512MB | 300-700MB | `docker stats` during k6 |
| CPU usage (average) | ? | < 30% | 20-50% | `docker stats` |
| CPU usage (peak) | ? | < 70% | 50-90% | `docker stats` during k6 |
| **Database** | | | | |
| DB connections (idle) | ? | < 5 | 3-10 | `SELECT count(*) FROM pg_stat_activity` |
| DB connections (load) | ? | < 30 | 20-50 | During load test |
| Query time (p95) | ? | < 50ms | 30-100ms | `pg_stat_statements` |

**Measurement Commands**:
```bash
# Measure baseline
{{CAPABILITIES_TEST_RUN_K6_BASELINE}}

# Monitor resources during test
watch -n 1 'docker stats --no-stream {{CONTAINER_NAME}}'

# Check DB connections
{{CAPABILITIES_DB_CHECK_CONNECTIONS}}
```

2. Define Golden Signals:
   - **Latency**: Request time (p50, p95, p99).
   - **Traffic**: Req/sec.
   - **Errors**: 4xx/5xx rates.
   - **Saturation**: CPU/Memory/Disk % utilization.

// turbo
2. **Profile the Application**:

**A. cProfile (Built-in, baseline)**:
```bash
# Profile entire application
{{CAPABILITIES_PERF_PROFILE_CPROFILE}} -o profile.stats {{PATH_ENTRYPOINT}}

# View top 20 functions by cumulative time
poetry run python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

**B. Pyinstrument (Best for FastAPI async code)**:
```bash
# Install
pip install pyinstrument

# Add middleware to FastAPI
# In {{PATH_ENTRYPOINT}}:
from pyinstrument import Profiler
from pyinstrument.renderers import HTMLRenderer

@app.middleware("http")
async def profile_request(request, call_next):
    profiler = Profiler()
    profiler.start()
    response = await call_next(request)
    profiler.stop()

    # Save profile
    with open(f"profile_{request.url.path.replace('/', '_')}.html", "w") as f:
        f.write(profiler.output_html())

    return response

# Run app and make requests
{{CAPABILITIES_RUN_BACKEND}}

# Open generated HTML files in browser
open profile__api_members.html
```

**C. Py-Spy (Production-safe, low overhead)**:
```bash
# Install
pip install py-spy

# Start app
{{CAPABILITIES_RUN_BACKEND}} &
PID=$!

# Profile for 60 seconds, generate flame graph
sudo py-spy record --pid $PID --duration 60 --output flamegraph.svg

# View flame graph
open flamegraph.svg
```

**D. Memory Profiling (tracemalloc)**:
```python
# Add to {{PATH_ENTRYPOINT}}
import tracemalloc

@app.on_event("startup")
async def startup():
    tracemalloc.start()

@app.get("/memory-snapshot")
async def get_memory_snapshot():
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    return {
        "top_10_memory_consumers": [
            {
                "file": str(stat.traceback),
                "size_mb": stat.size / 1024 / 1024,
                "count": stat.count
            }
            for stat in top_stats[:10]
        ]
    }
```

**Profiling Interpretation**:
- **Red flags**:
  - Any function taking > 10% of total time
  - Synchronous DB calls in async functions
  - Multiple small queries (N+1 pattern)
  - Large memory allocations (> 100MB for single objects)

---

## Phase 1.5: Load Testing Setup **Skill**: /performance-optimization

**Choose a Load Testing Tool**:

| Tool | Language | Best For | Ease of Use | Production Profiling |
|------|----------|----------|-------------|----------------------|
| **k6** | JavaScript | API testing, CI/CD | High | No |
| **Locust** | Python | Complex scenarios, Web UI | High | No |
| **Apache Bench** | CLI | Quick tests | Very High | No |

**Recommended**: k6 for gym app (API-focused)

### k6 Load Testing

**1. Install k6**:
```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Windows
choco install k6
```

**2. Create Load Test Script** (`{{PATH_TEST_ROOT}}/performance/load_test.js`):
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 users
    { duration: '1m', target: 50 },   // Stay at 50 users
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],    // Error rate < 1%
  },
};

const BASE_URL = '{{URL_BACKEND_LOCAL}}';

export default function () {
  // Test 1: Health check
  let healthResponse = http.get(`${BASE_URL}/health`);
  check(healthResponse, {
    'health check status 200': (r) => r.status === 200,
  });

  sleep(1);

  // Test 2: Get members list
  let token = getAuthToken();
  let membersResponse = http.get(`${BASE_URL}/api/members?limit=20`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  check(membersResponse, {
    'members list status 200': (r) => r.status === 200,
    'members list has data': (r) => JSON.parse(r.body).length > 0,
  });

  sleep(2);
}

function getAuthToken() {
  let loginRes = http.post(`${BASE_URL}/api/token`, {
    username: 'admin',
    password: 'TestGym2024!',
  });
  return JSON.parse(loginRes.body).access_token;
}
```

**3. Run Load Test**:
```bash
# Run test
k6 run {{PATH_TEST_ROOT}}/performance/load_test.js

# Generate HTML report
k6 run --out json=results.json {{PATH_TEST_ROOT}}/performance/load_test.js
```

**4. Interpret Results**:
```
Expected output:
✓ http_req_duration..............: avg=245ms  p(95)=450ms  max=800ms
✓ http_req_failed................: 0.02%
✓ http_reqs......................: 5000 (50 req/s)
✓ vus............................: 1 min=1 max=50

Pass criteria:
- p95 < 500ms ✅
- Error rate < 1% ✅
- Throughput > 40 req/s ✅
```

### Locust Alternative

**1. Install Locust**:
```bash
pip install locust
```

**2. Create Locustfile** (`{{PATH_TEST_ROOT}}/performance/locustfile.py`):
```python
from locust import HttpUser, task, between

class GymAppUser(HttpUser):
    wait_time = between(1, 3)  # Simulate think time

    def on_start(self):
        # Login once per user
        response = self.client.post("/api/token", data={
            "username": "admin",
            "password": "TestGym2024!"
        })
        self.token = response.json()["access_token"]

    @task(3)  # Weight: 3x more likely than other tasks
    def get_members(self):
        self.client.get("/api/members?limit=20", headers={
            "Authorization": f"Bearer {self.token}"
        })

    @task(1)
    def get_contracts(self):
        self.client.get("/api/contracts?limit=10", headers={
            "Authorization": f"Bearer {self.token}"
        })
```

**3. Run Locust**:
```bash
# Start Locust web UI
locust -f {{PATH_TEST_ROOT}}/performance/locustfile.py --host=http://localhost:8000

# Open browser: http://localhost:8089
# Set users: 50, spawn rate: 5 users/sec
```

---

## Phase 2: Bottleneck Identification **Skill**: /performance-optimization

3. Common bottlenecks checklist:

**Database**
- [ ] N+1 queries (multiple queries where one would do)
- [ ] Missing indexes on filtered columns
- [ ] Full table scans
- [ ] Inefficient joins

**I/O**
- [ ] Synchronous external API calls
- [ ] Unoptimized file operations
- [ ] Missing caching for repeated data

**Memory**
- [ ] Loading full datasets into memory
- [ ] Memory leaks from unclosed resources
- [ ] Inefficient data structures

**CPU**
- [ ] Tight loops with heavy computation
- [ ] Redundant processing
- [ ] Missing memoization

4. Use appropriate profiling tools:
   - **Python**: cProfile, line_profiler, memory_profiler
   - **Database**: EXPLAIN ANALYZE, slow query log
   - **HTTP**: Apache Benchmark (ab), wrk, locust

---

## Phase 3: Optimization **Skill**: /performance-optimization

5. **FastAPI-Specific Optimization Strategies**:

**A. Async/Await Optimization**:
```python
# Bad: Blocking I/O in async function
@app.get("/members")
async def get_members():
    members = db.query(Member).all()  # Synchronous DB call!
    return members

# Good: Async database driver
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/members")
async def get_members(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Member))
    members = result.scalars().all()
    return members
```

**B. Database Connection Pooling**:
```python
# In {{PATH_CONFIG}}
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=10,           # Max persistent connections
    max_overflow=20,        # Max temp connections
    pool_pre_ping=True,     # Verify connection before use
    pool_recycle=3600       # Recycle connections after 1 hour
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

**C. Caching with Redis**:
```python
import redis.asyncio as redis
from functools import lru_cache

# Setup Redis client
@lru_cache()
def get_redis_client():
    return redis.Redis(host='localhost', port=6379, decode_responses=True)

# Cache expensive query results
@app.get("/members/{member_id}")
async def get_member(member_id: int, cache: redis.Redis = Depends(get_redis_client)):
    # Check cache first
    cached = await cache.get(f"member:{member_id}")
    if cached:
        return json.loads(cached)

    # Query database
    member = await db.get(Member, member_id)

    # Cache for 5 minutes
    await cache.setex(
        f"member:{member_id}",
        300,
        json.dumps(member.dict())
    )

    return member
```

**D. Response Streaming** (for large datasets):
```python
from fastapi.responses import StreamingResponse

@app.get("/members/export")
async def export_members(db: AsyncSession = Depends(get_async_db)):
    async def generate_csv():
        yield "id,name,email\n"

        # Stream rows instead of loading all into memory
        async for member in db.stream(select(Member)):
            yield f"{member.id},{member.first_name},{member.email}\n"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=members.csv"}
    )
```

**E. Dependency Injection Caching**:
```python
# Bad: Creating new instance per request
def get_expensive_service():
    return ExpensiveService()  # Recreated every time!

@app.get("/data")
async def get_data(service = Depends(get_expensive_service)):
    ...

# Good: Cache with lru_cache
from functools import lru_cache

@lru_cache()
def get_expensive_service():
    return ExpensiveService()  # Created once!

@app.get("/data")
async def get_data(service = Depends(get_expensive_service)):
    ...
```

**F. JSON Serialization (use orjson)**:
```python
# Install orjson
pip install orjson

# In src/main.py
from fastapi.responses import ORJSONResponse

app = FastAPI(default_response_class=ORJSONResponse)

# 2-3x faster JSON encoding than default
```

**Performance Impact Estimates**:
| Optimization | Latency Improvement | Complexity |
|--------------|---------------------|------------|
| Async DB driver | 30-50% | Medium |
| Connection pooling | 20-40% | Low |
| Redis caching | 80-95% (cache hits) | Medium |
| orjson | 10-20% | Low |
| Dependency caching | 5-15% | Low |

6. Implementation guidelines:
   - [ ] One optimization at a time
   - [ ] Measure after each change
   - [ ] Keep the unoptimized version available
   - [ ] Document trade-offs made

---

## Phase 4: Validation **Skill**: /performance-optimization

// turbo
7. Run load tests:
```bash
{{CAPABILITIES_TEST_RUN_K6_BASELINE}}
```

8. Compare metrics:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| p50 latency | Xms | Yms | Z% |
| p99 latency | Xms | Yms | Z% |
| Throughput | X req/s | Y req/s | Z% |

9. Verify no regressions:
   - [ ] All tests still pass
   - [ ] Functionality unchanged
   - [ ] Memory usage acceptable
   - [ ] Error rate unchanged

10. SLO Verification:
    - [ ] Does the new baseline meet the 99.9% availability target?
    - [ ] Is Latency p95 < 200ms?

---

## Phase 5: Documentation **Skill**: /technical-writer

10. Document optimizations:
    - What was the problem?
    - What was the solution?
    - What are the trade-offs?
    - How to monitor ongoing?

---

## Anti-patterns to Avoid
- ❌ Optimizing without measuring
- ❌ Micro-optimizations before macro
- ❌ Sacrificing readability for negligible gains
- ❌ Premature caching (cache invalidation is hard)
- ❌ Ignoring infrastructure solutions
