import datetime
import os
import random
import threading
import time

from flask import Flask
import pytz
import telebot

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8226177508:AAEhEO8PwgrvY-mYA8hCJhB5Vag977iay_E")
CHANNEL_ID = -1002814870264

WIN_STICKER_ID = ("CAACAgUAAxkBAAER4h1qo_aDagqTDFeZsvVfXRWkHL1gMQACxiAAAlKt-FSX-5IBfGtcPz0E")

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
# PERIOD & PREDICTION GENERATION
# ============================================================

def get_current_period_info():
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(tz)
    total_minutes = now.hour * 60 + now.minute
    sequence = total_minutes + 1
    date_string = now.strftime("%Y%m%d")
    return f"{date_string}100{sequence:04d}"


def generate_prediction():
    number = random.randint(0, 9)

    if number in [2, 4, 6, 8]:
        color = "🔴 RED"
        emoji = "🔴"
    elif number in [1, 3, 7, 9]:
        color = "🟢 GREEN"
        emoji = "🟢"
    elif number == 0:
        color = "🔴🟣 RED + VIOLET"
        emoji = "🔴"
    else:
        color = "🟢🟣 GREEN + VIOLET"
        emoji = "🟢"

    size = "📈 BIG" if number >= 5 else "📉 SMALL"
    return number, color, size, emoji


def create_prediction():
    global total_rounds_played
    period = get_current_period_info()
    number, color, size, emoji = generate_prediction()

    prediction = {
        "period": period,
        "number": number,
        "color": color,
        "size": size,
        "emoji": emoji,
        "created_at": time.time(),
    }

    with state_lock:
        total_rounds_played += 1
        predictions[period] = prediction
        level = current_level

        if len(predictions) > 20:
            oldest_period = next(iter(predictions))
            del predictions[oldest_period]

    return prediction, level

# ============================================================
# TELEGRAM DISPATCH & RESULT CHECKER
# ============================================================

def send_prediction():
    try:
        prediction, level = create_prediction()

        period = prediction["period"]
        number = prediction["number"]
        color = prediction["color"]
        size = prediction["size"]
        emoji = prediction["emoji"]

        message = (
            "🔥 <b>WINGO 1 MIN</b> 🔥\n\n"
            f"📅 <b>PERIOD NUMBER:</b> <code>{period}</code>\n\n"
            f"📊 <b>BIG/SMALL:</b> {size}\n"
            f"🎨 <b>COLOR:</b> {color}\n"
            f"🔢 <b>NUMBER:</b> {emoji} <code>{number}</code> {emoji}\n\n"
            f"📈 <b>LEVEL:</b> <code>{level}</code>\n\n"
            "📩 <b>DM FOR MORE DETAILS:</b>\n"
            "@Maayan001\n"
            "@anonymoustele01\n"
            "@madexgurl\n\n"
            "⚠️ <i>Random game guess — not guaranteed.</i>"
        )

        bot.send_message(
            CHANNEL_ID,
            message,
            parse_mode="HTML"
        )
        print(f"Prediction sent: {period}")

    except Exception as error:
        print(f"Prediction error: {error}")


def evaluate_previous_period(expired_period):
    """Evaluates result and sends Win/Loss sticker to channel."""
    try:
        with state_lock:
            if expired_period in predictions:
                pred = predictions[expired_period]
                actual_number = random.randint(0, 9)
                
                predicted_is_big = pred["number"] >= 5
                actual_is_big = actual_number >= 5

                is_win = (predicted_is_big == actual_is_big)

                if is_win:
                    bot.send_sticker(CHANNEL_ID, WIN_STICKER_ID)
                    print(f"Period {expired_period}: WIN sticker sent.")
                else:
                    bot.send_sticker(CHANNEL_ID, LOSS_STICKER_ID)
                    print(f"Period {expired_period}: LOSS sticker sent.")
    except Exception as error:
        print(f"Evaluation error: {error}")


def automatic_prediction_loop():
    print("Automatic prediction system started.")
    last_period = None

    while True:
        try:
            current_period = get_current_period_info()

            if current_period != last_period:
                if last_period is not None:
                    evaluate_previous_period(last_period)

                send_prediction()
                last_period = current_period

            time.sleep(2)

        except Exception as error:
            print(f"Automatic loop error: {error}")
            time.sleep(5)

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):
    text = (
        "🤖 <b>Wingo Channel Bot</b>\n\n"
        "🟢 Bot is online.\n\n"
        "The bot is configured to automatically post predictions and result stickers."
    )
    bot.reply_to(message, text, parse_mode="HTML")


@bot.message_handler(commands=["help"])
def help_command(message):
    text = (
        "❓ <b>BOT HELP</b>\n\n"
        "Automatic predictions and win/loss stickers are active."
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
        "🟢 Status: <code>ONLINE</code>\n"
        f"⏳ Uptime: <code>{hours}h {minutes}m</code>\n"
        f"📈 Level: <code>{level}</code>\n"
        f"🔄 Rounds: <code>{rounds}</code>\n"
        f"📢 Channel ID: <code>{CHANNEL_ID}</code>"
    )
    bot.reply_to(message, text, parse_mode="HTML")

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route("/")
def home():
    return "Telegram Channel Bot is online."


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
