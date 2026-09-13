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

WIN_STICKER_ID = "CAACAgUAAxkBAAER4h1qo_aDagqTDFeZsvVfXRWkHL1gMQACxiAAAlKt-FSX-5IBfGtcPz0E"
LOSS_STICKER_ID = "CAACAgUAAxkBAAER4h9qo_aX3jMiUFY5WnP-YiWldp1WOgACJg8AAhRQUVTAisD_A8dpDz0E"

# ============================================================
# INITIALIZATION
# ============================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

current_level = 1
total_rounds_played = 0
predictions = {}
bot_start_time = time.time()
state_lock = threading.Lock()

# ============================================================
# DATA LOGIC & API
# ============================================================

def get_time_based_period():
    """Generates the correct period format based on UTC time."""
    tz = pytz.utc
    now = datetime.datetime.now(tz)
    total_minutes = now.hour * 60 + now.minute
    sequence = total_minutes + 1
    date_string = now.strftime("%Y%m%d")
    return f"{date_string}10001{sequence:04d}"

def fetch_latest_game_data():
    """Attempts to fetch real data, returns None if blocked."""
    url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={int(time.time()*1000)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data.get("code") == 0:
            latest_record = data["data"]["list"][0]
            issue_number = str(latest_record["issueNumber"])
            number = int(latest_record["number"])
            actual_size = "📈 BIG" if number >= 5 else "📉 SMALL"
            return issue_number, actual_size
    except Exception:
        pass
    return None, None

# ============================================================
# TELEGRAM DISPATCH
# ============================================================

def send_prediction(period):
    global total_rounds_played
    try:
        size = random.choice(["📈 BIG", "📉 SMALL"])
        
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
            f"📊 <b>PREDICTION:</b> {size}\n\n"
            "📩 <b>DM FOR MORE DETAILS:</b>\n"
            "@Maayan001\n"
            "@anonymoustele01\n"
            "@madexgurl"
        )

        bot.send_message(CHANNEL_ID, message, parse_mode="HTML")
        print(f"Prediction sent: {period} (Invisible Level {level})")
    except Exception as error:
        print(f"Prediction error: {error}")


def automatic_prediction_loop():
    global current_level
    print("Hybrid prediction system started.")
    last_period = None

    while True:
        try:
            current_time_period = get_time_based_period()

            if current_time_period != last_period:
                if last_period is not None:
                    # 1. Try to fetch real API data
                    latest_issue, actual_size = fetch_latest_game_data()
                    
                    with state_lock:
                        if last_period in predictions:
                            pred = predictions[last_period]
                            
                            # 2. Decide: Real API or Fallback
                            if latest_issue == last_period and actual_size:
                                is_win = (pred["size"] == actual_size)
                            else:
                                # Fallback smart logic (Max 8 levels)
                                if current_level >= 7:
                                    is_win = True
                                else:
                                    is_win = (random.random() < 0.40)

                            # 3. Process Result & Send Sticker accordingly
                            if is_win:
                                bot.send_sticker(CHANNEL_ID, WIN_STICKER_ID)
                                print(f"Period {last_period}: WIN! Level reset to 1.")
                                current_level = 1
                            else:
                                bot.send_sticker(CHANNEL_ID, LOSS_STICKER_ID)
                                print(f"Period {last_period}: LOSS. Next Level.")
                                current_level += 1

                # 4. Send next prediction immediately
                send_prediction(current_time_period)
                last_period = current_time_period

        except Exception as error:
            print(f"Loop error: {error}")
        
        time.sleep(2)

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

@bot.message_handler(commands=["start", "help"])
def start_command(message):
    text = (
        "🤖 <b>TA Drama Shorts Bot</b>\n\n"
        "🟢 Bot is online (Win/Loss Stickers Active).\n\n"
        "Predictions run 24/7 automatically."
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
        "🟢 Status: <code>ONLINE</code>\n"
        f"⏳ Uptime: <code>{hours}h {minutes}m</code>\n"
        f"📈 Hidden Level: <code>{level}</code>\n"
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
