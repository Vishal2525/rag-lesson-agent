import json
import os

import pytest

from lessongen.checks import check_jargon_defined, run_code_checks
from lessongen.evaluator import evaluate, load_rubric
from lessongen.generator import inject_error
from lessongen.graph import Pipeline
from lessongen.memory import Memory
from lessongen.mock_content import FLAWED_LESSON, GOOD_LESSON
from lessongen.mock_llm import MockLLM

FACTS = open(os.path.join(os.path.dirname(__file__), "..", "facts", "rag_facts.md"), encoding="utf-8").read()
RUBRIC = load_rubric()


class AlwaysBad(MockLLM):
    """Generator that never improves: proves the loop terminates."""

    def _generate(self, user):
        return FLAWED_LESSON


class GarbageJudge(MockLLM):
    def _judge(self, user):
        return "I think the lesson is great!"


def make_pipeline(tmp_path, gen=None, judge=None, max_retries=2, inject=False, threshold=2):
    return Pipeline(gen or MockLLM(), judge or MockLLM(), RUBRIC, FACTS, Memory(tmp_path / "mem"),
                    tmp_path / "out", max_retries, threshold, inject)


# ---------- code checks ----------
def test_good_lesson_passes_all_code_checks():
    assert all(r["passed"] for r in run_code_checks(GOOD_LESSON, RUBRIC).values())


def test_flawed_lesson_fails_code_checks():
    res = run_code_checks(FLAWED_LESSON, RUBRIC)
    assert not res["structure"]["passed"]
    assert not res["jargon_defined"]["passed"]
    assert not res["reading_ease"]["passed"]


def test_unexplained_jargon_is_detected():
    params = next(cp for cp in RUBRIC["checkpoints"] if cp["id"] == "jargon_defined")["params"]
    ok, reason, _ = check_jargon_defined("## T\n\nWe store each embedding in a store.", params)
    assert not ok and "embedding" in reason
    ok, _, _ = check_jargon_defined("## T\n\nEach list of numbers is called an embedding.", params)
    assert ok


# ---------- evaluator ----------
def test_good_lesson_passes_everything():
    ev = evaluate(GOOD_LESSON, RUBRIC, FACTS, MockLLM())
    assert ev["passed"], ev["failed_ids"]
    assert ev["total"] == len(RUBRIC["checkpoints"])


def test_injected_factual_error_is_caught():
    bad, claim = inject_error(GOOD_LESSON)
    assert claim in bad and bad != GOOD_LESSON
    ev = evaluate(bad, RUBRIC, FACTS, MockLLM())
    assert not ev["passed"]
    assert "accurate_grounded" in ev["failed_ids"]
    # only the injected problem should fail; the rest of the lesson is still fine
    assert ev["failed_ids"] == ["accurate_grounded"]


def test_judge_fails_closed_on_garbage():
    ev = evaluate(GOOD_LESSON, RUBRIC, FACTS, GarbageJudge())
    llm_ids = [cp["id"] for cp in RUBRIC["checkpoints"] if cp["type"] == "llm"]
    assert not ev["passed"]
    assert set(llm_ids) <= set(ev["failed_ids"])


# ---------- the loop ----------
def test_loop_recovers_on_retry(tmp_path):
    state = make_pipeline(tmp_path).run("Introduction to RAG")
    assert state["passed"] and state["attempt"] == 2
    out = tmp_path / "out"
    run_dir = next(out.iterdir())
    assert (run_dir / "lesson.md").exists()
    log = (run_dir / "rejection_log.md").read_text()
    assert "Attempt 1: REJECTED" in log and "Attempt 2: PASSED" in log
    assert "What changed on retry" in log


def test_loop_always_terminates(tmp_path):
    state = make_pipeline(tmp_path, gen=AlwaysBad(), max_retries=2).run("Introduction to RAG")
    assert not state["passed"]
    assert state["attempt"] == 3  # 1 + max_retries, never more
    run_dir = next((tmp_path / "out").iterdir())
    assert (run_dir / "lesson.DRAFT_NEEDS_REVIEW.md").exists()
    assert not (run_dir / "lesson.md").exists()  # a failing lesson is never presented as shipped


def test_inject_error_demo_flow(tmp_path):
    os.environ["MOCK_SCENARIO"] = "good"
    try:
        state = make_pipeline(tmp_path, inject=True).run("Introduction to RAG")
    finally:
        del os.environ["MOCK_SCENARIO"]
    assert state["passed"] and state["attempt"] == 2
    first = state["history"][0]
    assert first["injected_error"] and first["evaluation"]["failed_ids"] == ["accurate_grounded"]
    final = state["history"][-1]["lesson"]
    assert "retraining the AI model" not in final


# ---------- memory + self-evolution ----------
def test_memory_persists_and_evolves(tmp_path):
    make_pipeline(tmp_path).run("Introduction to RAG")  # run 1: failures counted once
    mem = Memory(tmp_path / "mem")
    assert len(mem.data["runs"]) == 1 and not mem.guidelines()

    make_pipeline(tmp_path).run("Introduction to RAG")  # run 2: threshold (2) reached
    mem = Memory(tmp_path / "mem")  # reload from disk
    assert len(mem.data["runs"]) == 2
    assert mem.guidelines(), "repeated failures should have produced learned guidelines"
    assert all(g["source"] == "auto-evolve" for g in mem.data["guidelines"])


def test_memory_feeds_next_generation(tmp_path):
    mem = Memory(tmp_path / "mem")
    mem.add_feedback("Use more examples from Karnataka.")
    mem.add_guideline("Define every term in the same sentence.", "jargon_defined", "auto-evolve")
    from lessongen.generator import build_prompt

    p = build_prompt("RAG", RUBRIC, FACTS, mem.guidelines(), mem.human_feedback())
    assert "Karnataka" in p and "same sentence" in p


def test_rubric_is_not_modified_by_evolution(tmp_path):
    before = open(os.path.join(os.path.dirname(__file__), "..", "rubric.yaml")).read()
    make_pipeline(tmp_path).run("RAG")
    make_pipeline(tmp_path).run("RAG")
    after = open(os.path.join(os.path.dirname(__file__), "..", "rubric.yaml")).read()
    assert before == after


def test_two_runs_in_same_second_do_not_overwrite(tmp_path):
    a = make_pipeline(tmp_path)
    a.run("RAG")
    b = make_pipeline(tmp_path)
    b.run("RAG")
    assert a.run_id != b.run_id
    assert len(list((tmp_path / "out").iterdir())) == 2
