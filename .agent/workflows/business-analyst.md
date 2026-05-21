---
description: Business requirements analysis and user story creation
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Business requirements analysis and user story creation
---

# /ba - Business Analyst Workflow

## 0. Pre-Task Anti-Hallucination Check
Before analysis or storytelling, you **MUST** verify the source of truth for requirements:

| Artifact | Purpose | Placeholder |
| :--- | :--- | :--- |
| **BRS** | Business Requirements Document | `{{PATH_BRS}}` |
| **User Stories** | Existing stories & BDD scenarios | `{{PATH_USER_STORIES}}` |
| **RTM** | Requirements Traceability Matrix | `{{PATH_RTM}}` |
| **Business Rules** | Logic governing domain behavior | `{{PATH_BUSINESS_RULES}}` |

**Verification Steps:**
1. [ ] Check `{{PATH_BRS}}` to ensure new stories align with high-level business goals.
2. [ ] Review `{{PATH_USER_STORIES}}` to avoid duplication.
3. [ ] Consult `{{PATH_BUSINESS_RULES}}` for existing constraints on the feature.

---

## Trigger
Use when: clarifying requirements, writing user stories, gap analysis, or stakeholder communication.

## Mindset
- **User value first** - every feature must tie to a benefit
- **Testable criteria** - if you can't test it, you can't ship it
- **Assumptions are risks** - surface and validate them early

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all requirement analysis and user story creation tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human BA)**: 1-2 days
- **AI Mode (Agentic)**: 1.4 hours
- **User Time**: 1.25 hours (approvals only)

### Input: Client Meeting Transcript

**User Provides** (automatic if recorded):
```
Client Meeting Transcript - PT Booking Feature
Date: 2023-12-15

User: "Our trainers are frustrated. Members call them directly to book sessions,
and there's constant confusion about who's available when. We need a system where
members can see trainer availability and book directly."

Client: "Yes, exactly. And trainers should be able to block off time when they're
not available - vacation, sick days, whatever."

User: "What happens if two members try to book the same slot?"

Client: "First come, first served. The second person should see it's taken and
pick another time."

User: "Do members need to pay upfront or at the session?"

Client: "We'll handle payment separately for now. Just booking for now."

User: "Should trainers be able to cancel sessions?"

Client: "Yes, but they should have to provide a reason, and the member needs
to be notified immediately."
```

### AI Processing Pipeline (10 min)

**Step 1: Requirement Extraction** (3 min)

AI identifies:
- Explicit requirements (stated directly)
- Implicit requirements (inferred from context)
- Non-requirements (explicitly excluded)
- Ambiguities (needs clarification)

**AI Output**:
```markdown
## Requirements Extraction Results

**Explicit Requirements**:
1. ✅ Members view trainer availability
2. ✅ Members book PT sessions
3. ✅ Trainers mark unavailable time periods
4. ✅ Prevent double-booking (concurrent booking handling)
5. ✅ Trainers cancel sessions with reason
6. ✅ Member notification on cancellation

**Implicit Requirements** (Confidence: 0.75-0.85):
7. ⚠️ Search/filter trainers (inferred from "see availability")
8. ⚠️ Booking confirmation notification (standard practice)
9. ⚠️ View booking history (needed for UX)

**Excluded from Scope**:
- ❌ Payment processing (client said "handle separately")
- ❌ Member cancellation (not mentioned)
- ❌ Recurring bookings (not mentioned)

**Ambiguities - User Clarification Needed**:
- ❓ How far in advance can members book? (1 week? 1 month?)
- ❓ Can trainers see who booked them before accepting?
- ❓ Minimum/maximum session duration?
```

**Step 2: User Story Generation** (5 min)

```markdown
## User Stories (INVEST Format)

### Epic: PT Session Booking

**US-001: View Trainer Availability** (Priority: HIGH, Points: 5)
**Confidence**: 0.95

**As a** member
**I want to** view available time slots for each trainer
**So that** I can book a PT session at my convenience

**Acceptance Criteria**:
- [ ] Members see list of all trainers
- [ ] For each trainer, see available time slots for next 2 weeks
- [ ] Unavailable slots are grayed out/hidden
- [ ] Time slots displayed in member's timezone

---

**US-002: Book PT Session** (Priority: HIGH, Points: 8)
**Confidence**: 0.98

**As a** member
**I want to** book an available PT session slot
**So that** I can reserve time with a trainer

**Acceptance Criteria**:
- [ ] Select trainer and available time slot
- [ ] Receive immediate confirmation
- [ ] Booking appears in "My Sessions"
- [ ] Trainer receives notification
- [ ] System prevents double-booking (concurrent handling)

---

**US-003: Trainer Block Unavailable Time** (Priority: HIGH, Points: 3)
**Confidence**: 0.92

**As a** trainer
**I want to** mark time periods as unavailable
**So that** members can't book me when I'm not working

**Acceptance Criteria**:
- [ ] Mark single day or date range as unavailable
- [ ] Specify reason (optional): Vacation, Sick, Personal
- [ ] Blocked time immediately hidden from member view
- [ ] Can edit/delete blocked periods

---

**US-004: Trainer Cancel Session** (Priority: MEDIUM, Points: 3)
**Confidence**: 0.88

**As a** trainer
**I want to** cancel a booked session with a reason
**So that** I can handle emergencies while keeping member informed

**Acceptance Criteria**:
- [ ] Trainer selects booked session
- [ ] Must provide cancellation reason (required field)
- [ ] Member receives immediate notification (email + in-app)
- [ ] Session slot becomes available again

---

**US-005: Search/Filter Trainers** (Priority: MEDIUM, Points: 3)
**Confidence**: 0.75 ⚠️

**As a** member
**I want to** search trainers by specialty or name
**So that** I can find the right trainer for my needs

**Acceptance Criteria**:
- [ ] Search by trainer name
- [ ] Filter by specialty (e.g., "Weight Loss", "Strength")
- [ ] Filter by availability (show only trainers with open slots)

**⚠️ Note**: Inferred requirement - user should confirm if trainer specialties exist in system
```

**Step 3: BDD Scenario Generation** (8 min)

```gherkin
# bdd/features/pt_booking.feature

Feature: PT Session Booking
  As a member, I want to book PT sessions with trainers

  Background:
    Given the following trainers exist:
      | id | name        | specialty    |
      | 1  | John Smith  | Weight Loss  |
      | 2  | Jane Doe    | Strength     |
    And trainer "John Smith" has the following availability:
      | date       | time  | available |
      | 2023-12-20 | 10:00 | true      |
      | 2023-12-20 | 11:00 | true      |
      | 2023-12-21 | 10:00 | false     |

  Scenario: Member books available session successfully
    Given I am logged in as member "Alice"
    When I select trainer "John Smith"
    And I book the session on "2023-12-20" at "10:00"
    Then I should see "Booking confirmed"
    And the session should appear in my bookings
    And the slot should no longer be available to other members
    And trainer "John Smith" should receive a booking notification

  Scenario: Prevent double-booking under concurrent requests
    Given member "Alice" is booking "John Smith" on "2023-12-20" at "10:00"
    When member "Bob" attempts to book the same slot concurrently
    Then only one booking should succeed
    And the unsuccessful member should see "Slot no longer available"

  Scenario: Trainer blocks unavailable time
    Given I am logged in as trainer "John Smith"
    When I block the date "2023-12-25" with reason "Holiday"
    Then members should not see "2023-12-25" as available
    And the block should appear in my unavailability list

  Scenario: Trainer cancels confirmed session
    Given member "Alice" has a confirmed session with "John Smith" on "2023-12-20" at "10:00"
    When trainer "John Smith" cancels the session with reason "Emergency"
    Then member "Alice" should receive a cancellation notification
    And the session should be removed from "Alice" bookings
    And the slot "2023-12-20 10:00" should become available again
```

### Hallucination Detection & Confidence Scoring

**AI flags potential hallucinations**:

| Requirement | Confidence | Hallucination Risk | Action |
|-------------|------------|-------------------|--------|
| View trainer availability | 0.95 | Low | ✅ Auto-approve |
| Book PT session | 0.98 | Low | ✅ Auto-approve |
| Concurrent booking prevention | 0.90 | Low | ✅ Auto-approve |
| Trainer cancel with reason | 0.92 | Low | ✅ Auto-approve |
| **Search by specialty** | 0.75 | Medium | ⚠️ User confirms if feature exists |
| **Booking history** | 0.70 | Medium | ⚠️ User confirms requirement |
| **Email notifications** | 0.85 | Low-Medium | ⚠️ User confirms notification method |

**Example Hallucination Alert**:
```markdown
## ⚠️ Potential Hallucination Detected - User Review Required

**Requirement**: US-005 Search trainers by specialty

**Confidence**: 0.75 (medium)

**Why Low Confidence?**:
- Client mentioned "see availability" but didn't explicitly say "search"
- "Specialty" not mentioned in transcript at all
- AI inferred this as standard PT booking feature

**Questions for User**:
1. Do trainers have specialties in the system?
2. Is search/filter needed, or is simple list sufficient?
3. Should this be deferred to v2?

**AI Recommendation**: Confirm with client before including in sprint
```

### User Review Checkpoint (15 min)

**User Reviews AI Output**:
1. Verifies explicit requirements match transcript ✅
2. Approves/rejects implicit requirements
3. Answers ambiguity questions
4. Flags any hallucinated features

**User Edits**:
```markdown
## User Feedback

**Approved**:
- ✅ US-001 through US-004 (all high confidence stories)

**Modified**:
- ⚠️ US-005 (Search) → Defer to Phase 2, just show alphabetical list for now

**Added**:
- ➕ US-006: Member cancel session (client forgot to mention, but needed)

**Answered Ambiguities**:
- Q: Booking advance time? → A: 2 weeks maximum
- Q: Session duration? → A: Fixed 60 minutes
- Q: Auto-accept? → A: Yes, no trainer approval needed
```

### Auto-Generate Requirements Traceability Matrix (3 min)

**AI Output**:
```markdown
## Requirements Traceability Matrix

| Req ID | User Story | BDD Scenario | Test Status | Implementation Status |
|--------|-----------|--------------|-------------|----------------------|
| US-001 | View Trainer Availability | `test_view_trainer_availability.feature` | ⏳ Pending | ⏳ Pending |
| US-002 | Book PT Session | `test_book_pt_session.feature` | ⏳ Pending | ⏳ Pending |
| US-003 | Trainer Block Time | `test_trainer_block_unavailable.feature` | ⏳ Pending | ⏳ Pending |
| US-004 | Trainer Cancel Session | `test_trainer_cancel_session.feature` | ⏳ Pending | ⏳ Pending |

**Auto-updated as**:
- `/qa` generates tests ({{CAPABILITIES_TEST_RUN_ALL}}) → Test Status: ✅ Pass
- Developer implements → Implementation Status: ✅ Done
```

---

## Phase 1: Requirements Elicitation **Skill**: /business-analyst

1. **Conduct Stakeholder Analysis**:
   - [ ] **Identify Stakeholders**:
     1. List all stakeholders (end-users, business owners, SMEs, developers)
     2. Document in table:
        | Stakeholder | Role | Influence (H/M/L) | Interest (H/M/L) |
        |-------------|------|-------------------|-------------------|
        | Jane (Gym Owner) | Decision Maker | H | H |
   - [ ] **Understand the Business Problem**:
     1. Ask: "What happens if we do nothing?" (establish urgency)
     2. Ask: "What does success look like in 6 months?" (define outcomes)
     3. Document in: `docs/requirements/problem_statement.md`

2. **Select Elicitation Technique(s)**:
   Based on project phase and stakeholder availability:

   **For Early Discovery** (use 2-3):
   - [ ] **Interviews** (one-on-one with key stakeholders)
     - Prepare 5-7 open-ended questions
     - Schedule 30-60 min sessions
     - Record (with permission) or take detailed notes
   - [ ] **Workshops** (collaborative session with 3-8 participants)
     - Create agenda (5-10 items)
     - Book room/Zoom + send calendar invites 48hrs ahead
     - Assign facilitator (not the note-taker)
   - [ ] **Document Analysis** (review existing materials)
     - Collect: project plans, user manuals, process diagrams
     - Flag: gaps, inconsistencies, outdated info

   **For Validation** (use 1-2):
   - [ ] **Surveys** (gather feedback from large audience)
     - Use Google Forms / Typeform
     - 5-10 questions max (avoid survey fatigue)
   - [ ] **Prototyping** (create mockups)
     - Tool: Figma, Balsamiq, or hand-drawn sketches
     - Get feedback: "Does this solve your problem?"

### Interview Script Template

**Purpose**: One-on-one stakeholder interview
**Duration**: 30-60 minutes
**Attendees**: BA + 1 stakeholder

**Pre-Interview**:
- Book calendar slot
- Send agenda 24hrs advance: "We'll discuss [topic] to understand [goal]"
- Prepare 5-7 open-ended questions

**Interview Structure**:

1. **Opening** (5 min)
   - Thank them for their time
   - State purpose: "I want to understand [X] so we can deliver [Y]"
   - Ask permission to record/take notes

2. **Discovery** (30-40 min)
   Ask open-ended questions:
   - "Walk me through how you currently [do task X]..."
   - "What frustrates you most about the current process?"
   - "If you had a magic wand, what would you change?"
   - "What happens if we don't build this feature?"
   - "Who else should I talk to about this?"

3. **Validation** (10 min)
   - Summarize: "So what I'm hearing is..."
   - Ask: "Did I miss anything?"
   - Confirm next steps

4. **Closing**
   - Thank them
   - Set expectation: "I'll send you my notes within 48hrs for review"

**Post-Interview**:
- Transcribe notes within 24hrs (while fresh)
- Send summary to interviewee for validation
- Update requirements traceability matrix

3. **Ask Clarifying Questions** (batch into one email/meeting):

   Use the **5 Ws + H** framework:

   **WHO:**
   - Who are the users? (personas)
   - Who are the stakeholders? (decision-makers)
   - Who will maintain this? (support team)

   **WHAT:**
   - What problem are we solving?
   - What does success look like? (metrics: e.g., "30% faster check-in")
   - What are we NOT building? (out of scope)

   **WHEN:**
   - When is this needed? (deadline)
   - When do users need this? (usage patterns: peak hours?)

   **WHERE:**
   - Where will this be used? (kiosk, mobile app, admin panel?)
   - Where is the data stored? (database, third-party API?)

   **WHY:**
   - Why now? (business driver)
   - Why this approach? (vs. alternatives)

   **HOW:**
   - How will we measure success? (KPIs: e.g., check-in time < 10 seconds)
   - How does this integrate with existing systems?

   **Example Email Template**:
   ```
   Subject: Clarifying Questions - Member Check-In Feature

   Hi [Stakeholder],

   To ensure we build the right solution, I need clarification on a few points:

   1. **Scope**: Should this support guest check-ins, or members only?
   2. **Priority**: Is QR code check-in a must-have for launch, or can we start with manual entry?
   3. **Timeline**: What's the latest acceptable launch date?
   4. **Success Metrics**: How will we know this feature is successful? (e.g., 80% of members use QR vs. manual?)

   Please reply by [date]. Happy to schedule a 15-min call if easier.

   Thanks,
   [Your Name]
   ```

4. **Elicit Non-Functional Requirements (NFRs)**:
   - [ ] **Performance**: What response time is acceptable? (e.g., "Check-in < 2 seconds")
   - [ ] **Scalability**: Expected user load? (e.g., "50 concurrent check-ins during 6-7pm")
   - [ ] **Security**: Authentication required? Data encryption? (e.g., "PCI DSS for payments")
   - [ ] **Compliance**: Regulations? (e.g., "GDPR for EU members")

5. **Define Data Requirements**:
   - [ ] Schema changes needed (new tables, columns)
   - [ ] Migration strategy for existing data
   - [ ] Data retention policy (how long to keep records)

---

## Phase 2: Requirements Documentation **Skill**: /business-analyst

6. Write user stories in standard format:
```markdown
As a [persona],
I want to [action],
So that [benefit].

Acceptance Criteria:
- Given [context], when [action], then [result]
- Given [context], when [action], then [result]
```

### User Story Quality Checklist (INVEST Criteria)

Before finalizing a user story, verify it meets INVEST criteria:

- [ ] **Independent**: Can this story be developed without depending on other stories?
  - ✅ Good: "As a member, I want to reset my password..."
  - ❌ Bad: "As a member, I want to receive a password reset email..." (depends on email service story)

- [ ] **Negotiable**: Is the implementation approach flexible (not prescribed)?
  - ✅ Good: "...so that I can regain access to my account" (outcome-focused)
  - ❌ Bad: "...using a 6-digit OTP sent via SMS" (solution-focused)

- [ ] **Valuable**: Does this deliver clear user or business value?
  - Ask: "What happens if we don't build this?" If answer is "nothing," re-evaluate.

- [ ] **Estimable**: Can the team estimate effort (story points or hours)?
  - If not: story is too vague OR team needs more context → Spike required

- [ ] **Small**: Can this be completed in one sprint (2 weeks)?
  - If not: Break into smaller stories (e.g., "Login" → "Email Login," "Social Login")

- [ ] **Testable**: Are acceptance criteria specific enough to write tests?
  - ✅ Good: "Given I enter correct credentials, when I click Login, then I see the Dashboard"
  - ❌ Bad: "The login should work properly"

<details>
<summary>📘 Example: INVEST-Compliant User Story</summary>

**Story**:
```markdown
As a gym member,
I want to check in using a QR code,
So that I can enter the gym without staff assistance during peak hours.

**Acceptance Criteria**:
- **Given** I have an active membership
  **When** I scan my QR code at the kiosk
  **Then** I see "Welcome, [Name]" and the gate opens

- **Given** my membership has expired
  **When** I scan my QR code
  **Then** I see "Membership expired. Please renew at reception."
  **And** the gate remains closed

- **Given** the system is offline
  **When** I scan my QR code
  **Then** I see "System unavailable. Please see reception."
```

**INVEST Check**:
- ✅ Independent (no dependency on other stories)
- ✅ Negotiable (QR code implementation details not prescribed)
- ✅ Valuable (reduces staff workload, improves member experience)
- ✅ Estimable (team can estimate ~5 story points)
- ✅ Small (fits in one sprint)
- ✅ Testable (clear Given-When-Then scenarios)
</details>

7. Create a requirements traceability matrix:

| ID | Requirement | Source | Priority | Status |
|----|-------------|--------|----------|--------|
| R1 | ... | Stakeholder X | Must | Draft |

---

## Phase 3: Gap Analysis **Skill**: /business-analyst

8. **Perform Gap Analysis**:

   **Step 1: Catalog Existing Functionality**
   ```bash
   # List all API endpoints
   grep -r "@app.get\|@app.post" {{PATH_PRESENTATION}}/api/ --include="*.py"

   # List all database tables
   grep "class.*Base" {{PATH_DOMAIN}}/models.py
   ```
   Document in table:
   | Feature | Exists? | Reusable? | Modification Needed |
   |---------|---------|-----------|---------------------|
   | Member CRUD | ✅ Yes | ✅ Yes | Add `qr_code` field |

   **Step 2: Identify Completely New Components**
   - [ ] New database tables? (list them)
   - [ ] New API endpoints? (list routes)
   - [ ] New UI pages? (list views)
   - [ ] Third-party integrations? (list APIs: e.g., Twilio, Stripe)

   **Step 3: Document Effort Estimate**
   | Component | Effort | Complexity (S/M/L) |
   |-----------|--------|---------------------|
   | Add `members.qr_code` column | 1 hour | S |
   | QR generation API | 4 hours | M |
   | Kiosk UI | 8 hours | L |

9. Identify risks and assumptions:

| Assumption | Impact if Wrong | Mitigation |
|------------|-----------------|------------|
| Users have modern browsers | UI may break | Add browser check |

---

## Phase 4: Validation **Skill**: /business-analyst

10. Review with stakeholders:
    - [ ] Requirements complete and unambiguous?
    - [ ] Acceptance criteria testable?
    - [ ] Dependencies identified?
    - [ ] Estimates reasonable?

11. Create Definition of Done:
    - [ ] Code complete and reviewed
    - [ ] Tests passing (unit + integration)
    - [ ] Documentation updated
    - [ ] Deployed to staging
    - [ ] Stakeholder sign-off

---

## Expected Deliverables

Upon completing this workflow, produce the following artifacts:

1. **User Stories** (`docs/requirements/user_stories/US-NNN.md`)
   - Format: "As a [persona], I want [action], so that [benefit]"
   - INVEST-compliant (verified via checklist)
   - Acceptance criteria in Given-When-Then format
   - Story points estimated (Fibonacci: 1, 2, 3, 5, 8, 13)
   - Example filename: `US-042-member-qr-checkin.md`

2. **Requirements Traceability Matrix** (`docs/REQUIREMENTS_TRACEABILITY.md`)
   | Req ID | User Story | Source | Priority | Status | Test Cases |
   |--------|------------|--------|----------|--------|------------|
   | R-MEM-01 | US-042 | Gym Owner | Must Have | Draft | TC-042-01, TC-042-02 |

3. **Stakeholder Analysis** (`docs/requirements/stakeholders.md`)
   | Name | Role | Influence | Interest | Communication Frequency |
   |------|------|-----------|----------|-------------------------|
   | Jane | Gym Owner | High | High | Weekly (Sprint Review) |

4. **Risk & Assumption Log** (`docs/requirements/risks.md`)
   | ID | Risk/Assumption | Impact if Wrong | Probability | Mitigation |
   |----|-----------------|-----------------|-------------|------------|
   | A-001 | Members have smartphones | Low QR adoption | Medium | Provide fallback (staff check-in) |

5. **Definition of Done** (agreed with team, documented in user story)
   ```markdown
   ## Definition of Done
   - [ ] Code complete and peer-reviewed
   - [ ] Unit tests passing (coverage ≥ 80%)
   - [ ] Integration tests added
   - [ ] API documentation updated
   - [ ] User acceptance testing (UAT) passed
   - [ ] Deployed to TEST environment
   - [ ] Product Owner sign-off
   ```

---

## Anti-patterns to Avoid
- ❌ Solutioning before understanding the problem
- ❌ Accepting vague requirements ("make it better")
- ❌ Skipping acceptance criteria
- ❌ Gold-plating (adding unrequested features)
