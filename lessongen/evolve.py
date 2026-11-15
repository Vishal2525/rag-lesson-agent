"""Self-evolution: learn from repeated failures.

When a checkpoint has failed in >= EVOLVE_THRESHOLD runs since its last evolution:
  1. AUTO-APPLIED : distil the recent failure reasons into ONE short writing guideline and save it
                    to memory. The generator reads it on every future run.
  2. PROPOSED ONLY: ask whether the checkpoint itself is vague/too strict/too loose and write any
                    suggested rubric change to memory/rubric_proposals.md for a human to approve.

Why the split? Prompts are cheap to change and easy to roll back. The rubric is the definition of
"good enough". If the system could edit its own rubric it could quietly lower the bar to pass.
So the rubric stays human-owned.
"""
import time

GUIDE_SYSTEM = "You improve a lesson-writing assistant by turning failure reports into one short, concrete rule."
PROPOSE_SYSTEM = (
    "You review a grading checkpoint for a beginner-lesson pipeline. Suggest a change only if the "
    "failures show the checkpoint is vague, contradictory or unfair. Never suggest lowering quality."
)


def maybe_evolve(llm, memory, rubric, threshold: int, proposals_path) -> list[str]:
    by_id = {cp["id"]: cp for cp in rubric["checkpoints"]}
    notes = []
    for cid, count in list(memory.data["failure_counts"].items()):
        cp = by_id.get(cid)
        if cp is None or count - memory.data["evolve_marker"].get(cid, 0) < threshold:
            continue
        reasons = [f["reason"] for f in memory.data["failures"] if f["check_id"] == cid][-3:]
        info = (
            f"CHECK_ID: {cid}\nREQUIREMENT: {cp['requirement']}\nFIX_HINT: {cp.get('fix_hint', '')}\n"
            "RECENT_FAILURE_REASONS:\n" + "\n".join(f"- {r}" for r in reasons)
        )

        guideline = llm.complete(
            "evolve", GUIDE_SYSTEM,
            info + "\n\nWrite ONE imperative rule (max 25 words) the lesson writer can follow to avoid "
            "this failure next time. Output only the rule.",
        ).strip().strip('"').splitlines()[0]
        memory.add_guideline(guideline, cid, "auto-evolve")
        notes.append(f"learned guideline for '{cid}': {guideline}")

        proposal = llm.complete(
            "propose", PROPOSE_SYSTEM,
            info + "\n\nIf the checkpoint wording or its parameters should change, reply with a short "
            "proposal. If it is fine, reply exactly NO_CHANGE.",
        ).strip()
        if proposal.upper() != "NO_CHANGE":
            with open(proposals_path, "a", encoding="utf-8") as f:
                f.write(f"## {time.strftime('%Y-%m-%d %H:%M')} - checkpoint `{cid}`\n\n{proposal}\n\n")
            notes.append(f"rubric change PROPOSED for '{cid}' (needs human approval): see rubric_proposals.md")

        memory.data["evolve_marker"][cid] = count
    memory.save()
    return notes
