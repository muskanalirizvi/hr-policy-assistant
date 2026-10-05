from dotenv import load_dotenv
from flashrank import Ranker, RerankRequest
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from rag.ingest import get_embeddings, get_sparse_embeddings, COLLECTION, qdrant_kwargs

load_dotenv()

ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=".flashrank_cache")


def get_vector_store():
    return QdrantVectorStore.from_existing_collection(
        embedding=get_embeddings(),
        sparse_embedding=get_sparse_embeddings(),
        retrieval_mode=RetrievalMode.HYBRID,
        **qdrant_kwargs(),
        collection_name=COLLECTION,
    )


def retrieve(store, question, fetch_k=6, top_n=3):
    # 1. Hybrid search se zyada candidates laao
    docs = store.similarity_search(question, k=fetch_k)

    # 2. Reranker sawal aur har chunk ko saath padh ke score deta hai
    passages = [{"id": i, "text": d.page_content} for i, d in enumerate(docs)]
    results = ranker.rerank(RerankRequest(query=question, passages=passages))

    # 3. Top N rakho, score metadata mein save karo
    top_docs = []
    for r in results[:top_n]:
        doc = docs[r["id"]]
        doc.metadata["rerank_score"] = float(r["score"])
        top_docs.append(doc)
    return top_docs


if __name__ == "__main__":
    store = get_vector_store()

    test_questions = [
        "Can I take annual leave during probation?",
        "Can I work from Dubai for a few weeks?",
        "What is the $300 allowance for?",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        for doc in retrieve(store, q):
            print(f"  [{doc.metadata['rerank_score']:.3f}] {doc.metadata['source']} → {doc.metadata.get('section', 'title')}")

    store.client.close()