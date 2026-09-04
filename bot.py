import telebot
from telebot import types
import sqlite3
import re
import time
from datetime import datetime, timedelta
import os
import random
from html import escape

BOT_TOKEN = "8718352884:AAHKzLuJPAfeC8Ov93rqrQrmY-ertAH1GSM"
OWNER_ID = 8687306834
DB_PATH = "telegram_research.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        username TEXT,
        welcome_msg TEXT,
        goodbye_msg TEXT,
        warn_limit INTEGER DEFAULT 3,
        anti_spam INTEGER DEFAULT 1,
        filter_on INTEGER DEFAULT 1,
        welcome_on INTEGER DEFAULT 1,
        goodbye_on INTEGER DEFAULT 1,
        suggest_on INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        warns INTEGER DEFAULT 0,
        muted_until TIMESTAMP,
        banned INTEGER DEFAULT 0,
        warn_reason TEXT,
        mute_reason TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        keyword TEXT,
        response TEXT,
        created_by INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        name TEXT,
        content TEXT,
        created_by INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        user_id INTEGER,
        username TEXT,
        suggestion TEXT,
        status TEXT DEFAULT 'pending'
    )''')
    conn.commit()
    conn.close()

init_db()

def get_settings(chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
    data = c.fetchone()
    conn.close()
    return data

def set_setting(chat_id, key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE groups SET {key} = ? WHERE chat_id = ?", (value, chat_id))
    conn.commit()
    conn.close()

def create_group(chat_id, title, username=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (chat_id, title, username) VALUES (?, ?, ?)", (chat_id, title, username))
    conn.commit()
    conn.close()

def get_user(user_id, chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    data = c.fetchone()
    conn.close()
    return data

def create_user(user_id, chat_id, first_name, last_name=None, username=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, chat_id, first_name, last_name, username) VALUES (?, ?, ?, ?, ?)",
              (user_id, chat_id, first_name, last_name, username))
    conn.commit()
    conn.close()

def add_warn(user_id, chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    c.execute("SELECT warns FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    warns = c.fetchone()[0]
    conn.close()
    return warns

def reset_warns(user_id, chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET warns = 0, warn_reason = NULL WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def set_mute(user_id, chat_id, duration):
    conn = get_db()
    c = conn.cursor()
    muted_until = datetime.now() + timedelta(seconds=duration)
    c.execute("UPDATE users SET muted_until = ? WHERE user_id = ? AND chat_id = ?", (muted_until, user_id, chat_id))
    conn.commit()
    conn.close()
    return muted_until

def set_unmute(user_id, chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET muted_until = NULL, mute_reason = NULL WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def add_filter(chat_id, keyword, response, user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO filters (chat_id, keyword, response, created_by) VALUES (?, ?, ?, ?)",
              (chat_id, keyword.lower(), response, user_id))
    conn.commit()
    conn.close()

def get_filters(chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM filters WHERE chat_id = ?", (chat_id,))
    data = c.fetchall()
    conn.close()
    return data

def del_filter(chat_id, keyword):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM filters WHERE chat_id = ? AND keyword = ?", (chat_id, keyword.lower()))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def add_note(chat_id, name, content, user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO notes (chat_id, name, content, created_by) VALUES (?, ?, ?, ?)",
              (chat_id, name.lower(), content, user_id))
    conn.commit()
    conn.close()

def get_note(chat_id, name):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE chat_id = ? AND name = ?", (chat_id, name.lower()))
    data = c.fetchone()
    conn.close()
    return data

def get_notes(chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE chat_id = ?", (chat_id,))
    data = c.fetchall()
    conn.close()
    return data

def del_note(chat_id, name):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE chat_id = ? AND name = ?", (chat_id, name.lower()))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def add_suggestion(chat_id, user_id, username, suggestion):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO suggestions (chat_id, user_id, username, suggestion) VALUES (?, ?, ?, ?)",
              (chat_id, user_id, username, suggestion))
    conn.commit()
    conn.close()

def is_admin(user_id, chat_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_owner(user_id):
    return user_id == OWNER_ID

def escape(text):
    if text is None: return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def fmt(seconds):
    if seconds >= 86400: return f"{seconds//86400}d"
    if seconds >= 3600: return f"{seconds//3600}h"
    if seconds >= 60: return f"{seconds//60}m"
    return f"{seconds}s"

def resolve_user(message, target):
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        return (user.id, user.first_name, user.last_name, user.username)
    
    if target and target.startswith('@'):
        username = target[1:]
        try:
            u = bot.get_chat(username)
            return (u.id, u.first_name, u.last_name, u.username)
        except:
            pass
        try:
            members = bot.get_chat_members(message.chat.id, limit=200)
            for m in members:
                if m.user.username and m.user.username.lower() == username.lower():
                    u = m.user
                    return (u.id, u.first_name, u.last_name, u.username)
        except:
            pass
        return None
    
    if target and target.isdigit():
        try:
            uid = int(target)
            u = bot.get_chat(uid)
            return (u.id, u.first_name, u.last_name, u.username)
        except:
            pass
    
    if target:
        try:
            members = bot.get_chat_members(message.chat.id, limit=200)
            for m in members:
                if m.user.first_name and target.lower() in m.user.first_name.lower():
                    u = m.user
                    return (u.id, u.first_name, u.last_name, u.username)
        except:
            pass
    
    return None

def mention_user(name, uid):
    return f"<a href='tg://user?id={uid}'>{escape(name)}</a>"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
BOT_NAME = "IllusionEyes"

@bot.message_handler(commands=['start'])
def start_cmd(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("👥 Admins", callback_data="admins"),
        types.InlineKeyboardButton("🟢 Online", callback_data="online"),
        types.InlineKeyboardButton("📊 Group Info", callback_data="groupinfo"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        types.InlineKeyboardButton("🔰 Warnings", callback_data="warn"),
        types.InlineKeyboardButton("🔇 Mute", callback_data="mute"),
        types.InlineKeyboardButton("🚫 Ban/Kick", callback_data="ban"),
        types.InlineKeyboardButton("📝 Filters", callback_data="filters"),
        types.InlineKeyboardButton("📋 Notes", callback_data="notes"),
        types.InlineKeyboardButton("💡 Suggest", callback_data="suggest"),
        types.InlineKeyboardButton("👑 Promote", callback_data="promote"),
        types.InlineKeyboardButton("❓ Help", callback_data="help")
    ]
    keyboard.add(*buttons)
    
    text = (
        f"✨ <b>{BOT_NAME}</b> ✨\n"
        "╔══════════════════════════╗\n"
        "║  🌟 Ultimate Group Control  ║\n"
        "╚══════════════════════════╝\n\n"
        "📌 Add me to your group & make me admin\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔰 Available Commands:\n"
        "  /admins  •  /online  •  /groupinfo\n"
        "  /settings  •  /warn  •  /mute\n"
        "  /ban  •  /unban  •  /kick\n"
        "  /filter  •  /note  •  /suggest\n"
        "  /promote  •  /demote  •  /stats\n"
        "  /welcome  •  /goodbye  •  /unmute\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Just type / and command name"
    )
    bot.reply_to(message, text, reply_markup=keyboard)

@bot.message_handler(commands=['admins'])
def admins_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    admins = bot.get_chat_administrators(message.chat.id)
    text = "👑 Admins\n╔══════════════════════════╗\n"
    for a in admins:
        if a.user.is_bot: continue
        role = "👑 Owner" if a.status == 'creator' else "🛡️ Admin"
        name = f"{a.user.first_name} {a.user.last_name or ''}".strip()
        text += f"║ {role} : {escape(name)}\n"
    text += "╚══════════════════════════╝"
    bot.reply_to(message, text)

@bot.message_handler(commands=['online'])
def online_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    msg = bot.reply_to(message, "⏳ Fetching online members...")
    try:
        members = bot.get_chat_members(message.chat.id)
        online = []
        total = 0
        for m in members:
            if m.status in ['creator', 'administrator']: continue
            if not m.user.is_bot:
                total += 1
                if m.status == 'member':
                    online.append(f"🟢 {escape(m.user.first_name)}")
        
        text = "🟢 Online Members\n╔══════════════════════════╗\n"
        text += f"║ 📊 Online: {len(online)}\n║ 👥 Total: {total}\n╠══════════════════════════╣\n"
        if online:
            text += "\n".join([f"║ {x}" for x in online[:15]])
            if len(online) > 15:
                text += f"\n║ ... & {len(online)-15} more"
        else:
            text += "║ 📭 No online members"
        text += "\n╚══════════════════════════╝"
        bot.edit_message_text(text, message.chat.id, msg.message_id)
    except:
        bot.edit_message_text("⚠️ Error fetching online members.", message.chat.id, msg.message_id)

@bot.message_handler(commands=['groupinfo'])
def groupinfo_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    chat = bot.get_chat(message.chat.id)
    count = bot.get_chat_member_count(message.chat.id)
    admins = bot.get_chat_administrators(message.chat.id)
    text = (
        "📊 Group Info\n"
        "╔══════════════════════════╗\n"
        f"║ 📛 {escape(chat.title)}\n"
        f"║ 🆔 <code>{chat.id}</code>\n"
        f"║ 👤 @{chat.username if chat.username else 'N/A'}\n"
        f"║ 👥 {count} members\n"
        f"║ 🛡️ {len(admins)} admins\n"
        "╚══════════════════════════╝"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['settings'])
def settings_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can view settings.")
    
    s = get_settings(message.chat.id)
    if not s:
        create_group(message.chat.id, message.chat.title, message.chat.username)
        s = get_settings(message.chat.id)
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("✅ Welcome" if s['welcome_on'] else "❌ Welcome", callback_data="toggle_welcome_on"),
        types.InlineKeyboardButton("✅ Goodbye" if s['goodbye_on'] else "❌ Goodbye", callback_data="toggle_goodbye_on"),
        types.InlineKeyboardButton("✅ Anti-Spam" if s['anti_spam'] else "❌ Anti-Spam", callback_data="toggle_anti_spam"),
        types.InlineKeyboardButton("✅ Filters" if s['filter_on'] else "❌ Filters", callback_data="toggle_filter_on"),
        types.InlineKeyboardButton("✅ Suggestions" if s['suggest_on'] else "❌ Suggestions", callback_data="toggle_suggest_on"),
        types.InlineKeyboardButton("⚡ Warn Limit", callback_data="warnlimit"),
        types.InlineKeyboardButton("⬅️ Back", callback_data="menu_back")
    ]
    keyboard.add(*buttons)
    
    text = (
        "⚙️ Settings\n"
        "╔══════════════════════════╗\n"
        f"║ Welcome    : {'✅' if s['welcome_on'] else '❌'}\n"
        f"║ Goodbye    : {'✅' if s['goodbye_on'] else '❌'}\n"
        f"║ Anti-Spam  : {'✅' if s['anti_spam'] else '❌'}\n"
        f"║ Filters    : {'✅' if s['filter_on'] else '❌'}\n"
        f"║ Suggestions: {'✅' if s['suggest_on'] else '❌'}\n"
        f"║ Warn Limit : {s['warn_limit']}\n"
        "╚══════════════════════════╝\n"
        "💡 Tap buttons to toggle settings"
    )
    bot.reply_to(message, text, reply_markup=keyboard)

@bot.message_handler(commands=['warn'])
def warn_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can warn users.")
    
    args = message.text.split(maxsplit=1)
    target = args[1].strip() if len(args) > 1 else None
    user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    if uid == message.from_user.id:
        return bot.reply_to(message, "❌ You cannot warn yourself.")
    
    try:
        target_admin = bot.get_chat_member(message.chat.id, uid)
        if target_admin.status in ['administrator', 'creator']:
            return bot.reply_to(message, "❌ You cannot warn an admin.")
    except:
        pass
    
    create_user(uid, message.chat.id, first_name, last_name, username)
    warns = add_warn(uid, message.chat.id)
    s = get_settings(message.chat.id)
    limit = s['warn_limit'] if s else 3
    
    text = (
        "⚠️ Warned\n"
        "╔══════════════════════════╗\n"
        f"║ 👤 {mention_user(first_name, uid)}\n"
        f"║ 📊 {warns}/{limit}\n"
    )
    if warns >= limit:
        try:
            bot.ban_chat_member(message.chat.id, uid)
            text += "╠══════════════════════════╣\n"
            text += "║ 🚫 Banned!\n"
            reset_warns(uid, message.chat.id)
        except:
            text += "╠══════════════════════════╣\n"
            text += "║ ⚠️ Can't ban - check perms\n"
    text += "╚══════════════════════════╝"
    bot.reply_to(message, text)

@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can mute users.")
    
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /mute @username 5m\n\nYou can also reply to a user's message with /mute 5m")
    
    target = args[1].strip()
    dur_str = args[2].strip() if len(args) > 2 else "5m"
    
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    if uid == message.from_user.id:
        return bot.reply_to(message, "❌ You cannot mute yourself.")
    
    try:
        target_admin = bot.get_chat_member(message.chat.id, uid)
        if target_admin.status in ['administrator', 'creator']:
            return bot.reply_to(message, "❌ You cannot mute an admin.")
    except:
        pass
    
    seconds = 0
    if dur_str.endswith('s'): seconds = int(dur_str[:-1])
    elif dur_str.endswith('m'): seconds = int(dur_str[:-1]) * 60
    elif dur_str.endswith('h'): seconds = int(dur_str[:-1]) * 3600
    elif dur_str.endswith('d'): seconds = int(dur_str[:-1]) * 86400
    else:
        try: seconds = int(dur_str)
        except: seconds = 300
    
    create_user(uid, message.chat.id, first_name, last_name, username)
    muted_until = set_mute(uid, message.chat.id, seconds)
    
    try:
        perms = types.ChatPermissions(can_send_messages=False)
        bot.restrict_chat_member(message.chat.id, uid, perms, until_date=muted_until)
        text = (
            "🔇 Muted\n"
            "╔══════════════════════════╗\n"
            f"║ 👤 {mention_user(first_name, uid)}\n"
            f"║ ⏱️ {fmt(seconds)}\n"
            "╚══════════════════════════╝"
        )
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ Could not mute: {e}")

@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can unmute users.")
    
    args = message.text.split(maxsplit=1)
    target = args[1].strip() if len(args) > 1 else None
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    set_unmute(uid, message.chat.id)
    try:
        perms = types.ChatPermissions(can_send_messages=True, can_send_media=True, can_send_other_messages=True, can_add_web_page_previews=True)
        bot.restrict_chat_member(message.chat.id, uid, perms)
        bot.reply_to(message, f"🔊 {escape(first_name)} has been unmuted.")
    except:
        bot.reply_to(message, "❌ Could not unmute user.")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can ban users.")
    
    args = message.text.split(maxsplit=1)
    target = args[1].strip() if len(args) > 1 else None
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    try:
        bot.ban_chat_member(message.chat.id, uid)
        bot.reply_to(message, f"🚫 {escape(first_name)} has been banned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Could not ban: {e}")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can unban users.")
    
    args = message.text.split(maxsplit=1)
    target = args[1].strip() if len(args) > 1 else None
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    try:
        bot.unban_chat_member(message.chat.id, uid)
        bot.reply_to(message, f"✅ {escape(first_name)} has been unbanned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Could not unban: {e}")

@bot.message_handler(commands=['kick'])
def kick_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can kick users.")
    
    args = message.text.split(maxsplit=1)
    target = args[1].strip() if len(args) > 1 else None
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    try:
        bot.ban_chat_member(message.chat.id, uid)
        bot.unban_chat_member(message.chat.id, uid)
        bot.reply_to(message, f"👢 {escape(first_name)} has been kicked.")
    except Exception as e:
        bot.reply_to(message, f"❌ Could not kick: {e}")

@bot.message_handler(commands=['filter'])
def filter_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can add filters.")
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return bot.reply_to(message, "📝 Usage: /filter keyword reply")
    
    word = args[1].strip()
    reply = args[2].strip()
    add_filter(message.chat.id, word, reply, message.from_user.id)
    bot.reply_to(message, f"✅ Filter added: {word}")

@bot.message_handler(commands=['filters'])
def filters_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    filters = get_filters(message.chat.id)
    if not filters:
        return bot.reply_to(message, "📭 No filters in this group.")
    
    text = "📝 Filters\n╔══════════════════════════╗\n"
    for f in filters[:20]:
        text += f"║ • {escape(f['keyword'])}\n"
    if len(filters) > 20:
        text += f"║ ... & {len(filters)-20} more"
    text += f"\n╚══════════════════════════╝\n📊 Total: {len(filters)}"
    bot.reply_to(message, text)

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can remove filters.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /stop keyword")
    
    if del_filter(message.chat.id, args[1].strip()):
        bot.reply_to(message, f"✅ Removed filter: {args[1].strip()}")
    else:
        bot.reply_to(message, f"❌ Filter not found.")

@bot.message_handler(commands=['note'])
def note_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can add notes.")
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return bot.reply_to(message, "📝 Usage: /note name content")
    
    name = args[1].strip()
    content = args[2].strip()
    add_note(message.chat.id, name, content, message.from_user.id)
    bot.reply_to(message, f"✅ Note added: {name}")

@bot.message_handler(commands=['notes'])
def notes_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    notes = get_notes(message.chat.id)
    if not notes:
        return bot.reply_to(message, "📭 No notes in this group.")
    
    text = "📋 Notes\n╔══════════════════════════╗\n"
    for n in notes[:20]:
        text += f"║ • {escape(n['name'])}\n"
    if len(notes) > 20:
        text += f"║ ... & {len(notes)-20} more"
    text += f"\n╚══════════════════════════╝\n📊 Total: {len(notes)}"
    bot.reply_to(message, text)

@bot.message_handler(commands=['get'])
def get_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /get note_name")
    
    note = get_note(message.chat.id, args[1].strip())
    if note:
        bot.reply_to(message, f"📋 {escape(note['name'])}\n╔══════════════════════════╗\n{note['content']}\n╚══════════════════════════╝")
    else:
        bot.reply_to(message, "❌ Note not found.")

@bot.message_handler(commands=['delnote'])
def delnote_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can delete notes.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /delnote note_name")
    
    if del_note(message.chat.id, args[1].strip()):
        bot.reply_to(message, f"✅ Deleted note: {args[1].strip()}")
    else:
        bot.reply_to(message, "❌ Note not found.")

@bot.message_handler(commands=['suggest'])
def suggest_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    s = get_settings(message.chat.id)
    if not s or not s['suggest_on']:
        return bot.reply_to(message, "❌ Suggestions are disabled in this group.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /suggest your suggestion")
    
    add_suggestion(message.chat.id, message.from_user.id, message.from_user.username, args[1].strip())
    bot.reply_to(message, "💡 Thank you! Your suggestion has been submitted.")

@bot.message_handler(commands=['promote'])
def promote_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only the bot owner can promote users.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /promote @username")
    
    target = args[1].strip()
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    try:
        bot.promote_chat_member(message.chat.id, uid, can_change_info=True, can_delete_messages=True, can_invite_users=True, can_restrict_members=True, can_pin_messages=True)
        bot.reply_to(message, f"👑 {escape(first_name)} has been promoted to admin!")
    except Exception as e:
        bot.reply_to(message, f"❌ Could not promote: {e}")

@bot.message_handler(commands=['demote'])
def demote_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only the bot owner can demote users.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /demote @username")
    
    target = args[1].strip()
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    try:
        bot.promote_chat_member(message.chat.id, uid, can_change_info=False, can_delete_messages=False, can_invite_users=False, can_restrict_members=False, can_pin_messages=False)
        bot.reply_to(message, f"🔽 {escape(first_name)} has been demoted.")
    except Exception as e:
        bot.reply_to(message, f"❌ Could not demote: {e}")

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT chat_id) FROM groups")
    groups = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM filters")
    filters = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM notes")
    notes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM suggestions")
    suggestions = c.fetchone()[0]
    conn.close()
    
    text = (
        "📊 Statistics\n"
        "╔══════════════════════════╗\n"
        f"║ 👥 Users : {users}\n"
        f"║ 💬 Groups: {groups}\n"
        f"║ 📝 Filters: {filters}\n"
        f"║ 📋 Notes : {notes}\n"
        f"║ 💡 Ideas : {suggestions}\n"
        "╚══════════════════════════╝"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['welcome'])
def setwelcome_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can set welcome message.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /welcome Welcome {mention}!\n\nVariables: {mention}, {name}, {group}")
    
    msg = args[1].strip()
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE groups SET welcome_msg = ? WHERE chat_id = ?", (msg, message.chat.id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Welcome message set!\n\n📝 {msg}")

@bot.message_handler(commands=['goodbye'])
def setgoodbye_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can set goodbye message.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /goodbye Goodbye {mention}!\n\nVariables: {mention}, {name}, {group}")
    
    msg = args[1].strip()
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE groups SET goodbye_msg = ? WHERE chat_id = ?", (msg, message.chat.id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Goodbye message set!\n\n📝 {msg}")

@bot.message_handler(commands=['warns'])
def warns_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    
    args = message.text.split(maxsplit=1)
    target = args[1].strip() if len(args) > 1 else None
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    user = get_user(uid, message.chat.id)
    if not user or user['warns'] == 0:
        bot.reply_to(message, f"✅ {escape(first_name)} has no warnings.")
    else:
        text = "⚠️ Warnings\n╔══════════════════════════╗\n"
        text += f"║ 👤 {escape(first_name)}\n"
        text += f"║ 📊 {user['warns']}\n"
        text += "╚══════════════════════════╝"
        bot.reply_to(message, text)

@bot.message_handler(commands=['resetwarns'])
def resetwarns_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can reset warnings.")
    
    args = message.text.split(maxsplit=1)
    target = args[1].strip() if len(args) > 1 else None
    if not target and message.reply_to_message:
        user = message.reply_to_message.from_user
        user_info = (user.id, user.first_name, user.last_name, user.username)
    else:
        user_info = resolve_user(message, target)
    if not user_info:
        return bot.reply_to(message, "❌ Could not find that user. Please use @username, numeric ID, or reply to a user's message.")
    
    uid, first_name, last_name, username = user_info
    reset_warns(uid, message.chat.id)
    bot.reply_to(message, f"✅ {escape(first_name)} warnings have been reset.")

@bot.message_handler(commands=['setwarnlimit'])
def setwarn_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return bot.reply_to(message, "❌ Use this command in a group.")
    if not is_admin(message.from_user.id, message.chat.id) and not is_owner(message.from_user.id):
        return bot.reply_to(message, "⛔ Only admins can set warn limit.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "📝 Usage: /setwarnlimit <1-10>")
    
    try:
        limit = int(args[1].strip())
        if limit < 1 or limit > 10:
            return bot.reply_to(message, "❌ Please enter a number between 1 and 10.")
    except:
        return bot.reply_to(message, "❌ Please enter a valid number.")
    
    set_setting(message.chat.id, "warn_limit", limit)
    bot.reply_to(message, f"✅ Warn limit set to {limit}.")

@bot.message_handler(content_types=['new_chat_members'])
def welcome_handler(message):
    s = get_settings(message.chat.id)
    if not s or not s['welcome_on']:
        return
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        create_user(member.id, message.chat.id, member.first_name, member.last_name, member.username)
        msg = s['welcome_msg']
        if msg:
            msg = msg.replace('{mention}', f"<a href='tg://user?id={member.id}'>{escape(member.first_name)}</a>")
            msg = msg.replace('{name}', member.first_name)
            msg = msg.replace('{group}', message.chat.title)
            bot.send_message(message.chat.id, msg)
        else:
            bot.send_message(message.chat.id, f"👋 Welcome! <a href='tg://user?id={member.id}'>{escape(member.first_name)}</a>")

@bot.message_handler(content_types=['left_chat_member'])
def goodbye_handler(message):
    s = get_settings(message.chat.id)
    if not s or not s['goodbye_on']:
        return
    member = message.left_chat_member
    if member.is_bot:
        return
    msg = s['goodbye_msg']
    if msg:
        msg = msg.replace('{mention}', f"<a href='tg://user?id={member.id}'>{escape(member.first_name)}</a>")
        msg = msg.replace('{name}', member.first_name)
        msg = msg.replace('{group}', message.chat.title)
        bot.send_message(message.chat.id, msg)
    else:
        bot.send_message(message.chat.id, f"👋 Goodbye! <a href='tg://user?id={member.id}'>{escape(member.first_name)}</a>")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def auto_filter(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    s = get_settings(message.chat.id)
    if not s or not s['filter_on']:
        return
    filters = get_filters(message.chat.id)
    text = message.text.lower()
    for f in filters:
        if f['keyword'] in text:
            bot.reply_to(message, f['response'])
            break

@bot.message_handler(func=lambda m: True, content_types=['text'])
def auto_mute(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    user = get_user(message.from_user.id, message.chat.id)
    if user and user['muted_until']:
        until = datetime.strptime(user['muted_until'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() < until:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
        else:
            set_unmute(message.from_user.id, message.chat.id)
            try:
                perms = types.ChatPermissions(can_send_messages=True, can_send_media=True, can_send_other_messages=True, can_add_web_page_previews=True)
                bot.restrict_chat_member(message.chat.id, message.from_user.id, perms)
            except:
                pass

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    
    if data == "menu_back":
        start_cmd(call.message)
        return
    
    if data.startswith("toggle_"):
        key = data.replace("toggle_", "")
        s = get_settings(call.message.chat.id)
        new_val = 0 if s[key] else 1
        set_setting(call.message.chat.id, key, new_val)
        bot.answer_callback_query(call.id, "✅ Setting toggled!")
        settings_cmd(call.message)
        return
    
    if data == "warnlimit":
        bot.answer_callback_query(call.id, "Use: /setwarnlimit <number>", show_alert=True)
        return
    
    menus = {
        "admins": "👑 Admins list: /admins",
        "online": "🟢 Online members: /online",
        "groupinfo": "📊 Group info: /groupinfo",
        "settings": "⚙️ Settings: /settings",
        "warn": "🔰 Warn commands:\n/warn @user\n/warns @user\n/resetwarns @user",
        "mute": "🔇 Mute commands:\n/mute @user 5m\n/unmute @user",
        "ban": "🚫 Ban/Kick/Unban:\n/ban @user\n/unban @user\n/kick @user",
        "filters": "📝 Filters:\n/filter word reply\n/filters\n/stop word",
        "notes": "📋 Notes:\n/note name text\n/notes\n/get name\n/delnote name",
        "suggest": "💡 Suggestions:\n/suggest your idea",
        "promote": "👑 Promote/Demote:\n/promote @user\n/demote @user",
        "help": "📖 All commands:\n/start, /admins, /online, /groupinfo, /settings, /warn, /mute, /unmute, /ban, /unban, /kick, /filter, /note, /suggest, /promote, /demote, /stats"
    }
    
    if data in menus:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, menus[data])
        return
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def auto_create(message):
    if message.chat.type in ['group', 'supergroup']:
        if not get_settings(message.chat.id):
            create_group(message.chat.id, message.chat.title, message.chat.username)

if __name__ == "__main__":
    print("="*60)
    print(f"✨ {BOT_NAME} STARTED")
    print("="*60)
    print(f"👑 Owner ID: {OWNER_ID}")
    print("="*60)
    print("✅ Bot is running!")
    print("="*60)
    bot.infinity_polling()
