---
plan: 02-05
phase: 02-core-pipeline-scout-through-writer
status: complete
completed_at: "2026-02-26"
---

# 02-05 Summary: Writer Agent — MCQ Personalization, Email Generation, CAN-SPAM

## What Was Built

Complete `src/ingot/agents/writer.py` — the final production step before the review queue.
Two PydanticAI agents, MCQ optional flow, tone-aware email generation, CAN-SPAM footer, SQLite persistence.

## Key Files

### Created / Modified
- `src/ingot/agents/writer.py` — full Phase 2 rewrite (Phase 1 stub replaced)

## Implementation Details

### Model Assignments
- `mcq_agent`: `anthropic:claude-3-5-haiku-latest` — cheap for question generation
- `writer_agent`: `anthropic:claude-3-5-sonnet-20241022` — higher quality for email composition
- Both use `defer_model_check=True` (codebase convention — API key validated at runtime, not import)

### Recipient Type Detection (role keyword routing)
```python
role_lower = (brief.person_role or "").lower()
if any(t in role_lower for t in ["hr", "recruit", "talent", "people"]):
    recipient_type = "hr"
elif any(t in role_lower for t in ["cto", "vp eng", "engineering", "tech lead"]):
    recipient_type = "cto"
elif any(t in role_lower for t in ["ceo", "founder", "co-founder", "president"]):
    recipient_type = "ceo"
else:
    recipient_type = "default"
```
Stored on `lead.__dict__["_resolved_recipient_type"]` for persistence (set during system prompt injection, read in `run_writer()`).

### Tone Differentiation
- **HR**: Medium length (150-250w), credentials prominently highlighted, formal, process-focused
- **CTO**: Short (80-150w), direct/technical, peer-to-peer, strong hook first
- **CEO**: Short (80-150w), mission-focused, genuine observation, one fast-mover credential
- **Default**: Short-medium (100-200w), professional but direct (same brevity as CTO/CEO)

### CAN-SPAM Footer Structure
Three FTC-mandated elements (15 U.S.C. § 7704):
```
---
This email was sent by {sender_name} <{sender_email}>.
{physical_address}

Not interested? Reply with 'unsubscribe' to be removed from future outreach.
```
- `physical_address` comes from `ConfigManager().load().mailing_address` via `WriterDeps.physical_address`
- Empty address: issues `UserWarning` with setup instructions, inserts placeholder (does NOT raise)

### MCQ Flow
- `questionary.confirm()` gate — MCQ is skippable (returns `MCQAnswers(answers={}, skipped=True)`)
- When run: `mcq_agent` generates 2-3 questions from `IntelBriefFull` (company-specific, not hardcoded)
- `questionary.text()` collects each answer; empty answers are not stored
- Returns `MCQAnswers(answers={q: a}, skipped=False)`

### FollowUp Persistence
- `FollowUp(scheduled_for_day=3)` and `FollowUp(scheduled_for_day=7)` both created with `FollowUpStatus.queued`
- Both linked to `Email.id` via `parent_email_id` foreign key
- CAN-SPAM footer appended to `Email.body` before insert (stored once, not duplicated in follow-ups)

### run_writer() Signature
```python
async def run_writer(deps: WriterDeps, retrigger_mcq: bool = False) -> EmailDraft
```
- `retrigger_mcq=True` re-runs MCQ flow before generation (WRITER-13 reject/regenerate path)
- Used by Orchestrator (02-06) for the rejection loop

## Requirements Coverage

All WRITER-01 through WRITER-13 addressed:
- WRITER-01/02: MCQ optional flow with questionary confirm gate
- WRITER-03/04: LLM-generated questions from IntelBriefFull (not hardcoded)
- WRITER-05/06/07/08: Tone differentiation for hr/cto/ceo/default
- WRITER-09: followup_day3 + followup_day7 in EmailDraft and FollowUp persistence
- WRITER-10: CAN-SPAM footer with all 3 mandatory elements
- WRITER-11/12: Email + FollowUp SQLite persistence; Lead.status → "drafted"
- WRITER-13: retrigger_mcq parameter on run_writer()

## Self-Check: PASSED

- ✓ mcq_agent generates questions from IntelBrief context (not templates)
- ✓ run_mcq() returns MCQAnswers(skipped=True) when user declines
- ✓ _TONE_PROMPTS has all 4 keys with meaningfully different content
- ✓ writer_agent output_type=EmailDraft; mcq_agent output_type=MCQQuestions
- ✓ run_writer() is async; persists Email + 2 FollowUp records; sets Lead.status="drafted"
- ✓ build_can_spam_footer() has sender identity, physical address, unsubscribe mechanism
- ✓ Both agents use defer_model_check=True
