"""OFFLINE MOCK PROVIDER. A test double, not a real model.

It lets you (and the tests) run the whole loop with no API key. It returns canned lessons and
grades with simple keyword rules. It proves the PLUMBING works (loop, routing, logs, memory,
evolution). It says nothing about real lesson quality: use a real provider for that.

MOCK_SCENARIO=flawed_first (default): draft 1 is bad, the retry is good.
MOCK_SCENARIO=good                  : draft 1 is already good.
"""
import json
import os
import re

from . import checks
from .llm import LLM
from .mock_content import FLAWED_LESSON, GOOD_LESSON


def _sentences_with(rx, text):
    return [s for s in checks.sentences(text) if re.search(rx, s, re.I)]


def _negated(text, m):
    return bool(re.search(r"\b(not|no|never|n't)\b", text[max(0, m.start() - 25) : m.start()], re.I))


class MockLLM(LLM):
    name = "mock (offline test double)"

    def complete(self, role, system, user, temperature=None):
        return getattr(self, f"_{role}")(user)

    # ---- generator ----
    def _generate(self, user):
        if "PREVIOUS ATTEMPT FAILED" in user:
            ids = re.findall(r"^- \[(\w+)\]", user, re.M)
            bullets = "\n".join(f"- Fixed `{i}` as the grader asked." for i in ids) or "- Rewrote the lesson."
            return GOOD_LESSON + "\n===CHANGES===\n" + bullets + "\n- Kept the sections that already passed."
        return GOOD_LESSON if os.getenv("MOCK_SCENARIO") == "good" else FLAWED_LESSON

    # ---- judge (keyword rules, deliberately simple) ----
    def _judge(self, user):
        lesson = re.search(r"<lesson>\n(.*)\n</lesson>", user, re.S).group(1)
        ids = re.findall(r'<checkpoint id="(\w+)">', user)
        low = lesson.lower()
        out = []
        for cid in ids:
            ok, reason, ev = getattr(self, f"_j_{cid}")(lesson, low)
            out.append({"id": cid, "passed": ok, "reason": reason, "evidence": ev})
        return json.dumps({"results": out})

    def _j_accurate_grounded(self, lesson, low):
        for m in re.finditer(r"\bretrain(s|ed)?\b", low):
            if not _negated(low, m):
                s = _sentences_with(r"\bretrain", lesson)
                return False, "Says RAG retrains the model, which contradicts the fact sheet.", s[0] if s else ""
        for rx in (r"never hallucinat", r"always gives? the right answer", r"100%", r"zero mistakes"):
            s = _sentences_with(rx, lesson)
            if s and not re.search(r"\b(not|cannot|can't)\b", s[0], re.I):
                return False, "Claims RAG guarantees correct answers, which contradicts the fact sheet.", s[0]
        return True, "No contradiction with the fact sheet.", ""

    def _j_covers_key_points(self, lesson, low):
        groups = {
            "K1": r"training|out of date|new things",
            "K2": r"hallucinat|make up|made-up|made up",
            "K3": r"retriev",
            "K4": r"chunk.*(embedding|vector)|(embedding|vector).*chunk",
            "K5": r"embedding is a list of numbers|list of numbers",
            "K6": r"fresh answers|private answers|low cost|up to date|up-to-date",
            "K7": r"not magic|wrong chunks|cannot make them zero|limits",
        }
        missing = [k for k, rx in groups.items() if not re.search(rx, low, re.S)]
        if missing:
            return False, f"Key point(s) missing or unexplained: {', '.join(missing)}.", ""
        return True, "All key points are covered.", ""

    def _j_teaches_by_example(self, lesson, low):
        if "example" in low and "step 1" in low and "?" in lesson:
            return True, "A step-by-step worked example is present.", ""
        return False, "No concrete step-by-step worked example following one question through RAG.", ""

    def _j_analogy_sound(self, lesson, low):
        if re.search(r"open-book|open book", low):
            return True, "Open-book analogy matches retrieve-then-answer.", ""
        return False, "No everyday analogy found.", ""

    def _j_jargon_explained(self, lesson, low):
        ok, reason, ev = checks.check_jargon_defined(lesson, _JARGON_PARAMS)
        return ok, reason, ev

    def _j_coherent_flow(self, lesson, low):
        hs = [h.lower() for h in checks.headings(lesson)]

        def pos(rx):
            return next((i for i, h in enumerate(hs) if re.search(rx, h)), None)

        order = [pos(r"\bwhat\b"), pos(r"\bwhy\b"), pos(r"\bhow\b"), pos("example"), pos("limit")]
        if None in order or order != sorted(order):
            return False, "Sections are missing or out of the order problem, idea, how, example, limits.", ""
        return True, "Sections build in a sensible order.", ""

    def _j_zero_background(self, lesson, low):
        for phrase in ("as you know", "you already know", "neural network", "transformer", "gradient"):
            if phrase in low:
                return False, f"Assumes background knowledge ('{phrase}').", phrase
        return True, "Assumes no prior knowledge.", ""

    # ---- evolution ----
    def _evolve(self, user):
        m = re.search(r"FIX_HINT: (.*)", user)
        return (m.group(1) if m else "Follow the rubric more carefully.").strip()[:200]

    def _propose(self, user):
        return "NO_CHANGE"


_JARGON_PARAMS = {
    "terms": {
        "LLM": r"\bLLMs?\b", "embedding": "embedding", "vector database": r"vector (database|store)",
        "chunk": r"\bchunks?\b", "retrieval": "retriev", "hallucination": "hallucinat",
        "prompt": r"\bprompts?\b", "token": r"\btokens?\b", "semantic": "semantic",
        "context window": "context window",
    }
}
