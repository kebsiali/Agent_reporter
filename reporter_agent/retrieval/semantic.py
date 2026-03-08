from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import ReportKnowledgeBase, SlideRecord

_MODEL_CACHE: dict[str, Any] = {}


@dataclass
class SearchHit:
    rank: int
    score: float
    source_file: str
    slide_index: int
    section: str
    title: str
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "score": self.score,
            "source_file": self.source_file,
            "slide_index": self.slide_index,
            "section": self.section,
            "title": self.title,
            "excerpt": self.excerpt,
        }


def _load_embedding_dependencies():
    try:
        import faiss  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Embedding dependencies missing. Install with: "
            "python -m pip install sentence-transformers faiss-cpu numpy"
        ) from exc
    return faiss, np, SentenceTransformer


def _get_model(SentenceTransformer, embedding_model: str, device: str | None):
    cache_key = f"{embedding_model}::{device or 'default'}"
    if cache_key not in _MODEL_CACHE:
        kwargs = {"device": device} if device else {}
        _MODEL_CACHE[cache_key] = SentenceTransformer(embedding_model, **kwargs)
    return _MODEL_CACHE[cache_key]


def _slide_text(slide: SlideRecord) -> str:
    return f"{slide.title}\n{slide.raw_text}".strip()


def _normalize_rows(mat, np):
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


def _compute_records_hash(records: list[SlideRecord]) -> str:
    h = hashlib.sha256()
    for r in records:
        h.update(r.source_file.encode("utf-8", errors="ignore"))
        h.update(str(r.slide_index).encode("utf-8"))
        h.update(r.title.encode("utf-8", errors="ignore"))
        h.update(r.raw_text.encode("utf-8", errors="ignore"))
        h.update(r.section.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def _load_cached_embeddings(cache_path: Path, expected_hash: str, np):
    if not cache_path.exists():
        return None
    payload = np.load(str(cache_path), allow_pickle=True).item()
    if payload.get("records_hash") != expected_hash:
        return None
    return payload.get("embeddings")


def _save_cached_embeddings(cache_path: Path, records_hash: str, embeddings, np) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(
        str(cache_path),
        {
            "records_hash": records_hash,
            "embeddings": embeddings,
        },
        allow_pickle=True,
    )


def build_semantic_index(
    kb: ReportKnowledgeBase,
    index_dir: Path,
    embedding_model: str,
    batch_size: int = 64,
    device: str | None = None,
    use_embedding_cache: bool = True,
) -> tuple[Path, Path]:
    faiss, np, SentenceTransformer = _load_embedding_dependencies()
    index_dir.mkdir(parents=True, exist_ok=True)

    records = list(kb.slides)
    texts = [_slide_text(s) for s in records]
    if not texts:
        raise ValueError("Knowledge base has no slides to embed.")

    records_hash = _compute_records_hash(records)
    cache_path = index_dir / "embeddings_cache.npy"
    embeddings = None
    if use_embedding_cache:
        embeddings = _load_cached_embeddings(cache_path, records_hash, np)

    if embeddings is None:
        model = _get_model(SentenceTransformer, embedding_model=embedding_model, device=device)
        embeddings = model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            batch_size=batch_size,
            normalize_embeddings=False,
        )
        if use_embedding_cache:
            _save_cached_embeddings(cache_path, records_hash, embeddings, np)

    embeddings = embeddings.astype("float32")
    embeddings = _normalize_rows(embeddings, np)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    index_path = index_dir / "semantic.index"
    meta_path = index_dir / "semantic_meta.json"
    faiss.write_index(index, str(index_path))
    meta_path.write_text(
        json.dumps(
            {
                "embedding_model": embedding_model,
                "size": len(records),
                "device": device or "default",
                "batch_size": batch_size,
                "items": [s.to_dict() for s in records],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return index_path, meta_path


def semantic_search(
    query: str,
    index_dir: Path,
    top_k: int = 5,
    device: str | None = None,
) -> list[SearchHit]:
    faiss, np, SentenceTransformer = _load_embedding_dependencies()
    index_path = index_dir / "semantic.index"
    meta_path = index_dir / "semantic_meta.json"

    if not index_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"Semantic index files not found in {index_dir}. Run `index` first."
        )

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    embedding_model = meta["embedding_model"]
    items = meta["items"]
    slides = [SlideRecord(**item) for item in items]

    model = _get_model(SentenceTransformer, embedding_model=embedding_model, device=device)
    qvec = model.encode([query], convert_to_numpy=True).astype("float32")
    qvec = _normalize_rows(qvec, np)

    index = faiss.read_index(str(index_path))
    scores, indices = index.search(qvec, top_k)

    hits: list[SearchHit] = []
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
        if idx < 0 or idx >= len(slides):
            continue
        slide = slides[idx]
        excerpt = slide.raw_text.strip().replace("\n", " ")
        hits.append(
            SearchHit(
                rank=rank,
                score=float(score),
                source_file=slide.source_file,
                slide_index=slide.slide_index,
                section=slide.section,
                title=slide.title,
                excerpt=excerpt[:280],
            )
        )
    return hits
