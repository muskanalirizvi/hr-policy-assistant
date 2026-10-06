import logging
from dotenv import load_dotenv
from rag.retriever import get_vector_store, retrieve
from agent.llm import llm, to_text

load_dotenv()
logging.getLogger("google_genai").setLevel(logging.ERROR) 


MIN_SCORE = 0.0  

PROMPT = """You are Acme Corp's HR assistant. Answer the question using ONLY the policy excerpts below.
If the excerpts do not contain the answer, reply with exactly: NOT_IN_POLICY


Rules:
- Be concise, but include the key details from the excerpts (numbers, limits, what each item covers).
- Cite the policy and section once, at the end of the answer, e.g. (Leave Policy, 1. Annual Leave)..
- Reply in the same language as the question (English, Urdu or Roman Urdu).

Policy excerpts:
{context}

Question: {question}"""


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
    