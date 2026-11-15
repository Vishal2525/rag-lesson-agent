"""Deterministic (code) checkpoints. Same input -> same verdict, every time.

Each check returns (passed: bool, reason: str, evidence: str).
"""
import re

HEADING = re.compile(r"^\s*#{1,6}\s*(.+?)\s*$")

# A sentence "explains" a term if it contains a definition cue. This is a heuristic safety net;
# the LLM judge (jargon_explained) makes the real call on whether the explanation is good.
CUE = re.compile(
    r"\bmeans?\b|\bis an?\b|\bis the\b|\bare the\b|\bcalled\b|\bstands? for\b|"
    r"\brefers? to\b|\bis when\b|\bis like\b|\(",
    re.I,
)


# ---------- text helpers ----------
def headings(lesson: str) -> list[str]:
    return [m.group(1) for line in lesson.splitlines() if (m := HEADING.match(line))]


def body_lines(lesson: str) -> list[str]:
    out = []
    for line in lesson.splitlines():
        if HEADING.match(line):
            continue
        t = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line)
        t = re.sub(r"[*_`>]", "", t).strip()
        if t:
            out.append(t)
    return out


def sentences(lesson: str) -> list[str]:
    out = []
    for line in body_lines(lesson):
        for s in re.split(r"(?<=[.!?])\s+", line):
            if s.strip():
                out.append(s.strip())
    return out


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'’-]*", text)


def syllables(word: str) -> int:
    total = 0
    for part in re.split(r"-", word.lower()):
        part = re.sub(r"[^a-z]", "", part)
        if not part:
            continue
        n = len(re.findall(r"[aeiouy]+", part))
        if part.endswith("e") and not part.endswith(("le", "ee")) and n > 1:
            n -= 1
        total += max(n, 1)
    return max(total, 1)


def flesch(lesson: str) -> float:
    sents = sentences(lesson)
    ws = [w for s in sents for w in words(s)]
    if not sents or not ws:
        return 0.0
    syl = sum(syllables(w) for w in ws)
    return 206.835 - 1.015 * (len(ws) / len(sents)) - 84.6 * (syl / len(ws))


# ---------- checks ----------
def check_structure(lesson, p):
    hs = [h.lower() for h in headings(lesson)]
    missing = [n for n, pat in p["required_sections"].items() if not any(re.search(pat, h) for h in hs)]
    if missing:
        return False, f"Missing section(s): {', '.join(missing)}. Headings found: {headings(lesson) or 'none'}.", ""
    return True, "All required sections are present.", ""


def check_length(lesson, p):
    n = sum(len(words(s)) for s in sentences(lesson))
    if n < p["min_words"]:
        return False, f"Too short: {n} words (minimum {p['min_words']}).", ""
    if n > p["max_words"]:
        return False, f"Too long: {n} words (maximum {p['max_words']}).", ""
    return True, f"{n} words, within range.", ""


def check_sentence_length(lesson, p):
    sents = sentences(lesson)
    counts = [len(words(s)) for s in sents]
    if not counts:
        return False, "No sentences found.", ""
    avg = sum(counts) / len(counts)
    longest = max(sents, key=lambda s: len(words(s)))
    longest_n = len(words(longest))
    if avg > p["max_avg_words"]:
        return False, f"Average sentence length is {avg:.1f} words (max {p['max_avg_words']}).", longest
    if longest_n > p["max_sentence_words"]:
        return False, f"A sentence has {longest_n} words (max {p['max_sentence_words']}).", longest
    return True, f"Average {avg:.1f} words, longest {longest_n}.", ""


def check_reading_ease(lesson, p):
    score = flesch(lesson)
    if score < p["min_flesch"]:
        return False, f"Flesch Reading Ease is {score:.0f} (needs at least {p['min_flesch']}).", ""
    return True, f"Flesch Reading Ease is {score:.0f}.", ""


def check_long_words(lesson, p):
    ws = []
    for s in sentences(lesson):
        for w in words(s):
            ws.extend(re.split(r"-", w))
    ws = [w for w in ws if w]
    if not ws:
        return False, "No words found.", ""
    long_ = sorted({w.lower() for w in ws if len(w) >= p["min_letters"]})
    ratio = sum(1 for w in ws if len(w) >= p["min_letters"]) / len(ws)
    if ratio > p["max_ratio"]:
        return False, f"{ratio:.1%} of words have {p['min_letters']}+ letters (max {p['max_ratio']:.0%}). Examples: {', '.join(long_[:6])}.", ""
    return True, f"{ratio:.1%} long words.", ""


def check_acronym_expanded(lesson, p):
    rx = re.compile(rf"\b{p['acronym']}\b")
    for s in sentences(lesson):
        if rx.search(s):
            if p["expansion"] in s.lower() or re.search(r"stands for", s, re.I):
                return True, "Acronym is expanded at first use.", ""
            return False, f"'{p['acronym']}' is used before it is expanded.", s
    return False, f"The lesson never uses '{p['acronym']}' in its body text.", ""


def check_jargon_defined(lesson, p):
    sents = sentences(lesson)
    bad = []
    for name, pat in p["terms"].items():
        rx = re.compile(pat, re.I)
        for s in sents:
            if rx.search(s):
                if not CUE.search(s):
                    bad.append((name, s))
                break  # only the FIRST use matters
    if bad:
        names = ", ".join(n for n, _ in bad)
        return False, f"Used without a plain-words explanation at first appearance: {names}.", bad[0][1]
    return True, "Every technical term is explained where it first appears.", ""


CHECKS = {
    "structure": check_structure,
    "length": check_length,
    "sentence_length": check_sentence_length,
    "reading_ease": check_reading_ease,
    "long_words": check_long_words,
    "acronym_expanded": check_acronym_expanded,
    "jargon_defined": check_jargon_defined,
}


def run_code_checks(lesson: str, rubric: dict) -> dict[str, dict]:
    results = {}
    for cp in rubric["checkpoints"]:
        if cp["type"] != "code":
            continue
        passed, reason, evidence = CHECKS[cp["fn"]](lesson, cp.get("params", {}))
        results[cp["id"]] = {
            "id": cp["id"],
            "dimension": cp["dimension"],
            "type": "code",
            "passed": bool(passed),
            "reason": reason,
            "evidence": evidence,
        }
    return results
