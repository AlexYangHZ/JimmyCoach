#!/usr/bin/env python3
"""Chunk math Markdown files and create ChromaDB vector store.

Usage: python3 scripts/vectorize_math.py
Creates: data/vectordb/math/
"""

import re
import hashlib
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

MARKDOWN_DIR = Path("data/textbooks/math/grade7")
VECTORDB_DIR = Path("data/vectordb/math")
COLLECTION_NAME = "math_grade7"

# Use a Chinese-optimized embedding model
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def chunk_markdown(text: str, source_file: str, chapter: str, section: str) -> list[dict]:
    """Split markdown text into semantic chunks with metadata.

    Each chunk is ~300-500 chars, preserving paragraph boundaries where possible.
    """
    chunks = []

    # Remove markdown headings for cleaner chunks (metadata has this info)
    cleaned = re.sub(r"^#.*$", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*.*?\*\*", "", cleaned)  # Remove bold markers

    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]

    current_chunk = ""
    for para in paragraphs:
        # Skip very short lines (page numbers, single chars)
        if len(para) < 20:
            continue

        if len(current_chunk) + len(para) < 500:
            current_chunk += para + "\n\n"
        else:
            if len(current_chunk) >= 50:
                chunks.append({
                    "text": current_chunk.strip(),
                    "source": source_file,
                    "chapter": chapter,
                    "section": section,
                })
            current_chunk = para + "\n\n"

    # Don't forget the last chunk
    if len(current_chunk) >= 50:
        chunks.append({
            "text": current_chunk.strip(),
            "source": source_file,
            "chapter": chapter,
            "section": section,
        })

    # If the section is short enough, use it as a single chunk
    if not chunks and len(cleaned) >= 30:
        chunks.append({
            "text": cleaned.strip()[:1000],
            "source": source_file,
            "chapter": chapter,
            "section": section,
        })

    return chunks


def process_markdown_files():
    """Process all markdown files and return list of chunks."""
    all_chunks = []
    md_files = sorted(MARKDOWN_DIR.rglob("*.md"))

    for md_file in md_files:
        # Parse chapter/section from path
        rel = md_file.relative_to(MARKDOWN_DIR)
        parts = rel.parts

        chapter = "Unknown"
        section = "Unknown"

        if len(parts) >= 1:
            ch_dir = parts[0]  # e.g., "chapter_01"
            ch_match = re.match(r"chapter_(\d+)", ch_dir)
            if ch_match:
                chapter = f"第{int(ch_match.group(1))}章"

        if len(parts) >= 2:
            filename = parts[1]
            # Parse section_XX.md
            sec_match = re.match(r"section_(\d+)\.md", filename)
            if sec_match:
                section = f"知识点{sec_match.group(1)}"
            elif "activity" in filename:
                section = "拓展阅读"
            elif "README" in filename:
                section = "章节概述"

        text = md_file.read_text(encoding="utf-8")

        # Parse the actual section title from the first heading
        title_match = re.search(r"^#\s+(.+)", text, re.MULTILINE)
        if title_match:
            section = title_match.group(1).strip()

        chunks = chunk_markdown(text, str(rel), chapter, section)
        if chunks:
            print(f"  {rel}: {len(chunks)} chunks")
            all_chunks.extend(chunks)

    return all_chunks


def create_vector_store(chunks: list[dict]):
    """Create ChromaDB collection from chunks."""
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    VECTORDB_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Creating ChromaDB at {VECTORDB_DIR}")
    client = chromadb.PersistentClient(
        path=str(VECTORDB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    # Delete existing collection if present
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"subject": "math", "grade": "7", "semester": "上册"},
    )

    print(f"Embedding {len(chunks)} chunks...")
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [
            hashlib.md5(c["text"][:100].encode()).hexdigest()[:16] + f"_{j}"
            for j, c in enumerate(batch)
        ]

        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "chapter": c["chapter"],
                    "section": c["section"],
                    "source": c["source"],
                }
                for c in batch
            ],
        )

        if (i + batch_size) % 100 == 0 or i + batch_size >= len(chunks):
            print(f"  {min(i + batch_size, len(chunks))}/{len(chunks)} chunks embedded")

    print(f"\nCollection '{COLLECTION_NAME}' created with {collection.count()} documents")
    return collection


def test_query():
    """Quick test to verify the vector store works."""
    client = chromadb.PersistentClient(
        path=str(VECTORDB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_collection(COLLECTION_NAME)
    model = SentenceTransformer(EMBEDDING_MODEL)

    test_queries = [
        "什么是正数和负数？",
        "如何计算分数的乘法？",
        "一元一次方程怎么解？",
    ]

    print("\n=== Test Queries ===")
    for query in test_queries:
        print(f"\n🔍 Q: {query}")
        embedding = model.encode([query]).tolist()
        results = collection.query(query_embeddings=embedding, n_results=2)

        for j, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            print(f"  #{j+1} [{meta['chapter']} | {meta['section']}] dist={dist:.3f}")
            print(f"     {doc[:120]}...")


def main():
    print("Processing markdown files...")
    chunks = process_markdown_files()
    print(f"\nTotal chunks: {len(chunks)}")

    create_vector_store(chunks)
    test_query()

    print(f"\n✅ Vector store ready at: {VECTORDB_DIR}")


if __name__ == "__main__":
    main()
