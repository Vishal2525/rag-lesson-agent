import argparse
import os
from pathlib import Path

from . import config
from .evaluator import load_rubric
from .graph import Pipeline, say
from .llm import make_llm
from .memory import Memory


def cmd_run(a):
    rubric = load_rubric()
    facts = Path(a.facts).read_text(encoding="utf-8")
    memory = Memory(config.MEMORY_DIR)
    gen = make_llm(a.provider, a.model)
    judge_model = a.judge_model or os.getenv("LESSONGEN_JUDGE_MODEL") or a.model
    judge = make_llm(a.provider, judge_model) if judge_model else gen

    say(f"topic     : {a.topic}")
    say(f"generator : {gen.name}")
    say(f"judge     : {judge.name}")
    say(f"memory    : {len(memory.guidelines())} learned guideline(s), {len(memory.human_feedback())} feedback note(s)")
    say(f"max tries : {1 + a.max_retries}" + ("   (error injection ON)" if a.inject_error else ""))

    p = Pipeline(gen, judge, rubric, facts, memory, config.OUTPUT_DIR, a.max_retries,
                 config.EVOLVE_THRESHOLD, a.inject_error)
    state = p.run(a.topic)

    say("\n" + "=" * 60)
    if state["passed"]:
        say(f"SHIPPED after {state['attempt']} attempt(s).")
    else:
        say(f"NOT SHIPPED after {state['attempt']} attempts. Draft saved for human review.")
    say(f"output: {state['out_dir']}")
    return 0 if state["passed"] else 1


def cmd_feedback(a):
    Memory(config.MEMORY_DIR).add_feedback(a.text)
    say("Saved. The generator will follow this on every future run.")
    return 0


def cmd_memory(a):
    say(Memory(config.MEMORY_DIR).summary())
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="lessongen", description="Self-evaluating lesson generator")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="generate -> evaluate -> regenerate")
    r.add_argument("--topic", default=config.DEFAULT_TOPIC)
    r.add_argument("--facts", default=str(config.FACTS_PATH))
    r.add_argument("--provider", default=None, help="anthropic | openai | mock (default: $LESSONGEN_PROVIDER or anthropic)")
    r.add_argument("--model", default=None)
    r.add_argument("--judge-model", default=None, help="use a different (ideally stronger) model as judge")
    r.add_argument("--max-retries", type=int, default=config.MAX_RETRIES)
    r.add_argument("--inject-error", action="store_true", help="demo: insert a false claim into draft 1")
    r.set_defaults(fn=cmd_run)

    f = sub.add_parser("feedback", help="give the system human feedback it will remember")
    f.add_argument("text")
    f.set_defaults(fn=cmd_feedback)

    m = sub.add_parser("memory", help="show what the system has learned")
    m.set_defaults(fn=cmd_memory)

    a = p.parse_args(argv)
    return a.fn(a)
