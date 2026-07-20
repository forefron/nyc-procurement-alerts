# Deploy for FREE in ~20 minutes (click-by-click)

Two pieces, both free:

- **Alerts** → GitHub Actions runs `fetcher.py` every 30 minutes (free, nothing to keep on)
- **Q&A bot** → `bot.py` runs on your own always-on computer (e.g. a Mac mini), reading the feed straight from your GitHub repo

You can do Part A alone today and add Part B whenever.

---

## Part A — Telegram + alerts (the core, ~20 min)

### Step 1: Create the bot (2 min)
1. In Telegram, search **@BotFather** → tap Start
2. Send `/newbot` → give it a name (e.g. `NYC Contract Alerts`) and a username ending in `bot` (e.g. `nyc_contract_alerts_bot`)
3. **Copy the token** it gives you (looks like `123456789:AAE...`). Keep it secret.

### Step 2: Create the channel (3 min)
1. Telegram → New Channel → name it (e.g. "NYC Procurement Alerts"), make it **Public** so it's easy to share, pick a link like `t.me/nycprocurementalerts`
2. Channel settings → Administrators → Add Admin → search your bot's username → add it (needs "Post Messages" permission)
3. Optional but recommended: create a group "NYC Procurement Chat", add the bot there too, and link it to the channel (Channel settings → Discussion) so members can talk and use commands.

### Step 3: Get your chat ID (2 min)
For a **public channel** you can simply use `@yourchannelname` as the chat ID. Done.
(For a private channel/group: post any message in it, open
`https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser, and copy the
`"chat":{"id":-100xxxxxxxxxx}` number.)

### Step 4: Put the code on GitHub (5 min, all in the browser)
1. Sign up / log in at github.com
2. Click **+ → New repository** → name: `nyc-procurement-alerts` → **Public** → Create
   (Public = unlimited free Actions minutes. The code contains no secrets, so public is fine.)
3. Click **uploading an existing file** → drag in ALL the files from this folder
   **including the `.github/workflows/fetch.yml` file with its folder path kept intact** → Commit.
   - If drag-and-drop loses the folder: use **Add file → Create new file**, type
     `.github/workflows/fetch.yml` as the filename, and paste the file's contents.

### Step 5: Add your two secrets (2 min)
Repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `TELEGRAM_BOT_TOKEN` → value: the BotFather token
- Name: `TELEGRAM_CHAT_ID` → value: `@yourchannelname` (or the `-100...` number)

### Step 6: Turn it on and test (2 min)
1. Repo → **Actions** tab → enable workflows if prompted
2. Click **NYC procurement alerts** → **Run workflow** → Run
3. Within a minute your channel gets its first post (a digest on the first run). After that it checks for new opportunities every 30 minutes, forever, free.

### Step 7: Invite your 800 members
Pin a message in your WhatsApp group with your channel link (`t.me/yourchannel`) and a one-liner: "Instant alerts for every new NYC contract opportunity — free."

**Note:** GitHub pauses scheduled workflows after 60 days of no repo activity — but this workflow commits its state file back to the repo on every new alert, which keeps it active automatically. If you ever get an email saying the workflow was paused, one click re-enables it.

---

## Part B — The Q&A bot, free on your own computer (~10 min)

`bot.py` answers /latest, /search, /due, /info, /categories. It needs to run continuously, so use any computer that stays on (a Mac mini is perfect):

```bash
# one-time setup
pip3 install python-telegram-bot
export TELEGRAM_BOT_TOKEN="your-token"
export FEED_URL="https://raw.githubusercontent.com/<your-user>/nyc-procurement-alerts/main/feed.json"
python3 bot.py
```

`FEED_URL` makes the bot read the opportunity cache straight from your GitHub repo — no syncing needed. To keep it running after you close the terminal, run it with `nohup python3 bot.py &` or ask Cowork to set it up as a login service.

If the computer is off, alerts still post (Part A is independent); only the interactive commands pause.

---

## Total cost: $0. No credit card anywhere.
