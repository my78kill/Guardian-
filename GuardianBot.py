import asyncio
import re
import sqlite3
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, Message

# ========== CONFIG ==========
API_ID = 29765104
API_HASH = "1c0348c74607923c87b7cab20bc77af0"
BOT_TOKEN = "8413126697:AAGtnfTM_rEiPOyOWGTVK29m8jvad5LE4BM"
OWNER_ID = 8316921366
FRIEND_ID = 7658033495
ALLOWED_USERS = [OWNER_ID, FRIEND_ID]

bot = Client("GuardianBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== DB SETUP ==========
conn = sqlite3.connect("guardian.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS punished_users (user_id INTEGER PRIMARY KEY)")
conn.commit()

def punish_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO punished_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def unpunish_user(user_id):
    cursor.execute("DELETE FROM punished_users WHERE user_id = ?", (user_id,))
    conn.commit()

def is_punished(user_id):
    cursor.execute("SELECT user_id FROM punished_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def has_link(text):
    return bool(re.search(r"(t\.me|https?://|www\.)", text or "", re.IGNORECASE))

# ========== BAD WORD LIST ==========
BAD_WORDS = [
    "harami", "suar", "bharwa", "bhadwa", "raand", "randi", "randwa", "bhenchod", "behenchod", "bhxchod",
    "bxnchod", "bxnod", "bk!", "bkl", "b/k/l", "mc", "bc", "sex", "boobs", "boobies", "xxx", "xx", "mutthi",
    "muth", "madharchod", "madhchod", "mchod", "madarchod", "chut", "cht", "madarjat", "jhaat", "jhant",
    "bsdk", "bhosdike", "bhosda", "bhosdha", "bhosdiwale", "l**", "lwda", "lawde", "lund", "loda", "lode",
    "gaand", "gnd", "gmd", "mwale", "ld", "ramdi", "fuddi", "randike", "chutiya", "chutiye", "c", "bkc", "bakchodi",
    "bokachoda", "fuck", "sexy", "chodu", "hijde", "chhakka", "chakka", "chutmari"
]

# ========== COMMAND HANDLERS ==========
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "🤖 GuardianBot is active.\n"
        "✔️ Abuse filter\n"
        "✔️ Global punish system\n\n"
        "Use /punish and /unpunish by replying to messages."
    )

@bot.on_message(filters.command("punish") & filters.reply & filters.group)
async def punish_cmd(client, message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        return await message.reply("🚫 You are not allowed to use this command.")

    target = message.reply_to_message.from_user
    if not target:
        return await message.reply("⚠️ No user found in replied message.")

    punish_user(target.id)
    await message.reply(f"🔒 [{target.first_name}](tg://user?id={target.id}) has been *globally punished*.", quote=True)

@bot.on_message(filters.command("unpunish") & filters.reply & filters.group)
async def unpunish_cmd(client, message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        return await message.reply("🚫 You are not allowed to use this command.")

    target = message.reply_to_message.from_user
    if not target:
        return await message.reply("⚠️ No user found in replied message.")

    unpunish_user(target.id)
    await message.reply(f"✅ [{target.first_name}](tg://user?id={target.id}) has been *unpunished*.", quote=True)

# ========== MAIN MONITOR ==========
@bot.on_message(filters.group & filters.text)
async def monitor(client, message: Message):
    user = message.from_user
    if not user or user.is_bot:
        return

    # 🚫 If punished
    if is_punished(user.id):
        try:
            await message.delete()
            return
        except:
            pass

    # 💣 Abuse detection
    text = message.text.lower()
    for word in BAD_WORDS:
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, text):
            try:
                await message.delete()
                return
            except:
                pass

    # 🔗 Bio link detection (with rate-limit handling)
    try:
        if not hasattr(bot, "bio_cache"):
            bot.bio_cache = {}

        last_checked = bot.bio_cache.get(user.id, datetime.min)
        if datetime.utcnow() - last_checked > timedelta(hours=1):
            profile = await client.get_chat(user.id)
            bio = profile.bio or ""
            bot.bio_cache[user.id] = datetime.utcnow()

            if has_link(bio):
                member = await client.get_chat_member(message.chat.id, "me")
                if member.can_restrict_members:
                    until = datetime.utcnow() + timedelta(minutes=30)
                    await client.restrict_chat_member(
                        message.chat.id,
                        user.id,
                        ChatPermissions(),
                        until_date=until
                    )
                    await message.reply(
                        "🔇 You’ve been muted for 30 minutes.\nPlease remove your bio link."
                    )
    except Exception as e:
        print(f"[BIO MUTE ERROR] {e}")

# ========== AUTO DELETE FOR PUNISHED ==========
@bot.on_message(filters.group)
async def auto_delete_punished(client, message: Message):
    user = message.from_user
    if user and is_punished(user.id):
        try:
            await message.delete()
        except:
            pass

# ========== FLASK PORT BIND FOR RENDER ==========
import threading
import main  # make sure you have a file `main.py` with a Flask app named `app`
threading.Thread(target=main.app.run, kwargs={"host": "0.0.0.0", "port": 10000}).start()

print("✅ GuardianBot is running...")
bot.run()
