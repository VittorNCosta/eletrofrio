"""Knowledge store leve para RAG — TF-IDF + cosseno, stdlib pura.

Substitui a abordagem anterior (sentence-transformers + FAISS + torch,
~1 GB de dependências) que era over-engineering para os 6 documentos
fixos da knowledge base. Para esse volume, TF-IDF com similaridade de
cosseno entrega ranking equivalente, sem dependência pesada — o app
roda em qualquer host (Render free, etc.) sem risco de OOM.

Interface mantida idêntica à anterior (`get_instance()`, `search()`),
então `RagAgent` não precisa saber qual implementação está embaixo.
"""
import math
import re
import unicodedata
from collections import Counter
from typing import Optional

from loguru import logger

from src.infrastructure.rag.knowledge_base import KNOWLEDGE_BASE

# Stopwords PT-BR mínimas — reduzem ruído sem precisar de lib externa.
_STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das",
    "e", "ou", "em", "no", "na", "nos", "nas", "por", "para", "com",
    "se", "que", "ao", "aos", "à", "as", "the", "of", "is", "are",
}


def _normalize(text: str) -> list[str]:
    """Lowercase, remove acentos, tokeniza em [a-z0-9], tira stopwords."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


class KnowledgeStore:
    _instance: Optional["KnowledgeStore"] = None

    def __init__(self) -> None:
        self.docs: list[dict[str, str]] = KNOWLEDGE_BASE
        self._idf: dict[str, float] = {}
        self._doc_vectors: list[dict[str, float]] = []
        self._build()
        logger.info(f"KnowledgeStore (TF-IDF) pronto com {len(self.docs)} documentos")

    def _build(self) -> None:
        tokenized = [
            _normalize(f"{d['title']}. {d['content']}") for d in self.docs
        ]
        n = len(tokenized)
        df: Counter[str] = Counter()
        for toks in tokenized:
            df.update(set(toks))
        # IDF suavizado (estilo sklearn): log((1+n)/(1+df)) + 1
        self._idf = {
            term: math.log((1 + n) / (1 + freq)) + 1.0
            for term, freq in df.items()
        }
        self._doc_vectors = [self._vectorize(toks) for toks in tokenized]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts = Counter(tokens)
        # TF sublinear (1 + log(count)) * IDF
        vec = {
            term: (1.0 + math.log(c)) * self._idf.get(term, 0.0)
            for term, c in counts.items()
        }
        norm = math.sqrt(sum(w * w for w in vec.values()))
        if norm == 0:
            return {}
        return {term: w / norm for term, w in vec.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        # vetores já normalizados → produto escalar = cosseno
        smaller, larger = (a, b) if len(a) < len(b) else (b, a)
        return sum(w * larger.get(term, 0.0) for term, w in smaller.items())

    def search(self, query: str, k: int = 3) -> list[dict[str, str]]:
        q_vec = self._vectorize(_normalize(query))
        if not q_vec:
            return []
        scored = [
            (self._cosine(q_vec, dv), i)
            for i, dv in enumerate(self._doc_vectors)
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, i in scored[:k]:
            if score <= 0.0:
                continue
            results.append({**self.docs[i], "score": float(score)})
        return results

    @classmethod
    def get_instance(cls) -> "KnowledgeStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
