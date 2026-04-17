from sentence_transformers import SentenceTransformer

from ..config import EMBEDDING_MODEL_NAME


_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode([text], normalize_embeddings=True)
    return vector[0].tolist()
