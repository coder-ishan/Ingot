# Phase 2: Core Pipeline (Scout through Writer) - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the full pipeline from YC lead discovery through email drafts sitting in a review queue: Scout (discover + score leads) → Research (two-phase intel with approval gate) → Matcher (match score + value prop) → Writer (MCQ flow + email generation) → Review Queue (approve/edit/reject/regenerate). No sending required. The done condition is 10 personalized email drafts the user would actually send, sitting in the review queue.

</domain>

<decisions>
## Implementation Decisions

### Review Queue UX
- **Entry point:** Show a list view table first (lead name, company, status: pending/approved/rejected). User picks which lead to deep-dive.
- **Navigation:** One lead at a time when deep-diving — present the full draft set (subject line variants, body, Day 3 + Day 7 follow-ups) for that lead, then prompt for action.
- **Inline editing:** Use Rich text input (no external editor dependency). User re-types or pastes revised draft in the terminal.
- **Regeneration:** Silent re-run — writer re-generates with same MCQ answers + different seed. No additional prompts before regenerating.

### MCQ Writer Flow
- **MCQ is optional:** If the user skips the MCQ step, the writer generates using IntelBrief + match data alone (AI defaults). No forced interaction.
- **When MCQ is used, question types:** Personalization hooks (what genuinely interests you about this company, referencing IntelBrief specifics) and tone/intent (informational interview vs. direct job ask vs. connection request).
- **Question generation:** Dynamically generated per lead from the IntelBrief — questions reference specific company context (e.g., recent funding, product pivot, tech stack noted). Not a fixed template.
- **Email length/tone adapts by recipient type:**
  - HR: slightly longer, highlights credentials, relevant experience prominently
  - CTO/CEO: shorter and more direct, strong hook, minimal credentials, clear ask
  - Default to shorter and direct if recipient type is unknown

### Lead Sourcing & Filtering
- **Targeting priority:** Companies whose tech stack or domain overlaps with the user's resume skills. Stack/domain match is the primary relevance signal.
- **Leads per run:** 10-20 leads surfaced by default.
- **Initial scoring formula:** Build a documented, weighted multi-factor formula. Factors and example weights (planner to finalize and document in code):
  - Stack/domain match vs. resume skills: ~40%
  - Company stage (seed/Series A preferred for impact): ~25%
  - Job listing keyword match (if available): ~20%
  - Company description semantic similarity to resume: ~15%
  - Formula weights must be documented in code and in a planning note so they can be tuned.
- **Deduplication:** By contact email, case-insensitive. If a lead's email already exists in SQLite (any status), skip it on subsequent runs.

### Claude's Discretion
- Exact Rich component choices (Panel, Table, Prompt styles) within the list view and deep-dive UX
- Exact scoring formula weights (guided by the ~% ranges above, but planner can adjust based on research)
- Checkpoint/resume implementation details for the Orchestrator
- CAN-SPAM footer exact content
- Subject line generation strategy (both variants)

</decisions>

<specifics>
## Specific Ideas

- The scoring formula is intentionally visible and tunable — weights should not be buried in code but documented (in a config, a docstring, or a planning artifact) so the user can adjust them over time.
- The MCQ flow should feel lightweight enough that skipping it is a genuine option, not a fallback. AI defaults should produce reasonable emails without MCQ input.
- Email tone differentiation (HR vs. CTO/CEO) is meaningful, not cosmetic — length, credential emphasis, and directness should visibly differ.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-core-pipeline-scout-through-writer*
*Context gathered: 2026-02-26*
