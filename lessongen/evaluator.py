"""Evaluator: code checks + an independent LLM judge. All checkpoints must pass.

Design rules:
  * hard PASS/FAIL per checkpoint, no scores
  * the judge is grounded in a fact sheet, so "accurate" means "matches the sheet"
  * fail-closed: if the judge returns junk or skips a checkpoint, that checkpoint FAILS
  * a failing verdict must quote evidence; we verify the quote really is in the lesson
"""
import json
import re
import yaml

from .checks import run_code_checks
from .config import RUBRIC_PATH


def load_rubric(path=None) -> dict:
    return yaml.safe_load((path or RUBRIC_PATH).read_text(encoding="utf-8"))


JUDGE_SYSTEM = (
    "You are a strict, impartial grader of beginner lessons. You give hard PASS or FAIL verdicts: "
    "no partial credit. When you are unsure, FAIL. For accuracy, the FACT SHEET is the only "
    "ground truth. You never rewrite the lesson. Reply with one JSON object and nothing else."
)


def _judge_prompt(lesson: str, facts: str, cps: list[dict]) -> str:
    blocks = []
    for cp in cps:
        blocks.append(
            f'<checkpoint id="{cp["id"]}">\n'
            f"Question: {cp['question']}\n"
            f"PASS only if: {cp['pass_if']}\n"
            f"FAIL if: {cp['fail_if']}\n"
            f"</checkpoint>"
        )
    return (
        f"<fact_sheet>\n{facts}\n</fact_sheet>\n\n"
        f"<checkpoints>\n" + "\n".join(blocks) + "\n</checkpoints>\n\n"
        f"<lesson>\n{lesson}\n</lesson>\n\n"
        "Judge the lesson on EVERY checkpoint above. Return JSON exactly like:\n"
        '{"results":[{"id":"<checkpoint id>","passed":true,"reason":"one short sentence",'
        '"evidence":"short exact quote from the lesson that shows the problem; empty if passed"}]}'
    )


def _parse_json(text: str):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*_`#>]", "", s)).strip().lower()


def run_llm_checks(lesson: str, rubric: dict, facts: str, judge_llm) -> dict[str, dict]:
    cps = [cp for cp in rubric["checkpoints"] if cp["type"] == "llm"]
    prompt = _judge_prompt(lesson, facts, cps)

    parsed, last_err = None, ""
    for _ in range(2):  # one retry on malformed output
        raw = judge_llm.complete("judge", JUDGE_SYSTEM, prompt, temperature=0)
        try:
            parsed = _parse_json(raw)
            break
        except Exception as e:  # noqa: BLE001
            last_err = str(e)

    by_id = {}
    if parsed:
        for r in parsed.get("results", []):
            if isinstance(r, dict) and "id" in r:
                by_id[r["id"]] = r

    results = {}
    for cp in cps:
        r = by_id.get(cp["id"])
        if r is None:  # fail-closed
            why = f"Judge returned no usable verdict ({last_err or 'checkpoint missing'}); failing closed."
            results[cp["id"]] = dict(id=cp["id"], dimension=cp["dimension"], type="llm",
                                     passed=False, reason=why, evidence="", evidence_verified=False)
            continue
        passed = bool(r.get("passed")) is True and r.get("passed") is not False
        evidence = (r.get("evidence") or "").strip()
        verified = (not evidence) or (_norm(evidence) in _norm(lesson))
        results[cp["id"]] = dict(
            id=cp["id"], dimension=cp["dimension"], type="llm", passed=passed,
            reason=str(r.get("reason", "")).strip() or ("Passed." if passed else "Failed."),
            evidence=evidence, evidence_verified=verified,
        )
    return results


def evaluate(lesson: str, rubric: dict, facts: str, judge_llm) -> dict:
    code = run_code_checks(lesson, rubric)
    llm = run_llm_checks(lesson, rubric, facts, judge_llm)
    ordered = [code.get(cp["id"]) or llm[cp["id"]] for cp in rubric["checkpoints"]]
    failed = [r for r in ordered if not r["passed"]]
    return {
        "passed": not failed,  # ALL must pass
        "total": len(ordered),
        "n_passed": len(ordered) - len(failed),
        "failed_ids": [r["id"] for r in failed],
        "results": ordered,
    }


def format_feedback(evaluation: dict, rubric: dict) -> str:
    """Turn failures into instructions the generator can act on."""
    hints = {cp["id"]: cp.get("fix_hint", "") for cp in rubric["checkpoints"]}
    lines = []
    for r in evaluation["results"]:
        if r["passed"]:
            continue
        line = f"- [{r['id']}] {r['reason']}"
        if r.get("evidence"):
            line += f' (problem text: "{r["evidence"]}")'
        if hints.get(r["id"]):
            line += f" FIX: {hints[r['id']]}"
        lines.append(line)
    return "\n".join(lines)
