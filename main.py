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
# REAL-TIME API FETCHING (WITH HEADERS FIX)
# ============================================================

def fetch_latest_game_data():
    """Fetches the actual real-time game result directly from Wingo API using Browser Headers."""
    url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={int(time.time()*1000)}"
    
    # Adding headers to bypass bot protection
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive"
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
        else:
            print(f"API Data Error: {data}")
    except Exception as e:
        print(f"API Fetch Error: {e}")
        
    return None, None

# ============================================================
# TELEGRAM DISPATCH & RESULT CHECKER
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
                oldest_period = next(iter(predictions))
                del predictions[oldest_period]

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

        bot.send_message(
            CHANNEL_ID,
            message,
            parse_mode="HTML"
        )
        print(f"Prediction sent: {period} (Invisible Level {level})")

    except Exception as error:
        print(f"Prediction error: {error}")


def automatic_prediction_loop():
    global current_level
    print("Real-time API prediction system started.")
    last_evaluated_period = None
    current_prediction_period = None

    while True:
        try:
            latest_issue, actual_size = fetch_latest_game_data()

            if latest_issue:
                if latest_issue != last_evaluated_period:
                    with state_lock:
                        if latest_issue in predictions:
                            pred = predictions[latest_issue]
                            is_win = (pred["size"] == actual_size)
                            
                            if is_win:
                                bot.send_sticker(CHANNEL_ID, WIN_STICKER_ID)
                                print(f"Period {latest_issue}: REAL WIN! Level reset to 1.")
                                current_level = 1
                            else:
                                print(f"Period {latest_issue}: REAL LOSS. Moving to Level {current_level + 1}.")
                                current_level += 1
                            
                    last_evaluated_period = latest_issue

                next_period = str(int(latest_issue) + 1)
                
                if next_period != current_prediction_period:
                    send_prediction(next_period)
                    current_prediction_period = next_period
            else:
                print("Waiting for API data...")

        except Exception as error:
            print(f"Automatic loop error: {error}")
        
        time.sleep(3)

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

@bot.message_handler(commands=["start", "help"])
def start_command(message):
    text = (
        "🤖 <b>TA Drama Shorts Bot</b>\n\n"
        "🟢 Bot is online and synced with Real Wingo API.\n\n"
        "Predictions and true WIN stickers run entirely automatically."
    )
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=["status"])
def status_command(message):
    uptime = int(time.time() - bot_start_time)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    with state_lock:
        level = current_level
        rounds = total_rounds_played

    text = (
        "📊 <b>BOT STATUS</b>\n\n"
        "🟢 Status: <code>ONLINE (API SYNCED)</code>\n"
        f"⏳ Uptime: <code>{hours}h {minutes}m</code>\n"
        f"📈 Hidden Level: <code>{level}</code>\n"
        f"🔄 Rounds: <code>{rounds}</code>\n"
        f"📢 Channel ID: <code>{CHANNEL_ID}</code>"
    )
    bot.reply_to(message, text, parse_mode="HTML")

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route("/")
def home():
    return "Telegram Channel Bot is online and synced with API."

@app.route("/health")
def health():
    return {
        "status": "online",
        "uptime": int(time.time() - bot_start_time),
        "rounds": total_rounds_played,
    }

# ============================================================
# POLLING THREAD
# ============================================================

def run_bot():
    while True:
        try:
            print("Telegram polling started.")
            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30,
            )
        except Exception as error:
            print(f"Telegram polling error: {error}")
            time.sleep(5)

# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=automatic_prediction_loop, daemon=True).start()

    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=10000)
