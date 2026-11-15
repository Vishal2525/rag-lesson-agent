# Fact sheet: Retrieval-Augmented Generation (RAG)

This is the ground truth the evaluator uses to judge accuracy. It is deliberately short and
conservative: only well-established, non-controversial facts. A lesson may add simple
explanations and examples, but it must not contradict anything here or state specific
numbers, product claims or benchmarks that are not here.

## Key points a beginner lesson must cover

- K1. An LLM (large language model) answers using patterns learned from its training data. That
  data stops at a certain date, so the model does not know newer events.
- K2. An LLM does not have access to private information (a company's or college's own
  documents) unless it is given that information. When it lacks the facts it may produce
  confident, wrong, made-up answers. This is called hallucination.
- K3. RAG = Retrieval-Augmented Generation. The idea: first RETRIEVE relevant information from an
  external source (documents), then AUGMENT the question by adding that information, then
  GENERATE the answer with the LLM using it.
- K4. How it works. Preparation (done ahead of time): split documents into small chunks,
  convert each chunk into an embedding, store embeddings in a vector database. At question
  time: convert the question into an embedding, search the vector database for the most similar
  chunks, put the question and those chunks together in the prompt, and let the LLM write the
  answer from them.
- K5. An embedding is a list of numbers that represents the meaning of a piece of text. Texts
  with similar meaning get similar numbers, which is what makes search-by-meaning possible.
- K6. Why it matters: answers can use up-to-date information and private documents; fewer made-up
  answers; the answer can point to its source; updating knowledge means updating the documents,
  which is far cheaper and faster than training a new model.
- K7. Limits: if retrieval finds the wrong or outdated chunks, the answer can still be wrong.
  RAG reduces hallucination but does not eliminate it. Quality depends on the documents.

## Facts the lesson must NOT contradict

- RAG does NOT retrain the model or change its internal weights. The model stays the same; only
  the input (prompt) changes.
- RAG is NOT only a search engine. A search step is one part; the LLM still writes the answer.
- RAG does NOT guarantee correct answers or remove hallucination completely.
- The vector database stores embeddings (numbers) of chunks, usually together with the original
  chunk text, so the text can be handed to the LLM.
- Retrieval finds chunks by closeness of meaning (similarity of embeddings), not only by
  matching exact words.
- The RAG idea was introduced in a 2020 research paper by Lewis et al. (Facebook AI Research).
  A lesson need not mention this, but if it does, it must not give a different year or origin.
