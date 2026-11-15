"""Writes the rejection log: what failed, why, and what changed on retry."""
import difflib
import re


def diff_stats(before: str, after: str) -> dict:
    a, b = before.split(), after.split()
    sim = difflib.SequenceMatcher(None, a, b).ratio()
    return {"words_before": len(a), "words_after": len(b), "text_kept_pct": round(sim * 100)}


def _cell(s: str, limit: int = 160) -> str:
    s = re.sub(r"\s+", " ", (s or "").replace("|", "/")).strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def render_rejection_log(run: dict) -> str:
    attempts = run["attempts"]
    out = [
        f"# Rejection log: {run['topic']}",
        "",
        f"- Run: `{run['run_id']}`",
        f"- Generator: `{run['generator']}`  |  Judge: `{run['judge']}`",
        f"- Rule: ALL {attempts[0]['evaluation']['total']} checkpoints must pass. Max {run['max_retries']} retries.",
        f"- Result: **{'SHIPPED (passed)' if run['passed'] else 'NOT SHIPPED: needs human review'}** "
        f"after {len(attempts)} attempt(s)",
        "",
    ]
    for i, rec in enumerate(attempts):
        ev = rec["evaluation"]
        status = "PASSED" if ev["passed"] else "REJECTED"
        out.append(f"## Attempt {rec['attempt']}: {status} ({ev['n_passed']}/{ev['total']} checkpoints passed)")
        out.append("")
        if rec.get("injected_error"):
            out += [f"> Deliberate error injected for the demo: \"{rec['injected_error']}\"", ""]
        if not ev["passed"]:
            out += ["| Checkpoint | Dimension | Why it failed | Evidence |", "|---|---|---|---|"]
            for r in ev["results"]:
                if not r["passed"]:
                    ev_txt = _cell(r.get("evidence"))
                    if ev_txt and r.get("evidence_verified") is False:
                        ev_txt += " (quote not found in lesson)"
                    out.append(f"| `{r['id']}` | {r['dimension']} | {_cell(r['reason'])} | {ev_txt} |")
            out.append("")
            if i + 1 < len(attempts):
                nxt = attempts[i + 1]
                st = nxt["diff"]
                out.append(f"**What changed on retry (attempt {nxt['attempt']}):**")
                out.append(
                    f"- Size {st['words_before']} -> {st['words_after']} words; "
                    f"{st['text_kept_pct']}% of the wording kept."
                )
                out += [f"- {c}" for c in nxt.get("changes", [])] or ["- (the model did not report its changes)"]
                out.append("")
            else:
                out += ["_No retries left. The last draft is saved for a human to review._", ""]
    return "\n".join(out)
