"""Persistent memory (a plain JSON file, so it is easy to read, diff and explain).

Stores:
  runs            - one record per run (did it pass, on which attempt, what failed)
  failure_counts  - in how many RUNS each checkpoint has failed
  failures        - recent failure reasons (raw material for self-evolution)
  guidelines      - short rules learned from repeated failures + human feedback; injected into the generator prompt
  human_feedback  - free-text feedback from a person, also injected into the generator prompt
  evolve_marker   - failure count at the last evolution, per checkpoint
"""
import json
import time
from pathlib import Path

EMPTY = {
    "runs": [],
    "failure_counts": {},
    "failures": [],
    "guidelines": [],
    "human_feedback": [],
    "evolve_marker": {},
}


class Memory:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "memory.json"
        if self.path.exists():
            self.data = {**json.loads(json.dumps(EMPTY)), **json.loads(self.path.read_text(encoding="utf-8"))}
        else:
            self.data = json.loads(json.dumps(EMPTY))

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- read side (used by the generator) ----
    def guidelines(self, limit: int = 8) -> list[str]:
        return [g["text"] for g in self.data["guidelines"]][-limit:]

    def human_feedback(self, limit: int = 5) -> list[str]:
        return [f["text"] for f in self.data["human_feedback"]][-limit:]

    # ---- write side ----
    def add_feedback(self, text: str, run_id: str | None = None):
        self.data["human_feedback"].append({"text": text, "run_id": run_id, "at": _now()})
        self.save()

    def add_guideline(self, text: str, check_id: str, source: str):
        if text and text not in self.guidelines(limit=1000):
            self.data["guidelines"].append({"text": text, "check_id": check_id, "source": source, "at": _now()})
            self.save()

    def record_run(self, run_id: str, topic: str, passed: bool, attempts: list[dict]):
        failed_this_run = set()
        for rec in attempts:
            for r in rec["evaluation"]["results"]:
                if not r["passed"]:
                    failed_this_run.add(r["id"])
                    self.data["failures"].append(
                        {"check_id": r["id"], "reason": r["reason"], "run_id": run_id, "attempt": rec["attempt"]}
                    )
        for cid in failed_this_run:  # count once per RUN, not per attempt
            self.data["failure_counts"][cid] = self.data["failure_counts"].get(cid, 0) + 1
        self.data["failures"] = self.data["failures"][-200:]
        self.data["runs"].append(
            {
                "run_id": run_id,
                "topic": topic,
                "passed": passed,
                "attempts": len(attempts),
                "failed_by_attempt": [rec["evaluation"]["failed_ids"] for rec in attempts],
            }
        )
        self.save()

    def summary(self) -> str:
        d = self.data
        top = sorted(d["failure_counts"].items(), key=lambda kv: -kv[1])[:5]
        lines = [
            f"runs recorded : {len(d['runs'])}",
            f"most-failed   : {', '.join(f'{k} x{v}' for k, v in top) or 'none yet'}",
            f"guidelines    : {len(d['guidelines'])}",
        ]
        lines += [f"   - ({g['source']}/{g['check_id']}) {g['text']}" for g in d["guidelines"]]
        lines.append(f"human feedback: {len(d['human_feedback'])}")
        lines += [f"   - {f['text']}" for f in d["human_feedback"]]
        return "\n".join(lines)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
