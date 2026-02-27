"""
Writer Agent — Email generation with MCQ personalization flow.

Two-agent pipeline:
  1. mcq_agent (factory): LLM-generates 2-3 personalized questions from IntelBriefFull
     Questions reference specific company context (funding, product, person background)
     NOT hardcoded templates (Pitfall in 02-RESEARCH.md Anti-Patterns)
  2. writer_agent (factory): Generates EmailDraft from Lead + IntelBriefFull + UserProfile + MatchResult + MCQ answers
     Tone adapts by recipient_type: HR (longer, credentials) | CTO/CEO (shorter, direct)
     Produces: body, subject_a, subject_b, followup_day3, followup_day7, can_spam_footer

Both agents are created via factory functions (create_mcq_agent / create_writer_agent) so the
Orchestrator can inject the model string from ConfigManager at runtime. No hardcoded model
strings at module level.

MCQ is OPTIONAL (LOCKED DECISION from 02-CONTEXT.md):
  - User can skip MCQ; writer generates from IntelBrief + match data alone (AI defaults)
  - Skip is the genuine option, not a fallback — AI defaults produce reasonable emails

CAN-SPAM compliance (WRITER-10):
  Three mandatory elements (FTC requirement, $51,744/email fine for violations):
  1. Sender identity (name + email)
  2. Physical postal address or registered PO box
  3. Clear unsubscribe mechanism (link or instruction)
"""
# AGENT-05: This module MUST NOT import from other agent modules.
# Only Orchestrator coordinates between agents.
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone

import questionary
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from ingot.agents.registry import register_agent
from ingot.db.models import Email, EmailStatus, FollowUp, FollowUpStatus, Lead, LeadStatus
from ingot.models.schemas import EmailDraft, IntelBriefFull, MatchResult, MCQAnswers, UserProfile


@dataclass
class WriterDeps:
    user_profile: UserProfile
    intel_brief: IntelBriefFull
    match_result: MatchResult
    lead: Lead
    session: AsyncSession
    mcq_answers: MCQAnswers = field(default_factory=lambda: MCQAnswers(answers={}, skipped=True))
    sender_name: str = ""        # From config — used in CAN-SPAM footer
    sender_email: str = ""       # From config — used in CAN-SPAM footer
    physical_address: str = ""   # From setup wizard config — REQUIRED for CAN-SPAM
    resolved_recipient_type: str = "default"  # set by inject_writer_context; read by run_writer


# ---------------------------------------------------------------------------
# MCQ Question Generator — local output schema
# ---------------------------------------------------------------------------

class MCQQuestions(BaseModel):
    """LLM-generated questions from IntelBriefFull context."""

    questions: list[str]  # 2-3 questions referencing IntelBrief specifics


# ---------------------------------------------------------------------------
# Static system prompt strings (shared across factory calls)
# ---------------------------------------------------------------------------

_MCQ_STATIC_PROMPT = (
    "You are generating personalized MCQ questions to help craft a cold outreach email. "
    "Generate EXACTLY 2-3 questions. "
    "\n\n"
    "QUESTION TYPES (per 02-CONTEXT.md):\n"
    "  1. Personalization hook: What genuinely interests the sender about THIS company? "
    "     Reference a specific company signal, product, or milestone from the IntelBrief.\n"
    "  2. Tone/intent: What is the goal? (informational interview / direct job ask / connection request)\n"
    "  3. Optional: A specific experience connection ('Which of your projects relates most to their challenge?')\n"
    "\n"
    "RULES:\n"
    "  - Every question MUST reference specific IntelBrief data (company name, product, person name, signal)\n"
    "  - NO generic questions like 'What interests you about this company?' without referencing specifics\n"
    "  - Questions should be answerable in 1-2 sentences\n"
    "  - Maximum 3 questions total"
)

_WRITER_STATIC_PROMPT = (
    "You are an expert at writing personalized cold outreach emails. "
    "Generate a complete EmailDraft with: subject_a, subject_b, body, "
    "followup_day3, followup_day7, can_spam_footer. "
    "\n\n"
    "RULES:\n"
    "1. NEVER use generic phrases: 'I would be a great fit', 'I am passionate about', "
    "'I came across your company online', 'I am reaching out to express interest'.\n"
    "2. body MUST reference the company by name AND include at least one talking point.\n"
    "3. subject_a and subject_b must both reference the company or person — not generic.\n"
    "   Subject A: direct (e.g., 'RE: {company} backend infra')\n"
    "   Subject B: curiosity/question (e.g., 'Question about your API platform at {company}')\n"
    "4. followup_day3: Slightly warmer tone, adds a new talking point or insight.\n"
    "5. followup_day7: Brief, low-pressure final nudge. Do NOT threaten or pressure.\n"
    "6. can_spam_footer: Include the provided footer EXACTLY as given — do not modify it.\n"
    "7. Apply the tone guidance provided in your system context."
)


# ---------------------------------------------------------------------------
# Agent factories — called by Orchestrator with model from ConfigManager
# ---------------------------------------------------------------------------

def create_mcq_agent(model: str) -> Agent[WriterDeps, MCQQuestions]:
    """
    Factory — returns a configured MCQ question generator agent.

    Called by the Orchestrator with the model string from ConfigManager:
        agent = create_mcq_agent(config.agents["writer"].model)
    """
    agent: Agent[WriterDeps, MCQQuestions] = Agent(
        model,
        deps_type=WriterDeps,
        output_type=MCQQuestions,
        defer_model_check=True,
        system_prompt=_MCQ_STATIC_PROMPT,
    )

    @agent.system_prompt
    async def inject_brief_for_mcq(ctx: RunContext[WriterDeps]) -> str:
        brief = ctx.deps.intel_brief
        return (
            f"\n\nCOMPANY CONTEXT FOR QUESTIONS:\n"
            f"Company: {brief.company_name}\n"
            f"Product: {brief.company_product_description}\n"
            f"Contact: {brief.person_name} — {brief.person_role}\n"
            f"Signals: {'; '.join(brief.company_signals[:3])}\n"
            f"Talking points:\n" + "\n".join(f"  - {tp}" for tp in brief.talking_points)
        )

    return agent


def create_writer_agent(model: str) -> Agent[WriterDeps, EmailDraft]:
    """
    Factory — returns a configured email writer agent.

    Called by the Orchestrator with the model string from ConfigManager:
        agent = create_writer_agent(config.agents["writer"].model)
    """
    agent: Agent[WriterDeps, EmailDraft] = Agent(
        model,
        deps_type=WriterDeps,
        output_type=EmailDraft,
        defer_model_check=True,
        system_prompt=_WRITER_STATIC_PROMPT,
    )

    @agent.system_prompt
    async def inject_writer_context(ctx: RunContext[WriterDeps]) -> str:
        """Inject all writer context: profile, intel brief, match result, MCQ answers, tone."""
        deps = ctx.deps
        profile = deps.user_profile
        brief = deps.intel_brief
        match = deps.match_result
        mcq = deps.mcq_answers

        # Determine tone from person_role
        role_lower = (brief.person_role or "").lower()
        if any(t in role_lower for t in ["hr", "recruit", "talent", "people"]):
            recipient_type = "hr"
        elif any(t in role_lower for t in ["cto", "vp eng", "engineering", "tech lead"]):
            recipient_type = "cto"
        elif any(t in role_lower for t in ["ceo", "founder", "co-founder", "president"]):
            recipient_type = "ceo"
        else:
            recipient_type = "default"

        # Tone detection priority: HR > CTO > CEO > default
        # (e.g. "VP Engineering & Talent Acquisition" matches "talent" → HR, which is correct)
        tone_guidance = _TONE_PROMPTS[recipient_type]
        deps.resolved_recipient_type = recipient_type

        if not mcq.skipped and mcq.answers:
            mcq_section = "\nMCQ ANSWERS (user's personalization input):\n"
            for q, a in mcq.answers.items():
                mcq_section += f"  Q: {q}\n  A: {a}\n"
        else:
            mcq_section = "\nMCQ: Skipped — generate from IntelBrief and match data alone.\n"

        footer = build_can_spam_footer(
            sender_name=deps.sender_name or profile.name,
            sender_email=deps.sender_email,
            physical_address=deps.physical_address,
            company_name=brief.company_name,
        )

        return (
            f"\n\nTONE GUIDANCE ({recipient_type.upper()}):\n{tone_guidance}\n"
            f"\nSENDER (the user):\n"
            f"  Name: {profile.name}\n"
            f"  Headline: {profile.headline}\n"
            f"  Skills: {', '.join(profile.skills[:8])}\n"
            f"  Experience: {'; '.join(profile.experience[:3])}\n"
            f"\nRECIPIENT:\n"
            f"  Name: {brief.person_name or 'the team'}\n"
            f"  Role: {brief.person_role or 'unknown'}\n"
            f"  Company: {brief.company_name}\n"
            f"  Product: {brief.company_product_description}\n"
            f"  Contact background: {brief.person_background}\n"
            f"\nTALKING POINTS (use at least one):\n"
            + "\n".join(f"  {i+1}. {tp}" for i, tp in enumerate(brief.talking_points))
            + f"\nVALUE PROPOSITION: {match.value_proposition}\n"
            + mcq_section
            + f"\nCAN-SPAM FOOTER (include EXACTLY):\n{footer}\n"
        )

    return agent


# ---------------------------------------------------------------------------
# CAN-SPAM Footer Builder
# ---------------------------------------------------------------------------

def build_can_spam_footer(
    sender_name: str,
    sender_email: str,
    physical_address: str,
    company_name: str = "",
) -> str:
    """
    Build a CAN-SPAM compliant email footer.

    THREE MANDATORY ELEMENTS (FTC CAN-SPAM Act, 15 U.S.C. § 7704):
    1. Sender identity (name + email address)
    2. Physical postal address or registered PO box (MUST include street/city/state/zip)
    3. Clear unsubscribe mechanism

    WARNING: Physical address is NOT optional. $51,744 per violating email.
    Collect from setup wizard (INFRA-04) via ConfigManager.

    If physical_address is empty, uses a placeholder and logs a warning.
    """
    if not physical_address or not physical_address.strip():
        physical_address = "[YOUR PHYSICAL ADDRESS — configure in setup wizard]"
        warnings.warn(
            "CAN-SPAM footer: physical_address is empty. "
            "Run 'ingot config setup' to set your mailing address.",
            stacklevel=2,
        )

    footer_parts = [
        "---",
        f"This email was sent by {sender_name} <{sender_email}>.",
        f"{physical_address}",
        "",
        "Not interested? Reply with 'unsubscribe' to be removed from future outreach.",
    ]
    return "\n".join(footer_parts)


# ---------------------------------------------------------------------------
# Tone System Prompts (from 02-CONTEXT.md LOCKED DECISIONS)
# ---------------------------------------------------------------------------

_TONE_PROMPTS: dict[str, str] = {
    "hr": (
        "You are writing a cold outreach email to an HR or recruiting professional. "
        "TONE: Professional, process-focused, slightly formal. "
        "LENGTH: Medium (150-250 words) — HR readers expect substance. "
        "STRUCTURE: Opening (why you're reaching out) -> Credentials section (highlight relevant experience) "
        "-> Specific skill match -> Clear ask (interview, call, or application process). "
        "Mention relevant experience prominently — HR is evaluating fit against a job spec."
    ),
    "cto": (
        "You are writing a cold outreach email to a CTO or technical lead. "
        "TONE: Direct, technical, peer-to-peer. Skip corporate pleasantries. "
        "LENGTH: Short (80-150 words) — CTOs are busy and respect brevity. "
        "STRUCTURE: Strong hook (specific technical observation about their stack or product) "
        "-> 1-2 specific technical credentials -> One talking point -> Direct ask. "
        "Do NOT list skills like a resume. Show technical judgment instead."
    ),
    "ceo": (
        "You are writing a cold outreach email to a CEO or founder. "
        "TONE: Visionary, culture-and-mission focused, direct. "
        "LENGTH: Short (80-150 words) — founders receive many emails, respect directness. "
        "STRUCTURE: Opening (genuine observation about company mission or achievement) "
        "-> Why you specifically want to join THIS company (not generic) "
        "-> One credential that shows you can move fast -> Clear ask. "
        "Avoid credential lists. Focus on fit and excitement."
    ),
    "default": (
        "You are writing a cold outreach email to a professional whose exact role is unknown. "
        "TONE: Professional but direct. "
        "LENGTH: Short to medium (100-200 words). "
        "STRUCTURE: Brief intro -> Specific observation about the company -> Relevant experience "
        "-> Clear ask. Avoid corporate filler language."
    ),
}


# ---------------------------------------------------------------------------
# Orchestration functions
# ---------------------------------------------------------------------------

async def run_mcq(
    deps: WriterDeps,
    model: str,
) -> MCQAnswers:
    """
    Run the optional MCQ flow for personalization.

    LOCKED DECISION (02-CONTEXT.md):
    - MCQ is optional — confirm with user before running
    - If skipped, returns MCQAnswers(answers={}, skipped=True)
    - When run, questions are LLM-generated from IntelBriefFull (not hardcoded)

    Args:
        deps: Writer dependencies including IntelBriefFull.
        model: LLM model string from ConfigManager (e.g. "anthropic:claude-3-5-haiku-latest").
    """
    run_mcq_flag = questionary.confirm(
        f"Run personalization questions for {deps.intel_brief.company_name}? "
        f"(recommended, or press Enter to skip)",
        default=True,
    ).ask()

    if not run_mcq_flag:
        return MCQAnswers(answers={}, skipped=True)

    agent = create_mcq_agent(model)
    result = await agent.run(
        "Generate personalized MCQ questions for this lead's outreach email.",
        deps=deps,
    )
    questions: list[str] = result.output.questions

    answers: dict[str, str] = {}
    for q in questions:
        answer = questionary.text(q, default="").ask()
        if answer and answer.strip():
            answers[q] = answer.strip()

    return MCQAnswers(answers=answers, skipped=False)


async def run_writer(
    deps: WriterDeps,
    model: str,
    mcq_model: str,
    retrigger_mcq: bool = False,
) -> EmailDraft:
    """
    Run the Writer pipeline for a single Lead.

    Args:
        deps: Writer dependencies.
        model: LLM model string for the writer agent (from ConfigManager).
        mcq_model: LLM model string for the MCQ agent (from ConfigManager).
        retrigger_mcq: If True (WRITER-13), re-runs MCQ before generation.

    Persists Email + FollowUp(day=3) + FollowUp(day=7) to SQLite.
    Transitions Lead.status -> 'drafted'.
    Returns EmailDraft.
    """
    lead = deps.lead

    # WRITER-13: retrigger MCQ if requested (reject/regenerate with different angle)
    if retrigger_mcq:
        deps.mcq_answers = await run_mcq(deps, model=mcq_model)

    agent = create_writer_agent(model)
    result = await agent.run(
        "Generate the complete email draft set for this lead.",
        deps=deps,
    )
    draft: EmailDraft = result.output

    # Determine recipient type (set by inject_writer_context via deps.resolved_recipient_type)
    recipient_type = deps.resolved_recipient_type

    # Persist Email record (WRITER-11, DB-05)
    email_record = Email(
        subject_a=draft.subject_a,
        subject_b=draft.subject_b,
        body=f"{draft.body}\n\n{draft.can_spam_footer}",  # CAN-SPAM footer appended
        tone_adapted_for=recipient_type,
        mcq_answers_json=json.dumps(deps.mcq_answers.answers),
        status=EmailStatus.drafted,
        lead_id=lead.id,
        created_at=datetime.now(timezone.utc),
    )
    deps.session.add(email_record)
    # flush (not commit) to get the DB-assigned email_record.id while keeping
    # Email + FollowUps + Lead status update in a single atomic transaction
    await deps.session.flush()
    assert email_record.id is not None, "DB failed to assign email.id after flush"

    # Persist Day 3 follow-up (WRITER-09, DB-06)
    followup_day3 = FollowUp(
        parent_email_id=email_record.id,
        scheduled_for_day=3,
        body=draft.followup_day3,
        status=FollowUpStatus.queued,
        created_at=datetime.now(timezone.utc),
    )
    # Persist Day 7 follow-up (WRITER-09, DB-06)
    followup_day7 = FollowUp(
        parent_email_id=email_record.id,
        scheduled_for_day=7,
        body=draft.followup_day7,
        status=FollowUpStatus.queued,
        created_at=datetime.now(timezone.utc),
    )
    deps.session.add(followup_day3)
    deps.session.add(followup_day7)

    # Transition Lead status
    lead.status = LeadStatus.drafted
    deps.session.add(lead)

    await deps.session.commit()
    await deps.session.refresh(email_record)
    return draft


register_agent("writer", run_writer)
