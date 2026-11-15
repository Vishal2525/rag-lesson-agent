# Example output (OFFLINE MOCK, not a real model)

`rejection_log.md` was produced by:

    MOCK_SCENARIO=good python -m lessongen run --provider mock --inject-error

It shows the log format only. The lesson text and the grader here are canned test doubles
(`lessongen/mock_llm.py`). Your submission log and lesson must come from a real model run.
