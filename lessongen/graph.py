"""The agentic loop, as a LangGraph state machine.

            +----------+     +----------+   pass            +----------+    +-------+
  START --> | generate | --> | evaluate | ----------------> | finalize | -> | learn | -> END
            +----------+     +----------+                   +----------+    +-------+
                  ^                |  fail AND attempts left        ^
                  +----------------+                                |
                                   +--- fail AND no attempts left --+  (saved as NEEDS REVIEW)

The loop is bounded: attempts <= 1 + max_retries, so it always terminates.
"""
import json
import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .evaluator import evaluate, format_feedback
from .evolve import maybe_evolve
from .generator import Generator, inject_error
from .logs import diff_stats, render_rejection_log


class State(TypedDict, total=False):
    topic: str
    attempt: int
    lesson: str
    changes: list
    injected: str
    feedback: str
    history: list
    passed: bool
    out_dir: str


def say(msg=""):
    print(msg, flush=True)


class Pipeline:
    def __init__(self, gen_llm, judge_llm, rubric, facts, memory, output_dir, max_retries=2,
                 evolve_threshold=2, inject=False):
        self.gen_llm, self.judge_llm = gen_llm, judge_llm
        self.rubric, self.facts, self.memory = rubric, facts, memory
        self.output_dir, self.max_retries = Path(output_dir), max_retries
        self.evolve_threshold, self.inject = evolve_threshold, inject
        self.generator = Generator(gen_llm, rubric, facts, memory)
        base = time.strftime("%Y%m%d-%H%M%S")
        self.run_id, n = base, 1
        while (self.output_dir / self.run_id).exists():  # never overwrite an earlier run
            n += 1
            self.run_id = f"{base}-{n}"
        self.graph = self._build()

    # ---------------- nodes ----------------
    def n_generate(self, s: State) -> State:
        attempt = s.get("attempt", 0) + 1
        retry = attempt > 1
        say(f"\n[attempt {attempt}] {'regenerating using evaluator feedback' if retry else 'generating first draft'}...")
        lesson, changes = self.generator.generate(
            s["topic"], previous=s.get("lesson") if retry else None, feedback=s.get("feedback") if retry else None
        )
        injected = None
        if self.inject and attempt == 1:
            lesson, injected = inject_error(lesson)
            say(f'[attempt 1] !! deliberate error injected: "{injected}"')
        return {"attempt": attempt, "lesson": lesson, "changes": changes, "injected": injected or ""}

    def n_evaluate(self, s: State) -> State:
        say(f"[attempt {s['attempt']}] evaluating against {len(self.rubric['checkpoints'])} hard checkpoints...")
        ev = evaluate(s["lesson"], self.rubric, self.facts, self.judge_llm)
        history = list(s.get("history", []))
        prev_lesson = history[-1]["lesson"] if history else s["lesson"]
        history.append(
            {
                "attempt": s["attempt"],
                "lesson": s["lesson"],
                "evaluation": ev,
                "changes": s.get("changes", []),
                "diff": diff_stats(prev_lesson, s["lesson"]),
                "injected_error": s.get("injected", ""),
            }
        )
        for r in ev["results"]:
            say(f"   {'PASS' if r['passed'] else 'FAIL'}  {r['id']:<18}" + ("" if r["passed"] else f" {r['reason']}"))
        say(f"[attempt {s['attempt']}] {ev['n_passed']}/{ev['total']} passed -> {'SHIP IT' if ev['passed'] else 'REJECTED'}")
        return {"history": history, "passed": ev["passed"], "feedback": format_feedback(ev, self.rubric)}

    def route(self, s: State) -> str:
        if s["passed"]:
            return "done"
        return "retry" if s["attempt"] < 1 + self.max_retries else "done"

    def n_finalize(self, s: State) -> State:
        out = self.output_dir / self.run_id
        out.mkdir(parents=True, exist_ok=True)
        passed = s["passed"]
        final = s["history"][-1]["lesson"]
        (out / ("lesson.md" if passed else "lesson.DRAFT_NEEDS_REVIEW.md")).write_text(final, encoding="utf-8")
        run = {
            "run_id": self.run_id, "topic": s["topic"], "passed": passed, "max_retries": self.max_retries,
            "generator": self.gen_llm.name, "judge": self.judge_llm.name, "attempts": s["history"],
        }
        (out / "rejection_log.md").write_text(render_rejection_log(run), encoding="utf-8")
        (out / "run.json").write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"out_dir": str(out)}

    def n_learn(self, s: State) -> State:
        self.memory.record_run(self.run_id, s["topic"], s["passed"], s["history"])
        notes = maybe_evolve(
            self.gen_llm, self.memory, self.rubric, self.evolve_threshold,
            self.memory.dir / "rubric_proposals.md",
        )
        for n in notes:
            say(f"[learn] {n}")
        return {}

    # ---------------- wiring ----------------
    def _build(self):
        g = StateGraph(State)
        g.add_node("generate", self.n_generate)
        g.add_node("evaluate", self.n_evaluate)
        g.add_node("finalize", self.n_finalize)
        g.add_node("learn", self.n_learn)
        g.set_entry_point("generate")
        g.add_edge("generate", "evaluate")
        g.add_conditional_edges("evaluate", self.route, {"retry": "generate", "done": "finalize"})
        g.add_edge("finalize", "learn")
        g.add_edge("learn", END)
        return g.compile()

    def run(self, topic: str) -> dict:
        return self.graph.invoke({"topic": topic, "attempt": 0, "history": []})
