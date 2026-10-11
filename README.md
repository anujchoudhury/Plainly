# Plainly

**Snap a text, letter or bill. Plainly tells you if it's real, what it says in plain English, and exactly what to do next, with a message ready to send.**

Scam texts and confusing bills hit everyone, and they hit our parents hardest. Plainly answers the three questions people actually have when something scary shows up on their phone or in the mail:

1. **Is it real?** A scam / careful / looks real / not sure verdict, stamped onto your photo, with the red flags circled and numbered right on the image.
2. **What does it say?** A plain-English explanation, plus the amount, the deadline (one tap to add it to Calendar) and who it's really from.
3. **What do I do?** Concrete steps, your rights with sources, and a ready-to-send reply: a dispute letter for a bad bill, or a fraud report for a scam.

On the result screen you can also have the answer **read aloud**, get a **phone script** with your account details filled in, and **send your family** a picture card of the check.

A live **"This week in New York"** panel shows which scams are hitting the city, built from every check (anonymously).

**See how it works:** open `/about` on the running app, or the [explainer page](https://anujchoudhury.github.io/Plainly/) (published from `docs/` with GitHub Pages).

## Run it (2 minutes)

**Windows:** clone or unzip, then double-click **`run.bat`**. It finds Python, creates a `.venv`, installs everything, creates `.env`, starts the server and opens http://localhost:8000 in your browser. Needs Python 3.9+ from python.org (tick "Add python.exe to PATH" when installing). If Windows Firewall asks, click Allow.

**macOS / Linux:** `./run.sh`

With no keys it runs in **demo mode**: the three sample buttons replay saved results, so the demo works with no wifi. To go live, open `.env` (Windows: `notepad .env` in the folder), paste your keys, save, and start it again.

| Key | Where | What happens without it |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com/apikey | Demo mode only |
| `NIMBLE_API_KEY` | online.nimbleway.com → API keys | Falls back to Gemini + Google Search grounding |
| `DATABASE_URL` | Tiger Data console → service → connection string | Trends kept in memory |
| `SENTRY_DSN` | sentry.io → new FastAPI project | No tracing |

**On your iPhone**

`localhost` only works on the laptop itself, and venue Wi-Fi usually blocks phones from reaching laptops directly, so use a tunnel:

- Windows: keep `run.bat` open and double-click **`phone.bat`**. It uses cloudflared if you have it (forced over HTTP/2, which gets through Wi-Fi that blocks UDP), otherwise Pinggy over the `ssh` built into Windows on port 443, with no install. If ssh asks for a password, press Enter.
- No-install one-liner (Windows PowerShell or macOS Terminal): `ssh -p 443 -R0:127.0.0.1:8000 free.pinggy.io` (use `127.0.0.1`, not `localhost`: on Windows `localhost` resolves to IPv6 and the tunnel connects but the page never loads)
- macOS with cloudflared: `cloudflared tunnel --protocol http2 --url http://127.0.0.1:8000`
- Type the `https://` link into Safari, then Share → Add to Home Screen. It opens full-screen like an app, and "Take a photo" opens the camera.

## How it works

```
photo / PDF / pasted text
  │  (resized on the phone to ≤1800px JPEG)
  ▼
1. READ    Gemini (multimodal, JSON mode) → sender, amounts, dates, links,
           boxed regions [ymin,xmin,ymax,xmax] for flags & facts, 3 search queries
2. VERIFY  Nimble Search API, in parallel → official site, scam reports, the rule that applies
           (streamed to the phone as each source lands)
3. DECIDE  Gemini weighs document + sources → verdict, confidence, steps, rights,
           ready-to-send message. URLs it cites are filtered to the sources actually fetched.
4. LOG     anonymous (category, verdict, scam domain) row → Tiger Data hypertable
           → real-time continuous aggregate → weekly trends panel
Sentry: one gen_ai transaction per check, spans per stage, Gemini auto-instrumented.
```

Everything streams to the phone as server-sent events, so you watch it read, search and decide.

**Tiger Data specifics:** `checks` is a hypertable (1-day chunks), `checks_daily` is a continuous aggregate with `materialized_only = false` (real-time: new checks show up immediately), a 5-minute refresh policy, and a compression policy segmented by category after 7 days.

**Privacy:** photos are sent to Gemini for analysis and never stored. Only category, verdict, document type and (for scams only) the scam link's domain are kept.

## Files

- `run.bat` / `phone.bat`: Windows launcher and iPhone link; `run.sh` for macOS/Linux
- `main.py`: FastAPI app, the pipeline, Tiger/in-memory trend stores, Sentry, `.ics` export
- `static/index.html`: the whole iPhone web app (no build step)
- `static/about.html`: the explainer page, served at `/about` (copied to `docs/index.html` for GitHub Pages)
- `examples/README.md`: real scam texts and real confusing documents from the web, to try in a demo
- `demo_data.py` + `demo_boxes.json`: saved results for the three samples
- `make_samples.py`: regenerates the sample images and icons

## 60-second demo script

1. Phone on the projector (or desktop browser). "Everyone's gotten this text." Tap **A toll text**.
2. Watch it read → search the web → the **SCAM** stamp lands. Tap red flag 1: the fake link pulses on the image.
3. Scroll: plain English, steps, and the **fraud report already written**. Tap Copy.
4. Back. Tap **A hospital bill**: it's *real*, but $2,847.50 is an out-of-network ER charge the No Surprises Act protects you from. The dispute letter is written; the deadline goes to Calendar in one tap.
5. Back to home: the New York trends panel just ticked up. "Every check makes the map of scams better."
6. Live finale: upload one of the [real-world examples](examples/README.md), like the fake E-ZPass text that hit NYC drivers, or photograph someone's real spam text from the audience.

## Submission blurb

> **Plainly**: snap a text, letter or bill and get three answers in seconds. Is it real? What does it say? What do I do? Gemini reads the photo and circles the red flags right on it, Nimble checks the live web for the official site, scam reports and the consumer-protection rule that applies, and Gemini writes a verdict, plain-English summary, next steps and a ready-to-send reply (a dispute letter or a fraud report). Every check anonymously feeds a Tiger Data hypertable + continuous aggregate that powers a live "scams hitting New York this week" panel, and Sentry traces every stage of the agent. It's an installable iPhone web app, built for the people who get these messages most: everyone's parents.

Built with Gemini API, Nimble, Tiger Data and Sentry at AI Engineer NYC 2026.

_Plainly isn't legal or financial advice._
