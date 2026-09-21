
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

_client = None
_init_error = None

if API_KEY:
    try:
        from google import genai
        _client = genai.Client(api_key=API_KEY)
    except Exception as e:  # pragma: no cover
        _init_error = str(e)

NO_KEY_MESSAGE = (
    "⚠️ **No Gemini API key configured.**\n\n"
    "1. Get a free key at https://aistudio.google.com/apikey\n"
    "2. Open the `.env` file in this project\n"
    "3. Set `GEMINI_API_KEY=your_key_here`\n"
    "4. Restart the server (`uvicorn main:app --reload`)\n\n"
    "Once that's done, this page will generate real answers for any topic."
)


def _generate(prompt: str) -> str:
    if _init_error:
        return f"⚠️ Could not initialize Gemini: {_init_error}"
    if not _client:
        return NO_KEY_MESSAGE
    try:
        response = _client.models.generate_content(model=MODEL_NAME, contents=prompt)
        text = (response.text or "").strip()
        return text if text else "Sorry, I couldn't generate a response. Please try again."
    except Exception as e:
        msg = str(e)
        if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in msg or "401" in msg:
            return (
                "⚠️ **Google rejected this API key (401 ACCESS_TOKEN_TYPE_UNSUPPORTED).**\n\n"
                "This is a known, currently unresolved issue with Google's new `AQ.` key "
                "rollout affecting many developers right now — it is not a bug in this app. "
                "Options while Google fixes it:\n"
                "- Try regenerating the key in [AI Studio](https://aistudio.google.com/apikey) "
                "a couple of times (some accounts intermittently get a working key)\n"
                "- Report it via Google's compatibility form linked from the "
                "[API key docs](https://ai.google.dev/gemini-api/docs/api-key)\n"
                "- Check https://discuss.ai.google.dev for the latest status"
            )
        return f"⚠️ Error contacting Gemini API: {e}"


def ask_question(question: str) -> str:
    prompt = (
        "You are EduGenie, a friendly AI-powered educational assistant. "
        "Answer the student's question clearly and accurately, in simple language, "
        "with short paragraphs, **bold** for key terms, and bullet points where useful. "
        "Keep it focused and not too long.\n\n"
        f"Student's question: {question}"
    )
    return _generate(prompt)


def generate_quiz(topic: str, difficulty: str, count: int) -> str:
    count = max(1, min(count, 20))
    prompt = (
        f"You are EduGenie, an AI quiz generator. Create {count} multiple-choice "
        f"questions about '{topic}' at a {difficulty} difficulty level.\n\n"
        "Format each question in markdown exactly like this:\n"
        "**1. <question text>**\n"
        "A) option\nB) option\nC) option\nD) option\n\n"
        "**Correct Answer:** <letter>) <text>\n"
        "**Explanation:** <one short sentence>\n\n---\n\n"
        "Start with a short one-paragraph friendly intro to the topic before the quiz, "
        "then a '### Quiz Time!' heading, then the questions."
    )
    return _generate(prompt)


def summarize_text(text: str) -> str:
    prompt = (
        "You are EduGenie, an AI study-notes summarizer. Summarize the following "
        "material into a clear, well-organized markdown summary: use headings, "
        "bold key terms, and bullet points, and keep it significantly shorter than "
        "the original while preserving the important concepts.\n\n"
        f"Material:\n{text}"
    )
    return _generate(prompt)


def generate_roadmap(topic: str) -> str:
    prompt = (
        f"You are EduGenie, an AI tutor. Create a structured, week-by-week learning "
        f"roadmap for mastering '{topic}', going from beginner to advanced.\n\n"
        "Start with a short friendly one-paragraph intro, then a "
        "'# 🚀 Your Learning Roadmap for <topic>' heading, then organize the plan "
        "into weekly phases with '## Week N: <focus area>' headings, bullet points "
        "for topics/resources to study each week, and end with a short "
        "'## Outcome' section describing what the learner will be able to do."
    )
    return _generate(prompt)
