import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RUBRIC_PATH = Path(os.getenv("LESSONGEN_RUBRIC", ROOT / "rubric.yaml"))
FACTS_PATH = Path(os.getenv("LESSONGEN_FACTS", ROOT / "facts" / "rag_facts.md"))
MEMORY_DIR = Path(os.getenv("LESSONGEN_MEMORY_DIR", ROOT / "memory"))
OUTPUT_DIR = Path(os.getenv("LESSONGEN_OUTPUT_DIR", ROOT / "output"))

# Retries after the first attempt. 2 => at most 3 attempts, so the loop always ends.
MAX_RETRIES = int(os.getenv("LESSONGEN_MAX_RETRIES", "2"))

# A checkpoint must fail in this many *runs* since its last evolution before we evolve.
EVOLVE_THRESHOLD = int(os.getenv("LESSONGEN_EVOLVE_THRESHOLD", "2"))

DEFAULT_TOPIC = "Introduction to RAG (Retrieval-Augmented Generation)"

AUDIENCE = (
    "A student who just finished 12th grade in India. Their schooling was not in English medium, "
    "so their English vocabulary is limited. They have zero background in AI, machine learning "
    "or programming. They want to start a career in AI and need to truly understand the idea, "
    "not just memorise words."
)
