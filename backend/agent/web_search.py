import logging
import os
from dotenv import load_dotenv
from tavily import TavilyClient
from agent.llm import llm, to_text

load_dotenv()
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.ERROR)

tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

DISCLAIMER = (
    "⚠️ This is general information from the web, not official Acme Corp policy. "
    "Please confirm with HR before relying on it."
)

PROMPT = """Answer the question using ONLY the web search results below. Be concise (3-5 sentences).
Do not mention "search results" or "provided results" in your answer.
If the results don't answer the question, say you couldn't find a reliable answer.

Search results:
{results}

Question: {question}"""


def web_answer(question):
    results = tavily.search(question, max_results=3).get("results", [])
    if not results:
        return f"I couldn't find anything reliable on this.\n\n{DISCLAIMER}", []

    context = "\n\n".join(
        f"[{i + 1}] {r['title']} ({r['url']})\n{r['content']}" for i, r in enumerate(results)
    )
    resp = llm.invoke(PROMPT.format(results=context, question=question))
    text = to_text(resp.content).strip()
    sources = [r["url"] for r in results]
    return f"{text}\n\n{DISCLAIMER}", sources


if __name__ == "__main__":
    for q in [
        "What is the legal minimum maternity leave in Pakistan?",
        "What is a typical notice period when resigning from a job?",
    ]:
        answer, sources = web_answer(q)
        print(f"\nQ: {q}\nA: {answer}\nSources:")
        for s in sources:
            print("  -", s)