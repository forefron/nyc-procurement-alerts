#!/usr/bin/env python3
"""
Telegram Q&A bot for NYC procurement alerts (simple commands, no AI fees).

Commands:
  /latest [n]        - last n opportunities posted (default 5)
  /search <keyword>  - search recent notices by keyword (title/desc/agency)
  /due [days]        - notices due within N days (default 7)
  /info <request_id> - full details for one notice
  /categories        - counts by category in the current feed
  /help              - this list

Runs alongside fetcher.py and reads the feed.json cache it maintains.
Uses long polling - no webhook/SSL setup needed. Keep it running with
systemd, tmux, or a small always-on host (see README).

Requires: pip install python-telegram-bot>=21
"""

import json
import os
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

FEED_FILE = Path(__file__).parent / "feed.json"
# If set, fetch the feed from your GitHub repo instead of a local file, e.g.
# https://raw.githubusercontent.com/<user>/<repo>/main/feed.json
FEED_URL = os.getenv("FEED_URL", "")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

_cache: dict = {"t": 0.0, "rows": []}

HELP = (
    "🤖 *NYC Procurement Bot — Commands*\n\n"
    "/latest — 5 most recent opportunities\n"
    "/latest 10 — last 10\n"
    "/search security — find notices matching a keyword\n"
    "/due — closing in the next 7 days\n"
    "/due 3 — closing in the next 3 days\n"
    "/info 20260626017 — full details for one notice\n"
    "/categories — what industries are in the feed\n"
)


def load_feed() -> list[dict]:
    if FEED_URL:
        # refresh at most every 5 minutes
        if time.time() - _cache["t"] > 300:
            try:
                with urllib.request.urlopen(FEED_URL, timeout=30) as resp:
                    _cache["rows"] = json.loads(resp.read().decode("utf-8"))
                _cache["t"] = time.time()
            except Exception as e:
                print(f"[warn] feed fetch failed: {e}")
        return _cache["rows"]
    if FEED_FILE.exists():
        return json.loads(FEED_FILE.read_text())
    return []


def brief(r: dict) -> str:
    due = r.get("end_date", "")[:10]
    return (f"• *{r.get('short_title','Untitled').strip()}*\n"
            f"  {r.get('agency_name','')} | {r.get('category_description','')} "
            f"| due {due or 'n/a'}\n"
            f"  /info {r.get('request_id','')}")


def full(r: dict) -> str:
    rid = r.get("request_id", "")
    parts = [
        f"*{r.get('short_title','Untitled').strip()}*",
        "",
        f"🏛 {r.get('agency_name','n/a')}",
        f"🏷 {r.get('category_description','n/a')} | {r.get('type_of_notice_description','')}",
        f"⚖️ {r.get('selection_method_description','')}",
        f"📌 PIN: {r.get('pin','n/a')}",
        f"🗓 Posted {r.get('start_date','')[:10]}  ⏰ Due/End {r.get('end_date','')[:10]}",
    ]
    if r.get("contract_amount"):
        parts.append(f"💰 {r['contract_amount']}")
    if r.get("additional_description_1"):
        parts += ["", r["additional_description_1"][:900]]
    contact = ", ".join(x for x in [r.get("contact_name"), r.get("email")] if x)
    if contact:
        parts += ["", f"📞 {contact}"]
    parts += ["", f"🔗 https://a856-cityrecord.nyc.gov/RequestDetail/{rid}"]
    return "\n".join(parts)


async def cmd_help(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode=ParseMode.MARKDOWN)


async def cmd_latest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    n = 5
    if ctx.args and ctx.args[0].isdigit():
        n = min(int(ctx.args[0]), 15)
    rows = load_feed()[:n]
    if not rows:
        await update.message.reply_text("No opportunities cached yet — check back soon.")
        return
    await update.message.reply_text(
        "\n\n".join(brief(r) for r in rows), parse_mode=ParseMode.MARKDOWN)


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /search <keyword>  e.g. /search construction")
        return
    kw = " ".join(ctx.args).lower()
    hits = [r for r in load_feed() if kw in json.dumps(r).lower()][:8]
    if not hits:
        await update.message.reply_text(f"No recent notices matching “{kw}”.")
        return
    await update.message.reply_text(
        "\n\n".join(brief(r) for r in hits), parse_mode=ParseMode.MARKDOWN)


async def cmd_due(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    days = 7
    if ctx.args and ctx.args[0].isdigit():
        days = int(ctx.args[0])
    cutoff = datetime.utcnow() + timedelta(days=days)
    now = datetime.utcnow() - timedelta(days=1)
    hits = []
    for r in load_feed():
        try:
            d = datetime.fromisoformat(r.get("end_date", "").replace("Z", ""))
            if now <= d <= cutoff:
                hits.append(r)
        except Exception:
            pass
    hits.sort(key=lambda r: r.get("end_date", ""))
    if not hits:
        await update.message.reply_text(f"Nothing due in the next {days} days.")
        return
    await update.message.reply_text(
        "\n\n".join(brief(r) for r in hits[:10]), parse_mode=ParseMode.MARKDOWN)


async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /info <request_id>")
        return
    rid = ctx.args[0].strip()
    for r in load_feed():
        if r.get("request_id") == rid:
            await update.message.reply_text(full(r), parse_mode=ParseMode.MARKDOWN)
            return
    await update.message.reply_text(
        f"Not in my cache. Try the notice page:\n"
        f"https://a856-cityrecord.nyc.gov/RequestDetail/{rid}")


async def cmd_categories(update: Update, _: ContextTypes.DEFAULT_TYPE):
    counts: dict[str, int] = {}
    for r in load_feed():
        c = r.get("category_description", "Uncategorized")
        counts[c] = counts.get(c, 0) + 1
    if not counts:
        await update.message.reply_text("Feed is empty right now.")
        return
    lines = [f"• {c}: {n}" for c, n in sorted(counts.items(), key=lambda x: -x[1])]
    await update.message.reply_text("📊 Current feed by category:\n" + "\n".join(lines))


def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["help", "start"], cmd_help))
    app.add_handler(CommandHandler("latest", cmd_latest))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("due", cmd_due))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("categories", cmd_categories))
    print("Bot running (long polling)…")
    app.run_polling()


if __name__ == "__main__":
    main()
