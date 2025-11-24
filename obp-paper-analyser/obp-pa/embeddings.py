from typing import List

from sentence_transformers import SentenceTransformer


_model: SentenceTransformer | None = None


def get_text_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_text_embedding_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()
