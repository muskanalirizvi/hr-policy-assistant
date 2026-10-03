import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.ERROR)

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")


def to_text(content):
    # Kuch Gemini versions content ko list of blocks mein dete hain
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content