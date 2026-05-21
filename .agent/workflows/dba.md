---
description: Database design, optimization, and administration
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Database design, optimization, and administration
---

# /dba - Database Administrator Workflow

## 0. Pre-Task Anti-Hallucination Check
Before modifying the schema, you **MUST** verify the current state:

| Artifact | Purpose | Placeholder |
| :--- | :--- | :--- |
| **Alembic Workflow** | Standard migration process | `{{PATH_ALEMBIC_WORKFLOW}}` |
| **Indexing Strategy** | Approved index patterns | `{{PATH_DB_INDEXING}}` |
| **Technical Spec** | Data model & ERD | `{{PATH_TECH_SPEC}}` |
| **RDS Config** | AWS Database infrastructure (Terraform) | `{{PATH_TERRAFORM_DIR}}/rds.tf` |
| **Business Rules** | Logic governing data integrity | `{{PATH_BUSINESS_RULES}}` |

**Verification Steps:**
1. [ ] Check `{{PATH_ALEMBIC_WORKFLOW}}` for the correct auto-generation commands.
2. [ ] Review Section 4 of `{{PATH_TECH_SPEC}}` for the existing ERD.
3. [ ] Consult `{{PATH_DB_INDEXING}}` before adding new indexes.

## 0.1 Related Skills

> [!TIP]
> Load the following skills for enhanced capabilities when working on database tasks.

| Skill | Path | Use Case |
|-------|------|----------|
| **Database Design** | `.agent/skills/database-design/SKILL.md` | Schema patterns, normalization, indexing |

**Available Scripts:**
- `analyze_schema.py` - Analyze tables, relationships, and suggest indexes
- `validate_migration.py` - Check migrations for safety issues

**Example:**
```bash
# Analyze current schema
poetry run python .agent/skills/database-design/scripts/analyze_schema.py

# Validate a migration before applying
poetry run python .agent/skills/database-design/scripts/validate_migration.py alembic/versions/xxx_description.py
```

---

## Trigger
Use when: designing schemas, optimizing queries, managing migrations, or troubleshooting database issues.

## Mindset
- **Data integrity first** - constraints are features, not obstacles
- **Normalize, then denormalize** - start clean, optimize with evidence
- **Migrations must be reversible** - always plan the rollback
- **Backup before everything** - paranoia is healthy

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all schema changes, query optimizations, and database maintenance unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human DBA)**: 2-3 hours
- **AI Automated**: 26 min
- **User Time**: 5 min (approve/reject)

### Automated Migration Testing Pipeline

**AI Executes Automatically** (no user approval needed):

```bash
# Step 1: Create production database copy (5 min)
{{CAPABILITIES_DB_DUMP}} -h prod-db -U admin {{TECH_STACK_DB_NAME}} > prod_copy.sql
{{CAPABILITIES_DB_CREATE}} {{TECH_STACK_DB_NAME}}_test
{{CAPABILITIES_DB_RESTORE}} -d {{TECH_STACK_DB_NAME}}_test prod_copy.sql

# Step 2: Test migration forward (3 min)
{{CAPABILITIES_DB_MIGRATE}}
# AI verifies: No errors, all constraints intact

# Step 3: Test migration rollback (3 min)
{{CAPABILITIES_DB_ROLLBACK}} -1
# AI verifies: Database restored to pre-migration state

# Step 4: Stairway test (8 min)
for i in {1..3}; do
  {{CAPABILITIES_DB_MIGRATE}}
  {{CAPABILITIES_DB_ROLLBACK}} -1
done
# AI verifies: No errors on any iteration

# Step 5: Performance impact analysis (5 min)
EXPLAIN ANALYZE SELECT * FROM members WHERE ...;
# AI compares query plans before/after migration

# Step 6: Row count verification (2 min)
# Before migration
SELECT COUNT(*) FROM members;  -- Result: 1523

# After migration
SELECT COUNT(*) FROM members;  -- Result: 1523 ✅ No data loss
```

**AI Report** (auto-generated):
```markdown
## Migration Safety Report - Migration v043_add_pt_sessions

**Status**: ✅ SAFE TO DEPLOY

### Test Results

**Database Copy**: ✅ Created from production (1.2GB, 1523 members, 3421 contracts)

**Forward Migration**: ✅ Success (executed in 2.3s)
- Added table: `pt_sessions`
- Added indexes: `idx_pt_sessions_trainer_id`, `idx_pt_sessions_schedule_time`
- No data loss detected

**Rollback Migration**: ✅ Success (executed in 1.1s)
- Dropped table: `pt_sessions`
- Database restored to previous state
- All row counts match pre-migration

**Stairway Test**: ✅ Passed (3 up/down cycles)
- Iteration 1: ✅ Success
- Iteration 2: ✅ Success
- Iteration 3: ✅ Success

**Performance Impact**:
- New indexes add 15MB disk space
- Query performance on related tables: No degradation
- Estimated migration time on production: 3-5 seconds

**Data Integrity**:
- No foreign key violations
- All constraints intact
- Row counts match across all tables

### Recommendation
✅ **APPROVED FOR PRODUCTION** - Migration is safe with minimal impact
```

### Query Optimization Automation

**AI Auto-Optimizes Slow Queries** (confidence-based):

**Step 1: Identify Slow Queries** (AI runs automatically):
```sql
-- AI monitors pg_stat_statements
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- Queries slower than 100ms
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Step 2: Analyze Query Plans**:
```sql
-- AI runs EXPLAIN ANALYZE on each slow query
EXPLAIN ANALYZE
SELECT m.*, c.*
FROM members m
LEFT JOIN contracts c ON m.id = c.member_id
WHERE m.status = 'active';

-- Result: Sequential Scan on members (time: 245ms) ⚠️
```

**Step 3: AI Proposes Optimization** (with confidence):

| Issue | AI Solution | Confidence | Action |
|-------|-------------|------------|--------|
| Missing index on `status` | Add index | 0.95 | ✅ Auto-create migration |
| N+1 query pattern | Eager loading | 0.98 | ✅ Auto-fix in code |
| Full table scan | Add composite index | 0.88 | ⚠️ User approves (cost/benefit) |
| Inefficient JOIN | Rewrite query | 0.70 | ⚠️ User reviews rewrite |

**Example Auto-Fix**:
```markdown
## 🚀 Query Optimization Applied

**Query**: Fetch active members with contracts

**Before** (245ms):
```sql
SELECT m.*, c.*
FROM members m
LEFT JOIN contracts c ON m.id = c.member_id
WHERE m.status = 'active';
```
Execution Plan: Sequential Scan on members

**AI Applied**: Created index on `members(status)`

```sql
CREATE INDEX idx_members_status ON members(status);
```

**After** (12ms):
Execution Plan: Index Scan using idx_members_status

**Result**: 95% performance improvement ✅
**Migration**: Auto-generated `v044_add_members_status_index.py`
```

### Backup Verification Automation

**AI Verifies Backups Daily** (no human intervention):

```bash
# Step 1: Perform backup
{{CAPABILITIES_DB_DUMP}} -h prod-db -U admin -Fc {{TECH_STACK_DB_NAME}} > backup_$(date +%Y-%m-%d).dump

# Step 2: AI automatically verifies backup validity
{{CAPABILITIES_DB_CREATE}} {{TECH_STACK_DB_NAME}}_verify
{{CAPABILITIES_DB_RESTORE}} -d {{TECH_STACK_DB_NAME}}_verify backup_$(date +%Y-%m-%d).dump

# Step 3: Row count integrity check
for table in members contracts checkins pt_sessions staff; do
  prod_count=$(psql prod-db -c "SELECT COUNT(*) FROM $table" -t)
  backup_count=$(psql gym_app_verify -c "SELECT COUNT(*) FROM $table" -t)

  if [ "$prod_count" != "$backup_count" ]; then
    echo "⚠️ MISMATCH in $table: $prod_count vs $backup_count"
  fi
done

# Step 4: Upload to S3 if verified
aws s3 cp backup_2023-12-15.dump s3://gym-app-backups/2023/12/
```

**AI Backup Report** (daily):
```markdown
## Daily Backup Verification - 2023-12-15

**Backup Status**: ✅ SUCCESS

**Backup Details**:
- File: `backup_2023-12-15.dump`
- Size: 1.23 GB
- Duration: 3m 45s
- Compression: Custom format

**Verification Results**:
- ✅ Restore successful
- ✅ All tables present (8/8)
- ✅ Row counts match:
  - members: 1,523 ✅
  - contracts: 3,421 ✅
  - checkins: 45,234 ✅
  - pt_sessions: 892 ✅
  - staff: 23 ✅
  - equipment: 67 ✅
  - products: 34 ✅
  - transactions: 12,456 ✅

**S3 Upload**: ✅ Uploaded to `s3://gym-app-backups/2023/12/backup_2023-12-15.dump`

**Retention**: Older backups (>30 days) automatically archived to Glacier

**Next Backup**: 2023-12-16 02:00 UTC
```

### User Approval Checkpoints

**Always Require User Approval**:
1. **New indexes with high cost** (large tables >1M rows)
2. **Query rewrites** that change logic (confidence <0.9)
3. **Schema changes** affecting production (always manual approval)

**Never Require User Approval** (AI handles):
- Backup verification (daily automated)
- Migration testing on copies
- Index creation for small tables (<100k rows)
- Query optimization with confidence >0.95

---

## Phase 1: Schema Analysis **Skill**: /database-design

// turbo
1. Review current schema:
```bash
poetry run python -c "from {{PATH_MODELS_IMPORT}} import Base; print([t.name for t in Base.metadata.tables.values()])"
```

2. Document existing entities:

| Table | Primary Key | Foreign Keys | Indexes | Purpose |
|-------|-------------|--------------|---------| --------|
| members | id | - | email (unique) | Member profiles |
| contracts | id | member_id | - | Membership contracts |
| check_ins | id | member_id | timestamp | Access log |

3. Identify data relationships:
   - One-to-Many (Member → Contracts)
   - One-to-Many (Member → Check-ins)
   - Many-to-Many (if any)

---

## Phase 2: Schema Design **Skill**: /database-design

4. Apply normalization rules:
   - [ ] **1NF**: No repeating groups, atomic values
   - [ ] **2NF**: No partial dependencies
   - [ ] **3NF**: No transitive dependencies
   - [ ] **BCNF**: If needed for complex domains

5. Define constraints:
   - [ ] Primary keys on all tables
   - [ ] Foreign key relationships with appropriate ON DELETE behavior
   - [ ] NOT NULL on required fields
   - [ ] UNIQUE constraints where applicable
   - [ ] CHECK constraints for business rules

6. Index strategy:
   - [ ] **Reference**: Consult `docs/technical/DATABASE_INDEXING.md` for approved patterns.
   - [ ] Primary keys (automatic)
   - [ ] Foreign keys (for join performance)
   - [ ] Frequently filtered columns (WHERE clauses)
   - [ ] Covering indexes for hot queries

7. Data Lifecycle Policy:
   - [ ] When is data archived? (Hot vs. Cold storage).
   - [ ] When is data deleted? (GDPR compliance).

---

## Phase 3: Migration Management **Skill**: /dba

// turbo
7. Create migration:
```bash
{{CAPABILITIES_DB_GENERATE_MIGRATION}} "description_of_change"
```

> [!IMPORTANT]
> **Multi-Branch Rule**: Every new table MUST include a `branch_id` and appropriate foreign key to `branches.id`.


8. Review generated migration:
   - [ ] Upgrade path is correct
   - [ ] Downgrade path is correct
   - [ ] No data loss in migration
   - [ ] Large tables handled appropriately (batching)
   - [ ] **All drop operations use safe helpers from `migration_helpers.py`** (see `{{PATH_ALEMBIC_WORKFLOW}}` Section 6)
   - [ ] **No bare `op.drop_table()`, `batch_op.drop_index()`, `batch_op.drop_constraint()`** — use `drop_table_if_exists()`, `index_exists()` guards, `drop_constraint_if_exists()` instead
   - [ ] **No imports from `env.py`** — use `migration_helpers.py` to avoid recursive execution
   - [ ] Upgrade/downgrade symmetry verified (every create has a matching drop)

9. **Migration Safety Checklist**:

   **Pre-Deployment Testing** (CRITICAL - do not skip):

   - [ ] **Generate Migration**:
     ```bash
     poetry run alembic revision --autogenerate -m "add_qr_code_to_members"
     ```

   - [ ] **Review Generated SQL**:
     ```bash
     # Show SQL without executing
     poetry run alembic upgrade head --sql > migration.sql
     cat migration.sql  # Review for data loss, table locks
     ```

   - [ ] **Test on Production Copy**:
     1. Dump production database:
        ```bash
        {{CAPABILITIES_DB_DUMP}} -h localhost -U postgres -d {{TECH_STACK_DB_NAME}} > prod_backup.sql
        ```
     2. Create test database:
        ```bash
        {{CAPABILITIES_DB_CREATE}} {{TECH_STACK_DB_NAME}}_test
        psql -d {{TECH_STACK_DB_NAME}}_test < prod_backup.sql
        ```
     3. Apply migration to test DB:
        ```bash
        export DATABASE_URL="postgresql://user:pass@localhost/gym_app_test"
        poetry run alembic upgrade head
        ```
     4. Verify data integrity:
        ```sql
        -- Check row counts
        SELECT 'members' AS table_name, COUNT(*) FROM members
        UNION ALL SELECT 'contracts', COUNT(*) FROM contracts;

        -- Check for NULL values where unexpected
        SELECT * FROM members WHERE email IS NULL LIMIT 5;
        ```

   - [ ] **Test Downgrade Path**:
     ```bash
     # Downgrade one revision
     poetry run alembic downgrade -1

     # Verify data still intact
     psql -d gym_app_test -c "SELECT COUNT(*) FROM members;"

     # Re-upgrade
     poetry run alembic upgrade head
     ```

   - [ ] **Stairway Test** (CI Integration):
     Create `tests/test_migrations.py`:
     ```python
     def test_migrations_stairway():
         """Test all migrations can upgrade and downgrade."""
         # Downgrade to base
         subprocess.run(["alembic", "downgrade", "base"], check=True)

         # Upgrade step by step
         subprocess.run(["alembic", "upgrade", "head"], check=True)

         # Downgrade step by step
         subprocess.run(["alembic", "downgrade", "base"], check=True)
     ```

   - [ ] **Performance Impact Assessment**:
     - [ ] Will migration lock tables? If yes, estimate duration:
       ```sql
       EXPLAIN ANALYZE ALTER TABLE members ADD COLUMN qr_code VARCHAR(255);
       ```
     - [ ] For large tables (> 1M rows), use batching:
       ```python
       # In migration
       op.execute("""
           ALTER TABLE members ADD COLUMN qr_code VARCHAR(255);
           -- Add in batches to avoid long locks
       """)
       ```

   - [ ] **Backup Production Database**:
     ```bash
     {{CAPABILITIES_DB_DUMP}} -h prod-host -U postgres -d {{TECH_STACK_DB_NAME}} -F c -f "backup_$(date +%Y%m%d_%H%M%S).dump"
     # Verify backup size
     ls -lh backup_*.dump
     ```

## Phase 3.5: Docker Staging Migration Gate (Required Pre-PR Step) **Skill**: /devops-cicd

> **This step is mandatory before opening any PR to `devops`.** The project runs on a 4-context PostgreSQL isolation model (SQLite has been fully retired as of Phase 4). You must verify that your database migrations run and downgrade cleanly against PostgreSQL to prevent pipeline breakages.
>
> **4-Context Isolation Architecture:**
> 1. **Native Local Dev**: Port 5432, database `gym_app_dev`
> 2. **Docker Staging**: Port 5433, database `gym_app_docker` (defined in `docker-compose.staging.yml`)
> 3. **CI (GitHub Actions)**: Runner-scoped PostgreSQL service container, database `gym_test`
> 4. **UAT / Production**: AWS RDS PostgreSQL instances, database `gymapp`

// turbo
10. Start the staging Postgres service:
```bash
docker compose -f docker-compose.staging.yml up db -d
# Wait for healthy (the healthcheck polls pg_isready every 10s, up to 5 retries)
docker compose -f docker-compose.staging.yml ps db
```

11. Run the stairway test against staging Postgres:
```bash
# Upgrade to head
docker compose -f docker-compose.staging.yml run --rm \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/gym_staging \
  backend poetry run alembic upgrade head

# Downgrade to base
docker compose -f docker-compose.staging.yml run --rm \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/gym_staging \
  backend poetry run alembic downgrade base

# Re-apply (verify repeatability)
docker compose -f docker-compose.staging.yml run --rm \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/gym_staging \
  backend poetry run alembic upgrade head

# Confirm models are in sync with migration history
docker compose -f docker-compose.staging.yml run --rm \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/gym_staging \
  backend poetry run alembic check
```

12. Gate result:
   - [ ] All four commands exit 0 → **PR to `devops` may be opened**
   - [ ] Any command fails → **fix migration before opening PR** — do not rely on CI to catch Postgres errors

13. Tear down staging db (optional, preserves volume for re-use):
```bash
docker compose -f docker-compose.staging.yml stop db
```

---

// turbo
14. Apply migration to local dev (PostgreSQL) after staging gate passes:
```bash
poetry run alembic upgrade head
```

---

## Phase 4: Query Optimization **Skill**: /performance-optimization

11. **Identify Slow Queries**:

   **Enable `pg_stat_statements`** (if not already):
   ```sql
   -- In postgresql.conf
   shared_preload_libraries = 'pg_stat_statements'
   pg_stat_statements.track = all

   -- Restart PostgreSQL, then create extension
   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
   ```

   **Find Top 10 Slowest Queries**:
   ```sql
   SELECT
       query,
       calls,
       total_exec_time / 1000 AS total_time_sec,
       mean_exec_time / 1000 AS avg_time_sec,
       max_exec_time / 1000 AS max_time_sec
   FROM pg_stat_statements
   WHERE query NOT LIKE '%pg_stat_statements%'
   ORDER BY total_exec_time DESC
   LIMIT 10;
   ```

   **Identify N+1 Queries**:
   ```sql
   -- Queries called many times with similar structure
   SELECT
       SUBSTRING(query, 1, 100) AS query_pattern,
       calls,
       mean_exec_time
   FROM pg_stat_statements
   WHERE calls > 1000
   ORDER BY calls DESC;
   ```

12. **Analyze Query Execution Plans**:

   ```sql
   -- Basic plan (no execution)
   EXPLAIN SELECT * FROM members WHERE email = 'test@example.com';

   -- Actual execution with timing
   EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
   SELECT m.*, c.*
   FROM members m
   LEFT JOIN contracts c ON m.id = c.member_id
   WHERE m.status = 'active';
   ```

   **Red Flags in EXPLAIN Output**:
   - ❌ **Seq Scan** on large tables (> 10k rows) → Missing index
   - ❌ **Nested Loop** with high cost → Consider hash join
   - ❌ **Rows Removed by Filter: 99%** → Better WHERE clause or index needed
   - ❌ **Buffers: shared read = 10000** → Too much disk I/O, needs caching

13. **Optimization Techniques**:

   **A. Add Indexes Strategically**:
   ```sql
   -- Single-column index (WHERE, ORDER BY)
   CREATE INDEX idx_members_email ON members(email);

   -- Multi-column index (WHERE on both columns)
   CREATE INDEX idx_contracts_member_dates
   ON contracts(member_id, start_date, end_date);

   -- Partial index (subset of data)
   CREATE INDEX idx_members_active
   ON members(email)
   WHERE status = 'active' AND is_deleted = false;

   -- Covering index (index-only scan)
   CREATE INDEX idx_members_email_status
   ON members(email) INCLUDE (status, created_at);
   ```

   **B. Rewrite N+1 Queries**:
   ```python
   # Bad: N+1 (1 query + N queries in loop)
   members = session.query(Member).all()
   for member in members:
       contracts = session.query(Contract).filter_by(member_id=member.id).all()

   # Good: Eager loading (2 queries or 1 with JOIN)
   members = session.query(Member).options(
       joinedload(Member.contracts)
   ).all()
   ```

   **C. Use Connection Pooling**:
   ```python
   # In src/config.py
   from sqlalchemy.pool import QueuePool

   engine = create_engine(
       DATABASE_URL,
       poolclass=QueuePool,
       pool_size=10,          # Max persistent connections
       max_overflow=20,       # Max temp connections
       pool_pre_ping=True     # Verify connection before use
   )
   ```

14. **Monitoring Queries**:

   **Check Index Usage**:
   ```sql
   SELECT
       schemaname,
       tablename,
       indexname,
       idx_scan AS index_scans,
       idx_tup_read AS tuples_read,
       idx_tup_fetch AS tuples_fetched
   FROM pg_stat_user_indexes
   WHERE idx_scan < 50  -- Rarely used indexes
   ORDER BY idx_scan;
   ```

   **Identify Missing Indexes**:
   ```sql
   SELECT
       schemaname,
       tablename,
       seq_scan,
       seq_tup_read,
       idx_scan,
       seq_tup_read / NULLIF(seq_scan, 0) AS avg_seq_read
   FROM pg_stat_user_tables
   WHERE seq_scan > 1000  -- Frequently scanned
     AND idx_scan < seq_scan  -- More seq scans than index scans
   ORDER BY seq_tup_read DESC;
   ```

   **Check Table Bloat**:
   ```sql
   SELECT
       schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
       n_dead_tup AS dead_tuples,
       last_vacuum,
       last_autovacuum
   FROM pg_stat_user_tables
   WHERE n_dead_tup > 1000
   ORDER BY n_dead_tup DESC;
   ```

---

## Phase 4.5: PostgreSQL Configuration Tuning **Skill**: /devops-cicd

15. **Key Configuration Parameters** (`postgresql.conf`):

   **Memory Settings**:
   ```conf
   # Shared memory buffer (25-40% of total RAM)
   shared_buffers = 2GB

   # Per-query memory for sorts/hashes
   work_mem = 16MB

   # Maintenance operations (VACUUM, REINDEX)
   maintenance_work_mem = 512MB

   # Query planner's estimate of OS cache
   effective_cache_size = 6GB
   ```

   **Connection Settings**:
   ```conf
   # Max concurrent connections (use pooling for more)
   max_connections = 100

   # Parallel query workers
   max_parallel_workers_per_gather = 4
   max_parallel_workers = 8
   ```

   **WAL (Write-Ahead Log) Settings**:
   ```conf
   # Separate WAL disk for performance
   wal_buffers = 16MB
   checkpoint_completion_target = 0.9
   ```

   **Apply Changes**:
   ```bash
   # Edit config
   sudo nano /etc/postgresql/15/main/postgresql.conf

   # Restart PostgreSQL
   sudo systemctl restart postgresql

   # Verify settings
   psql -c "SHOW shared_buffers;"
   psql -c "SHOW max_connections;"
   ```

   **Use pgTune for Recommendations**:
   - Visit: https://pgtune.leopard.in.ua/
   - Input: RAM, CPU cores, DB type (Web/OLTP/Data Warehouse)
   - Copy generated config to `postgresql.conf`

---

## Phase 5: Backup and Recovery **Skill**: /devops-cicd

16. **Backup Strategy**:

   **A. Create Backup**:
   ```bash
   # Full backup (custom format, compressed)
   pg_dump -h localhost -U postgres -d gym_app \
     -F c -f "backup_$(date +%Y%m%d).dump"

   # Directory format (parallel restore)
   pg_dump -h localhost -U postgres -d gym_app \
     -F d -j 4 -f "backup_dir_$(date +%Y%m%d)"

   # SQL format (human-readable)
   pg_dump -h localhost -U postgres -d gym_app \
     > "backup_$(date +%Y%m%d).sql"
   ```

   **B. Verify Backup Integrity**:
   ```bash
   # Restore to test database
   createdb gym_app_backup_test
   pg_restore -d gym_app_backup_test backup_20231213.dump

   # Check row counts match production
   psql -d gym_app_backup_test -c "SELECT COUNT(*) FROM members;"
   psql -d gym_app -c "SELECT COUNT(*) FROM members;"
   ```

   **C. Automate Daily Backups** (cron job):
   ```bash
   # Add to crontab: crontab -e
   0 2 * * * /usr/bin/pg_dump -h localhost -U postgres -d gym_app \
     -F c -f /backups/gym_app_$(date +\%Y\%m\%d).dump && \
     find /backups -name "gym_app_*.dump" -mtime +7 -delete
   ```

   **D. Off-Site Backup** (AWS S3):
   ```bash
   # Upload to S3
   aws s3 cp backup_$(date +%Y%m%d).dump \
     s3://my-gym-backups/$(date +%Y/%m/)

   # Verify upload
   aws s3 ls s3://my-gym-backups/$(date +%Y/%m/)/
   ```

   **E. Maintenance Schedule**:
   - [ ] **Weekly `VACUUM ANALYZE`**:
     ```bash
     psql -d gym_app -c "VACUUM ANALYZE;"
     ```
   - [ ] **Monthly Index Rebuild** (if fragmented):
     ```bash
     psql -d gym_app -c "REINDEX DATABASE gym_app;"
     ```

17. **Disaster Recovery Testing**:

   **Define Objectives**:
   - **RTO** (Recovery Time Objective): 4 hours
   - **RPO** (Recovery Point Objective): 24 hours (daily backups)

   **Recovery Procedure**:
   ```bash
   # 1. Create new database
   createdb gym_app_restored

   # 2. Restore from backup
   pg_restore -d gym_app_restored -j 4 --no-owner \
     /backups/gym_app_20231213.dump

   # 3. Verify data integrity
   psql -d gym_app_restored -c """
   SELECT
       'members' AS table, COUNT(*) AS count FROM members
   UNION ALL
   SELECT 'contracts', COUNT(*) FROM contracts;
   """

   # 4. Update application config
   export DATABASE_URL="postgresql://user:pass@localhost/gym_app_restored"

   # 5. Restart application
   docker-compose restart
   ```

   **Test Recovery Annually**:
   - [ ] Schedule recovery drill (Q1 each year)
   - [ ] Document time taken vs. RTO target
   - [ ] Update procedure based on learnings

---

## Anti-patterns to Avoid
- ❌ Storing denormalized data without clear justification
- ❌ Missing foreign key constraints
- ❌ Using TEXT for everything (use appropriate types)
- ❌ No indexes on frequently queried columns
- ❌ Migrations without downgrade paths
- ❌ Trusting ORM to generate optimal queries
- ❌ **Bare `op.drop_table()` / `op.drop_index()` without IF EXISTS guard** — crashes on schema drift
- ❌ **Bare `batch_op.drop_constraint()` without existence check** — crashes on PostgreSQL if constraint missing and aborts transaction
- ❌ **Importing helpers from `env.py`** — causes recursive migration execution (use `migration_helpers.py` instead)
- ❌ **Create operations without existence guards** — `add_column`, `create_index`, `create_table` crash on re-apply if object already exists
