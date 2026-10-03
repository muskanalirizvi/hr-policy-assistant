import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from rag.retriever import get_vector_store, retrieve

load_dotenv()
logging.getLogger("google_genai").setLevel(logging.ERROR) # INFO wale logs band

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")

MIN_SCORE = 0.01  # isse kam score wale chunks bilkul irrelevant hain

PROMPT = """You are Acme Corp's HR assistant. Answer the question using ONLY the policy excerpts below.
If the excerpts do not contain the answer, reply with exactly: NOT_IN_POLICY

Rules:
- Be concise.
- Cite the policy and section, e.g. (Leave Policy, 1. Annual Leave).

Policy excerpts:
{context}

Question: {question}"""


def to_text(content):
    # Kuch Gemini versions content ko list of blocks mein dete hain
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content


def answer(store, question):
    docs = [d for d in retrieve(store, question) if d.metadata["rerank_score"] >= MIN_SCORE]
    if not docs:
        return None, []  # koi relevant chunk nahi → web fallback

    context = "\n\n".join(d.page_content for d in docs)
    resp = llm.invoke(PROMPT.format(context=context, question=question))
    text = to_text(resp.content).strip()

    if "NOT_IN_POLICY" in text:
        return None, docs  # chunks mile, lekin jawab nahi → web fallback
    return text, docs


if __name__ == "__main__":
    store = get_vector_store()

    test_questions = [
        "Can I take annual leave during probation?",
        "Can I work from Dubai for a few weeks?",
        "What is the $300 allowance for?",
        "What is the legal minimum maternity leave in Pakistan?",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        text, docs = answer(store, q)
        if text is None:
            print("  → NOT IN POLICY (web fallback chalega)")
        else:
            print(f"  A: {text}")

    store.client.close()
    