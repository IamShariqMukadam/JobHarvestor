# clustering/embedder.py
from sentence_transformers import SentenceTransformer
import numpy as np
import os

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDINGS_CACHE = os.path.join(os.getenv("JH_SESSION_DIR","data"), "embeddings.npy")


def get_embeddings(texts: list[str], force_recompute=False) -> np.ndarray:
    """
    Converts list of text strings to embedding vectors.
    Caches to disk — won't recompute on re-run unless forced.
    Cache is invalidated automatically if job count changes.
    """
    if os.path.exists(EMBEDDINGS_CACHE) and not force_recompute:
        cached = np.load(EMBEDDINGS_CACHE)
        if len(cached) == len(texts):
            print("  [Embedder] Loading cached embeddings...")
            return cached
        print(f"  [Embedder] Cache mismatch ({len(cached)} cached vs {len(texts)} jobs) — recomputing...")

    print(f"  [Embedder] Computing embeddings for {len(texts)} texts...")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    np.save(EMBEDDINGS_CACHE, embeddings)
    print(f"  [Embedder] Saved → {EMBEDDINGS_CACHE}")
    return embeddings