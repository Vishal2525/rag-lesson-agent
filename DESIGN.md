# Design notes: why it is built this way

The brief is not "write a prompt that makes a lesson". It is "own a loop that decides whether
content is good enough to ship". So the design starts from the question: **what makes an automatic
ship/no-ship decision trustworthy?**

## 1. The decision problem

A pipeline that generates and then asks the same model "is this good?" will mostly say yes. To
make the decision trustworthy I separated three things that are usually blurred:

| Concern | Decision | Why |
|---|---|---|
| *What is "good"?* | A written rubric of hard pass/fail checkpoints, owned by a human | A score like 7/10 hides what is wrong and cannot gate anything. Binary checks tell the generator exactly what to fix. |
| *How do we measure it?* | Code where possible, LLM only where needed | Readability, length, structure, acronym expansion are measurable. Code is repeatable and cannot be argued with. Only judgement calls (is the example correct? is the analogy misleading?) go to an LLM. |
| *What is "true"?* | A fact sheet the judge grades against | "Accurate" without a source is just the judge's opinion. The fact sheet makes accuracy checkable and makes the judge's job narrow: contradiction or unsupported claim. |

## 2. Why hard pass/fail, no partial credit

- A lesson with a wrong fact is not "86% good". It is not shippable.
- Every failure maps to a specific `fix_hint`, so the retry prompt is concrete.
- It makes the rejection log meaningful: each row is a distinct, nameable defect.

## 3. Why 14 checkpoints, and why a hybrid evaluator

The six dimensions in the brief (accurate, beginner language, examples, no jargon, key points,
flow) each get at least one check. Where a dimension is measurable I used code:

- *Beginner language*: avg sentence ≤ 15 words, none > 25, Flesch ≥ 60, ≤ 3% words of 12+ letters.
  These matter specifically for a non-English-medium reader, so they are enforced mechanically.
- *No unexplained jargon*: a code check finds the **first** use of each technical term and requires
  a definition cue in that sentence. It is crude, so an LLM check (`jargon_explained`) backs it up.
  Two layers, because jargon is the failure I most expect from a model.

LLM checks run on every attempt even when code checks already failed. Skipping them would save
tokens but give the generator partial feedback and cause an extra retry for the failures it did
not hear about. Retries are the scarcest resource (capped at 2), so feedback must be complete.

## 4. Failure handling: fail closed

- Judge returns invalid JSON → one retry → then **every LLM checkpoint fails**. A broken grader
  never produces a pass.
- Judge skips a checkpoint → that checkpoint fails.
- A failure verdict must include a quote; the system checks the quote exists in the lesson
  (`evidence_verified`) so a hallucinated complaint is visible in the log.
- Retries are capped (`1 + max_retries` attempts), so the loop is guaranteed to terminate.
- After the cap, the draft is saved as `lesson.DRAFT_NEEDS_REVIEW.md` and the process exits 1.
  The system never labels a failing lesson as shipped.

## 5. Why LangGraph

The control flow is a real state machine: generate → evaluate → conditional edge (retry/finalize)
→ learn. LangGraph makes that explicit and inspectable (a conditional edge is the whole "decide
whether to ship" idea in one line), without forcing the LLM to decide control flow. I deliberately
kept routing **deterministic** (`all checkpoints passed?`), not LLM-chosen. The model writes and
judges; code decides. I chose Python over n8n because the evaluator's code checks, fail-closed
logic and tests are much easier to express and verify in code.

## 6. Memory and self-evolution, and where I drew the line

Plain JSON memory, on purpose: a reviewer can open it, diff it, and understand it in a minute.

- **Counted per run, not per attempt**, so one bad session does not look like a pattern.
- **Auto-applied: generator guidelines.** When a checkpoint fails in ≥ 2 runs, one short rule is
  distilled from the failure reasons and added to the generator prompt. Low risk, reversible.
- **Human-approved: the rubric.** The system can *propose* rubric edits (`rubric_proposals.md`) but
  cannot apply them. If it could, the cheapest way to "improve" the pass rate is to lower the bar.
  Letting the writer edit the grading standard is the classic reward-hacking failure.
- Human feedback (`feedback` command) enters the same channel, so a reviewer's note ("use Karnataka
  examples") affects every future lesson.
- Guideline injection is capped at the 8 most recent, to stop prompt bloat.

## 7. Trade-offs I accepted

| Choice | Cost | Why I accepted it |
|---|---|---|
| Fact sheet instead of live retrieval for grounding | Accuracy ceiling = the sheet | Predictable and auditable; a live-RAG grader would add its own failure modes to a RAG lesson. |
| Strict thresholds | Real models may need a retry or two | The audience is the constraint. A retry is cheap; a confusing lesson is not. |
| Keyword-style jargon check | False positives/negatives | Cheap tripwire; the LLM check is the real judge. |
| Same provider for generate and judge by default | Shared blind spots | `--judge-model` lets you split them; the code checks and fact sheet limit the damage. |
| JSON file memory | No concurrency, no scale | Right size for one pipeline; swap for SQLite/a DB if it ran in parallel. |

## 8. What I would do next

1. Calibrate thresholds on 20+ real generations and report the false-fail rate per checkpoint.
2. Add a small "golden set" of known-bad lessons (one defect each) as a regression test for the
   judge, so a prompt change to the judge cannot silently make it more lenient.
3. Evaluate with a *different-family* judge and track agreement with the primary judge.
4. A real learner test: have 5 target-audience readers answer the "Check yourself" questions;
   use their results as ground truth for whether the rubric predicts understanding.
5. Generalise: topic-specific fact sheets generated from vetted sources, one rubric template per topic.
