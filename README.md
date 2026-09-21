# 🎓 EduGenie AI

An AI-powered educational assistant — Ask AI, Quiz Generator, Text Summarizer,
Learning Roadmap, Dashboard and Chat History — built with **FastAPI** +
**Google Gemini**, matching the original mini-project UI.

It works with **any topic you type in**, because every page calls the Gemini
API in real time.

## 1. Requirements

- Python 3.9+
- A free Google Gemini API key: https://aistudio.google.com/apikey

## 2. Setup

```bash
# 1. Unzip and enter the project
cd edugenie-ai

# 2. (Recommended) create a virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Gemini API key
cp .env.example .env
# then open .env and paste your key:
#   GEMINI_API_KEY=your_key_here
```

## 3. Run it

```bash
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

## 4. Pages

| Page             | URL             | What it does                                   |
|------------------|-----------------|-------------------------------------------------|
| Home             | `/`             | Landing page with feature cards                 |
| Dashboard        | `/dashboard`    | Usage stats + recent activity                    |
| Ask AI           | `/ask-ai`       | Chat with Gemini about any academic topic        |
| Quiz Generator   | `/quiz`         | Generates MCQ quizzes on any topic + difficulty  |
| Text Summarizer  | `/summary`      | Summarizes any pasted text                       |
| Learning Roadmap | `/roadmap-page` | Generates a week-by-week roadmap on any subject  |
| History          | `/history`      | Past Ask AI conversations, with a clear button   |

## 5. Notes

- All activity (questions, quizzes, summaries, roadmaps) is saved to
  `data/history.json`, which is what powers the Dashboard stats and History page.
- Dark mode toggle (top-right moon icon) is saved in the browser's local storage.
- The Users page is private to the first registered account, which becomes the app owner. Set `ADMIN_USERNAME` in the environment to override the owner username.
- If you haven't set `GEMINI_API_KEY` yet, every page will still load and clearly
  tell you how to add your key instead of crashing.
- To change the Gemini model, set `GEMINI_MODEL` in `.env`
  (defaults to `gemini-2.0-flash`).

## 6. Project structure

```
edugenie-ai/
├── main.py            # FastAPI app & routes
├── ai_service.py       # Gemini prompt logic for all 4 AI features
├── requirements.txt
├── .env.example
├── data/history.json   # auto-created activity log
├── templates/          # Jinja2 HTML pages
└── static/
    ├── css/style.css   # light/dark theme, matches original design
    └── js/main.js       # dark mode + fetch helpers
```
