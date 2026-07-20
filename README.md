# NYC Procurement Alerts — Telegram

Breaking-news-style alerts for NYC procurement opportunities (the same solicitations shown in PASSPort), posted automatically to your Telegram channel, with a command bot that answers member questions.

**Want to deploy right now for $0? Follow DEPLOY_FREE.md — it's the click-by-click guide.**

## The key insight: you don't need to scrape PASSPort

PASSPort (passport.cityofnewyork.us) blocks crawlers via robots.txt — scraping it is brittle and against its rules. But by law, every NYC solicitation is also published in the **City Record**, and the City publishes that as an official, free, machine-readable API on NYC Open Data:

- Dataset: [City Record Online (dg92-zbpx)](https://data.cityofnewyork.us/City-Government/City-Record-Online/dg92-zbpx)
- API endpoint: `https://data.cityofnewyork.us/resource/dg92-zbpx.json`
- Filter: `section_name='Procurement'` and `type_of_notice_description='Solicitation'`
- Fields: request_id, agency_name, short_title, category_description, selection_method_description, pin, start_date, end_date (deadline), contract_amount, contact_name, email, description
- Each notice links to a public detail page: `https://a856-cityrecord.nyc.gov/RequestDetail/<request_id>`

This is more reliable than scraping, updated daily, and completely legal. The same pattern (find the official feed before scraping) applies to future sites: NY State has the NYS Contract Reporter, the federal government has the SAM.gov API, other cities have their own open-data feeds.

## Architecture (100% free)

```
NYC Open Data API (City Record / PASSPort solicitations)
        │  polled every 30 min by GitHub Actions (free)
        ▼
fetcher.py ── dedupes via state.json, formats alert, tags category
        ├──► Telegram Bot API ──► your Telegram channel   (official, free)
        └──► feed.json (rolling cache, committed to the repo)
                    ▲  read via raw.githubusercontent.com
bot.py ─────────────┘  runs on any always-on computer (e.g. your Mac mini)
                       answers /latest /search /due /info /categories
```

## Files

- `fetcher.py` — polls the API, posts new opportunities to Telegram (stdlib only, no installs)
- `bot.py` — the Q&A command bot (needs `pip install python-telegram-bot`)
- `.github/workflows/fetch.yml` — GitHub Actions schedule that runs the fetcher every 30 min
- `DEPLOY_FREE.md` — click-by-click free deployment guide
- `COWORK_PROMPT.md` — ready-to-paste prompt for future Cowork sessions (deploy help, new feeds, upgrades)
- `config.example.env` — settings reference for running locally

## Bot commands (free, no AI fees)

`/latest [n]`, `/search <keyword>`, `/due [days]`, `/info <request_id>`, `/categories`, `/help`

## Costs summary

| Item | Cost |
|---|---|
| NYC data feed | Free |
| Telegram bot + channel | Free |
| GitHub Actions (public repo) | Free |
| Q&A bot on your own computer | Free |

## Migrating your WhatsApp community

Post a pinned message in the WhatsApp group with the Telegram channel link and a one-line pitch ("instant NYC contract alerts + a searchable bot"). The first few exclusive alerts on Telegram usually pull people over.

## Growing it later

- Add NY State (Contract Reporter) and federal (SAM.gov API) feeds as new fetch functions.
- Add keyword/industry filtering per member (`/subscribe construction`).
- Upgrade Q&A to AI answers (Claude API) grounded in each notice's full text.
- Auto-post a weekly "closing soon" digest.
