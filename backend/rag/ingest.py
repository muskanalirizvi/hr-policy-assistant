import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode

load_dotenv()

POLICY_DIR = Path("data/policies")
QDRANT_PATH = "qdrant_data"
COLLECTION = "acme_policies"

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


def qdrant_kwargs():
    """QDRANT_URL ho to Qdrant Cloud, warna local folder."""
    if QDRANT_URL:
        return {"url": QDRANT_URL, "api_key": QDRANT_API_KEY, "timeout": 60}
    return {"path": QDRANT_PATH}


splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "policy"), ("##", "section")],
    strip_headers=False,
)


def load_chunks():
    chunks = []
    for file in sorted(POLICY_DIR.glob("*.md")):
        text = file.read_text(encoding="utf-8")
        for doc in splitter.split_text(text):
            doc.metadata["source"] = file.name
            policy = doc.metadata.get("policy", "")
            if not doc.page_content.startswith("# "):
                doc.page_content = f"{policy}\n{doc.page_content}"
            chunks.append(doc)
    return chunks


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def get_sparse_embeddings():
    return FastEmbedSparse(model_name="Qdrant/bm25")


def ingest():
    chunks = load_chunks()
    QdrantVectorStore.from_documents(
        chunks,
        embedding=get_embeddings(),
        sparse_embedding=get_sparse_embeddings(),
        retrieval_mode=RetrievalMode.HYBRID,
        **qdrant_kwargs(),
        collection_name=COLLECTION,
        force_recreate=True,  # har run pe collection fresh banegi
        batch_size=8,         # chhote batches, taake upload timeout na ho
    )
    print(f"Stored {len(chunks)} chunks in '{COLLECTION}'")


if __name__ == "__main__":
    ingest()