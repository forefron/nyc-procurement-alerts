#!/usr/bin/env python3
"""
NYC Procurement Opportunity Alert Fetcher
=========================================
Polls NYC's OFFICIAL City Record Online dataset (the same solicitations that
appear in PASSPort) and pushes breaking-news-style alerts to a Telegram
group/channel via the official Bot API (free).

Data source (no scraping, no login, no robots.txt issues):
  https://data.cityofnewyork.us/resource/dg92-zbpx.json   (Socrata API)

Run this on a schedule (e.g. every 30-60 min via cron / GitHub Actions).
State (already-alerted notice IDs) is kept in state.json next to this file.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration - all via environment variables (see config.example.env)
# --------------------------------------------------------------------------
SOCRATA_URL = "https://data.cityofnewyork.us/resource/dg92-zbpx.json"
SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "")  # optional, raises rate limits

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")    # group/channel id (-100...) or @channelname

# How far back to look on the very first run
FIRST_RUN_LOOKBACK_DAYS = int(os.getenv("FIRST_RUN_LOOKBACK_DAYS", "2"))

# Which notice types to alert on. "Solicitation" = open opportunities.
# Add "Intent to Award", "Award" etc. if the group wants those too.
NOTICE_TYPES = [t.strip() for t in os.getenv(
    "NOTICE_TYPES", "Solicitation").split(",") if t.strip()]

STATE_FILE = Path(__file__).parent / "state.json"
FEED_FILE = Path(__file__).parent / "feed.json"   # rolling cache used by bot.py

CATEGORY_EMOJI = {
    "Construction": "🏗️",
    "Construction Related": "🏗️",
    "Construction/Construction Services": "🏗️",
    "Goods": "📦",
    "Goods & Services": "📦",
    "Services": "🛠️",
    "Services (other than human services)": "🛠️",
    "Human Services": "🤝",
    "Human Services/Client Services": "🤝",
    "Professional Services": "💼",
    "Technology": "💻",
    "Information Technology": "💻",
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def http_get_json(url: str) -> list:
    req = urllib.request.Request(url, headers={
        "User-Agent": "nyc-procurement-alerts/1.0",
        **({"X-App-Token": SOCRATA_APP_TOKEN} if SOCRATA_APP_TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_ids": []}


def save_state(state: dict) -> None:
    # keep the seen list bounded
    state["seen_ids"] = state["seen_ids"][-20000:]
    STATE_FILE.write_text(json.dumps(state))


def fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "")).strftime("%b %d, %Y")
    except Exception:
        return iso or "n/a"


def fmt_amount(v: str) -> str:
    try:
        return f"${float(v):,.0f}"
    except Exception:
        return v or ""


# --------------------------------------------------------------------------
# Fetch new procurement notices
# --------------------------------------------------------------------------
def fetch_new_notices(state: dict) -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=FIRST_RUN_LOOKBACK_DAYS)).strftime("%Y-%m-%dT00:00:00")
    where = f"section_name='Procurement' AND start_date >= '{since}'"
    params = {
        "$where": where,
        "$order": "start_date DESC",
        "$limit": "500",
    }
    url = SOCRATA_URL + "?" + urllib.parse.urlencode(params)
    rows = http_get_json(url)

    seen = set(state["seen_ids"])
    fresh = []
    for r in rows:
        rid = r.get("request_id", "")
        if not rid or rid in seen:
            continue
        if NOTICE_TYPES and r.get("type_of_notice_description", "") not in NOTICE_TYPES:
            # still mark as seen so we don't re-inspect forever
            state["seen_ids"].append(rid)
            continue
        fresh.append(r)
        state["seen_ids"].append(rid)
    return fresh


# --------------------------------------------------------------------------
# Message formatting - "breaking news" style
# --------------------------------------------------------------------------
def format_alert(r: dict) -> str:
    cat = r.get("category_description", "Uncategorized")
    emoji = CATEGORY_EMOJI.get(cat, "📢")
    rid = r.get("request_id", "")
    lines = [
        f"🚨 {emoji} *NEW NYC OPPORTUNITY* {emoji}",
        "",
        f"*{r.get('short_title', 'Untitled').strip()}*",
        "",
        f"🏛 Agency: {r.get('agency_name', 'n/a')}",
        f"🏷 Category: {cat}",
        f"📄 Type: {r.get('type_of_notice_description', 'n/a')}",
        f"⚖️ Method: {r.get('selection_method_description', 'n/a')}",
    ]
    if r.get("contract_amount"):
        lines.append(f"💰 Est. value: {fmt_amount(r['contract_amount'])}")
    if r.get("pin"):
        lines.append(f"📌 PIN: {r['pin']}")
    lines.append(f"🗓 Posted: {fmt_date(r.get('start_date', ''))}")
    if r.get("end_date"):
        lines.append(f"⏰ *Due/End: {fmt_date(r['end_date'])}*")
    desc = (r.get("additional_description_1") or "").strip()
    if desc:
        if len(desc) > 600:
            desc = desc[:600] + "…"
        lines += ["", desc]
    contact = ", ".join(x for x in [r.get("contact_name"), r.get("email")] if x)
    if contact:
        lines += ["", f"📞 Contact: {contact}"]
    lines += [
        "",
        f"🔗 Full notice: https://a856-cityrecord.nyc.gov/RequestDetail/{rid}",
        "🔎 Respond in PASSPort: https://passport.cityofnewyork.us/page.aspx/en/rfp/request_browse_public",
        "",
        f"💬 Ask the bot: /info {rid}",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Senders
# --------------------------------------------------------------------------
def send_telegram(text: str) -> None:
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print("[skip] Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    http_post_json(url, {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    })


def update_feed(new_rows: list[dict]) -> None:
    """Keep a rolling cache of recent notices for the Q&A bot."""
    feed = []
    if FEED_FILE.exists():
        feed = json.loads(FEED_FILE.read_text())
    feed = new_rows + feed
    FEED_FILE.write_text(json.dumps(feed[:1000]))


# --------------------------------------------------------------------------
def main() -> None:
    state = load_state()
    first_run = not STATE_FILE.exists()
    fresh = fetch_new_notices(state)
    print(f"Found {len(fresh)} new notice(s)")
    update_feed(fresh)

    # On the very first run, don't flood the chat - just seed state,
    # send a digest of how many were found.
    if first_run and len(fresh) > 10:
        digest = (f"✅ NYC Procurement Alerts is live! {len(fresh)} open notices "
                  f"from the last {FIRST_RUN_LOOKBACK_DAYS} days are indexed. "
                  "New opportunities will post here as they drop. Type /help for commands.")
        send_telegram(digest)
    else:
        for r in reversed(fresh):  # oldest first
            msg = format_alert(r)
            try:
                send_telegram(msg)
            except Exception as e:
                print(f"[error] send failed for {r.get('request_id')}: {e}", file=sys.stderr)
            time.sleep(1.5)  # gentle on rate limits

    save_state(state)


if __name__ == "__main__":
    main()
