"""
Iron Log — Mini App backend routes.

This is a plain aiohttp RouteTableDef, written so it can be dropped into
whatever aiohttp `web.Application` your bot already runs (most Koyeb/Heroku
Pyrogram bots keep a tiny aiohttp app alive for health checks — see
`web/__init__.py` or wherever your project builds `app = web.Application()`).

Wire it in with:

    from web.gym_api import gym_routes, gym_static
    app.add_routes(gym_routes)
    app.add_routes(gym_static)   # serves the mini app's index.html/app.js/exercises.js

Every request from the mini app carries the raw Telegram `initData` string in
the `X-Telegram-Init-Data` header (see webapp/app.js). We verify it server
side with HMAC-SHA256 against BOT_TOKEN before trusting the user id inside
it — never trust `initDataUnsafe.user.id` sent as plain JSON, since that can
be spoofed by anyone calling the API directly.
"""

import os
import json
import hmac
import hashlib
import time
from urllib.parse import parse_qsl

from aiohttp import web

import database.database as db

try:
    # Matches this project's existing config pattern (see database.py's
    # `from config import DB_URI, DB_NAME`). Adjust the imported name if
    # your config.py calls the bot token something else.
    from config import TG_BOT_TOKEN as BOT_TOKEN
except ImportError:
    BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
INIT_DATA_MAX_AGE = 86400  # seconds; reject stale initData (Telegram recommends this)

gym_routes = web.RouteTableDef()
gym_static = web.RouteTableDef()

# The mini app is deployed on Vercel — a different origin from this API — so
# the browser will block requests unless CORS explicitly allows it. Call
# setup_cors(app, "https://your-project.vercel.app") once, right after
# app.add_routes(gym_routes), in whatever file builds your aiohttp app.
# Requires: pip install aiohttp-cors
def setup_cors(app: web.Application, allowed_origin: str):
    import aiohttp_cors

    cors = aiohttp_cors.setup(app, defaults={
        allowed_origin: aiohttp_cors.ResourceOptions(
            allow_headers="*",
            allow_methods="*",
            expose_headers="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)

WEBAPP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webapp")


# ---------------------------------------------------------------------------
# Telegram WebApp initData verification
# https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
# ---------------------------------------------------------------------------

def verify_init_data(init_data: str) -> dict:
    """Returns the parsed Telegram user dict if initData is valid, else raises ValueError."""
    if not init_data:
        raise ValueError("missing init data")
    if not BOT_TOKEN:
        raise ValueError("server misconfigured: BOT_TOKEN not set")

    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("missing hash")

    auth_date = int(pairs.get("auth_date", "0"))
    if auth_date and (time.time() - auth_date) > INIT_DATA_MAX_AGE:
        raise ValueError("init data expired")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("invalid hash")

    user_raw = pairs.get("user")
    if not user_raw:
        raise ValueError("missing user")
    return json.loads(user_raw)


def get_authed_user_id(request: web.Request) -> int:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    # Dev fallback: allow ?debug_user_id=123 ONLY when DEBUG_NO_AUTH=1 is set,
    # so you can test the mini app in a normal browser during development.
    if os.environ.get("DEBUG_NO_AUTH") == "1" and request.query.get("debug_user_id"):
        return int(request.query["debug_user_id"])
    user = verify_init_data(init_data)
    return int(user["id"])


def json_response(payload, status=200):
    return web.json_response(payload, status=status, dumps=lambda o: json.dumps(o, default=str))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@gym_routes.get("/api/gym/dashboard")
async def dashboard(request: web.Request):
    try:
        user_id = get_authed_user_id(request)
    except ValueError as e:
        return json_response({"error": str(e)}, status=401)

    summary = await db.get_dashboard_summary(user_id)
    return json_response(summary)


@gym_routes.post("/api/gym/profile")
async def save_profile(request: web.Request):
    try:
        user_id = get_authed_user_id(request)
    except ValueError as e:
        return json_response({"error": str(e)}, status=401)

    body = await request.json()
    profile = await db.save_gym_profile(
        user_id,
        height_cm=body.get("height_cm"),
        weight_kg=body.get("weight_kg"),
        age=body.get("age"),
        gender=body.get("gender"),
        activity_level=body.get("activity_level"),
    )
    return json_response({"ok": True, "profile": profile})


@gym_routes.get("/api/gym/weight-history")
async def weight_history(request: web.Request):
    try:
        user_id = get_authed_user_id(request)
    except ValueError as e:
        return json_response({"error": str(e)}, status=401)

    history = await db.get_weight_history(user_id)
    return json_response(history)


@gym_routes.post("/api/gym/workouts")
async def log_workout(request: web.Request):
    try:
        user_id = get_authed_user_id(request)
    except ValueError as e:
        return json_response({"error": str(e)}, status=401)

    body = await request.json()
    exercise = body.get("exercise")
    muscle = body.get("muscle")
    sets = body.get("sets") or []

    if not exercise or not muscle or not sets:
        return json_response({"error": "exercise, muscle and at least one set are required"}, status=400)

    result = await db.log_workout(user_id, exercise, muscle, sets, notes=body.get("notes"))
    return json_response(result)


@gym_routes.get("/api/gym/workouts")
async def workout_history(request: web.Request):
    try:
        user_id = get_authed_user_id(request)
    except ValueError as e:
        return json_response({"error": str(e)}, status=401)

    muscle = request.query.get("muscle")
    exercise = request.query.get("exercise")
    limit = int(request.query.get("limit", 50))
    history = await db.get_workout_history(user_id, limit=limit, muscle=muscle, exercise=exercise)
    return json_response(history)


@gym_routes.delete("/api/gym/workouts/{workout_id}")
async def remove_workout(request: web.Request):
    try:
        user_id = get_authed_user_id(request)
    except ValueError as e:
        return json_response({"error": str(e)}, status=401)

    await db.delete_workout(user_id, request.match_info["workout_id"])
    return json_response({"ok": True})


@gym_routes.get("/api/gym/prs")
async def prs(request: web.Request):
    try:
        user_id = get_authed_user_id(request)
    except ValueError as e:
        return json_response({"error": str(e)}, status=401)

    return json_response(await db.get_prs(user_id))


# ---------------------------------------------------------------------------
# Static file serving for the mini app itself (index.html / app.js / exercises.js)
# NOT NEEDED if you're hosting the mini app on Vercel (or any other static
# host) — Vercel already serves those three files directly, so this block is
# dead code in that setup. Safe to leave in or delete; just don't register
# gym_static if you're not using it, to avoid a duplicate route.
# ---------------------------------------------------------------------------

@gym_static.get("/gym-app/{filename}")
async def serve_webapp_file(request: web.Request):
    filename = request.match_info["filename"]
    safe_names = {"index.html", "app.js", "exercises.js"}
    if filename not in safe_names:
        raise web.HTTPNotFound()
    path = os.path.join(WEBAPP_DIR, filename)
    if not os.path.isfile(path):
        raise web.HTTPNotFound()
    content_type = "text/html" if filename.endswith(".html") else "application/javascript"
    with open(path, "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type=content_type)


@gym_static.get("/gym-app")
async def serve_webapp_root(request: web.Request):
    raise web.HTTPFound("/gym-app/index.html")
