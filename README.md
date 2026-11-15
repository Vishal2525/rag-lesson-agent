# Self-Evaluating Lesson Generator

An agentic system that writes a beginner lesson, **grades it against a hard pass/fail rubric, and
regenerates until it clears the bar**, deciding on its own whether the content is fit to ship
before a human sees it. Submission topic: **Introduction to RAG**.

```
            ┌──────────┐    ┌───────────────────────────┐  all 14 pass   ┌──────────┐   ┌───────┐
 topic ───▶ │ generate │───▶│ evaluate                  │───────────────▶│ finalize │──▶│ learn │──▶ memory
            └──────────┘    │  7 code checks (Python)   │                └──────────┘   └───────┘
                 ▲          │  7 LLM-judge checks       │                     ▲
                 │          │  grounded in a fact sheet │                     │
                 │          └─────────────┬─────────────┘                     │
                 │      any fail + retries left                  any fail + no retries left
                 └────── reasons fed back ─┘                     (saved as NEEDS_REVIEW, never "shipped")
```

Built with **Python + LangGraph**. Model-agnostic: Anthropic, OpenAI (or any OpenAI-compatible
endpoint), or an offline mock.

## Setup

```bash
git clone <this repo> && cd rag-lesson-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then put your key in it, and: export $(grep -v '^#' .env | xargs)
```

## Run

```bash
# the real thing (needs ANTHROPIC_API_KEY)
python -m lessongen run

# demo: plant a false claim in draft 1 and watch the evaluator catch it
python -m lessongen run --inject-error

# use a different (ideally stronger) model as the judge, to reduce self-grading bias
python -m lessongen run --judge-model claude-opus-5-5

# no API key? exercise the whole loop offline (canned lessons + keyword grader; plumbing only)
python -m lessongen run --provider mock
MOCK_SCENARIO=good python -m lessongen run --provider mock --inject-error

# memory
python -m lessongen memory                                   # what has the system learned?
python -m lessongen feedback "Use more examples from Karnataka"   # human feedback it will remember

python -m pytest -q                                          # 13 tests, no API key needed
```

Each run writes `output/<run_id>/`:

| File | What |
|---|---|
| `lesson.md` | the passing lesson (or `lesson.DRAFT_NEEDS_REVIEW.md` if it never passed) |
| `rejection_log.md` | per attempt: which checkpoints failed, why, evidence, and what changed on retry |
| `run.json` | full machine-readable trace (every draft, every verdict) |

Exit code is `0` if shipped, `1` if not, so it can gate a CI job or a publishing pipeline.

## The rubric (`rubric.yaml`)

14 checkpoints, each a hard PASS/FAIL, **all must pass**. They map to the six dimensions in the brief:

| Dimension | Checkpoints | Type |
|---|---|---|
| Accurate & grounded | `accurate_grounded` | LLM, judged against `facts/rag_facts.md` |
| Beginner-friendly language | `length`, `sentence_length`, `reading_ease`, `long_words` | code |
| Teaches by example | `teaches_by_example`, `analogy_sound` | LLM |
| Clear, no unexplained jargon | `acronym_expanded`, `jargon_defined` | code; `jargon_explained` | LLM |
| Covers the key points | `structure` | code; `covers_key_points` (K1–K7) | LLM |
| Coherent teaching flow | `coherent_flow`, `zero_background` | LLM |

Code checks are cheap, repeatable and cannot be talked around. LLM checks handle what code cannot
(is the example actually correct? is the analogy misleading?). The judge must quote evidence for
any failure, and the system verifies the quote really appears in the lesson.

## How it learns

- **Memory** (`memory/memory.json`, plain JSON): every run, failure counts per checkpoint, recent
  failure reasons, learned guidelines, human feedback. Guidelines and feedback are injected into
  the generator prompt on every future run.
- **Self-evolving prompts**: when a checkpoint fails in 2+ runs, the system distils the failure
  reasons into one short rule and adds it to memory (auto-applied, easy to inspect and roll back).
- **Rubric changes are *proposed*, never applied**: suggestions go to `memory/rubric_proposals.md`
  for a human to approve. A system that can edit its own bar can quietly lower it.

## Layout

```
rubric.yaml            the definition of "good enough" (human-owned)
facts/rag_facts.md     ground truth for accuracy + the key points K1-K7
lessongen/
  graph.py             LangGraph loop: generate -> evaluate -> (retry | finalize) -> learn
  generator.py         prompt builder, retry-with-feedback, --inject-error
  checks.py            7 deterministic checks
  evaluator.py         runs code + LLM-judge checks, fail-closed, feedback formatter
  memory.py evolve.py  persistence and self-evolution
  logs.py              rejection log writer
  llm.py               Anthropic / OpenAI providers
  mock_llm.py          offline test double
tests/                 13 tests (loop termination, fail-closed judge, injected error, memory...)
DESIGN.md              why it is built this way, and the trade-offs
VIDEO_SCRIPT.md        a 15-20 minute outline for the Loom
examples/              sample rejection log (from the OFFLINE MOCK, labelled)
```

## Honest limitations

- **Tested end to end only with the offline mock.** The loop, routing, termination, fail-closed
  judging, logs, memory and evolution are covered by tests. The real-model prompts have not been
  run against a live API from where this was built. Run it once with your key before recording.
- **Thresholds are calibrated on a hand-written lesson**, not on real model output. If a real model
  keeps failing e.g. `sentence_length` by a hair, tune the value in `rubric.yaml` (a human decision).
- **Accuracy is bounded by the fact sheet.** The judge can only catch what contradicts it. A true
  statement missing from the sheet is not credited, and an error the sheet is silent on can slip through.
- **`jargon_defined` is a heuristic** (looks for a definition cue in the first sentence using a term).
  It is a safety net; `jargon_explained` (LLM) makes the real call.
- **Same-family judging bias.** If generator and judge are the same model they can share blind spots.
  Use `--judge-model` with a different or stronger model.
- A lesson that fails after all retries is **not shipped**; it is saved for human review.
