"""
Ban‑metrics bot (event‑driven + one‑time backfill)
=================================================
Tracks user bans without parsing Carl‑bot text by listening to
`on_member_join` and `on_member_ban` events *and* performs a **one‑time
historical backfill** from the guild audit log. Now also syncs its slash
commands on startup so `/banstats` appears immediately.

Features
--------
* Persists ban data to SQLite (`bans.sqlite`).
* `/banstats` slash‑command returns three PNG charts:
  1. bans per day
  2. bans per moderator
  3. time‑to‑ban distribution (minutes between join and ban)
* Automatically back‑fills all existing ban audit‑log entries the first
  time the bot starts. A flag in the DB prevents re‑running.
* Syncs slash commands globally—or instantly for one guild if you set
  `GUILD_ID` in `.env`.

Prerequisites
-------------
1. **Intents** – enable **Guild Members**, **Guild Bans**, and **Guilds** in
   the Developer Portal.
2. **Permissions** – give the bot `View Audit Log`, `Send Messages`,
   `Attach Files`, and (optionally) `Read Message History`.
3. **OAuth2 scopes** – `bot` **and** `applications.commands` when you
   generate the invite link.
4. **Dependencies** – `discord.py 2.*`, `python‑dotenv`, `matplotlib`.
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -U discord.py python-dotenv matplotlib
   ```
5. **Token** – store in a local `.env` file:
   ```env
   DISCORD_TOKEN=PASTE_YOUR_TOKEN_HERE
   # Optional: make slash‑command sync instant in one guild
   GUILD_ID=123456789012345678
   ```

Run with `python bot.py`. First launch back‑fills historical bans and
registers `/banstats`; subsequent launches record only new events.
"""

from __future__ import annotations

import os
import sqlite3
from collections import Counter
from typing import Optional
import re
from datetime import datetime, timedelta, timezone, date
import time

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

###############################################################################
#  DB helpers
###############################################################################
DB_FILE = "bans.sqlite"
CARL_LOG_CHANNEL_ID = 797863282177736755
RAW_EVERY        = 500                       # how often to log progress
TIME_EVERY  = 10

SCHEMA_BANS = """
CREATE TABLE IF NOT EXISTS bans (
    offender_id   TEXT PRIMARY KEY,
    offender_tag  TEXT,
    joined_at     TEXT,
    banned_at     TEXT,
    moderator     TEXT,
    reason        TEXT
)"""

SCHEMA_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
)"""


def init_db() -> None:
    """Create tables if they do not exist."""
    with sqlite3.connect(DB_FILE) as cx:
        cx.execute(SCHEMA_BANS)
        cx.execute(SCHEMA_META)


def meta_get(key: str) -> Optional[str]:
    with sqlite3.connect(DB_FILE) as cx:
        row = cx.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def meta_set(key: str, value: str) -> None:
    with sqlite3.connect(DB_FILE) as cx:
        cx.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def save_or_update(offender_id: int | str, **cols) -> None:
    """Insert or up‑sert a row identified by *offender_id*."""
    keys = ", ".join(cols)
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{k}=excluded.{k}" for k in cols)
    with sqlite3.connect(DB_FILE) as cx:
        cx.execute(
            f"INSERT INTO bans (offender_id, {keys}) VALUES (?, {placeholders}) "
            f"ON CONFLICT(offender_id) DO UPDATE SET {updates}",
            (str(offender_id), *cols.values()),
        )

###############################################################################
#  Discord bot
###############################################################################

load_dotenv()

intents = discord.Intents.none()
intents.guilds = True
intents.members = True  # on_member_join
intents.bans = True     # on_member_ban

bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID_ENV = os.getenv("GUILD_ID")
TARGET_GUILD_OBJ = (
    discord.Object(int(GUILD_ID_ENV)) if GUILD_ID_ENV and GUILD_ID_ENV.isdigit() else None
)

###############################################################################
#  Events
###############################################################################

def parse_delta(text: str) -> timedelta:
    """Convert '2 minutes and 38 seconds' → timedelta(seconds=158)."""
    sec = 0
    for amt, unit in re.findall(r"(\d+)\s(\w+)", text):
        unit = unit.rstrip("s").lower()
        sec += int(amt) * {
            "second": 1, "minute": 60, "hour": 3600, "day": 86400
        }[unit]
    return timedelta(seconds=sec)

@bot.event
async def on_ready():
    init_db()
    print(f"Logged in as {bot.user} ({bot.user.id})")

    # ------------------------------------------------------------------
    # Sync slash commands (guild‑scoped if GUILD_ID set, else global)
    # ------------------------------------------------------------------
    try:
        if TARGET_GUILD_OBJ:
            synced = await bot.tree.sync(guild=TARGET_GUILD_OBJ)
            print('Local commands:', [cmd.name for cmd in bot.tree.get_commands()])
            print(f"Synced {len(synced)} command(s) to guild {TARGET_GUILD_OBJ.id}.")
        else:
            synced = await bot.tree.sync()
            print(
                f"Synced {len(synced)} global command(s). (May take up to 1 h to appear.)"
            )
    except Exception as exc:
        print(f"⚠️  Slash‑command sync failed: {exc}")

    # ------------------------------------------------------------------
    # One‑time historical backfill (skips if already done)
    # ------------------------------------------------------------------
    if meta_get("backfill_done") != "1":
        for guild in bot.guilds:
            await backfill_carl_history(guild)
        meta_set("backfill_done", "1")
        print("Historical backfill completed.")

# ------------------------------------------------------------------
START_AFTER = discord.Object(987134194998186044)
# ------------------------------------------------------------------

# ───────── regexes ────────────────────────────────────────────────
BAN_EMBED_RE = re.compile(
    r"\*\*Offender:\*\*.*?<@(\d+)>.*?"
    r"\*\*Responsible moderator:\*\*\s*([^\n<]+)",
    re.S
)
JOIN_PHRASE  = "joined the server"            # lower-case substring test
# ───────── back-fill function ──────────────────────────────────────
async def backfill_carl_history(guild: discord.Guild):
    chan = guild.get_channel(CARL_LOG_CHANNEL_ID)
    if not chan:
        print("⚠️  Log channel not found in", guild.name); return

    print(f"🔍  Scanning #{chan.name} starting at message ID {START_AFTER} …")
    msgs_scanned = join_added = ban_added = 0
    last_log = time.time()

    async for msg in chan.history(limit=None,
                                  oldest_first=True,
                                  after=START_AFTER):
        msgs_scanned += 1

        # ---- progress ticker -----------------------------------------
        if msgs_scanned % RAW_EVERY == 0 or time.time() - last_log >= TIME_EVERY:
            print(f"…{msgs_scanned:,} msgs | +{join_added} joins, +{ban_added} bans",
                  flush=True)
            last_log = time.time()

        if not msg.embeds:
            continue
        emb = msg.embeds[0]

        # ----- 1⃣  Ban embed -----------------------------------------
        if emb.title and emb.title.lower().startswith("ban | case"):
            m = BAN_EMBED_RE.search(emb.description or "")
            if not m:
                continue
            offender_id, moderator_tag = m.groups()
            banned_at = msg.created_at
            with sqlite3.connect(DB_FILE) as cx:
                cur = cx.execute(
                    "SELECT banned_at FROM bans WHERE offender_id = ?", (offender_id,)
                ).fetchone()
            if cur and cur[0]:
                continue  # already have this ban
            save_or_update(
                offender_id,
                banned_at=banned_at.isoformat(),
                moderator=moderator_tag.strip().lower(),
            )
            ban_added += 1
            continue   # don’t re-check as join

        # ----- 2⃣  Join embed ----------------------------------------
        if emb.description and JOIN_PHRASE in emb.description.lower():
            if not (emb.footer and emb.footer.text.startswith("ID: ")):
                continue
            offender_id = emb.footer.text.split(":")[1].strip()
            joined_at = msg.created_at
            with sqlite3.connect(DB_FILE) as cx:
                cur = cx.execute(
                    "SELECT joined_at FROM bans WHERE offender_id = ?", (offender_id,)
                ).fetchone()
            if cur and cur[0]:
                continue  # already have join time
            save_or_update(offender_id, joined_at=joined_at.isoformat())
            join_added += 1

    print(f"✅  Back-fill done: {msgs_scanned:,} msgs | "
          f"+{join_added} joins, +{ban_added} bans.")


@bot.event
async def on_member_join(member: discord.Member):
    """Record the exact UTC timestamp when a user joins."""
    save_or_update(
        member.id,
        offender_tag=str(member),
        joined_at=datetime.now(timezone.utc).isoformat(),
    )


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    """When someone is banned, capture *who* banned and *why* from audit log."""
    banned_at = datetime.now(timezone.utc)
    moderator = "unknown"
    reason = None

    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                moderator = str(entry.user)
                reason = entry.reason
                break
    except discord.Forbidden:
        # Bot lacks VIEW_AUDIT_LOG permission – fall back to unknown.
        pass

    save_or_update(
        user.id,
        banned_at=banned_at.isoformat(),
        moderator=moderator.lower(),
        reason=reason,
    )

###############################################################################
#  Slash command – /banstats
###############################################################################

@bot.tree.command(
    name="banstats",
    description="Show ban metrics. Optional: /banstats start:2024-01-01",
    guild=TARGET_GUILD_OBJ
)
@app_commands.describe(
    start="(optional) ISO date - show stats starting from this date"
)
async def banstats(inter: discord.Interaction, start: str = None):
    await inter.response.defer(thinking=True)
    MIN_DATE = datetime(2021, 1, 1, tzinfo=timezone.utc)

    # ---------- date filter -----------------------------------------------
    if start:
        try:
            since = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        except ValueError:
            await inter.response.send_message(
                "❌  Start date must be YYYY-MM-DD", ephemeral=True
            )
            return
    else:
        since = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=30)

    # Enforce lower bound
    if since < MIN_DATE:
        since = MIN_DATE

    with sqlite3.connect(DB_FILE) as cx:
        rows = cx.execute(
            "SELECT banned_at, joined_at, moderator FROM bans WHERE banned_at IS NOT NULL"
        ).fetchall()

    # keep only rows newer than `since`
    filtered = [
        (b, j, m) for (b, j, m) in rows
        if datetime.fromisoformat(b).replace(tzinfo=timezone.utc) >= since
    ]
    if not filtered:
        await inter.response.send_message("No bans in that period.")
        return

    banned_ts, joined_ts, mods = zip(*filtered)

    banned_dt = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in banned_ts]
    joined_dt = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) if t else None for t in joined_ts]

    # ------- Figure 1: bans over time --------------------------------------
    per_day = Counter(d.date() for d in banned_dt)

    start_date = since.date()
    end_date   = max(banned_dt).date()
    span_days  = (end_date - start_date).days + 1

    # Decide granularity
    use_monthly = span_days > 366          # > 1 year → monthly buckets

    if use_monthly:
        # ---- group by YYYY-MM --------------------------------------------
        per_month = Counter(
            (d.year, d.month) for d in banned_dt
        )
        # generate full month range
        cur = date(start_date.year, start_date.month, 1)
        end = date(end_date.year, end_date.month, 1)
        month_range = []
        while cur <= end:
            month_range.append(cur)
            # next month
            cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)

        counts = [per_month.get((m.year, m.month), 0) for m in month_range]
        labels = [m.strftime("%Y-%m") for m in month_range]

        plt.figure(figsize=(max(6, 0.4 * len(labels)), 4))
        plt.bar(labels, counts, width=0.9)
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Bans")
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.title("Bans per month")
    else:
        # ---- daily buckets (unchanged) -----------------------------------
        date_range = [start_date + timedelta(days=i) for i in range(span_days)]
        counts = [per_day.get(d, 0) for d in date_range]

        plt.figure(figsize=(max(6, 0.2 * len(date_range)), 4))
        plt.bar(date_range, counts, width=0.9)
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.ylabel("Bans")
        plt.title("Bans per day")
        plt.gcf().autofmt_xdate(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig("bans_per_day.png"); plt.close()

    # ------- Figure 2: bans by moderator -----------------------------------------
    per_mod = Counter(mods)
    plt.figure(figsize=(8, 0.45 * len(per_mod) + 1))  # auto-height
    mods_sorted = sorted(per_mod.items(), key=lambda kv: kv[1])
    labels, counts = zip(*mods_sorted)
    plt.barh(labels, counts)
    plt.xlabel("Bans")
    plt.title("Bans by moderator")
    plt.tight_layout()
    plt.savefig("bans_by_mod.png"); plt.close()

    # ------- Figure 3: time‑to‑ban (minutes) -------------------------------------
    time_to_ban = [
        (b - j).total_seconds() / 3600
        for b, j in zip(banned_dt, joined_dt)
        if j is not None
    ]
    if time_to_ban:
        max_hours = max(time_to_ban)
        bin_count = max(5, min(30, int(max_hours) + 1))
        plt.figure()
        plt.hist(time_to_ban, bins=bin_count, edgecolor="black")
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.xlabel("Hours from join → ban");
        plt.ylabel("Users");
        plt.title("Time-to-ban distribution");
        plt.tight_layout()
        plt.savefig("time_to_ban.png")
        plt.close()
    else:
        print("⏳  No finished time-to-ban data yet; skipping histogram.")

    files = [discord.File(p) for p in ("bans_per_day.png", "bans_by_mod.png", "time_to_ban.png")]
    await inter.followup.send(files=files, content="Here are the latest ban stats!")

###############################################################################
#  Main entry‑point
###############################################################################

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
