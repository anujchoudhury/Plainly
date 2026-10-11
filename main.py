"""Plainly — snap a letter, bill or text: is it real, what does it say, what do I do.

Pipeline (streamed to the phone as server-sent events):
  1. read    Gemini reads the image/PDF/text -> facts + boxed regions + search queries
  2. verify  Nimble searches the live web (official site, scam reports, the rule that applies)
  3. decide  Gemini weighs document + sources -> verdict, plan, ready-to-send message
  4. log     anonymous (category, verdict) row -> Tiger Data hypertable -> weekly trends
Sentry traces every stage. Missing keys degrade gracefully; no keys = demo mode.
"""
import asyncio
import json
import mimetypes
import os
import random
import re
import socket
import sys
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from demo_data import DEMO

ROOT = Path(__file__).parent
# Windows: keep console output from crashing on non-ASCII, and accept .env files saved with a BOM
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass
load_dotenv(ROOT / ".env", encoding="utf-8-sig")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
NIMBLE_API_KEY = os.getenv("NIMBLE_API_KEY", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
FORCE_DEMO = os.getenv("FORCE_DEMO", "0") == "1"
SEED_DEMO = os.getenv("SEED_DEMO", "1") == "1"
CITY = os.getenv("PLAINLY_CITY", "New York")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
MODELS = [m for m in [os.getenv("GEMINI_MODEL", "").strip(), "gemini-3.8-flash", "gemini-3.7-flash",
                      "gemini-3.6-flash", "gemini-2.5-flash"] if m]
LIVE = bool(GEMINI_API_KEY) and not FORCE_DEMO

CATEGORIES = ["toll", "package_delivery", "bank_or_card", "government_or_tax", "medical_bill", "insurance",
              "housing", "utility", "job_offer", "debt_collection", "prize_or_giveaway", "tech_support", "other"]
VERDICTS = ["scam", "suspicious", "legit", "unclear"]

# ------------------------------------------------------------------ Sentry
if SENTRY_DSN:
    import sentry_sdk
    _integrations = []
    try:
        from sentry_sdk.integrations.google_genai import GoogleGenAIIntegration
        _integrations.append(GoogleGenAIIntegration(include_prompts=False))
    except Exception:
        pass
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0, send_default_pii=False,
                    integrations=_integrations, environment=os.getenv("SENTRY_ENV", "hackathon"))


@contextmanager
def span(op, name, **data):
    if not SENTRY_DSN:
        yield None
        return
    with sentry_sdk.start_span(op=op, name=name) as s:
        for k, v in data.items():
            s.set_data(k, v)
        yield s


def capture(e):
    if SENTRY_DSN:
        sentry_sdk.capture_exception(e)
    print("error:", repr(e)[:300])


# ------------------------------------------------------------------ Gemini
_client = None
_model = None
GEMINI_OK = None      # None = not checked yet, True/False after the startup check
GEMINI_DETAIL = ""
CANDIDATES = []       # models this key can use, best first (filled by the startup check)
BUSY = ("503", "500", "429", "unavailable", "overloaded", "high demand", "resource_exhausted", "deadline", "internal")


BACKEND_ENV = ("GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_ENTERPRISE", "GOOGLE_CLOUD_PROJECT", "GOOGLE_API_KEY")


def make_client():
    # vertexai=False pins the Gemini Developer API even if GOOGLE_GENAI_USE_VERTEXAI etc. are set on this PC
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY, vertexai=False)


def _version_key(name):
    m = re.match(r"gemini-(\d+(?:\.\d+)?)-flash$", name)
    return float(m.group(1)) if m else -1.0


async def available_models(client):
    names = []
    pager = await client.aio.models.list(config={"page_size": 200})
    async for m in pager:
        acts = getattr(m, "supported_actions", None) or []
        if not acts or "generateContent" in acts:
            names.append((m.name or "").split("/")[-1])
    return [n for n in names if n]


def choose_models(names):
    """Order to try: pinned model, our preferred list, then the newest plain 'gemini-X-flash' this key can see."""
    have = set(names)
    out = [m for m in MODELS if m in have]
    flashes = sorted((n for n in names if _version_key(n) > 0), key=_version_key, reverse=True)
    out += [n for n in flashes if n not in out]
    out += [n for n in names if "flash" in n and not any(x in n for x in ("lite", "image", "tts", "live", "audio", "embed"))
            and n not in out]
    return out or MODELS


async def check_gemini():
    """Tiny real call at startup so a bad key shows up in the console, not in front of the judges."""
    global _client, _model, GEMINI_OK, GEMINI_DETAIL
    from google.genai import types
    for k in BACKEND_ENV:
        if os.environ.get(k):
            print(f"  note: {k} is set on this computer; Plainly ignores it and uses GEMINI_API_KEY from .env")
    client = make_client()
    try:
        names = await asyncio.wait_for(available_models(client), timeout=20)
        print(f"  this key can use {len(names)} models")
    except Exception as e:  # listing failing = the key itself is the problem; this is the real error
        GEMINI_OK, GEMINI_DETAIL = False, friendly(e) + f"  [{type(e).__name__}: {str(e)[:400]}]"
        return
    global CANDIDATES
    CANDIDATES = choose_models(names)[:6]
    last = None
    for model in CANDIDATES:
        try:
            await asyncio.wait_for(client.aio.models.generate_content(
                model=model, contents="Reply with the single word: ok",
                config=types.GenerateContentConfig(max_output_tokens=32)), timeout=25)
            _client, _model = client, model
            GEMINI_OK, GEMINI_DETAIL = True, f"works ({model})"
            return
        except Exception as e:
            last = e
            m = str(e).lower()
            if "404" in m or "not found" in m or "not_found" in m or any(b in m for b in BUSY):
                continue  # model missing or overloaded: try the next one this key listed
            break
    GEMINI_OK = False
    GEMINI_DETAIL = friendly(last) + (f"  [{type(last).__name__}: {str(last)[:400]}]" if last else "")


def gclient():
    global _client
    if _client is None:
        _client = make_client()
    return _client


def parse_json(text):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        a, b = t.find("{"), t.rfind("}")
        if a >= 0 and b > a:
            return json.loads(t[a:b + 1])
        raise ValueError("Gemini didn't return JSON")


async def gemini_json(contents, system, thinking="low"):
    """JSON-mode call that survives a missing model id, an unsupported thinking config, and overloaded models
    (503 / 429): it moves on to the next model this key can use, and makes a second pass after a short pause."""
    from google.genai import types
    global _model
    order = []
    for m in [_model] + CANDIDATES + MODELS:
        if m and m not in order:
            order.append(m)
    last = None
    for attempt in range(2):
        for model in order[:5]:
            for use_thinking in ([True, False] if thinking else [False]):
                cfg = {"system_instruction": system, "response_mime_type": "application/json"}
                if use_thinking:
                    cfg["thinking_config"] = types.ThinkingConfig(thinking_level=thinking)
                try:
                    with span("gen_ai.request", f"gemini {model}", model=model):
                        resp = await gclient().aio.models.generate_content(
                            model=model, contents=contents, config=types.GenerateContentConfig(**cfg))
                    if model != _model:
                        print(f"  using {model}")
                    _model = model
                    return parse_json(resp.text)
                except Exception as e:
                    last = e
                    msg = str(e).lower()
                    if "api key" in msg or "api_key" in msg or "permission" in msg:
                        raise
                    if any(b in msg for b in BUSY):
                        print(f"  {model} is busy, trying another model")
                        break
                    if "not found" in msg or "404" in msg or "is not supported" in msg:
                        break
                    if use_thinking and ("think" in msg or "400" in msg or "invalid" in msg):
                        continue
                    raise
        await asyncio.sleep(1.5)
    raise last


async def gemini_grounded_sources(queries):
    """Fallback when Nimble isn't configured: Gemini + Google Search grounding."""
    from google.genai import types
    q = "; ".join(x["query"] for x in queries)
    resp = await gclient().aio.models.generate_content(
        model=_model or MODELS[0],
        contents=f"Search the web for each of these and summarize what you find in 3 sentences: {q}",
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
    out = []
    gm = resp.candidates[0].grounding_metadata if resp.candidates else None
    for ch in (getattr(gm, "grounding_chunks", None) or [])[:6]:
        web = getattr(ch, "web", None)
        if web and web.uri:
            out.append({"title": web.title or urlparse(web.uri).hostname, "url": web.uri, "snippet": "", "purpose": "official"})
    return out


# ------------------------------------------------------------------ Nimble
async def nimble_search(http, q):
    body = {"query": q["query"], "max_results": 4, "search_depth": "lite", "country": "US", "locale": "en"}
    headers = {"Authorization": f"Bearer {NIMBLE_API_KEY}"}
    with span("http.client", f"nimble search: {q['purpose']}", query=q["query"]):
        for path in ("/v2/search", "/v1/search"):
            r = await http.post("https://sdk.nimbleway.com" + path, json=body, headers=headers, timeout=20)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or (data.get("data") or {}).get("results") or []
            return [{"title": (x.get("title") or "").strip()[:140] or urlparse(x.get("url", "")).hostname,
                     "url": x.get("url", ""),
                     "snippet": re.sub(r"\s+", " ", x.get("description") or x.get("content") or "")[:400],
                     "purpose": q["purpose"]} for x in results if x.get("url")]
    return []


# ------------------------------------------------------------------ prompts
def today():
    return date.today().isoformat()


EXTRACT_SYSTEM = """You are the reading step of Plainly, which helps ordinary people understand confusing or suspicious messages, letters, bills and notices. You get a photo, screenshot, PDF or pasted text. Extract ONLY what is actually there. Never invent amounts, dates, names or links. Today is {today}. The user is in {city}."""

EXTRACT_PROMPT = """Return JSON with exactly these keys:
{
 "doc_type": "text_message" | "email" | "letter" | "bill" | "notice" | "website" | "other",
 "category": one of %s,
 "claimed_sender": "who it says it's from, or empty",
 "sender_details": "the phone number, short code, email address or return address it actually came from, or empty",
 "organization": "the real-world organization it references, or empty",
 "summary": "one neutral sentence describing what this is",
 "asks": "what it asks the reader to do, one sentence",
 "urls": ["every link or web address shown, exactly as written"],
 "phones": ["phone numbers shown"],
 "amounts": [{"label": "...", "value": "$0.00"}],
 "dates": [{"label": "...", "date": "YYYY-MM-DD or empty", "raw": "as written"}],
 "location_hint": "city/state if visible, else empty",
 "regions": [{"id": "r1", "kind": "flag" | "fact", "label": "2-5 words", "text": "exact text in that area", "box_2d": [ymin, xmin, ymax, xmax]}],
 "verify_queries": [{"purpose": "official" | "scam_check" | "rules", "query": "3-8 word web search"}]
}
Regions: up to 6. box_2d is integers normalized 0-1000 relative to the image, tight around the text. kind "flag" = a possible warning sign (link not on the official domain, threats or urgency, odd payment method, odd sender, requests for personal info, a charge that may not be owed). kind "fact" = a key fact (amount due, deadline, reference number). For pasted text with no image use box_2d [0,0,0,0].
Queries: up to 3. "official" finds the organization's real website or official guidance; "scam_check" looks for reports of this exact scheme, link domain or phone number; "rules" finds the consumer-protection rule that applies (e.g. No Surprises Act, NYC security deposit law, FDCPA), with the location if known.""" % json.dumps(CATEGORIES)

DECIDE_SYSTEM = """You are the decision step of Plainly. You help everyday people — often not experts, sometimes elderly — decide whether a message, letter or bill is real, understand it, and know exactly what to do next. Be calm, direct and specific, at an 8th-grade reading level. Base the verdict on the document and the web sources provided. Only cite URLs from the provided sources. You are not a lawyer; don't claim certainty you don't have. Today is {today}. The user is in {city}."""

DECIDE_PROMPT = """What the document contains:
{extraction}

Web sources checked just now:
{sources}

Return JSON with exactly these keys:
{{
 "verdict": "scam" | "suspicious" | "legit" | "unclear",
 "confidence": 0-100,
 "headline": "max 9 words, e.g. 'This toll text is a scam.' or 'Real bill, but you may not owe all of it.'",
 "plain_english": "2-4 short sentences: what this is and what's really going on",
 "what_they_want": "one sentence",
 "amount_due": "e.g. $2,847.50, or empty",
 "deadline": "YYYY-MM-DD that actually matters to the reader, or empty",
 "deadline_label": "e.g. 'Payment due', 'Appeal deadline', or empty",
 "red_flags": [{{"region_id": "id from regions or empty", "title": "short", "why": "one sentence"}}],
 "good_signs": [{{"title": "short", "why": "one sentence"}}],
 "steps": [3-5 {{"title": "short imperative", "detail": "1-2 concrete sentences: who to contact, which official site to type in yourself, what to say"}}],
 "rights": [0-3 {{"title": "short", "detail": "one sentence", "source_url": "one of the source URLs, or empty"}}],
 "message": {{"kind": "reply" | "report" | "none", "to": "recipient (name, email, site or number)", "subject": "...", "body": "complete, polite, ready-to-send, first person; use [Your name] style placeholders"}},
 "sources_used": ["source URLs that support the verdict"],
 "calendar_title": "short reminder title if there's a deadline, else empty",
 "call_script": {{"who": "who to call, e.g. 'Riverside Mercy billing office'", "number": "phone number to call, ONLY if printed on a real document or found in an official source above, else empty", "when": "e.g. 'Mon-Fri, 8am-6pm' if known, else empty", "have_ready": ["account number, dates, amounts to have in hand"], "lines": [3-6 short first-person sentences to say on the call, in order, with the real names, numbers and amounts filled in], "if_they_say_no": "one sentence on how to push back or escalate"}}
}}
For scams: the message is a report (ReportFraud.ftc.gov, or forward texts to 7726), and the steps say not to tap links, reply or call numbers in the message, and to go to the official site by typing it in. For real documents: say whether the amount looks right, what the reader is entitled to, and draft the reply they'd actually send (dispute, itemized bill request, appeal, payment plan...). Use "suspicious" for warning signs without proof and "unclear" when you can't tell.
Phone script: for real documents where a call would help (disputing a charge, asking for an itemized bill, setting up a payment plan, appealing), write the call script. For scams, the script is for calling the REAL organization or your bank using a number you look up yourself (never one from the message): leave "number" empty and say where to find the real one in "who". If no call is useful, return empty "lines"."""


# ------------------------------------------------------------------ normalization
def _s(v, n=600):
    return v.strip()[:n] if isinstance(v, str) else ""


def _l(v):
    return v if isinstance(v, list) else []


def _box(b):
    try:
        b = [max(0, min(1000, int(round(float(x))))) for x in b][:4]
        if len(b) == 4 and b[2] > b[0] and b[3] > b[1]:
            return b
    except Exception:
        pass
    return None


def normalize_extraction(x, has_image):
    x = x if isinstance(x, dict) else {}
    regions = []
    for i, r in enumerate(_l(x.get("regions"))[:6]):
        if not isinstance(r, dict):
            continue
        regions.append({"id": _s(r.get("id"), 10) or f"r{i + 1}", "kind": "flag" if r.get("kind") == "flag" else "fact",
                        "label": _s(r.get("label"), 60), "text": _s(r.get("text"), 300),
                        "box_2d": _box(r.get("box_2d") or []) if has_image else None})
    qs = [{"purpose": q.get("purpose") if q.get("purpose") in ("official", "scam_check", "rules") else "official",
           "query": _s(q.get("query"), 120)} for q in _l(x.get("verify_queries")) if isinstance(q, dict) and _s(q.get("query"))][:3]
    org = _s(x.get("organization"), 80) or _s(x.get("claimed_sender"), 80)
    if not qs and org:
        qs = [{"purpose": "official", "query": f"{org} official website"}, {"purpose": "scam_check", "query": f"{org} scam text"}]
    return {
        "doc_type": _s(x.get("doc_type"), 20) or "other",
        "category": x.get("category") if x.get("category") in CATEGORIES else "other",
        "claimed_sender": _s(x.get("claimed_sender"), 120), "sender_details": _s(x.get("sender_details"), 160),
        "organization": org, "summary": _s(x.get("summary")), "asks": _s(x.get("asks")),
        "urls": [_s(u, 300) for u in _l(x.get("urls")) if _s(u)][:6],
        "phones": [_s(u, 40) for u in _l(x.get("phones")) if _s(u)][:4],
        "amounts": [{"label": _s(a.get("label"), 60), "value": _s(a.get("value"), 30)} for a in _l(x.get("amounts")) if isinstance(a, dict)][:5],
        "dates": [{"label": _s(a.get("label"), 60), "date": _s(a.get("date"), 10), "raw": _s(a.get("raw"), 40)} for a in _l(x.get("dates")) if isinstance(a, dict)][:5],
        "location_hint": _s(x.get("location_hint"), 80), "regions": regions, "verify_queries": qs,
    }


def norm_call(c):
    c = c if isinstance(c, dict) else {}
    lines = [_s(x, 300) for x in _l(c.get("lines")) if _s(x)][:6]
    if not lines:
        return None
    number = _s(c.get("number"), 40)
    if number and not re.search(r"\d{3}.*\d{4}", number):
        number = ""
    return {"who": _s(c.get("who"), 120), "number": number, "when": _s(c.get("when"), 80),
            "have_ready": [_s(x, 120) for x in _l(c.get("have_ready")) if _s(x)][:5], "lines": lines,
            "if_they_say_no": _s(c.get("if_they_say_no"), 300)}


def normalize_result(r, sources):
    r = r if isinstance(r, dict) else {}
    ok = {s["url"] for s in sources}
    verdict = (r.get("verdict") or "").lower()
    msg = r.get("message") if isinstance(r.get("message"), dict) else {}
    try:
        conf = max(0, min(100, int(r.get("confidence", 50))))
    except Exception:
        conf = 50
    deadline = _s(r.get("deadline"), 10)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
        deadline = ""
    item = lambda a, keys: {k: _s(a.get(k), 400) for k in keys}  # noqa: E731
    return {
        "verdict": verdict if verdict in VERDICTS else "unclear", "confidence": conf,
        "headline": _s(r.get("headline"), 90) or "Here's what this is.",
        "plain_english": _s(r.get("plain_english"), 900), "what_they_want": _s(r.get("what_they_want"), 300),
        "amount_due": _s(r.get("amount_due"), 30), "deadline": deadline, "deadline_label": _s(r.get("deadline_label"), 40),
        "red_flags": [item(a, ["region_id", "title", "why"]) for a in _l(r.get("red_flags")) if isinstance(a, dict)][:6],
        "good_signs": [item(a, ["title", "why"]) for a in _l(r.get("good_signs")) if isinstance(a, dict)][:4],
        "steps": [item(a, ["title", "detail"]) for a in _l(r.get("steps")) if isinstance(a, dict)][:5],
        "rights": [{**item(a, ["title", "detail"]), "source_url": a.get("source_url") if a.get("source_url") in ok else ""}
                   for a in _l(r.get("rights")) if isinstance(a, dict)][:3],
        "message": {"kind": msg.get("kind") if msg.get("kind") in ("reply", "report") else "none",
                    "to": _s(msg.get("to"), 160), "subject": _s(msg.get("subject"), 160), "body": _s(msg.get("body"), 4000)},
        "sources_used": [u for u in _l(r.get("sources_used")) if u in ok],
        "calendar_title": _s(r.get("calendar_title"), 80),
        "call_script": norm_call(r.get("call_script")),
    }


def domain_of(urls):
    for u in urls:
        u = u if "://" in u else "https://" + u
        host = urlparse(u).hostname
        if host:
            return host.removeprefix("www.")
    return None


# ------------------------------------------------------------------ trends store
def seed_rows(n_days=7):
    rng = random.Random(42)
    mix = [("toll", 26, 0.9), ("package_delivery", 22, 0.85), ("bank_or_card", 14, 0.7), ("job_offer", 8, 0.8),
           ("medical_bill", 10, 0.05), ("housing", 6, 0.15), ("government_or_tax", 6, 0.6), ("utility", 5, 0.3),
           ("prize_or_giveaway", 3, 0.95)]
    cats, weights = [m[0] for m in mix], [m[1] for m in mix]
    p = {m[0]: m[2] for m in mix}
    now, rows = datetime.now(timezone.utc), []
    for d in range(n_days):
        for _ in range(rng.randint(14, 26)):
            c = rng.choices(cats, weights)[0]
            u = rng.random()
            v = "scam" if u < p[c] else ("suspicious" if u < p[c] + 0.08 else "legit")
            rows.append({"time": now - timedelta(days=d, minutes=rng.randint(0, 1439)), "category": c, "verdict": v,
                         "doc_type": "text_message", "domain": None, "is_seed": True})
    return rows


def aggregate(rows, days, domains, source):
    start = date.today() - timedelta(days=days - 1)
    daily = {(start + timedelta(days=i)).isoformat(): {"total": 0, "flagged": 0} for i in range(days)}
    cats, tot, seed = {}, {"total": 0, "scam": 0, "suspicious": 0, "legit": 0, "unclear": 0}, 0
    for r in rows:
        n, v = int(r.get("n", 1)), r["verdict"] if r["verdict"] in VERDICTS else "unclear"
        c = cats.setdefault(r["category"], {"category": r["category"], "total": 0, "scam": 0, "suspicious": 0, "legit": 0, "unclear": 0})
        c["total"] += n
        c[v] += n
        tot["total"] += n
        tot[v] += n
        seed += n if r.get("is_seed") else 0
        day = r["day"] if "day" in r else r["time"].date()
        key = day.isoformat() if hasattr(day, "isoformat") else str(day)[:10]
        if key in daily:
            daily[key]["total"] += n
            daily[key]["flagged"] += n if v in ("scam", "suspicious") else 0
    by_cat = sorted(cats.values(), key=lambda c: (c["scam"] + c["suspicious"], c["total"]), reverse=True)
    return {"source": source, "city": CITY, "days": days, **tot, "seed_count": seed,
            "by_category": by_cat, "daily": [{"day": k, **v} for k, v in daily.items()], "top_domains": domains}


class MemoryStore:
    name = "memory"

    def __init__(self):
        self.rows = []

    async def init(self):
        if SEED_DEMO:
            self.rows += seed_rows()

    async def record(self, row):
        self.rows.append(row)

    async def trends(self, days=7):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = [r for r in self.rows if r["time"] >= since]
        dom = {}
        for r in rows:
            if r.get("domain") and r["verdict"] in ("scam", "suspicious"):
                dom[r["domain"]] = dom.get(r["domain"], 0) + 1
        top = [{"domain": k, "count": v} for k, v in sorted(dom.items(), key=lambda kv: -kv[1])[:5]]
        return aggregate(rows, days, top, self.name)


class TigerStore:
    """Tiger Data (TimescaleDB): hypertable + real-time continuous aggregate + compression policy."""
    name = "tiger"

    async def init(self):
        import asyncpg
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=4, command_timeout=15)
        self.cagg = False
        async with self.pool.acquire() as c:
            await c.execute("""CREATE TABLE IF NOT EXISTS checks (
                time TIMESTAMPTZ NOT NULL DEFAULT now(), category TEXT NOT NULL, verdict TEXT NOT NULL,
                doc_type TEXT, domain TEXT, city TEXT, is_seed BOOLEAN NOT NULL DEFAULT false)""")
            for sql in ("SELECT create_hypertable('checks', by_range('time', INTERVAL '1 day'), if_not_exists => TRUE)",
                        "SELECT create_hypertable('checks', 'time', if_not_exists => TRUE, migrate_data => TRUE)"):
                try:
                    await c.execute(sql)
                    break
                except Exception as e:
                    print("hypertable:", str(e)[:120])
            try:
                await c.execute("""CREATE MATERIALIZED VIEW IF NOT EXISTS checks_daily
                    WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
                    SELECT time_bucket(INTERVAL '1 day', time) AS day, category, verdict, is_seed, count(*) AS n
                    FROM checks GROUP BY day, category, verdict, is_seed WITH NO DATA""")
                self.cagg = True
                await c.execute("""SELECT add_continuous_aggregate_policy('checks_daily', start_offset => INTERVAL '30 days',
                    end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '5 minutes', if_not_exists => TRUE)""")
            except Exception as e:
                print("continuous aggregate:", str(e)[:160])
            try:
                await c.execute("ALTER TABLE checks SET (timescaledb.compress, timescaledb.compress_segmentby = 'category')")
                await c.execute("SELECT add_compression_policy('checks', INTERVAL '7 days', if_not_exists => TRUE)")
            except Exception as e:
                print("compression:", str(e)[:120])
            if SEED_DEMO and not await c.fetchval("SELECT count(*) FROM checks WHERE is_seed"):
                await c.executemany("INSERT INTO checks (time, category, verdict, doc_type, domain, city, is_seed) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                                    [(r["time"], r["category"], r["verdict"], r["doc_type"], None, CITY, True) for r in seed_rows()])

    async def record(self, row):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO checks (time, category, verdict, doc_type, domain, city, is_seed) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                            row["time"], row["category"], row["verdict"], row["doc_type"], row["domain"], CITY, row["is_seed"])

    async def trends(self, days=7):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        async with self.pool.acquire() as c:
            if self.cagg:
                try:
                    rows = await c.fetch("SELECT day, category, verdict, is_seed, n FROM checks_daily WHERE day >= $1", since)
                except Exception:
                    self.cagg = False
            if not self.cagg:
                rows = await c.fetch("""SELECT date_trunc('day', time) AS day, category, verdict, is_seed, count(*) AS n
                                        FROM checks WHERE time >= $1 GROUP BY 1,2,3,4""", since)
            dom = await c.fetch("""SELECT domain, count(*) AS n FROM checks WHERE time >= $1 AND domain IS NOT NULL
                                   AND verdict IN ('scam','suspicious') GROUP BY domain ORDER BY n DESC LIMIT 5""", since)
        rows = [{"day": r["day"].date() if hasattr(r["day"], "date") else r["day"], "category": r["category"],
                 "verdict": r["verdict"], "is_seed": r["is_seed"], "n": r["n"]} for r in rows]
        return aggregate(rows, days, [{"domain": d["domain"], "count": d["n"]} for d in dom], self.name)


store = MemoryStore()

# ------------------------------------------------------------------ app
@asynccontextmanager
async def lifespan(_app):
    await startup()
    yield


app = FastAPI(title="Plainly", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


async def startup():
    global store
    if DATABASE_URL:
        try:
            t = TigerStore()
            await t.init()
            store = t
            print("Trends: Tiger Data connected" + (" (hypertable + real-time continuous aggregate)" if t.cagg else ""))
        except Exception as e:
            capture(e)
            print(f"Trends: Tiger Data unavailable ({type(e).__name__}: {str(e)[:160]}), using in-memory store")
    if store.name == "memory":
        await store.init()
    if LIVE:
        print("Testing the Gemini key...")
        await check_gemini()
        if GEMINI_OK:
            print(f"  Gemini key: {GEMINI_DETAIL}")
        else:
            print("  " + "!" * 60)
            print(f"  Gemini key FAILED: {GEMINI_DETAIL}")
            print("  The sample buttons will replay saved demo results until this is fixed.")
            print("  " + "!" * 60)
    if SENTRY_DSN:
        print("Sentry: tracing on (each check shows up under Performance / Traces as plainly.analyze)")
    print(f"Plainly ready - mode={'live' if live_now() else 'demo'} gemini={bool(GEMINI_API_KEY)} nimble={bool(NIMBLE_API_KEY)} "
          f"tiger={store.name == 'tiger'} sentry={bool(SENTRY_DSN)}")
    print(f"  On this computer:          http://localhost:{PORT}")
    ip = lan_ip()
    if ip and HOST == "0.0.0.0":
        print(f"  Phone on the same Wi-Fi:   http://{ip}:{PORT}  (if it doesn't load, use the cloudflared link)")
    if os.getenv("OPEN_BROWSER") == "1":
        import webbrowser
        asyncio.get_running_loop().call_later(1.0, webbrowser.open, f"http://localhost:{PORT}")


def live_now():
    return LIVE and GEMINI_OK is not False


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # no packet is sent; this just picks the outbound interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/about")
def about():
    return FileResponse(ROOT / "static" / "about.html", headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(ROOT / "static" / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/api/config")
def config():
    return {"live": live_now(), "gemini": bool(GEMINI_API_KEY), "gemini_ok": GEMINI_OK, "gemini_detail": GEMINI_DETAIL,
            "nimble": bool(NIMBLE_API_KEY),
            "tiger": store.name == "tiger", "sentry": bool(SENTRY_DSN), "city": CITY, "model": _model or MODELS[0]}


@app.get("/api/trends")
async def trends(days: int = 7):
    try:
        return await store.trends(max(1, min(days, 30)))
    except Exception as e:
        capture(e)
        return JSONResponse({"error": "Trends are unavailable right now."}, status_code=503)


def _ics_escape(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@app.get("/api/ics")
def ics(title: str, day: str, notes: str = ""):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return JSONResponse({"error": "day must be YYYY-MM-DD"}, status_code=400)
    d0 = date.fromisoformat(day)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    body = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Plainly//EN", "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@plainly", f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{d0:%Y%m%d}", f"DTEND;VALUE=DATE:{d0 + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_ics_escape(title[:120])}", f"DESCRIPTION:{_ics_escape(notes[:1000])}",
        "BEGIN:VALARM", "TRIGGER:-PT39H", "ACTION:DISPLAY", f"DESCRIPTION:{_ics_escape(title[:120])}", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR", ""])
    return Response(body, media_type="text/calendar",
                    headers={"Content-Disposition": 'inline; filename="plainly-deadline.ics"'})


def sse(obj):
    return f"data: {json.dumps(obj)}\n\n"


async def demo_events(sample):
    d = DEMO[sample]
    yield {"type": "stage", "stage": "read", "status": "start"}
    await asyncio.sleep(1.4)
    yield {"type": "extract", "data": d["extract"]}
    yield {"type": "stage", "stage": "read", "status": "done"}
    yield {"type": "stage", "stage": "verify", "status": "start", "queries": d["extract"]["verify_queries"]}
    for s in d["sources"]:
        await asyncio.sleep(0.6)
        yield {"type": "source", "data": s}
    yield {"type": "stage", "stage": "verify", "status": "done", "count": len(d["sources"])}
    yield {"type": "stage", "stage": "decide", "status": "start"}
    await asyncio.sleep(1.6)
    yield {"type": "result", "data": d["result"]}
    await store.record({"time": datetime.now(timezone.utc), "category": d["extract"]["category"], "verdict": d["result"]["verdict"],
                        "doc_type": d["extract"]["doc_type"], "domain": None, "is_seed": True})


async def live_events(data, mime, text):
    from google.genai import types
    has_image = bool(data) and mime.startswith("image/")
    contents = []
    if data:
        contents.append(types.Part.from_bytes(data=data, mime_type=mime))
    if text:
        contents.append(f'Pasted by the user:\n"""\n{text[:8000]}\n"""')
    contents.append(EXTRACT_PROMPT)

    yield {"type": "stage", "stage": "read", "status": "start"}
    with span("gen_ai.invoke_agent", "read document"):
        ex = normalize_extraction(await gemini_json(contents, EXTRACT_SYSTEM.format(today=today(), city=CITY), thinking="low"), has_image)
    yield {"type": "extract", "data": ex}
    yield {"type": "stage", "stage": "read", "status": "done"}

    yield {"type": "stage", "stage": "verify", "status": "start", "queries": ex["verify_queries"]}
    sources, seen = [], set()
    with span("gen_ai.execute_tool", "verify on the web", queries=len(ex["verify_queries"])):
        if NIMBLE_API_KEY and ex["verify_queries"]:
            async with httpx.AsyncClient() as http:
                tasks = [asyncio.create_task(nimble_search(http, q)) for q in ex["verify_queries"]]
                for fut in asyncio.as_completed(tasks):
                    try:
                        found = await fut
                    except Exception as e:
                        capture(e)
                        continue
                    for s in found:
                        if s["url"] not in seen and len(sources) < 10:
                            seen.add(s["url"])
                            sources.append(s)
                            yield {"type": "source", "data": s}
        if not sources and ex["verify_queries"]:
            try:
                for s in await gemini_grounded_sources(ex["verify_queries"]):
                    if s["url"] not in seen:
                        seen.add(s["url"])
                        sources.append(s)
                        yield {"type": "source", "data": s}
            except Exception as e:
                capture(e)
    yield {"type": "stage", "stage": "verify", "status": "done", "count": len(sources)}

    yield {"type": "stage", "stage": "decide", "status": "start"}
    src_block = "\n".join(f"[{i + 1}] ({s['purpose']}) {s['title']} — {s['url']}\n    {s['snippet']}" for i, s in enumerate(sources)) \
        or "(No web sources were available. Rely on the document itself and say the web check couldn't run.)"
    prompt = DECIDE_PROMPT.format(extraction=json.dumps(ex, indent=1), sources=src_block)
    with span("gen_ai.invoke_agent", "decide verdict"):
        result = normalize_result(await gemini_json([prompt], DECIDE_SYSTEM.format(today=today(), city=CITY), thinking="low"), sources)
    yield {"type": "result", "data": result}
    try:
        await store.record({"time": datetime.now(timezone.utc), "category": ex["category"], "verdict": result["verdict"],
                            "doc_type": ex["doc_type"],
                            "domain": domain_of(ex["urls"]) if result["verdict"] in ("scam", "suspicious") else None,
                            "is_seed": False})
    except Exception as e:
        capture(e)


def friendly(e):
    m = str(e).lower()
    if isinstance(e, asyncio.TimeoutError) or "timed out" in m or "timeout" in m:
        return "Gemini took too long to answer. Check the internet connection and try again."
    if "proxy" in m or "connect" in m or "getaddrinfo" in m or "name resolution" in m or "network" in m:
        return "Couldn't reach Google from this computer. Check the internet connection (or a VPN/firewall)."
    if "service_disabled" in m or "has not been used in project" in m or "it is disabled" in m:
        return ("The Generative Language API is turned off for this key's Google Cloud project. Turn it on "
                "(the link is in the error below), or make a key at aistudio.google.com/apikey.")
    if "api_key_service_blocked" in m or "are blocked" in m or "unrestricted" in m or "restrict" in m:
        return ("This key isn't allowed to call the Gemini API. In Google Cloud console > APIs & Services > Credentials, "
                "edit the key and restrict it to the Generative Language API, or make a key at aistudio.google.com/apikey.")
    if "api keys are not supported by this api" in m:
        return ("Google sent this key to Vertex AI, which doesn't take API keys. Make sure GEMINI_API_KEY in .env is a key "
                "from aistudio.google.com/apikey.")
    if "api_key_invalid" in m or "api key not valid" in m or "api key expired" in m:
        return "Google says this key isn't valid. Re-copy it, or make a new one at aistudio.google.com/apikey."
    if "billing" in m:
        return "This Gemini key's project needs billing turned on for this model. Try a key from aistudio.google.com/apikey."
    if "api key" in m or "unauthenticated" in m or "access_token_type_unsupported" in m or "api_key" in m or "permission" in m or "401" in m or "403" in m:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in .env and restart."
    if "503" in m or "unavailable" in m or "high demand" in m or "overloaded" in m:
        return "Google's Gemini models are overloaded right now. Wait a few seconds and try again."
    if "quota" in m or "429" in m or "resource_exhausted" in m:
        return "Gemini is rate-limiting this key. Wait a few seconds and try again."
    if "json" in m:
        return "The reading came back garbled. Try again, or try a sharper photo."
    return "Something broke while checking this. Try again in a moment."


async def run(data, mime, text, sample):
    t0 = time.time()
    try:
        if sample and not live_now():
            events = demo_events(sample)
        elif not LIVE:
            yield sse({"type": "error", "message": "Live checks need a GEMINI_API_KEY in .env. Try one of the samples for now."})
            return
        else:
            events = live_events(data, mime, text)
        async for e in events:
            yield sse(e)
        yield sse({"type": "done", "ms": int((time.time() - t0) * 1000), "demo": bool(sample) and not live_now()})
    except Exception as e:
        capture(e)
        yield sse({"type": "error", "message": friendly(e)})


@app.post("/api/analyze")
async def analyze(file: Optional[UploadFile] = File(None), text: str = Form("")):
    data = await file.read() if file else b""
    name = (file.filename or "") if file else ""
    mime = (file.content_type or "") if file else ""
    if data and (not mime or mime == "application/octet-stream"):
        mime = mimetypes.guess_type(name)[0] or "image/jpeg"
    sample = None
    m = re.match(r"sample-(\w+)", name)
    if m and m.group(1) in DEMO:
        sample = m.group(1)

    async def stream():
        if len(data) > 15 * 1024 * 1024:
            yield sse({"type": "error", "message": "That file is over 15 MB. Try a screenshot or a smaller photo."})
            return
        if not data and not text.strip():
            yield sse({"type": "error", "message": "Add a photo, a PDF or some pasted text first."})
            return
        if SENTRY_DSN:
            with sentry_sdk.isolation_scope():
                with sentry_sdk.start_transaction(op="gen_ai.invoke_agent", name="plainly.analyze"):
                    async for chunk in run(data, mime, text.strip(), sample):
                        yield chunk
        else:
            async for chunk in run(data, mime, text.strip(), sample):
                yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    import uvicorn
    _probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _probe.settimeout(0.5)
    try:
        _busy = _probe.connect_ex(("127.0.0.1", PORT)) == 0  # something is already listening there
    finally:
        _probe.close()
    if _busy:
        print(f"Port {PORT} is already in use: Plainly is probably still running in another window.")
        print(f"Use that window (http://localhost:{PORT}), or close it and run this again.")
        print("To use a different port instead, add PORT=8001 to .env.")
        sys.exit(1)
    uvicorn.run(app, host=HOST, port=PORT)
