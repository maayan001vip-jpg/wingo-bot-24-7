import datetime
import os
import random
import threading
import time
import requests

from flask import Flask
import pytz
import telebot

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8226177508:AAEhEO8PwgrvY-mYA8hCJhB5Vag977iay_E")
CHANNEL_ID = -1002814870264

WIN_STICKER_ID = "CAACAgUAAxkBAAEG_9dqpxaKXtzfwrbW4Na4DTUzBCMvUQACahIAAvYiyVZikUGUoRZynz0E"

# ============================================================
# INITIALIZATION
# ============================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

current_level = 1
total_rounds_played = 0
predictions = {}
last_prediction_size = None
bot_start_time = time.time()
state_lock = threading.Lock()

# ============================================================
# PERIOD & API FETCHING
# ============================================================

def get_time_based_period():
    tz = pytz.utc
    now = datetime.datetime.now(tz)
    total_minutes = now.hour * 60 + now.minute
    sequence = total_minutes + 1
    date_string = now.strftime("%Y%m%d")
    return f"{date_string}10001{sequence:04d}"

def fetch_latest_game_result():
    """Fetches real result from Wingo API using secure headers."""
    url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={int(time.time()*1000)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://veergame11.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data.get("code") == 0:
            latest_record = data["data"]["list"][0]
            issue_number = str(latest_record["issueNumber"])
            number = int(latest_record["number"])
            # Wingo rule: 0-4 is SMALL, 5-9 is BIG
            actual_size = "📈 BIG" if number >= 5 else "📉 SMALL"
            return issue_number, actual_size
    except Exception as e:
        print(f"API Error: {e}")
    return None, None

# ============================================================
# TELEGRAM DISPATCH
# ============================================================

def send_prediction(period):
    global total_rounds_played, last_prediction_size
    try:
        options = ["📈 BIG", "📉 SMALL"]
        if last_prediction_size in options:
            options.remove(last_prediction_size)

        size = random.choice(options)
        last_prediction_size = size

        with state_lock:
            total_rounds_played += 1
            predictions[period] = {"size": size, "created_at": time.time()}
            level = current_level

            if len(predictions) > 20:
                oldest = next(iter(predictions))
                del predictions[oldest]

        message = (
            "👑 𝕍𝔼𝔼ℝ 𝔾𝔸𝕄𝔼 👑\n"
            "🔥 <b>WINGO 1 MIN</b> 🔥\n\n"
            f"📅 <b>PERIOD NUMBER:</b> <code>{period}</code>\n\n"
            f"📊 <b>PREDICTION:</b> {size}\n"
            f"📈 <b>LEVEL:</b> <code>{level} / 8</code>\n\n"
            "📩 <b>DM FOR MORE DETAILS:</b>\n"
            "@Maayan001\n"
            "@anonymoustele01\n"
            "@madexgurl"
        )

        bot.send_message(CHANNEL_ID, message, parse_mode="HTML")
        print(f"Prediction sent: {period} ({size}) - Level {level}")
    except Exception as error:
        print(f"Prediction error: {error}")


def automatic_prediction_loop():
    global current_level
    print("API-Synced prediction loop started.")
    last_period = None
    last_checked_issue = None

    while True:
        try:
            current_period = get_time_based_period()

            # 1. Fetch real result from the API to check previous wins
            latest_issue, actual_size = fetch_latest_game_result()

            if latest_issue and latest_issue != last_checked_issue:
                with state_lock:
                    if latest_issue in predictions:
                        pred_size = predictions[latest_issue]["size"]
                        is_win = (pred_size == actual_size)

                        if is_win:
                            bot.send_sticker(CHANNEL_ID, WIN_STICKER_ID)
                            print(f"Period {latest_issue}: REAL WIN! Level reset to 1.")
                            current_level = 1
                        else:
                            print(f"Period {latest_issue}: LOSS. Level incremented.")
                            if current_level < 8:
                                current_level += 1
                            else:
                                current_level = 1

                last_checked_issue = latest_issue

            # 2. Send new prediction for the current active period
            if current_period != last_period:
                send_prediction(current_period)
                last_period = current_period

        except Exception as error:
            print(f"Loop error: {error}")

        time.sleep(3)

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

@bot.message_handler(commands=["start", "help"])
def start_command(message):
    text = (
        "🤖 <b>Veer Game Bot</b>\n\n"
        "🟢 Bot is online and synced with Wingo API."
    )
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=["status"])
def status_command(message):
    uptime = int(time.time() - bot_start_time)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    with state_lock:
        level = current_level

    text = (
        "📊 <b>BOT STATUS</b>\n\n"
        "🟢 Status: <code>ONLINE (API SYNCED)</code>\n"
        f"⏳ Uptime: <code>{hours}h {minutes}m</code>\n"
        f"📈 Current Level: <code>{level} / 8</code>\n"
        f"📢 Channel ID: <code>{CHANNEL_ID}</code>"
    )
    bot.reply_to(message, text, parse_mode="HTML")

# ============================================================
# FLASK & EXECUTION
# ============================================================

@app.route("/")
def home():
    return "Bot is active."

def run_bot():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=automatic_prediction_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
