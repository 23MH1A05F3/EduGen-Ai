import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import ai_service

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "history.json"
RESET_CHALLENGES = {}

app = FastAPI(title="EduGenie AI")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def load_data():
    if not DATA_FILE.exists():
        return {"questions": [], "quizzes": [], "summaries": [], "roadmaps": [], "users": [], "admin_username": None}
    with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("questions", [])
    data.setdefault("quizzes", [])
    data.setdefault("summaries", [])
    data.setdefault("roadmaps", [])
    data.setdefault("users", [])
    data.setdefault("admin_username", None)
    return data


def save_data(data):
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- Page routes ----------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return RedirectResponse(url="/signin", status_code=307)


@app.get("/signin", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
@app.get("/signup", response_class=HTMLResponse)
@app.get("/register", response_class=HTMLResponse)
def signin_page(request: Request):
    return templates.TemplateResponse("signin.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/signin", status_code=303)
    data = load_data()
    users = sorted(data.get("users", []), key=lambda x: x.get("registered_at", ""), reverse=True)
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/signin", status_code=303)
    data = load_data()
    recent = sorted(data["questions"], key=lambda x: x["timestamp"], reverse=True)[:5]
    stats = {
        "questions": len(data["questions"]),
        "quizzes": len(data["quizzes"]),
        "summaries": len(data["summaries"]),
        "roadmaps": len(data["roadmaps"]),
    }
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "stats": stats, "recent": recent}
    )


@app.get("/ask-ai", response_class=HTMLResponse)
def ask_page(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse("ask.html", {"request": request})


@app.get("/quiz", response_class=HTMLResponse)
def quiz_page(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse("quiz.html", {"request": request})


@app.get("/summary", response_class=HTMLResponse)
def summary_page(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse("summary.html", {"request": request})


@app.get("/roadmap-page", response_class=HTMLResponse)
def roadmap_page(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse("roadmap.html", {"request": request})


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/signin", status_code=303)
    data = load_data()
    items = sorted(data["questions"], key=lambda x: x["timestamp"], reverse=True)
    return templates.TemplateResponse("history.html", {"request": request, "items": items})


# ---------- Authentication routes ----------

def normalize_username(username: str) -> str:
    return (username or "").strip()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.strip().encode("utf-8"), salt, 600_000
    )
    return f"pbkdf2_sha256$600000${salt.hex()}${derived_key.hex()}"


def password_matches(password: str, stored_password: str) -> bool:
    if stored_password.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt_hex, hash_hex = stored_password.split("$", 3)
            derived_key = hashlib.pbkdf2_hmac(
                "sha256",
                password.strip().encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
            return hmac.compare_digest(derived_key.hex(), hash_hex)
        except (TypeError, ValueError):
            return False
    return hmac.compare_digest(stored_password, hashlib.sha256(password.strip().encode("utf-8")).hexdigest())


def current_user(request: Request):
    username = normalize_username(request.cookies.get("edugenie_user") or "")
    if not username:
        return None
    data = load_data()
    return next(
        (user for user in data.get("users", []) if user.get("username", "").lower() == username.lower()),
        None,
    )


def is_admin(request: Request):
    user = current_user(request)
    if not user:
        return False
    data = load_data()
    configured_admin = (os.getenv("ADMIN_USERNAME") or "").strip()
    admin_username = configured_admin or data.get("admin_username")
    if not admin_username and data.get("users"):
        admin_username = data["users"][0].get("username")
    return bool(admin_username and user.get("username", "").lower() == admin_username.lower())


templates.env.globals["is_admin"] = is_admin


def require_api_user(request: Request):
    if not current_user(request):
        return JSONResponse({"error": "Please sign in first."}, status_code=401)
    return None


@app.post("/api/register")
async def register_user(request: Request):
    payload = await request.json()
    username = normalize_username(payload.get("username") or "")
    password = (payload.get("password") or "").strip()
    security_question = (payload.get("security_question") or "").strip()
    security_answer = (payload.get("security_answer") or "").strip()

    if not username or not password or not security_question or not security_answer:
        return JSONResponse({"error": "Username, password, security question, and answer are required."}, status_code=400)
    if len(username) < 3:
        return JSONResponse({"error": "Username must be at least 3 characters long."}, status_code=400)
    if len(password) < 4:
        return JSONResponse({"error": "Password must be at least 4 characters long."}, status_code=400)

    data = load_data()
    users = data.get("users", [])
    username_lower = username.lower()
    if any(user.get("username", "").lower() == username_lower for user in users):
        return JSONResponse({"error": "This username is already taken. Please choose another one."}, status_code=400)
    users.append(
        {
            "username": username,
            "password": hash_password(password),
            "security_question": security_question,
            "security_answer": hash_password(security_answer),
            "registered_at": datetime.now().isoformat(),
        }
    )
    if not data.get("admin_username"):
        data["admin_username"] = username
    data["users"] = users
    save_data(data)
    return {
        "success": True,
        "message": "Registration successful. You can now sign in with your username and password.",
        "user": {"username": username},
    }


@app.post("/api/login")
async def login_user(request: Request):
    payload = await request.json()
    username = normalize_username(payload.get("username") or "")
    password = (payload.get("password") or "").strip()

    if not username or not password:
        return JSONResponse({"error": "Username and password are required."}, status_code=400)

    data = load_data()
    users = data.get("users", [])
    user = next((u for u in users if u.get("username", "").lower() == username.lower()), None)
    if not user:
        return JSONResponse({"error": "No account found for this username. Please register first."}, status_code=400)
    if not password_matches(password, user.get("password") or ""):
        return JSONResponse({"error": "Incorrect password. Please try again."}, status_code=400)

    if not (user.get("password") or "").startswith("pbkdf2_sha256$"):
        user["password"] = hash_password(password)
        save_data(data)

    response = JSONResponse({
        "success": True,
        "message": "Login successful. Welcome back!",
        "user": {"username": user.get("username")},
    })
    response.set_cookie(key="edugenie_user", value=user.get("username"), httponly=True, samesite="lax")
    return response


@app.post("/api/request-reset-question")
async def request_reset_question(request: Request):
    payload = await request.json()
    username = normalize_username(payload.get("username") or "")
    if not username:
        return JSONResponse({"error": "Username is required."}, status_code=400)

    data = load_data()
    users = data.get("users", [])
    user = next((u for u in users if u.get("username", "").lower() == username.lower()), None)
    if not user:
        return JSONResponse({"error": "No account found with this username."}, status_code=404)

    question = user.get("security_question")
    if not question or not user.get("security_answer"):
        return JSONResponse({"error": "This account does not have a security question."}, status_code=400)
    RESET_CHALLENGES[username.lower()] = {"expires_at": datetime.now().timestamp() + 600}
    return {"success": True, "question": question}


@app.post("/api/verify-security-answer")
async def verify_security_answer(request: Request):
    payload = await request.json()
    username = normalize_username(payload.get("username") or "")
    answer = (payload.get("answer") or "").strip()
    challenge = RESET_CHALLENGES.get(username.lower())
    if not challenge or datetime.now().timestamp() > challenge["expires_at"]:
        return JSONResponse({"error": "The security-question session is missing or expired. Start again."}, status_code=400)

    data = load_data()
    user = next((u for u in data.get("users", []) if u.get("username", "").lower() == username.lower()), None)
    if not user or not password_matches(answer, user.get("security_answer") or ""):
        return JSONResponse({"error": "Incorrect security answer."}, status_code=400)

    reset_token = secrets.token_urlsafe(32)
    challenge["reset_token_hash"] = hashlib.sha256(reset_token.encode("utf-8")).hexdigest()
    challenge["reset_token_expires_at"] = datetime.now().timestamp() + 600
    response = JSONResponse({"success": True, "message": "Answer verified. You can now create a new password."})
    response.set_cookie("edugenie_reset_token", reset_token, httponly=True, samesite="lax", max_age=600)
    return response


@app.post("/api/reset-password")
async def reset_password(request: Request):
    payload = await request.json()
    username = normalize_username(payload.get("username") or "")
    new_password = (payload.get("new_password") or "").strip()
    confirm_password = (payload.get("confirm_password") or "").strip()

    if not username or not new_password or not confirm_password:
        return JSONResponse({"error": "Username, new password, and password confirmation are required."}, status_code=400)
    if new_password != confirm_password:
        return JSONResponse({"error": "The new passwords do not match."}, status_code=400)
    if len(new_password) < 4:
        return JSONResponse({"error": "New password must be at least 4 characters long."}, status_code=400)

    challenge = RESET_CHALLENGES.get(username.lower())
    reset_token = request.cookies.get("edugenie_reset_token") or ""
    if not challenge or not reset_token or datetime.now().timestamp() > challenge.get("reset_token_expires_at", 0):
        return JSONResponse({"error": "Verify the security answer before resetting your password."}, status_code=401)
    if not hmac.compare_digest(
        challenge.get("reset_token_hash", ""), hashlib.sha256(reset_token.encode("utf-8")).hexdigest()
    ):
        return JSONResponse({"error": "Password reset verification is invalid. Start the security-question process again."}, status_code=401)

    data = load_data()
    users = data.get("users", [])
    for user in users:
        if user.get("username", "").lower() == username.lower():
            user["password"] = hash_password(new_password)
            save_data(data)
            RESET_CHALLENGES.pop(username.lower(), None)
            response = JSONResponse({
                "success": True,
                "message": "Password reset successfully. You can now login with your new password.",
                "user": {"username": user.get("username")},
            })
            response.delete_cookie("edugenie_reset_token")
            return response

    return JSONResponse({"error": "No account found with this username."}, status_code=404)


# ---------- API routes ----------

@app.post("/api/ask")
async def api_ask(request: Request):
    unauthorized = require_api_user(request)
    if unauthorized:
        return unauthorized
    payload = await request.json()
    question = (payload.get("question") or "").strip()
    if not question:
        return JSONResponse({"error": "Question is empty"}, status_code=400)
    answer = ai_service.ask_question(question)
    data = load_data()
    data["questions"].append(
        {"question": question, "answer": answer, "timestamp": datetime.now().isoformat()}
    )
    save_data(data)
    return {"answer": answer}


@app.post("/api/quiz")
async def api_quiz(request: Request):
    unauthorized = require_api_user(request)
    if unauthorized:
        return unauthorized
    payload = await request.json()
    topic = (payload.get("topic") or "").strip()
    difficulty = payload.get("difficulty") or "Easy"
    try:
        count = int(payload.get("count") or 5)
    except ValueError:
        count = 5
    if not topic:
        return JSONResponse({"error": "Topic is empty"}, status_code=400)
    quiz = ai_service.generate_quiz(topic, difficulty, count)
    data = load_data()
    data["quizzes"].append(
        {
            "topic": topic,
            "difficulty": difficulty,
            "count": count,
            "quiz": quiz,
            "timestamp": datetime.now().isoformat(),
        }
    )
    save_data(data)
    return {"quiz": quiz}


@app.post("/api/summary")
async def api_summary(request: Request):
    unauthorized = require_api_user(request)
    if unauthorized:
        return unauthorized
    payload = await request.json()
    text = (payload.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "Text is empty"}, status_code=400)
    summary = ai_service.summarize_text(text)
    data = load_data()
    data["summaries"].append(
        {"input": text[:300], "summary": summary, "timestamp": datetime.now().isoformat()}
    )
    save_data(data)
    return {"summary": summary}


@app.post("/api/roadmap")
async def api_roadmap(request: Request):
    unauthorized = require_api_user(request)
    if unauthorized:
        return unauthorized
    payload = await request.json()
    topic = (payload.get("topic") or "").strip()
    if not topic:
        return JSONResponse({"error": "Topic is empty"}, status_code=400)
    roadmap = ai_service.generate_roadmap(topic)
    data = load_data()
    data["roadmaps"].append(
        {"topic": topic, "roadmap": roadmap, "timestamp": datetime.now().isoformat()}
    )
    save_data(data)
    return {"roadmap": roadmap}


@app.post("/api/delete-user")
async def delete_user(request: Request):
    if not is_admin(request):
        return JSONResponse({"error": "Only the app owner can manage users."}, status_code=403)
    payload = await request.json()
    username = normalize_username(payload.get("username") or "")
    if not username:
        return JSONResponse({"error": "Username is required."}, status_code=400)
    current = current_user(request)
    if current and current.get("username", "").lower() == username.lower():
        return JSONResponse({"error": "The app owner cannot delete their own account."}, status_code=400)

    data = load_data()
    users = data.get("users", [])
    updated_users = [user for user in users if (user.get("username") or "").lower() != username.lower()]
    if len(updated_users) == len(users):
        return JSONResponse({"error": "User not found."}, status_code=404)

    data["users"] = updated_users
    save_data(data)
    return {"success": True, "message": "User deleted successfully."}


@app.post("/api/clear-history")
def clear_history(request: Request):
    unauthorized = require_api_user(request)
    if unauthorized:
        return unauthorized
    data = load_data()
    data["questions"] = []
    save_data(data)
    return {"status": "cleared"}
