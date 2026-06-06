# ============================================================
# BOT - aiogram 2.25.1
# ============================================================

import os
import time
import random
import sqlite3
import asyncio
import schedule
from collections import Counter
from datetime import datetime, timedelta
from threading import Thread

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from flask import Flask

# ============================================================
# SECTION 1: CONFIG
# ============================================================

TOKEN = "8370081495:AAELEnisiFTAjr4ItPq480AQzAUtbM7cEhk"  # pip install aiogram==2.25.1 Flask schedule
ADMIN_IDS = {8494172900}
DB_PATH = "bot_database.db"

# ============================================================
# SECTION 2: DATABASE
# ============================================================

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT, joined_at INTEGER,
        is_banned INTEGER DEFAULT 0, referrer_id INTEGER,
        referral_count INTEGER DEFAULT 0, last_active INTEGER DEFAULT 0,
        total_activity INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, action TEXT, timestamp INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT, name TEXT, description TEXT, file_type TEXT,
        rating REAL DEFAULT 0, rating_count INTEGER DEFAULT 0,
        download_count INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ratings (
        user_id INTEGER, file_id INTEGER, rating INTEGER, rated_at INTEGER,
        PRIMARY KEY (user_id, file_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
        user_id INTEGER, post_id INTEGER, PRIMARY KEY (user_id, post_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS message_history (
        user_id INTEGER, message_id INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER, text TEXT, posted_at INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, post_id INTEGER, downloaded_at INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        channel_id INTEGER PRIMARY KEY,
        channel_name TEXT, is_active INTEGER DEFAULT 1
    )''')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("require_subscription", "True")')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("custom_post_text", "")')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("daily_report_time", "20:00")')
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("auto_dua_enabled", "True")')
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, referrer_id=None):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not c.fetchone():
        c.execute('INSERT INTO users (user_id, username, first_name, joined_at, referrer_id, last_active) VALUES (?, ?, ?, ?, ?, ?)',
                  (user_id, username, first_name, int(time.time()), referrer_id, int(time.time())))
        if referrer_id:
            c.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referrer_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def update_last_active(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (int(time.time()), user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result

def get_users_count():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    result = c.fetchone()[0]
    conn.close()
    return result

def get_active_count():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE is_banned = 0')
    result = c.fetchone()[0]
    conn.close()
    return result

def is_banned(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

def ban_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_referral_count(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_today_new_users():
    today_start = int(time.mktime(datetime.now().replace(hour=0, minute=0, second=0).timetuple()))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE joined_at > ?', (today_start,))
    result = c.fetchone()[0]
    conn.close()
    return result

def get_weekly_new_users():
    result = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = int(day.timestamp())
        day_end = int((day + timedelta(days=1)).timestamp())
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users WHERE joined_at BETWEEN ? AND ?', (day_start, day_end))
        count = c.fetchone()[0]
        conn.close()
        day_name = day.strftime('%A')
        names = {"Monday":"الإثنين","Tuesday":"الثلاثاء","Wednesday":"الأربعاء",
                 "Thursday":"الخميس","Friday":"الجمعة","Saturday":"السبت","Sunday":"الأحد"}
        result.append({'day': names.get(day_name, day_name), 'count': count})
    return result

def log_activity(user_id, action):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO activity_log (user_id, action, timestamp) VALUES (?, ?, ?)',
                  (user_id, action, int(time.time())))
        c.execute('UPDATE users SET last_active = ?, total_activity = total_activity + 1 WHERE user_id = ?',
                  (int(time.time()), user_id))
        conn.commit()
        conn.close()
    except:
        pass

def get_active_users_now(minutes=60):
    cutoff = int(time.time()) - (minutes * 60)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT DISTINCT user_id FROM activity_log WHERE timestamp > ?', (cutoff,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_active_users_count(minutes=60):
    return len(get_active_users_now(minutes))

def get_peak_hours():
    conn = get_db()
    c = conn.cursor()
    week_ago = int(time.time()) - (7 * 86400)
    c.execute('SELECT timestamp FROM activity_log WHERE timestamp > ?', (week_ago,))
    timestamps = [row[0] for row in c.fetchall()]
    conn.close()
    hours = [datetime.fromtimestamp(ts).hour for ts in timestamps]
    return Counter(hours).most_common(5)

def add_channel(channel_id, channel_name):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO channels (channel_id, channel_name, is_active) VALUES (?, ?, 1)', (channel_id, channel_name))
    conn.commit()
    conn.close()

def get_active_channels():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT channel_id, channel_name FROM channels WHERE is_active = 1')
    channels = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
    conn.close()
    return channels

def get_all_channels():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT channel_id, channel_name, is_active FROM channels')
    channels = [{'id': row[0], 'name': row[1], 'active': row[2] == 1} for row in c.fetchall()]
    conn.close()
    return channels

def delete_channel(channel_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

def get_channels_count():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM channels WHERE is_active = 1')
    result = c.fetchone()[0]
    conn.close()
    return result

def add_config(file_id, name, description=None, file_type="document"):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO configs (file_id, name, description, file_type, rating, rating_count, download_count) VALUES (?, ?, ?, ?, 0, 0, 0)',
              (file_id, name, description, file_type))
    conn.commit()
    conn.close()

def get_all_configs(sort_by_rating=False):
    conn = get_db()
    c = conn.cursor()
    order = 'ORDER BY rating DESC' if sort_by_rating else ''
    c.execute(f'SELECT id, file_id, name, description, file_type, rating, rating_count, download_count FROM configs {order}')
    configs = [{'id': r[0], 'file_id': r[1], 'name': r[2], 'description': r[3],
                'file_type': r[4], 'rating': r[5], 'rating_count': r[6], 'download_count': r[7]}
               for r in c.fetchall()]
    conn.close()
    return configs

def get_configs_count():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM configs')
    result = c.fetchone()[0]
    conn.close()
    return result

def clear_configs():
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM configs')
    c.execute('DELETE FROM ratings')
    conn.commit()
    conn.close()

def get_file_by_id(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, file_id, name, description, file_type, rating, rating_count, download_count FROM configs WHERE id = ?', (file_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'file_id': row[1], 'name': row[2], 'description': row[3],
                'file_type': row[4], 'rating': row[5], 'rating_count': row[6], 'download_count': row[7]}
    return None

def update_description(file_id, description):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE configs SET description = ? WHERE id = ?', (description, file_id))
    conn.commit()
    conn.close()

def get_top_rated_files(limit=5):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, name, rating, rating_count, download_count FROM configs WHERE rating_count > 0 ORDER BY rating DESC LIMIT ?', (limit,))
    files = [{'id': r[0], 'name': r[1], 'rating': r[2], 'count': r[3], 'downloads': r[4]} for r in c.fetchall()]
    conn.close()
    return files

def get_most_downloaded_files(limit=5):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, name, download_count FROM configs ORDER BY download_count DESC LIMIT ?', (limit,))
    result = [{'id': r[0], 'name': r[1], 'count': r[2]} for r in c.fetchall()]
    conn.close()
    return result

def add_rating(user_id, file_id, rating):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM downloads WHERE user_id = ? AND post_id = ?', (user_id, file_id))
    if c.fetchone():
        c.execute('SELECT * FROM ratings WHERE user_id = ? AND file_id = ?', (user_id, file_id))
        if not c.fetchone():
            c.execute('INSERT INTO ratings (user_id, file_id, rating, rated_at) VALUES (?, ?, ?, ?)',
                      (user_id, file_id, rating, int(time.time())))
            c.execute('SELECT AVG(rating), COUNT(*) FROM ratings WHERE file_id = ?', (file_id,))
            row = c.fetchone()
            c.execute('UPDATE configs SET rating = ?, rating_count = ? WHERE id = ?', (row[0] or 0, row[1], file_id))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

def add_like(user_id, post_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM likes WHERE user_id = ? AND post_id = ?', (user_id, post_id))
    if not c.fetchone():
        c.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', (user_id, post_id))
        conn.commit()
        conn.close()
        log_activity(user_id, "like")
        return True
    conn.close()
    return False

def get_likes_count(post_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post_id,))
    result = c.fetchone()[0]
    conn.close()
    return result

def get_all_likers():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT DISTINCT user_id FROM likes')
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result

def get_total_user_likes(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM likes WHERE user_id = ?', (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def add_post(message_id, text):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO posts (message_id, text, posted_at) VALUES (?, ?, ?)', (message_id, text, int(time.time())))
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id

def record_download(user_id, post_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM downloads WHERE user_id = ? AND post_id = ?', (user_id, post_id))
    existing = c.fetchone()
    if not existing:
        c.execute('INSERT INTO downloads (user_id, post_id, downloaded_at) VALUES (?, ?, ?)',
                  (user_id, post_id, int(time.time())))
        if post_id != 0:
            c.execute('UPDATE configs SET download_count = download_count + 1 WHERE id = ?', (post_id,))
        conn.commit()
        log_activity(user_id, "download")
        conn.close()
        return False
    conn.close()
    return True

def get_post_downloads(post_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT user_id) FROM downloads WHERE post_id = ?', (post_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_downloads():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM downloads')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_today_downloads():
    today_start = int(time.mktime(datetime.now().replace(hour=0, minute=0, second=0).timetuple()))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM downloads WHERE downloaded_at > ?', (today_start,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_best_file_today():
    today_start = int(time.mktime(datetime.now().replace(hour=0, minute=0, second=0).timetuple()))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT post_id, COUNT(*) as cnt FROM downloads WHERE downloaded_at > ? GROUP BY post_id ORDER BY cnt DESC LIMIT 1', (today_start,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_setting(key, default=None):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = c.fetchone()
    conn.close()
    if result:
        val = result[0]
        if val in ['True', 'False']:
            return val == 'True'
        return val
    return default

def set_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def get_stats():
    return {'total_users': get_users_count(), 'active_users': get_active_count(), 'configs': get_configs_count()}

# ============================================================
# SECTION 3: DUA MESSAGES
# ============================================================

MORNING_DUA = [
    "🌅 *دعاء الصباح*\n\nاللهم بك أصبحنا، وبك أمسينا، وبك نحيا، وبك نموت، وإليك النشور.\n\nاللهم إني أسألك خير هذا اليوم، وخير ما فيه، وأعوذ بك من شر هذا اليوم، وشر ما فيه.\n\n*اللهم اجعل يومنا هذا خيراً وبركة* 🤲",
    "☀️ *دعاء الصباح*\n\nاللهم ما أصبح بي من نعمة أو بأحد من خلقك، فمنك وحدك لا شريك لك، فلك الحمد ولك الشكر.\n\nاللهم إني أسألك العفو والعافية في الدنيا والآخرة.\n\n*بارك الله في صباحكم* 🌸",
]
EVENING_DUA = [
    "🌙 *دعاء المساء*\n\nاللهم بك أمسينا، وبك أصبحنا، وبك نحيا، وبك نموت، وإليك المصير.\n\nاللهم إني أسألك خير هذه الليلة، وخير ما فيها، وأعوذ بك من شر هذه الليلة، وشر ما فيها.\n\n*اللهم اجعل ليلتنا خيراً وبركة* 🤲",
    "🌃 *دعاء المساء*\n\nاللهم ما أمسى بي من نعمة أو بأحد من خلقك، فمنك وحدك لا شريك لك، فلك الحمد ولك الشكر.\n\nاللهم إني أسألك العفو والعافية في الدنيا والآخرة.\n\n*مساءكم خير وبركة* 🌙",
]

def get_random_morning_dua(): return random.choice(MORNING_DUA)
def get_random_evening_dua(): return random.choice(EVENING_DUA)

# ============================================================
# SECTION 4: BOT INSTANCE
# ============================================================

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot)
BOT_USERNAME = None
_loop = None

def run_async(coro):
    if _loop:
        asyncio.run_coroutine_threadsafe(coro, _loop)

# ============================================================
# SECTION 5: UTILS
# ============================================================

def is_admin(uid): return uid in ADMIN_IDS

def dname(user):
    return f"@{user.username}" if user.username else user.first_name

async def delete_msg(chat_id, msg_id):
    try:
        await bot.delete_message(chat_id, msg_id)
    except:
        pass

async def notify_admins(text):
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text)
        except:
            pass

async def is_channel_owner(user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status == "creator"
    except:
        return False

async def check_subscription(user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return True

async def get_channel_link(channel_id):
    try:
        chat = await bot.get_chat(channel_id)
        if chat.username:
            return f"https://t.me/{chat.username}"
        return f"https://t.me/c/{str(channel_id).replace('-100', '')}"
    except:
        return f"https://t.me/c/{str(channel_id).replace('-100', '')}"

async def update_channel_name_in_db(channel_id):
    try:
        chat = await bot.get_chat(channel_id)
        channel_name = chat.title or f"قناة {channel_id}"
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE channels SET channel_name = ? WHERE channel_id = ?', (channel_name, channel_id))
        conn.commit()
        conn.close()
        return channel_name
    except:
        return None

async def get_missing_channels_message(user_id):
    if not get_setting("require_subscription", True):
        return None
    channels = get_active_channels()
    if not channels:
        return None
    missing = []
    for ch in channels:
        if await is_channel_owner(user_id, ch['id']):
            continue
        if not await check_subscription(user_id, ch['id']):
            link = await get_channel_link(ch['id'])
            missing.append(f"• [{ch['name']}]({link})")
    if missing:
        msg = "⚠️ *للاستمرار، اشترك في القنوات التالية:*\n\n"
        msg += "\n".join(missing)
        msg += "\n\n✅ *بعد الاشتراك، حاول مرة أخرى*"
        return msg
    return None

def get_welcome_message_by_time(first_name):
    hour = datetime.now().hour
    morning = [f"☀️ صباح النور يا {first_name}!", f"🌅 صباح الخيرات {first_name}، نورت البوت!"]
    afternoon = [f"🌤️ مساء الخير {first_name}، كيف حالك؟", f"🌙 أهلاً بك {first_name} في هذا المساء الجميل!"]
    night = [f"🌙 تصبح على خير {first_name}!", f"✨ في هذا الليل الهادئ، أهلاً بك {first_name}!"]
    if 5 <= hour < 12:
        msg = random.choice(morning)
    elif 12 <= hour < 17:
        msg = random.choice(afternoon)
    else:
        msg = random.choice(night)
    if get_setting("require_subscription", True):
        msg += "\n\n📢 *تنبيه:* هذا البوت يتطلب الاشتراك في قنوات معينة"
    return msg + "\n\n📌 تذكر: اضغط ❤️ أولاً، ثم 📥"

# ============================================================
# SECTION 6: KEYBOARDS
# ============================================================

def main_admin_markup():
    mk = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("📤 رفع ملفات", "📤 إضافة ملفات")
    mk.add("✅ إنهاء", "📢 نشر بالقنوات")
    mk.add("🗑️ حذف الملفات", "📊 الإحصائيات")
    mk.add("👥 المتفاعلين", "📣 إذاعة جماعية")
    mk.add("✏️ تخصيص البوست", "🔄 تصفير شامل")
    mk.add("🧹 تصفير الإحصائيات", "📈 إحصائيات متقدمة")
    mk.add("🚫 بان مستخدم", "📡 إدارة القنوات")
    mk.add("✏️ تعديل وصف ملف", "🏆 أفضل الملفات")
    mk.add("⏰ ضبط التقرير", "📿 إعدادات الأدعية")
    mk.add("🔐 الاشتراك الإجباري", "❌ إخفاء")
    return mk

def channel_markup(post_id):
    likes = get_likes_count(post_id) if post_id else 0
    dl = get_post_downloads(post_id) if post_id else 0
    mk = InlineKeyboardMarkup(row_width=2)
    mk.row(
        InlineKeyboardButton(f"❤️ تفاعل ({likes})", callback_data="do_like"),
        InlineKeyboardButton(f"📥 استلم ({dl})", url=f"https://t.me/{BOT_USERNAME}?start=download")
    )
    return mk

def back_markup():
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def channels_manager_markup():
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(InlineKeyboardButton("➕ إضافة قناة جديدة", callback_data="add_channel"))
    mk.add(InlineKeyboardButton("🔄 تحديث أسماء القنوات", callback_data="refresh_channels"))
    for ch in get_all_channels():
        status = "✅" if ch['active'] else "❌"
        mk.add(InlineKeyboardButton(f"{status} {ch['name'][:30]}", callback_data=f"del_channel_{ch['id']}"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def subscription_settings_markup():
    enabled = get_setting("require_subscription", True)
    status = "🟢 مفعل" if enabled else "🔴 معطل"
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(InlineKeyboardButton(f"🔐 الاشتراك الإجباري: {status}", callback_data="toggle_subscription"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def publish_channels_markup():
    channels = get_active_channels()
    mk = InlineKeyboardMarkup(row_width=1)
    if not channels:
        mk.add(InlineKeyboardButton("➕ أضف قناة أولاً", callback_data="add_channel"))
    else:
        for ch in channels:
            mk.add(InlineKeyboardButton(f"📢 {ch['name']}", callback_data=f"publish_{ch['id']}"))
        if len(channels) > 1:
            mk.add(InlineKeyboardButton("📢 نشر في جميع القنوات", callback_data="publish_all"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def files_list_markup(page=1, per_page=10):
    configs = get_all_configs()
    total = len(configs)
    mk = InlineKeyboardMarkup(row_width=1)
    if total == 0:
        mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
        return mk
    start = (page - 1) * per_page
    end = start + per_page
    for cfg in configs[start:end]:
        stars = "⭐" * int(round(cfg['rating'])) if cfg['rating'] > 0 else "🆕"
        mk.add(InlineKeyboardButton(f"{stars} {cfg['name'][:25]}", callback_data=f"edit_file_{cfg['id']}"))
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"files_page_{page-1}"))
    if end < total: nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"files_page_{page+1}"))
    if nav: mk.row(*nav)
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def edit_file_markup(file_id, current_desc, rating, rating_count, download_count):
    mk = InlineKeyboardMarkup(row_width=1)
    stars = "⭐" * int(round(rating)) if rating > 0 else "📝"
    mk.add(InlineKeyboardButton(f"{stars} التقييم: {rating:.1f} ({rating_count} صوت) | 📥 {download_count}", callback_data="noop"))
    if current_desc:
        mk.add(InlineKeyboardButton("✏️ تعديل الوصف", callback_data=f"edit_desc_{file_id}"))
        mk.add(InlineKeyboardButton("🗑️ حذف الوصف", callback_data=f"delete_desc_{file_id}"))
    else:
        mk.add(InlineKeyboardButton("➕ إضافة وصف", callback_data=f"edit_desc_{file_id}"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_files"))
    return mk

def top_files_markup():
    top_files = get_top_rated_files(10)
    mk = InlineKeyboardMarkup(row_width=1)
    if top_files:
        for f in top_files:
            stars = "⭐" * int(round(f['rating']))
            mk.add(InlineKeyboardButton(f"{stars} {f['name'][:30]} (📥{f['downloads']})", callback_data=f"view_file_{f['id']}"))
    else:
        mk.add(InlineKeyboardButton("⚠️ لا توجد تقييمات بعد", callback_data="noop"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def set_report_time_markup():
    mk = InlineKeyboardMarkup(row_width=2)
    for t in ["06:00", "07:00", "08:00", "18:00", "19:00", "20:00", "21:00", "22:00"]:
        mk.add(InlineKeyboardButton(t, callback_data=f"set_time_{t}"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def dua_settings_markup():
    enabled = get_setting("auto_dua_enabled", True)
    status = "🟢 مفعل" if enabled else "🔴 معطل"
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(InlineKeyboardButton(f"📿 حالة الأدعية: {status}", callback_data="toggle_dua"))
    mk.add(InlineKeyboardButton("⏰ 06:00 - دعاء الصباح", callback_data="noop"))
    mk.add(InlineKeyboardButton("⏰ 18:00 - دعاء المساء", callback_data="noop"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

def advanced_stats_markup():
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(InlineKeyboardButton("🟢 المستخدمين النشطين الآن", callback_data="stats_active_now"))
    mk.add(InlineKeyboardButton("📊 رسم بياني للمستخدمين الجدد", callback_data="stats_weekly_chart"))
    mk.add(InlineKeyboardButton("⏰ أكثر الأوقات نشاطاً", callback_data="stats_peak_hours"))
    mk.add(InlineKeyboardButton("🏆 أكثر الملفات تحميلاً", callback_data="stats_top_downloads"))
    mk.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_panel"))
    return mk

# ============================================================
# SECTION 7: SCHEDULER TASKS
# ============================================================

async def _send_dua_to_all(dua_text, label):
    users = get_all_users()
    success = 0
    for uid in users:
        try:
            if not is_banned(uid):
                await bot.send_message(uid, dua_text)
                success += 1
                await asyncio.sleep(0.05)
        except:
            pass
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, f"{'🌅' if 'صباح' in label else '🌙'} *{label}*\n✅ تم الإرسال لـ {success} مستخدم")
        except:
            pass

def send_morning_dua_to_all():
    if get_setting("auto_dua_enabled", True):
        run_async(_send_dua_to_all(get_random_morning_dua(), "تم إرسال دعاء الصباح"))

def send_evening_dua_to_all():
    if get_setting("auto_dua_enabled", True):
        run_async(_send_dua_to_all(get_random_evening_dua(), "تم إرسال دعاء المساء"))

async def _send_daily_report():
    best_file_id = get_best_file_today()
    best_file_name = "لا يوجد"
    if best_file_id:
        fi = get_file_by_id(best_file_id)
        if fi: best_file_name = fi['name'][:30]
    report = f"""📊 *التقرير اليومي*
━━━━━━━━━━━━━━━━━━━
📅 التاريخ: `{datetime.now().strftime('%Y-%m-%d')}`

👥 *المستخدمين:*
• 🆕 جدد اليوم: `{get_today_new_users()}`
• 👥 الإجمالي: `{get_users_count()}`
• 🟢 نشط الآن: `{get_active_users_count(60)}`

📥 *التحميلات:*
• 📊 اليوم: `{get_today_downloads()}`
• 📈 الإجمالي: `{get_total_downloads()}`

🏆 *أفضل منشور اليوم:*
• {best_file_name}
━━━━━━━━━━━━━━━━━━━
✅ التقرير تلقائي - البوت يعمل بكفاءة!"""
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, report)
        except:
            pass

def send_daily_report():
    run_async(_send_daily_report())

def schedule_jobs():
    report_time = get_setting("daily_report_time", "20:00")
    schedule.clear()
    schedule.every().day.at(report_time).do(send_daily_report)
    schedule.every().day.at("06:00").do(send_morning_dua_to_all)
    schedule.every().day.at("18:00").do(send_evening_dua_to_all)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

# ============================================================
# SECTION 8: HANDLERS
# ============================================================

admin_state = {}
edit_file_state = {}

BTN_LIST = [
    "📤 رفع ملفات", "📤 إضافة ملفات", "✅ إنهاء", "📢 نشر بالقنوات",
    "🗑️ حذف الملفات", "📊 الإحصائيات", "👥 المتفاعلين", "📣 إذاعة جماعية",
    "✏️ تخصيص البوست", "🔄 تصفير شامل", "🧹 تصفير الإحصائيات",
    "📈 إحصائيات متقدمة", "🚫 بان مستخدم", "📡 إدارة القنوات",
    "✏️ تعديل وصف ملف", "🏆 أفضل الملفات", "⏰ ضبط التقرير",
    "📿 إعدادات الأدعية", "🔐 الاشتراك الإجباري", "❌ إخفاء"
]

def get_stats_text():
    s = get_stats()
    dua_status = "🟢 مفعل" if get_setting("auto_dua_enabled", True) else "🔴 معطل"
    sub_status = "🟢 مفعل" if get_setting("require_subscription", True) else "🔴 معطل"
    return f"""📊 *الإحصائيات*
━━━━━━━━━━━━━━━━━━━
👥 المستخدمين: `{s['total_users']}`
🆕 جدد اليوم: `{get_today_new_users()}`
🟢 نشط الآن: `{get_active_users_count(60)}`
📂 الملفات: `{s['configs']}`
📡 القنوات: `{get_channels_count()}`
❤️ متفاعلين: `{len(get_all_likers())}`
📥 تحميلات اليوم: `{get_today_downloads()}`
📥 إجمالي التحميلات: `{get_total_downloads()}`
📿 الأدعية: {dua_status}
🔐 الاشتراك الإجباري: {sub_status}"""

async def safe_send_message(chat_id, text, reply_markup=None, retries=3):
    for i in range(retries):
        try:
            return await bot.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as e:
            if i == retries - 1:
                raise e
            await asyncio.sleep(2)
    return None

async def send_files_after_check(uid, message, post_id):
    if get_setting("require_subscription", True):
        channels = get_active_channels()
        for ch in channels:
            if await is_channel_owner(uid, ch['id']):
                continue
            if not await check_subscription(uid, ch['id']):
                link = await get_channel_link(ch['id'])
                await bot.send_message(uid, f"⚠️ *للوصول إلى الملفات، اشترك في القناة:*\n\n{link}\n\n✅ بعد الاشتراك، اضغط /start مرة أخرى")
                return False

    if get_total_user_likes(uid) == 0:
        await bot.send_message(uid, "❌ *لا يمكنك استلام الملفات!*\n\n✅ اضغط على ❤️ تفاعل في المنشور أولاً")
        return False

    configs = get_all_configs(sort_by_rating=True)
    if not configs:
        await bot.send_message(uid, "⚠️ لا توجد ملفات حالياً!")
        return False

    existing = record_download(uid, post_id)
    if existing:
        await bot.send_message(uid, "✅ *لقد استلمت الملفات مسبقاً!*\n📂 جاري إعادة إرسال الملفات...")
    else:
        await bot.send_message(uid, "✅ *تم التحقق من تفاعلك!*\n📂 جاري إرسال الملفات...")

    for cfg in configs:
        try:
            caption = f"📝\n```\n{cfg['description']}\n```" if cfg.get('description') else None
            ft = cfg['file_type']
            fid = cfg['file_id']
            if ft == "photo":
                await bot.send_photo(uid, fid, caption=caption)
            elif ft == "video":
                await bot.send_video(uid, fid, caption=caption)
            elif ft == "audio":
                await bot.send_audio(uid, fid, caption=caption)
            elif ft == "voice":
                await bot.send_voice(uid, fid, caption=caption)
            elif ft == "animation":
                await bot.send_animation(uid, fid, caption=caption)
            elif ft == "sticker":
                await bot.send_sticker(uid, fid)
            else:
                await bot.send_document(uid, fid, caption=caption)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"خطأ في إرسال الملف: {e}")

    await bot.send_message(uid, "✅ *تم إرسال جميع الملفات بنجاح!*")

    if post_id and post_id != 0:
        try:
            mk = InlineKeyboardMarkup(row_width=2)
            mk.row(
                InlineKeyboardButton(f"❤️ تفاعل ({get_likes_count(post_id)})", callback_data="do_like"),
                InlineKeyboardButton(f"📥 استلم ({get_post_downloads(post_id)})", callback_data="get_file")
            )
            await bot.edit_message_reply_markup(message.chat.id, post_id, reply_markup=mk)
        except:
            pass

    return True

# ---------- Commands ----------

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    args = message.text.split()

    if len(args) > 1 and args[1] == "download":
        await send_files_after_check(uid, message, post_id=0)
        return

    if is_banned(uid) and not is_admin(uid):
        await message.answer("🚫 محظور")
        return

    update_last_active(uid)
    log_activity(uid, "start")

    referrer = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer = int(args[1].replace("ref_", ""))
        except:
            pass

    is_new = add_user(uid, message.from_user.username, message.from_user.first_name, referrer)

    if is_admin(uid):
        await delete_msg(message.chat.id, message.message_id)
        await message.answer("👑 لوحة التحكم", reply_markup=main_admin_markup())
        return

    if get_setting("require_subscription", True):
        missing_msg = await get_missing_channels_message(uid)
        if missing_msg:
            await message.answer(missing_msg)
            return

    await message.answer(get_welcome_message_by_time(message.from_user.first_name or "صديق"))

    if is_new and referrer:
        try:
            await bot.send_message(referrer, f"🎉 مستخدم جديد عبر إحالتك! ({get_referral_count(referrer)})")
        except:
            pass
        await notify_admins(f"👤 جديد: {dname(message.from_user)}\nID: {uid}")

@dp.message_handler(commands=["admin"])
async def cmd_admin(message: types.Message):
    if is_admin(message.from_user.id):
        await delete_msg(message.chat.id, message.message_id)
        await message.answer("👑 لوحة التحكم", reply_markup=main_admin_markup())

@dp.message_handler(commands=["myref"])
async def cmd_myref(message: types.Message):
    uid = message.from_user.id
    if BOT_USERNAME:
        await message.answer(f"🔗 https://t.me/{BOT_USERNAME}?start=ref_{uid}\n👥 إحالاتك: {get_referral_count(uid)}")

@dp.message_handler(commands=["top"])
async def cmd_top(message: types.Message):
    top_files = get_top_rated_files(10)
    if not top_files:
        await message.answer("⚠️ لا توجد تقييمات بعد!")
        return
    text = "🏆 *أفضل الملفات تقييماً*\n━━━━━━━━━━━━━━━━━━━\n"
    for i, f in enumerate(top_files, 1):
        stars = "⭐" * int(round(f['rating']))
        text += f"{i}. {stars} {f['rating']:.1f} - {f['name'][:30]} (📥{f['downloads']})\n"
    await message.answer(text)

# ---------- Admin state handlers (ORDER MATTERS - specific before general) ----------

@dp.message_handler(lambda m: admin_state.get(m.from_user.id) == "custom_post")
async def handle_custom_post(message: types.Message):
    uid = message.from_user.id
    if message.text.lower() == "reset":
        set_setting("custom_post_text", "")
        await message.answer("✅ تم استعادة الافتراضي", reply_markup=main_admin_markup())
    else:
        set_setting("custom_post_text", message.text)
        await message.answer("✅ تم الحفظ", reply_markup=main_admin_markup())
    admin_state.pop(uid, None)

@dp.message_handler(lambda m: admin_state.get(m.from_user.id) == "ban")
async def handle_ban(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip()
    try:
        if text.lower().startswith("unban"):
            target = int(text.split()[1])
            unban_user(target)
            await message.answer(f"✅ تم فك الحظر عن {target}", reply_markup=main_admin_markup())
        else:
            target = int(text)
            if target in ADMIN_IDS:
                await message.answer("❌ لا يمكن حظر مشرف", reply_markup=main_admin_markup())
                admin_state.pop(uid, None)
                return
            ban_user(target)
            await message.answer(f"🚫 تم حظر {target}", reply_markup=main_admin_markup())
    except:
        await message.answer("❌ صيغة خاطئة\nاستخدم: ID أو unban ID", reply_markup=main_admin_markup())
    admin_state.pop(uid, None)

@dp.message_handler(lambda m: admin_state.get(m.from_user.id) == "broadcast")
async def handle_broadcast(message: types.Message):
    uid = message.from_user.id
    users = get_all_users()
    if not users:
        await message.answer("⚠️ لا يوجد مستخدمين", reply_markup=main_admin_markup())
        admin_state.pop(uid, None)
        return
    ok = 0
    for tuid in users:
        try:
            if not is_banned(tuid):
                await bot.send_message(tuid, message.text)
                ok += 1
                await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"📣 تم الإرسال\n✅ {ok} من {len(users)}", reply_markup=main_admin_markup())
    admin_state.pop(uid, None)

@dp.message_handler(lambda m: admin_state.get(m.from_user.id) == "add_channel")
async def handle_add_channel_text(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip().replace(' ', '')
    if text.endswith('-'): text = text[:-1]
    channel_id = None
    try:
        if text.startswith('-') and text[1:].isdigit():
            channel_id = int(text)
        elif text.isdigit() and len(text) > 8:
            channel_id = int(f"-100{text}")
        elif 't.me/' in text:
            username = text.split('t.me/')[-1].split('/')[0].split('?')[0].lstrip('@')
            chat = await bot.get_chat(f"@{username}")
            channel_id = chat.id
        elif text.startswith('@'):
            chat = await bot.get_chat(text)
            channel_id = chat.id
        if not channel_id:
            await message.answer("❌ صيغة غير صحيحة!\n\n• `-1001234567890`\n• `https://t.me/username`\n• `@username`")
            admin_state.pop(uid, None)
            return
        chat = await bot.get_chat(channel_id)
        channel_name = chat.title
        channel_link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(channel_id).replace('-100', '')}"
        add_channel(channel_id, channel_name)
        await message.answer(f"✅ *تمت إضافة القناة بنجاح!*\n📡 الاسم: `{channel_name}`\n🔗 {channel_link}\n🆔 `{channel_id}`", reply_markup=main_admin_markup())
    except Exception as e:
        await message.answer(f"❌ خطأ: {str(e)[:150]}\nتأكد من أن البوت مشرف في القناة!", reply_markup=main_admin_markup())
    admin_state.pop(uid, None)

@dp.message_handler(lambda m: edit_file_state.get(m.from_user.id))
async def handle_edit_description(message: types.Message):
    uid = message.from_user.id
    file_id = edit_file_state.get(uid)
    description = message.text.strip()
    if description.lower() in ["تخطي", "حذف"]:
        update_description(file_id, None)
        await message.answer("✅ تم حذف الوصف", reply_markup=main_admin_markup())
    else:
        update_description(file_id, description)
        await message.answer(f"✅ تم حفظ الوصف:\n```\n{description}\n```", reply_markup=main_admin_markup())
    edit_file_state.pop(uid, None)

# ---------- Button list handler ----------

@dp.message_handler(lambda m: m.text in BTN_LIST)
async def handle_btns(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    act = message.text
    await delete_msg(message.chat.id, message.message_id)

    if act == "📤 رفع ملفات":
        admin_state[uid] = "uploading_new"
        clear_configs()
        await message.answer("📂 وضع الرفع (جديد - مسح القديم)\n📎 أرسل الملفات:", reply_markup=back_markup())

    elif act == "📤 إضافة ملفات":
        admin_state[uid] = "uploading_add"
        await message.answer(f"📂 وضع الرفع (إضافة)\n📁 الموجود: {get_configs_count()} ملف\n📎 أرسل الملفات:", reply_markup=back_markup())

    elif act == "✅ إنهاء":
        admin_state.pop(uid, None)
        count = get_configs_count()
        await message.answer(f"✅ تم الإنهاء\n📊 إجمالي الملفات: {count}", reply_markup=main_admin_markup())
        if count > 0:
            channels = get_active_channels()
            if channels:
                text = get_setting("custom_post_text", "") or f"""⚡️ *تم تجديد الكونفيجات!*

📂 عدد الملفات: `{count}` ملف
🚀 سرعة عالية | ⏳ محدد المدة

━━━━━━━━━━━━━━━
📌 *طريقة الاستلام:*

1️⃣ ادعمنا بضغطة ❤️
2️⃣ اضغط 📥 لاستلام الملفات
━━━━━━━━━━━━━━━
⚠️ سارع قبل انتهاء الصلاحية!"""
                success = 0
                for ch in channels:
                    try:
                        sent = await safe_send_message(ch['id'], text, channel_markup(0))
                        if sent:
                            add_post(sent.message_id, text)
                            success += 1
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"خطأ في النشر: {e}")
                await message.answer(f"📢 تم النشر تلقائياً في {success} قناة ✅", reply_markup=main_admin_markup())

    elif act == "🗑️ حذف الملفات":
        clear_configs()
        await message.answer("🗑️ تم حذف جميع الملفات", reply_markup=main_admin_markup())

    elif act == "📊 الإحصائيات":
        await message.answer(get_stats_text(), reply_markup=main_admin_markup())

    elif act == "👥 المتفاعلين":
        likers = get_all_likers()
        await message.answer(f"👥 عدد المتفاعلين: {len(likers)}" if likers else "⚠️ لا يوجد متفاعلين", reply_markup=main_admin_markup())

    elif act == "📢 نشر بالقنوات":
        if not get_all_configs():
            await message.answer("⚠️ لا توجد ملفات", reply_markup=main_admin_markup())
            return
        await message.answer("📢 اختر القناة للنشر:", reply_markup=publish_channels_markup())

    elif act == "✏️ تخصيص البوست":
        admin_state[uid] = "custom_post"
        current = get_setting("custom_post_text", "")
        await message.answer(f"✏️ النص الحالي:\n{current or '(افتراضي)'}\nأرسل النص الجديد أو 'reset'", reply_markup=back_markup())

    elif act == "📣 إذاعة جماعية":
        admin_state[uid] = "broadcast"
        await message.answer(f"📣 أرسل الرسالة\n👥 المستهدفون: {get_users_count()}", reply_markup=back_markup())

    elif act == "🚫 بان مستخدم":
        admin_state[uid] = "ban"
        await message.answer("🚫 أرسل ID\nللفك: unban ID", reply_markup=back_markup())

    elif act == "📡 إدارة القنوات":
        await message.answer("📡 إدارة القنوات", reply_markup=channels_manager_markup())

    elif act == "✏️ تعديل وصف ملف":
        await message.answer("📂 اختر الملف لتعديل وصفه:", reply_markup=files_list_markup())

    elif act == "🏆 أفضل الملفات":
        await message.answer("🏆 *أفضل الملفات تقييماً*", reply_markup=top_files_markup())

    elif act == "⏰ ضبط التقرير":
        current = get_setting("daily_report_time", "20:00")
        await message.answer(f"⏰ وقت التقرير الحالي: `{current}`\nاختر وقتاً جديداً:", reply_markup=set_report_time_markup())

    elif act == "📿 إعدادات الأدعية":
        await message.answer("📿 *إعدادات الأدعية التلقائية*", reply_markup=dua_settings_markup())

    elif act == "🔐 الاشتراك الإجباري":
        await message.answer("🔐 *إعدادات الاشتراك الإجباري*", reply_markup=subscription_settings_markup())

    elif act == "📈 إحصائيات متقدمة":
        await message.answer("📈 *الإحصائيات المتقدمة*", reply_markup=advanced_stats_markup())

    elif act == "🔄 تصفير شامل":
        clear_configs()
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM likes')
        c.execute('DELETE FROM downloads')
        c.execute('DELETE FROM ratings')
        conn.commit()
        conn.close()
        await message.answer("🔄 تم تصفير شامل للملفات واللايكات والتحميلات والتقييمات", reply_markup=main_admin_markup())

    elif act == "🧹 تصفير الإحصائيات":
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM likes')
        c.execute('DELETE FROM downloads')
        c.execute('DELETE FROM ratings')
        c.execute('UPDATE configs SET download_count = 0, rating = 0, rating_count = 0')
        conn.commit()
        conn.close()
        await message.answer("🧹 *تم تصفير الإحصائيات بنجاح!*", reply_markup=main_admin_markup())

    elif act == "❌ إخفاء":
        await message.answer("🔒 تم الإخفاء - /admin للظهور", reply_markup=ReplyKeyboardRemove())

# ---------- Media upload ----------

@dp.message_handler(content_types=['document', 'photo', 'video', 'audio', 'voice', 'animation', 'sticker'])
async def handle_all_media(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    if admin_state.get(uid) not in ["uploading_new", "uploading_add"]:
        await message.answer("⚠️ اضغط رفع ملفات أولاً")
        return

    ct = message.content_type
    if ct == 'document':
        fid = message.document.file_id
        fname = message.document.file_name or "file"
        ftype = "document"
    elif ct == 'photo':
        fid = message.photo[-1].file_id
        fname = f"image_{int(time.time())}.jpg"
        ftype = "photo"
    elif ct == 'video':
        fid = message.video.file_id
        fname = message.video.file_name or f"video_{int(time.time())}.mp4"
        ftype = "video"
    elif ct == 'audio':
        fid = message.audio.file_id
        fname = message.audio.file_name or f"audio_{int(time.time())}.mp3"
        ftype = "audio"
    elif ct == 'voice':
        fid = message.voice.file_id
        fname = f"voice_{int(time.time())}.ogg"
        ftype = "voice"
    elif ct == 'animation':
        fid = message.animation.file_id
        fname = f"gif_{int(time.time())}.gif"
        ftype = "animation"
    elif ct == 'sticker':
        fid = message.sticker.file_id
        fname = f"sticker_{int(time.time())}.webp"
        ftype = "sticker"
    else:
        return

    add_config(fid, fname, None, ftype)
    icons = {"photo":"🖼️","video":"🎥","audio":"🎵","voice":"🎤","animation":"🎞️","sticker":"🏷️"}
    await message.answer(f"✅ {icons.get(ftype, '📄')} تم رفع: {fname}\n📊 الإجمالي: {get_configs_count()}")

# ---------- Callbacks ----------

@dp.callback_query_handler(lambda c: True)
async def handle_callbacks(call: types.CallbackQuery):
    uid = call.from_user.id
    data = call.data

    if data == "back_panel":
        await call.message.edit_text("👑 لوحة التحكم", reply_markup=main_admin_markup())
        await call.answer()

    elif data == "refresh_channels":
        updated = 0
        for ch in get_all_channels():
            if await update_channel_name_in_db(ch['id']):
                updated += 1
            await asyncio.sleep(0.1)
        await call.answer(f"✅ تم تحديث {updated} قناة")
        await call.message.edit_text("📡 إدارة القنوات", reply_markup=channels_manager_markup())

    elif data == "add_channel":
        admin_state[uid] = "add_channel"
        await call.message.edit_text("➕ أرسل معرف القناة أو رابطها\n\n• `-1001234567890`\n• `https://t.me/username`\n• `@username`", reply_markup=back_markup())
        await call.answer()

    elif data == "toggle_subscription":
        current = get_setting("require_subscription", True)
        set_setting("require_subscription", not current)
        status = "🟢 مفعل" if not current else "🔴 معطل"
        await call.answer(f"🔐 تم {'تفعيل' if not current else 'تعطيل'} الاشتراك الإجباري")
        await call.message.edit_text(f"🔐 *إعدادات الاشتراك الإجباري*\n📌 الحالة: {status}", reply_markup=subscription_settings_markup())

    elif data.startswith("files_page_"):
        page = int(data.replace("files_page_", ""))
        await call.message.edit_text("📂 اختر الملف لتعديل وصفه:", reply_markup=files_list_markup(page))
        await call.answer()

    elif data == "back_to_files":
        await call.message.edit_text("📂 اختر الملف لتعديل وصفه:", reply_markup=files_list_markup())
        await call.answer()

    elif data.startswith("edit_file_"):
        file_id = int(data.replace("edit_file_", ""))
        fi = get_file_by_id(file_id)
        if fi:
            stars = "⭐" * int(round(fi['rating'])) if fi['rating'] > 0 else "📝"
            desc_text = f"\n📝 الوصف:\n```\n{fi['description']}\n```" if fi['description'] else "\n📝 لا يوجد وصف"
            await call.message.edit_text(
                f"📄 *{fi['name']}*{desc_text}\n{stars} التقييم: {fi['rating']:.1f} ({fi['rating_count']} صوت) | 📥 {fi['download_count']}",
                reply_markup=edit_file_markup(file_id, fi['description'], fi['rating'], fi['rating_count'], fi['download_count'])
            )
        await call.answer()

    elif data.startswith("edit_desc_"):
        file_id = int(data.replace("edit_desc_", ""))
        edit_file_state[uid] = file_id
        await call.message.edit_text("✏️ أرسل الوصف الجديد\nأو اكتب 'تخطي' أو 'حذف' لإزالة الوصف", reply_markup=back_markup())
        await call.answer()

    elif data.startswith("delete_desc_"):
        file_id = int(data.replace("delete_desc_", ""))
        update_description(file_id, None)
        await call.answer("🗑️ تم حذف الوصف")
        fi = get_file_by_id(file_id)
        stars = "⭐" * int(round(fi['rating'])) if fi['rating'] > 0 else "📝"
        await call.message.edit_text(
            f"📄 *{fi['name']}*\n📝 لا يوجد وصف\n{stars} التقييم: {fi['rating']:.1f} ({fi['rating_count']} صوت) | 📥 {fi['download_count']}",
            reply_markup=edit_file_markup(file_id, None, fi['rating'], fi['rating_count'], fi['download_count'])
        )

    elif data.startswith("del_channel_"):
        channel_id = int(data.replace("del_channel_", ""))
        delete_channel(channel_id)
        await call.answer("🗑️ تم حذف القناة")
        await call.message.edit_text("📡 إدارة القنوات", reply_markup=channels_manager_markup())

    elif data.startswith("view_file_"):
        file_id = int(data.replace("view_file_", ""))
        fi = get_file_by_id(file_id)
        if fi:
            stars = "⭐" * int(round(fi['rating']))
            text = f"📄 *{fi['name']}*\n{stars} التقييم: {fi['rating']:.1f} ({fi['rating_count']} صوت)\n📥 التحميلات: {fi['download_count']}"
            if fi.get('description'):
                text += f"\n📝\n```\n{fi['description']}\n```"
            await call.answer()
            await bot.send_message(uid, text)

    elif data.startswith("set_time_"):
        new_time = data.replace("set_time_", "")
        set_setting("daily_report_time", new_time)
        schedule_jobs()
        await call.answer(f"✅ تم ضبط وقت التقرير إلى {new_time}")
        await call.message.edit_text(f"⏰ تم ضبط الوقت إلى {new_time}", reply_markup=main_admin_markup())

    elif data == "toggle_dua":
        current = get_setting("auto_dua_enabled", True)
        set_setting("auto_dua_enabled", not current)
        status = "🟢 مفعل" if not current else "🔴 معطل"
        await call.answer(f"📿 تم {'تفعيل' if not current else 'تعطيل'} الأدعية")
        await call.message.edit_text(f"📿 *إعدادات الأدعية*\n📌 الحالة: {status}", reply_markup=dua_settings_markup())

    elif data == "stats_active_now":
        count = get_active_users_count(60)
        await call.message.edit_text(f"🟢 *المستخدمون النشطون الآن*\n━━━━━━━━━━━━━━━━━━━\n📊 العدد: `{count}`", reply_markup=advanced_stats_markup())
        await call.answer()

    elif data == "stats_weekly_chart":
        weekly = get_weekly_new_users()
        max_c = max([d['count'] for d in weekly]) if weekly else 0
        chart = "📊 *المستخدمون الجدد خلال الأسبوع*\n━━━━━━━━━━━━━━━━━━━\n```\n"
        for d in weekly:
            bar = "█" * (int((d['count'] / max_c) * 20) if max_c > 0 else 0)
            bar += "░" * (20 - len(bar))
            chart += f"{d['day'][:6]:6} │ {bar} {d['count']}\n"
        chart += "```"
        await call.message.edit_text(chart, reply_markup=advanced_stats_markup())
        await call.answer()

    elif data == "stats_peak_hours":
        peak = get_peak_hours()
        text = "⏰ *أكثر الأوقات نشاطاً*\n━━━━━━━━━━━━━━━━━━━\n"
        if peak:
            for hour, count in peak:
                h = "12 صباحاً" if hour == 0 else f"{hour} صباحاً" if hour < 12 else "12 ظهراً" if hour == 12 else f"{hour-12} مساءً"
                text += f"\n{h}: {count} نشاط"
        else:
            text += "⚠️ لا توجد بيانات كافية"
        await call.message.edit_text(text, reply_markup=advanced_stats_markup())
        await call.answer()

    elif data == "stats_top_downloads":
        top = get_most_downloaded_files(10)
        text = "🏆 *أكثر الملفات تحميلاً*\n━━━━━━━━━━━━━━━━━━━\n"
        if top and top[0]['count'] > 0:
            for i, f in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📄"
                text += f"\n{i}. {medal} {f['name'][:35]}\n   📥 {f['count']} تحميل"
        else:
            text += "⚠️ لا توجد تحميلات بعد"
        await call.message.edit_text(text, reply_markup=advanced_stats_markup())
        await call.answer()

    elif data.startswith("publish_"):
        channel_id = data.replace("publish_", "")
        configs = get_all_configs()
        if not configs:
            await call.answer("⚠️ لا توجد ملفات", show_alert=True)
            return
        text = get_setting("custom_post_text", "") or f"""⚡️ *تم تجديد الكونفيجات!*

📂 عدد الملفات: `{len(configs)}` ملف
🚀 سرعة عالية | ⏳ محدد المدة

━━━━━━━━━━━━━━━
📌 *طريقة الاستلام:*

1️⃣ ادعمنا بضغطة ❤️
2️⃣ اضغط 📥 لاستلام الملفات
━━━━━━━━━━━━━━━
⚠️ سارع قبل انتهاء الصلاحية!"""

        if channel_id == "all":
            channels = get_active_channels()
            if not channels:
                await call.answer("⚠️ لا توجد قنوات", show_alert=True)
                return
            await call.answer("📢 جاري النشر...")
            success = failed = 0
            for ch in channels:
                try:
                    sent = await safe_send_message(ch['id'], text, channel_markup(0))
                    if sent:
                        add_post(sent.message_id, text)
                        success += 1
                    else:
                        failed += 1
                    await asyncio.sleep(0.5)
                except:
                    failed += 1
            result = f"✅ تم النشر في {success} قناة"
            if failed: result += f"\n⚠️ فشل في {failed} قناة"
            await call.message.edit_text(result, reply_markup=main_admin_markup())
        else:
            try:
                sent = await safe_send_message(int(channel_id), text, channel_markup(0))
                if sent:
                    add_post(sent.message_id, text)
                    await call.answer("✅ تم النشر بنجاح!")
                    await call.message.edit_text("✅ تم النشر!", reply_markup=main_admin_markup())
            except Exception as e:
                await call.answer(f"❌ خطأ: {str(e)[:50]}", show_alert=True)

    elif data.startswith("rate_file_"):
        parts = data.split("_")
        if len(parts) >= 4:
            file_id = int(parts[2])
            rating = int(parts[3])
            if add_rating(uid, file_id, rating):
                await call.answer(f"✅ شكراً! تم تسجيل تقييمك ({rating} ⭐)")
            else:
                await call.answer("⚠️ لا يمكنك التقييم", show_alert=True)

    elif data == "do_like":
        if is_banned(uid):
            await call.answer("🚫 محظور", show_alert=True)
            return
        if get_setting("require_subscription", True):
            missing_msg = await get_missing_channels_message(uid)
            if missing_msg:
                await call.answer("⚠️ اشترك في القنوات أولاً!", show_alert=False)
                await bot.send_message(uid, missing_msg)
                return
        if add_like(uid, call.message.message_id):
            await call.answer("✅ شكراً لدعمك! ❤️\nيمكنك الآن الضغط على 📥")
            mk = InlineKeyboardMarkup(row_width=2)
            mk.row(
                InlineKeyboardButton(f"❤️ تفاعل ({get_likes_count(call.message.message_id)})", callback_data="do_like"),
                InlineKeyboardButton(f"📥 استلم ({get_post_downloads(call.message.message_id)})", url=f"https://t.me/{BOT_USERNAME}?start=download")
            )
            try:
                await call.message.edit_reply_markup(reply_markup=mk)
            except:
                pass
        else:
            await call.answer("⚠️ سبق أن تفاعلت! ❤️\nاضغط 📥 الآن", show_alert=True)

    elif data == "noop":
        await call.answer()

# ============================================================
# SECTION 9: FLASK KEEP-ALIVE
# ============================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "<h2>🤖 Bot Running</h2>"

def keep_alive():
    port = int(os.environ.get("FLASK_PORT", 5050))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False), daemon=True).start()

# ============================================================
# SECTION 10: MAIN
# ============================================================

async def on_startup(dispatcher):
    global BOT_USERNAME, _loop
    _loop = asyncio.get_event_loop()
    try:
        me = await bot.get_me()
        BOT_USERNAME = me.username
        print(f"✅ Bot: @{me.username}")
    except Exception as e:
        print(f"⚠️ Error: {e}")
    init_db()
    schedule_jobs()
    Thread(target=run_scheduler, daemon=True).start()
    print(f"✅ Admins: {ADMIN_IDS}")
    print("🚀 RUNNING!")

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 STARTING BOT - aiogram 2.25.1")
    print("=" * 60)
    keep_alive()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
