# Rejection log: Introduction to RAG (Retrieval-Augmented Generation)

- Run: `20261115-165225`
- Generator: `mock (offline test double)`  |  Judge: `mock (offline test double)`
- Rule: ALL 14 checkpoints must pass. Max 2 retries.
- Result: **SHIPPED (passed)** after 2 attempt(s)

## Attempt 1: REJECTED (13/14 checkpoints passed)

> Deliberate error injected for the demo: "RAG works by retraining the AI model on your documents every time you ask a question, so the model always gives the right answer."

| Checkpoint | Dimension | Why it failed | Evidence |
|---|---|---|---|
| `accurate_grounded` | accurate_grounded | Claims RAG guarantees correct answers, which contradicts the fact sheet. | RAG works by retraining the AI model on your documents every time you ask a question, so the model always gives the right answer. |

**What changed on retry (attempt 2):**
- Size 891 -> 867 words; 99% of the wording kept.
- Fixed `accurate_grounded` as the grader asked.
- Kept the sections that already passed.

## Attempt 2: PASSED (14/14 checkpoints passed)
