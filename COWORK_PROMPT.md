# Ready-to-paste Cowork prompt

Use this prompt in a new Cowork session whenever you want to build, deploy, or extend the alert system. Fill in anything in [brackets].

---

I run a community of ~800 NYC vendors/entrepreneurs on Telegram, and I want an automated "breaking news" bot for NYC government procurement opportunities.

**Goal:** Every new NYC solicitation should automatically post to my Telegram channel/group, formatted like a breaking-news alert, and members should be able to query a bot with simple commands.

**Data source — do NOT scrape PASSPort.** PASSPort blocks crawlers; instead use NYC's official City Record Online dataset on NYC Open Data (Socrata):
- Endpoint: https://data.cityofnewyork.us/resource/dg92-zbpx.json
- Filter: section_name='Procurement' AND type_of_notice_description='Solicitation', ordered by start_date DESC
- Key fields: request_id, agency_name, short_title, category_description, selection_method_description, pin, start_date, end_date (deadline), contract_amount, contact_name, email, additional_description_1
- Public detail link per notice: https://a856-cityrecord.nyc.gov/RequestDetail/<request_id>
- PASSPort browse link for responding: https://passport.cityofnewyork.us/page.aspx/en/rfp/request_browse_public

**Alert format:** emoji-tagged by category (🏗️ construction, 🤝 human services, 📦 goods, 💻 tech…), bold title, agency, category, procurement method, estimated value, PIN, posted date, deadline (emphasized), short description, contact, links, and a "/info <request_id>" hint.

**Behavior requirements:**
1. Poll every 30–60 minutes; dedupe using a persistent state file of seen request_ids so nothing posts twice.
2. On the very first run, don't flood the chat — post a single digest message instead.
3. Maintain a rolling feed cache (last ~1000 notices) that the Q&A bot reads.
4. Telegram: use the official Bot API (token from @BotFather), Markdown formatting, post to chat ID [YOUR_CHAT_ID].
5. Q&A bot (Telegram, long polling, python-telegram-bot): /latest [n], /search <keyword>, /due [days], /info <request_id>, /categories, /help. No AI needed — answer from the feed cache.
6. Handle errors gracefully: rate-limit sends (~1.5s apart), log failures, never crash the loop.

**My existing code:** I already have working files (fetcher.py, bot.py, config.example.env, requirements.txt, README.md) from a previous session — [attach them]. Start from those rather than rewriting.

**What I want in THIS session:** [pick one]
- Help me deploy: walk me through BotFather setup, getting my Telegram chat ID, setting up [GitHub Actions / a VPS / PythonAnywhere], installing the cron job, and testing end-to-end with a real post to my group.
- Add a new source: fetch [NY State Contract Reporter / SAM.gov federal opportunities / other city] and merge it into the same alert pipeline with a source tag.
- Add filtering: per-member /subscribe <keyword> subscriptions with DM alerts.
- Upgrade Q&A to AI answers using the Claude API, grounded only in the notice's own text, with a monthly budget cap.

Ask me for any tokens/IDs you need, test everything you can before calling it done, and give me a final checklist of what runs where.
