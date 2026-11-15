"""Canned lessons for the OFFLINE MOCK provider only (tests and a no-API-key dry run).
The real submission lesson must be generated with a real model."""

GOOD_LESSON = """# Introduction to RAG (Retrieval-Augmented Generation)

## What is RAG?

You may have used an AI chatbot like ChatGPT or Claude. Behind such a chatbot is an LLM (Large Language Model). An LLM is a computer program that has read a huge amount of text and can write answers in simple language.

RAG stands for Retrieval-Augmented Generation. That is a big name, so let us break it into three easy parts.

- Retrieval means finding. Here, it means finding the right information.
- Augmented means made stronger by adding something extra.
- Generation means writing. Here, it means writing the answer.

In short, RAG means this: first find useful information, then add it to the question, then let the AI write the answer.

## Why do we need RAG?

Think about an exam. A student who studied last year's book can answer many questions. But if a question comes from a new chapter, the student may guess. A guess can sound sure and still be wrong.

An LLM is like this student. It learned from text that was collected up to a certain date. This text is called its training data. So an LLM has three problems.

1. It does not know new things that happened after its training stopped.
2. It does not know private things, like your college rules or your shop's price list.
3. When it does not know, it may make up an answer that sounds right. This is called a hallucination.

RAG fixes this. Think of an open-book exam. The student does not need to guess, because the student can look in the book first. For RAG, the book is your own documents.

Here is why this matters:

- Fresh answers. To teach the AI something new, you only change the documents.
- Private answers. The AI can use your own files.
- Fewer made-up answers. The AI reads real text before it answers.
- Proof. The answer can show which document it came from.
- Low cost. You do not need to build a new model, which takes a lot of time and money.

## How does RAG work?

RAG has two parts. Part A is done once, before anyone asks a question. Part B happens every time someone asks a question.

**Part A: Get the documents ready**

1. Collect your documents, for example a PDF of college rules.
2. Cut each document into small pieces. Each piece is called a chunk. A chunk is just a few sentences.
3. Change each chunk into numbers. These numbers are called an embedding. An embedding is a list of numbers that shows the meaning of the text. Chunks with a similar meaning get similar numbers.
4. Save all the embeddings in a special store called a vector database.

**Part B: Answer a question**

1. The user asks a question.
2. The question is also changed into an embedding.
3. The system looks in the vector database for the chunks with the closest numbers. These are the chunks with the closest meaning. This step is the retrieval.
4. The best chunks are added to the question. This new, longer message is called a prompt. A prompt is the message we send to the LLM.
5. The LLM reads the prompt and writes the answer from the chunks.

The LLM itself does not change. RAG only gives it the right pages to read.

## Example: a college question

Ravi studies at a college in Mysuru. The college keeps its rules in a PDF. Ravi asks a chatbot: "What is the last date to pay the exam fee?"

**Without RAG:** The chatbot has never seen the college PDF. It can only guess a date. The guess may be wrong.

**With RAG:**

- Step 1. Ravi's question is changed into an embedding.
- Step 2. The system searches the vector database. It finds this chunk: "The last date to pay the exam fee is 10 December."
- Step 3. The question and the chunk are put together in one prompt.
- Step 4. The LLM answers: "The last date to pay the exam fee is 10 December. This comes from the college rules PDF."

The answer comes from the real document. It is not a guess.

## Limits of RAG

RAG is very helpful, but it is not magic.

- If the system finds the wrong chunks, the answer can be wrong.
- If the documents are old or have mistakes, the answer will have the same mistakes.
- RAG gives fewer made-up answers, but it cannot make them zero. Always check important answers.

## Quick recap

- An LLM can be out of date, can miss private facts, and can make up answers.
- RAG means find, add, and answer.
- Get ready: cut into chunks, make embeddings, save them in a vector database.
- Answer: embed the question, search, build the prompt, and let the LLM write.
- RAG does not change the model. It gives the model the right pages to read.

## Check yourself

1. What do the three words in RAG mean?
2. Why can an LLM give a wrong answer about your college rules?
3. Which step finds the right chunks?
"""

FLAWED_LESSON = """# RAG

## What is RAG

RAG utilizes embeddings and a vector database to subsequently augment the LLM context window, and it retrains the model on your documents so that the LLM never hallucinates, which is approximately the most sophisticated methodology for knowledge-intensive tasks in contemporary natural language processing pipelines.

## How it works

Documents are tokenized and chunked and the semantic embeddings go into the vector store, then the retriever fetches the top-k chunks and the prompt is constructed.
"""
