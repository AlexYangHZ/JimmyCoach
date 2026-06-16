"""Lightweight Chinese text retrieval using jieba + TF-IDF.

No GPU or model download needed. Works immediately.
"""

import re
import pickle
import asyncio
from pathlib import Path

import jieba

# Lazy imports to avoid sklearn TLS issues at server startup
_np = None
_TfidfVectorizer = None
_cosine_similarity = None

def _get_sklearn():
    global _np, _TfidfVectorizer, _cosine_similarity
    if _np is None:
        import numpy as _np_module
        _np = _np_module
    if _TfidfVectorizer is None:
        from sklearn.feature_extraction.text import TfidfVectorizer as TF
        _TfidfVectorizer = TF
    if _cosine_similarity is None:
        from sklearn.metrics.pairwise import cosine_similarity as CS
        _cosine_similarity = CS

MARKDOWN_DIR = Path("data/textbooks/math/grade7")
CACHE_PATH = Path("data/vectordb/math/retriever.pkl")


class MathRetriever:
    """TF-IDF based retriever for math textbook content."""

    def __init__(self, markdown_dir=None, cache_path=None):
        self.vectorizer = None
        self.doc_vectors = None
        self.documents = []
        self.markdown_dir = markdown_dir or MARKDOWN_DIR
        self.cache_path = cache_path or CACHE_PATH

    def _chunk_text(self, text: str, max_chars: int = 500) -> list[str]:
        """Split text into chunks of ~max_chars, preserving paragraph boundaries."""
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) < max_chars:
                current += para + "\n\n"
            else:
                if len(current) >= 50:
                    chunks.append(current.strip())
                current = para + "\n\n"

        if len(current) >= 50:
            chunks.append(current.strip())

        return chunks or [text.strip()[:1000]]

    def _tokenize(self, text: str) -> str:
        """Chinese word segmentation, returns space-separated tokens."""
        return " ".join(jieba.cut(text))

    def build_index(self):
        """Load all markdown files, chunk, and build TF-IDF index."""
        print("Building TF-IDF index for math textbook...")

        all_texts = []
        all_metadata = []

        for md_file in sorted(self.markdown_dir.rglob("*.md")):
            # Parse path for metadata
            rel = md_file.relative_to(self.markdown_dir)
            parts = rel.parts

            chapter = "Unknown"
            section = "Unknown"
            source_file = str(rel)

            if parts:
                ch_match = re.match(r"chapter_(\d+)", parts[0])
                if ch_match:
                    ch_num = int(ch_match.group(1))
                    chapter = f"第{ch_num}章"

            if len(parts) >= 2:
                fn = parts[1]
                sec_match = re.match(r"section_(\d+)\.md", fn)
                if sec_match:
                    section = f"知识点{sec_match.group(1)}"
                elif "activity" in fn:
                    section = "拓展阅读"

            # Parse actual title from first heading
            text = md_file.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)", text, re.MULTILINE)
            if title_match:
                section = title_match.group(1).strip()

            # Chunk and store
            chunks = self._chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_texts.append(chunk)
                all_metadata.append({
                    "text": chunk,
                    "chapter": chapter,
                    "section": section,
                    "source": source_file,
                    "chunk_idx": i,
                })

        # Build TF-IDF with Chinese tokenizer
        print(f"  Tokenizing {len(all_texts)} chunks...")
        tokenized = [self._tokenize(t) for t in all_texts]

        _get_sklearn()
        self.vectorizer = _TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),  # unigrams + bigrams
            sublinear_tf=True,
        )
        self.doc_vectors = self.vectorizer.fit_transform(tokenized)
        self.documents = all_metadata

        print(f"  Built index: {len(self.documents)} documents, "
              f"{self.doc_vectors.shape[1]} features")

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for most relevant chunks. Falls back to keyword match if TF-IDF fails."""
        if self.vectorizer is None:
            self.build_index()

        _get_sklearn()
        query_tok = self._tokenize(query)
        query_vec = self.vectorizer.transform([query_tok])
        scores = _cosine_similarity(query_vec, self.doc_vectors)[0]

        top_indices = _np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0.01:
                doc = self.documents[idx]
                results.append({
                    "text": doc["text"], "chapter": doc["chapter"],
                    "section": doc["section"], "source": doc["source"],
                    "score": float(scores[idx]),
                })

        # Fallback: if TF-IDF fails (e.g., cross-language query), try keyword match
        if not results:
            results = self._keyword_search(query, top_k)

        return results

    def _keyword_search(self, query: str, top_k: int = 5) -> list[dict]:
        """Simple keyword/substring match fallback for cross-language queries."""
        keywords = query.lower().split()
        # Also try character-level for Chinese queries against English docs
        if any('一' <= c <= '鿿' for c in query):
            keywords = list(query)  # character-level for Chinese

        scored = []
        for doc in self.documents:
            text_lower = doc["text"].lower()
            score = sum(text_lower.count(kw.lower()) for kw in keywords if len(kw) >= 1)
            if score > 0:
                scored.append({**doc, "score": float(score) / max(1, len(text_lower)) * 100})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def search_with_threshold(self, query: str, top_k: int = 5, min_score: float = 0.05) -> list[dict]:
        """Search with score threshold filtering."""
        results = self.search(query, top_k=top_k * 2)  # oversample
        filtered = [r for r in results if r.get("score", 0) >= min_score]
        return filtered[:top_k]

    def save(self):
        """Cache the built index to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "wb") as f:
            pickle.dump({
                "vectorizer": self.vectorizer,
                "doc_vectors": self.doc_vectors,
                "documents": self.documents,
            }, f)
        print(f"  Cached to {CACHE_PATH}")

    def load(self) -> bool:
        """Load cached index from disk. Returns True if successful."""
        if self.cache_path.exists():
            with open(self.cache_path, "rb") as f:
                data = pickle.load(f)
            self.vectorizer = data["vectorizer"]
            self.doc_vectors = data["doc_vectors"]
            self.documents = data["documents"]
            print(f"Loaded cached index: {len(self.documents)} documents")
            return True
        return False


# Global singleton with init lock
_retriever: MathRetriever | None = None
_retriever_lock = asyncio.Lock()


async def get_retriever() -> MathRetriever:
    """Get or create the global retriever instance (thread-safe)."""
    global _retriever
    if _retriever is not None:
        return _retriever
    async with _retriever_lock:
        if _retriever is not None:
            return _retriever
        _retriever = MathRetriever()
        if not _retriever.load():
            _retriever.build_index()
            _retriever.save()
        return _retriever


def get_retriever_sync() -> MathRetriever:
    """Synchronous fallback for non-async contexts."""
    global _retriever
    if _retriever is None:
        _retriever = MathRetriever()
        if not _retriever.load():
            _retriever.build_index()
            _retriever.save()
    return _retriever


def search_textbook(query: str, top_k: int = 5) -> list[dict]:
    """Convenience function: search the math textbook."""
    return get_retriever().search(query, top_k)


# ---- Multi-subject retrieval ----

AVAILABLE_RETRIEVERS: dict[str, "MathRetriever"] = {}
_retrievers_lock = asyncio.Lock()


async def get_multi_retriever(subject: str | None = None) -> dict[str, "MathRetriever"]:
    """Get retrievers for specified subject(s). If None, return all available."""
    global AVAILABLE_RETRIEVERS

    textbooks_dir = Path("data/textbooks")
    available = []
    if textbooks_dir.exists():
        for d in textbooks_dir.iterdir():
            if d.is_dir() and (d / "grade7").exists():
                available.append(d.name)

    async with _retrievers_lock:
        targets = [subject] if subject else available
        result = {}
        for subj in targets:
            if subj not in available:
                continue
            if subj not in AVAILABLE_RETRIEVERS:
                md_dir = Path(f"data/textbooks/{subj}/grade7")
                cache = Path(f"data/vectordb/{subj}/retriever.pkl")
                cache.parent.mkdir(parents=True, exist_ok=True)
                r = MathRetriever(markdown_dir=md_dir, cache_path=cache)
                if not r.load():
                    try:
                        r.build_index()
                        r.save()
                    except Exception as e:
                        print(f"[Retriever] Failed to build index for {subj}: {e}")
                        continue
                AVAILABLE_RETRIEVERS[subj] = r
            result[subj] = AVAILABLE_RETRIEVERS[subj]
        return result


async def search_all(query: str, subject: str | None = None, top_k: int = 5, min_score: float = 0.05) -> list[dict]:
    """Search across one or all retrievers, return merged ranked results."""
    retrievers = await get_multi_retriever(subject)
    all_results = []
    for subj, retriever in retrievers.items():
        results = retriever.search_with_threshold(query, top_k=top_k, min_score=min_score)
        for r in results:
            r["subject"] = subj
        all_results.extend(results)

    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_results[:top_k]


# Build on import
if __name__ == "__main__":
    r = get_retriever()
    print("\n=== Test Queries ===")
    for q in ["什么是正数和负数？", "有理数的乘法怎么算？", "一元一次方程怎么解？"]:
        print(f"\n🔍 Q: {q}")
        results = r.search(q, top_k=3)
        for i, res in enumerate(results):
            print(f"  #{i+1} [{res['chapter']} | {res['section']}] score={res['score']:.3f}")
            print(f"     {res['text'][:100]}...")
