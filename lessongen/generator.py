"""Generator: writes (or rewrites) the lesson.

On a retry it receives the previous lesson plus the evaluator's failure reasons and must say
what it changed. Memory (learned guidelines + human feedback) is injected on every attempt.
"""
import re

from .config import AUDIENCE

SYSTEM = (
    "You are an expert teacher who writes lessons for beginners who are learning in a second "
    "language. You write in very simple, warm, clear English. You teach with everyday examples "
    "from life in India. You never invent facts: you only use the FACT SHEET given to you."
)

CHANGES_MARK = "===CHANGES==="


def build_prompt(topic, rubric, facts, guidelines, human_feedback, previous=None, feedback=None) -> str:
    reqs = "\n".join(f"- {cp['requirement']}" for cp in rubric["checkpoints"])
    parts = [
        f"TOPIC: {topic}",
        f"LEARNER: {AUDIENCE}",
        "TASK: Write a standalone beginner lesson on the topic. After reading it, the learner should "
        "understand what it is, why it matters, and how it works.",
        f"FACT SHEET (your only source of truth; do not contradict it, do not add numbers or names "
        f"that are not in it):\n{facts}",
        f"QUALITY BAR (an independent grader will check ALL of these, pass or fail):\n{reqs}",
        "STYLE: Use short sentences. Use common words. Explain every technical term in the same "
        "sentence where it first appears. Use markdown headings (##). Start with one # title.",
    ]
    if guidelines:
        parts.append("LESSONS LEARNED FROM PAST FAILURES (follow these):\n" + "\n".join(f"- {g}" for g in guidelines))
    if human_feedback:
        parts.append("FEEDBACK FROM A HUMAN REVIEWER (follow this):\n" + "\n".join(f"- {f}" for f in human_feedback))
    if previous is not None and feedback:
        parts.append(
            "PREVIOUS ATTEMPT FAILED the grader. Here is the previous lesson:\n"
            f"<previous_lesson>\n{previous}\n</previous_lesson>\n\n"
            f"These checkpoints FAILED:\n{feedback}\n\n"
            "Rewrite the lesson so that every failed checkpoint passes. Keep the parts that already "
            "worked. Do not break checkpoints that passed before."
        )
        parts.append(
            f"OUTPUT FORMAT: First the full lesson in markdown. Then a line containing exactly "
            f"{CHANGES_MARK} and below it 2-6 bullet points saying what you changed and why."
        )
    else:
        parts.append("OUTPUT FORMAT: Only the lesson in markdown. No preface, no closing remarks.")
    return "\n\n".join(parts)


def split_output(raw: str) -> tuple[str, list[str]]:
    if CHANGES_MARK in raw:
        lesson, _, changes = raw.partition(CHANGES_MARK)
        bullets = [re.sub(r"^\s*[-*]\s*", "", l).strip() for l in changes.splitlines() if l.strip()]
        return lesson.strip(), bullets
    return raw.strip(), []


class Generator:
    def __init__(self, llm, rubric, facts, memory):
        self.llm, self.rubric, self.facts, self.memory = llm, rubric, facts, memory

    def generate(self, topic, previous=None, feedback=None):
        prompt = build_prompt(
            topic, self.rubric, self.facts,
            self.memory.guidelines(), self.memory.human_feedback(),
            previous, feedback,
        )
        raw = self.llm.complete("generate", SYSTEM, prompt)
        return split_output(raw)


# ---------- deliberate error, for the demo video ----------
FALSE_CLAIM = (
    "RAG works by retraining the AI model on your documents every time you ask a question, "
    "so the model always gives the right answer."
)


def inject_error(lesson: str) -> tuple[str, str]:
    """Insert one false sentence into the 'how it works' section. Used with --inject-error to
    prove the evaluator catches a subtle factual mistake inside an otherwise good lesson."""
    lines = lesson.splitlines()
    in_how = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            in_how = bool(re.search(r"\bhow\b", line, re.I))
            continue
        if in_how and line.strip():
            lines[i] = line + "\n\n" + FALSE_CLAIM
            return "\n".join(lines), FALSE_CLAIM
    return lesson + "\n\n" + FALSE_CLAIM, FALSE_CLAIM
