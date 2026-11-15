## 2026-11-16 00:12 - checkpoint `length`

Update the requirement to: "Between 450 and 1100 words: complete enough to teach, short enough for a beginner to finish."

## 2026-11-16 00:12 - checkpoint `acronym_expanded`

The requirement is overly strict and flags common, grammatically correct ways of introducing an acronym as errors. The current wording "The first sentence that uses 'RAG' also says what it stands for" means that if the full term is introduced in one sentence and then the acronym is used for the first time in the *next* sentence, it would fail, even though the full term has already been provided. This is not conducive to good writing flow for beginners.

The current failure reasons ("'RAG' is used before it is expanded.") indicate the core problem, which is that the acronym appears before its meaning is clear. The proposed change addresses this directly without imposing an artificial constraint on sentence structure.

Proposal: "The full term 'Retrieval-Augmented Generation' must appear before 'RAG' is used for the first time."

