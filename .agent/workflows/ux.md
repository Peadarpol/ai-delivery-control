---
description: Usability, accessibility (A11y), and user interface design
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Usability, accessibility (A11y), and user interface design
---

# /ux - UX Engineer Workflow

## 0. Pre-Task Anti-Hallucination Check
Before designing or auditing, you **MUST** verify the current styling standards:

| Artifact | Purpose | Placeholder |
| :--- | :--- | :--- |
| **Styling Audit** | Current branding & accessibility review | `{{PATH_STYLING_AUDIT}}` |
| **Technical Spec** | UI architecture & project structure | `{{PATH_TECH_SPEC}}` |
| **AI Guidelines** | UX/UI specific AI guidelines | `{{PATH_AGENT_GUIDELINES}}` |

**Verification Steps:**
1. [ ] Review `{{PATH_STYLING_AUDIT}}` to ensure alignment with active multi-tenant brands.
2. [ ] Check Section 2.2 of `{{PATH_TECH_SPEC}}` for UI layer responsibilities.

---

## Trigger
Use when: designing new interfaces, auditing usability, fixing accessibility issues, or analyzing user flows.

## Mindset
- **Empathy** - Advocate for the user, not the system
- **Inclusivity** - Accessibility is not optional (WCAG 2.1 AA)
- **Consistency** - Adhere to design systems and branding
- **Simplicity** - Less is more; reduce cognitive load

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all usability audits, accessibility checks, and UI design tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human)**: ~10 hours
- **AI Automated**: ~13 min
- **User Time**: 5 min (review results)

### Automated Design Validation

**AI scans code/components for issues** (2 min):

```bash
# Automated UX Checks
- ✅ WCAG 2.1 AA Compliance (Contrast, ARIA, Focus)
- ✅ Mobile Responsiveness (Media queries present)
- ✅ Touch Target Sizing (Min 44px/48px checks)
- ✅ Error State Definitions (Input validation msgs)
- ✅ Loading State Definitions (Skeletons/Spinners)
```

**Auto-Flagging Issues**:
- "⚠️ Button `.submit-btn` contrast is 3.5:1 (Fail). Change bg to `#2A4B8D` for 4.5:1?"
- "⚠️ Image `hero.png` missing `alt` text. Suggested: 'Gym interior with treadmills'."

**White Label Hardcoding Detection**:
- "❌ Found hardcoded color `#FF0000` in `login.py`. Replace with `os.getenv('KIOSK_PRIMARY_COLOR')`?"
- "❌ Found hardcoded font `Arial` in `custom.css`. Use `var(--font-family)`."

### User Approval Checkpoints

**Always Require User Approval**:
1.  **Major Layout Shifts**:
    - "Proposed changing 'Grid Layout' to 'List Layout' for Mobile key screens. Approve?"

2.  **Copy Tone Changes**:
    - "Rewrote error messages to be 'friendlier'. Review?"

**Never Require User Approval** (AI handles autonomously):
- Generating ARIA labels for icons
- Adjusting hex codes for contrast compliance
- Adding missing `type="button"` attributes
- Optimizing image compression

### Heuristic Analysis Engine

**AI evaluates user flows against heuristics**:

| Heuristic | Check | AI Finding |
|-----------|-------|------------|
| Visibility Status | Loaders? | ✅ "Skeleton loader present on Dashboard" |
| Match Real World | Jargon? | ⚠️ "Found 'Auth Token expired'. Suggest: 'Session timed out'" |
| User Control | Undo? | ❌ "Delete Member has no Undo action. Suggest removing immediate delete." |
| Consistency | Design Sys? | ✅ "All buttons use `.btn-primary` class." |

### Responsive Design Simulation

**AI analyzes CSS logic**:
- **Desktop (>1024px)**: "Sidebar verified visible."
- **Tablet (768px-1024px)**: "Sidebar verified collapsed to hamburger."
- **Mobile (<768px)**: "Menu verified full-screen overlay."
- **Kiosk (Touch)**: "Touch targets verified > 48px."

---

## Phase 1: UX Audit & Discovery **Skill**: /ux

1. Heuristic Evaluation (Jakob Nielsen's 10 Heuristics):
   - [ ] Visibility of system status (Loaders/Messages?)
   - [ ] Match between system and real world (Language?)
   - [ ] User control and freedom (Undo/Exit?)
   - [ ] Consistency and standards (Design system?)
   - [ ] Error prevention & recovery
   - [ ] Aesthetics and minimalist design

2. Accessibility Check (A11y):
   - [ ] Color contrast (> 4.5:1 for normal text)
   - [ ] Keyboard navigation (Tab order logical?)
   - [ ] Screen reader compatibility (ARIA labels?)
   - [ ] Focus states visible?

   *Tool Suggestion:* Use Lighthouse or Axe-core.

---

## Phase 2: Design **Skill**: /ux

3. Wireframing/Prototyping:
   - Define user flow steps
   - Sketch layout (Mobile-first if applicable)
   - Define component hierarchy

4. Branding & Interface Specifics:

   **A. Public Kiosk (Touch Interface)**:
   - [ ] **Touch Targets**: Min 48x48px (approx 10-15mm physical size)
   - [ ] **Placement**: Interactive elements in "reach zone" (15-48" from floor)
   - [ ] **Simplicity**: One primary action per screen
   - [ ] **Feedback**: Immediate visual/audio response to touch

   **B. Admin Dashboard**:
   - [ ] **Information Density**: "Inverted Pyramid" - Key KPIs at top
   - [ ] **Navigation**: Sidebar for context switching; Breadcrumbs for depth
   - [ ] **Data Viz**: Tooltips for granular data; clear axis labels
   - [ ] **Responsiveness**: Collapsible menus on smaller screens

   **C. White Label Compatibility**:
   - [ ] **Dynamic Colors**: Verify no hardcoded hex codes in components (use `st.secrets` or `os.getenv`).
   - [ ] **Variable Geometry**: Elements must look good with both `0px` and `20px` border-radius.
   - [ ] **Logo Area**: Header must support variable aspect ratio logos.
   - [ ] **Reference**: See `{{PATH_DOCS}}/deployment/BRANDING_GUIDE.md` for constraints.

---

## Phase 3: Implementation Guidance **Skill**: /ux

5. CSS/Frontend Recommendations:
   - "Use Flexbox for this layout to ensure responsiveness."
   - "Add `aria-label='Close'` to the icon button."
   - "Ensure feedback message persists for at least 3 seconds."

6. Review Code (Frontend):
   - Check HTML semantic correctness (`<button>` not `<div>`)
   - Verify responsive behavior triggers (media queries)

---

## Phase 4: Validation **Skill**: /ux

7. Usability Testing:
   - "Can a user complete the task 'Book a PT Session' in under 30 seconds?"
   - Observe error rates and confusion points.

8. Metrics to Watch:
   - Time on task
   - Completion rate
   - Click error rate
