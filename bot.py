import os
import json
import logging
import asyncio
import requests
import threading
from flask import Flask
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, constants
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Render portini aniqlash (Web Service uchun)
app_flask = Flask(__name__)

@app_flask.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= SOZLAMALAR =================
API_KEY = os.environ.get("API_KEY", "8701423585:AAFH17u9SEbt8HPf80OwoLuOMF0EksNFkYk")
OWNER_ID = int(os.environ.get("OWNER_ID", "6581120108"))

# Kataloglarni yaratish
BASE_DIR = Path(__file__).parent
USERS_DIR = BASE_DIR / "users"
STEPS_DIR = BASE_DIR / "step"
INFO_FILE = BASE_DIR / "info.txt"

USERS_DIR.mkdir(exist_ok=True)
STEPS_DIR.mkdir(exist_ok=True)

# === Klaviaturalar ===
MAIN_MENU = [
    ["🖼 Photo Ai"],
    ["ℹ️ Ma’lumot", "📬 Murojaat"]
]

ADMIN_MENU = [
    ["🖼 Photo Ai"],
    ["ℹ️ Ma’lumot", "📬 Murojaat"],
    ["🛠 Admin Panel"]
]

BACK_KB = [["◀️ Ortga"]]

def get_menu_kb(chat_id):
    kb = ADMIN_MENU if chat_id == OWNER_ID else MAIN_MENU
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def get_back_kb():
    return ReplyKeyboardMarkup(BACK_KB, resize_keyboard=True)

# === Handlerlar ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    name = update.effective_user.first_name
    
    # Userni saqlash
    user_file = USERS_DIR / f"{cid}.json"
    if not user_file.exists():
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump({"id": cid}, f)
    
    # Stepni tozalash
    step_file = STEPS_DIR / f"{cid}.step"
    if step_file.exists():
        step_file.unlink()
    
    await update.message.reply_text(
        f"<b>👋 Salom, {name}!</b>\n\nMenyu tanlang 👇",
        parse_mode=constants.ParseMode.HTML,
        reply_markup=get_menu_kb(cid)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    text = update.message.text
    logger.info(f"Incoming message from {cid}: {text}")
    
    # Ortga qaytish
    if text == "◀️ Ortga":
        await start(update, context)
        return

    # Photo Ai bo'limiga kirish
    if text == "🖼 Photo Ai":
        with open(STEPS_DIR / f"{cid}.step", "w", encoding="utf-8") as f:
            f.write("photo_ai")
        await update.message.reply_text(
            "<b>🖼 Tasvir tavsifini yuboring:</b>\n\n(Masalan: <i>Beautiful nature sunset</i>)",
            parse_mode=constants.ParseMode.HTML,
            reply_markup=get_back_kb()
        )
        return

    # Ma'lumot
    if text == "ℹ️ Ma’lumot":
        info_text = "Bot hozirda ishchi holatda!"
        if INFO_FILE.exists():
            with open(INFO_FILE, "r", encoding="utf-8") as f:
                info_text = f.read()
        await update.message.reply_text(
            f"ℹ️ <b>Bot haqida ma'lumot:</b>\n\n{info_text}",
            parse_mode=constants.ParseMode.HTML
        )
        return

    # Murojaat
    if text == "📬 Murojaat":
        inline_kb = [
            [InlineKeyboardButton("👨‍💻 Dasturchi", url="https://t.me/OdiDev")],
            [InlineKeyboardButton("📢 Kanal", url="https://t.me/Aibilan_1")]
        ]
        await update.message.reply_text(
            "Bog'lanish uchun quyidagilarni tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_kb)
        )
        return

    # Admin Panel
    if text == "🛠 Admin Panel" and cid == OWNER_ID:
        count = len(list(USERS_DIR.glob("*.json")))
        admin_inline = [
            [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton("📤 Xabar yuborish", callback_data="send")],
            [InlineKeyboardButton("📝 Ma'lumotni tahrirlash", callback_data="edit_info")]
        ]
        await update.message.reply_text(
            f"<b>🛠 Admin Panel</b>\n\nFoydalanuvchilar soni: {count} ta",
            parse_mode=constants.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(admin_inline)
        )
        return

    # Step-larni tekshirish
    step_file = STEPS_DIR / f"{cid}.step"
    if step_file.exists():
        with open(step_file, "r", encoding="utf-8") as f:
            step = f.read().strip()
        
        if step == "photo_ai":
            if len(text) > 4000:
                await update.message.reply_text("❌ Tasvir tavsifi juda uzun (maksimal 4000 belgi).")
                return

            await update.message.reply_chat_action(constants.ChatAction.UPLOAD_PHOTO)
            img_url = f"https://img-gen.wwiw.uz/?prompt={requests.utils.quote(text)}"
            
            # Telegram caption limiti 1024 belgi. Tavsifni qisqartirib chiqaramiz.
            display_text = text if len(text) < 900 else text[:900] + "..."
            
            try:
                await update.message.reply_photo(
                    photo=img_url,
                    caption=f"🖼 <b>Sizning so'rovingiz:</b>\n{display_text}",
                    parse_mode=constants.ParseMode.HTML
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Xatolik yuz berdi: {e}")
            return

        if step == "broadcast" and cid == OWNER_ID:
            step_file.unlink()
            users = list(USERS_DIR.glob("*.json"))
            success_count = 0
            for u in users:
                try:
                    target_cid = int(u.stem)
                    await context.bot.send_message(chat_id=target_cid, text=text)
                    success_count += 1
                except:
                    pass
            await update.message.reply_text(
                f"✅ Xabar {success_count} ta foydalanuvchiga yuborildi.",
                reply_markup=get_menu_kb(cid)
            )
            return

        if step == "edit_info" and cid == OWNER_ID:
            with open(INFO_FILE, "w", encoding="utf-8") as f:
                f.write(text)
            step_file.unlink()
            await update.message.reply_text(
                "✅ Ma'lumot bo'limi yangilandi!",
                reply_markup=get_menu_kb(cid)
            )
            return

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cid = query.from_user.id
    data = query.data
    
    if cid != OWNER_ID:
        await query.answer("Siz admin emassiz!")
        return
        
    if data == "stats":
        count = len(list(USERS_DIR.glob("*.json")))
        await query.answer(f"Jami a'zolar: {count}", show_alert=True)
    
    elif data == "send":
        with open(STEPS_DIR / f"{cid}.step", "w", encoding="utf-8") as f:
            f.write("broadcast")
        await query.message.delete()
        await context.bot.send_message(
            chat_id=cid,
            text="📤 <b>Barcha foydalanuvchilarga yuboriladigan xabarni yozing:</b>",
            parse_mode=constants.ParseMode.HTML,
            reply_markup=get_back_kb()
        )
        
    elif data == "edit_info":
        with open(STEPS_DIR / f"{cid}.step", "w", encoding="utf-8") as f:
            f.write("edit_info")
        await query.message.delete()
        await context.bot.send_message(
            chat_id=cid,
            text="📝 <b>Yangi 'Ma'lumot' matnini yuboring:</b>",
            parse_mode=constants.ParseMode.HTML,
            reply_markup=get_back_kb()
        )

def main():
    # Flask-ni alohida thread-da ishga tushirish
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(API_KEY).read_timeout(30).connect_timeout(30).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print("Bot ishga tushdi (Python Polling...)...")
    app.run_polling()

if __name__ == "__main__":
    main()
