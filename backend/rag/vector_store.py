import json
import re
from pathlib import Path

import faiss
import numpy as np

from ..config import FAISS_DIR


class VectorStoreManager:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or FAISS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_name(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower())

    def _subject_dir(self, year: str, subject: str) -> Path:
        key = f"{self._safe_name(year)}__{self._safe_name(subject)}"
        path = self.base_dir / key
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _index_path(self, year: str, subject: str) -> Path:
        return self._subject_dir(year, subject) / "index.faiss"

    def _meta_path(self, year: str, subject: str) -> Path:
        return self._subject_dir(year, subject) / "metadata.json"

    def _load_index(self, year: str, subject: str) -> faiss.Index | None:
        index_path = self._index_path(year, subject)
        if not index_path.exists():
            return None
        return faiss.read_index(str(index_path))

    def _save_index(self, year: str, subject: str, index: faiss.Index) -> None:
        faiss.write_index(index, str(self._index_path(year, subject)))

    def _load_metadata(self, year: str, subject: str) -> list[dict]:
        meta_path = self._meta_path(year, subject)
        if not meta_path.exists():
            return []
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def _save_metadata(self, year: str, subject: str, metadata: list[dict]) -> None:
        self._meta_path(year, subject).write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")

    def add_embeddings(self, year: str, subject: str, embeddings: list[list[float]], metadata_rows: list[dict]) -> int:
        if not embeddings:
            return 0

        matrix = np.array(embeddings, dtype=np.float32)
        dim = matrix.shape[1]
        index = self._load_index(year, subject)

        if index is None:
            index = faiss.IndexFlatL2(dim)

        if index.d != dim:
            raise ValueError(
                f"Embedding dimension mismatch for {year}/{subject}. Existing: {index.d}, New: {dim}"
            )

        index.add(matrix)
        self._save_index(year, subject, index)

        metadata = self._load_metadata(year, subject)
        metadata.extend(metadata_rows)
        self._save_metadata(year, subject, metadata)
        return len(embeddings)

    def search(self, year: str, subject: str, query_embedding: list[float], top_k: int = 4) -> list[dict]:
        index = self._load_index(year, subject)
        if index is None or index.ntotal == 0:
            return []

        metadata = self._load_metadata(year, subject)
        if not metadata:
            return []

        query = np.array([query_embedding], dtype=np.float32)
        k = min(top_k, len(metadata), index.ntotal)
        distances, indices = index.search(query, k)

        results: list[dict] = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(metadata):
                continue
            row = dict(metadata[idx])
            row["score"] = float(distance)
            results.append(row)

        return results
