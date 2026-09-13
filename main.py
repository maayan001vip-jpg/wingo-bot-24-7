import datetime
import os
import threading
import time
import random

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

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

current_level = 1
total_rounds_played = 0

predictions = {}
results = {}
history = []

bot_start_time = time.time()
state_lock = threading.Lock()

MAX_HISTORY = 50
MAX_PREDICTIONS = 50


# ============================================================
# PERIOD (UTC SYNCED FOR WINGO)
# ============================================================

def get_time_based_period():
    tz = pytz.utc
    now = datetime.datetime.now(tz)
    total_minutes = now.hour * 60 + now.minute
    sequence = total_minutes + 1
    date_string = now.strftime("%Y%m%d")
    return f"{date_string}10001{sequence:04d}"


# ============================================================
# BIG / SMALL & COLOR
# ============================================================

def get_size(number):
    return "BIG" if number >= 5 else "SMALL"

def get_color(number):
    if number in [2, 4, 6, 8]:
        return "RED"
    elif number in [1, 3, 7, 9]:
        return "GREEN"
    elif number == 0:
        return "RED + VIOLET"
    else:
        return "GREEN + VIOLET"


# ============================================================
# HISTORY & PATTERNS
# ============================================================

def add_to_history(number):
    with state_lock:
        history.append(number)
        if len(history) > MAX_HISTORY:
            history.pop(0)

def size_history():
    with state_lock:
        data = list(history)
    return [
        "B" if get_size(x) == "BIG" else "S"
        for x in data
    ]

def get_runs(sequence):
    if not sequence:
        return []
    runs = []
    current = sequence[0]
    count = 1
    for value in sequence[1:]:
        if value == current:
            count += 1
        else:
            runs.append((current, count))
            current = value
            count = 1
    runs.append((current, count))
    return runs

def detect_patterns(sequence):
    patterns = []
    if len(sequence) < 3:
        return ["Not enough history"]

    if len(sequence) >= 4:
        x = sequence[-4:]
        if x[0] == x[2] and x[1] == x[3] and x[0] != x[1]:
            patterns.append("ABAB")
        if x[0] == x[1] and x[2] == x[3] and x[0] != x[2]:
            patterns.append("AABB")
        if x[0] == x[1] and x[1] == x[2] and x[2] != x[3]:
            patterns.append("AAAB")
        if x[0] != x[1] and x[1] == x[2] and x[2] == x[3]:
            patterns.append("ABBB")

    if len(sequence) >= 3 and len(set(sequence[-3:])) == 1:
        patterns.append("TRIPLE TREND")

    if len(sequence) >= 4 and len(set(sequence[-4:])) == 1:
        patterns.append("QUAD TREND")

    if len(sequence) >= 5 and len(set(sequence[-5:])) == 1:
        patterns.append("LONG TREND")

    if not patterns:
        patterns.append("MIXED")

    return patterns

def analyze_history():
    sequence = size_history()
    if not sequence:
        return None
    big_count = sequence.count("B")
    small_count = sequence.count("S")
    runs = get_runs(sequence)
    last_value, last_run = runs[-1]
    patterns = detect_patterns(sequence)
    return {
        "total": len(sequence),
        "big": big_count,
        "small": small_count,
        "last": last_value,
        "last_run": last_run,
        "patterns": patterns
    }


# ============================================================
# AUTOMATIC PREDICTION GENERATOR (FIXED)
# ============================================================

def send_prediction(period):
    global total_rounds_played
    try:
        size = random.choice(["BIG", "SMALL"])
        with state_lock:
            total_rounds_played += 1
            predictions[period] = {"size": size, "created_at": time.time()}
            level = current_level

            if len(predictions) > MAX_PREDICTIONS:
                oldest = next(iter(predictions))
                del predictions[oldest]

        message = (
            "👑 𝕍𝔼𝔼ℝ 𝔾𝔸𝕄𝔼 👑\n"
            "🔥 <b>WINGO 1 MIN</b> 🔥\n\n"
            f"📅 <b>PERIOD NUMBER:</b> <code>{period}</code>\n\n"
            f"📊 <b>PREDICTION:</b> <b>{size}</b>\n"
            f"📈 <b>LEVEL:</b> <code>{level} / 8</code>\n\n"
            "📩 <b>DM FOR MORE DETAILS:</b>\n"
            "@Maayan001\n"
            "@anonymoustele01\n"
            "@madexgurl"
        )

        bot.send_message(CHANNEL_ID, message, parse_mode="HTML")
        print(f"Prediction sent successfully: {period} ({size}) - Level {level}")
    except Exception as error:
        print(f"Prediction error: {error}")

def automatic_prediction_loop():
    print("Automatic prediction loop started.")
    last_period = None
    
    # Send first prediction immediately on startup
    try:
        initial_period = get_time_based_period()
        send_prediction(initial_period)
        last_period = initial_period
    except Exception as e:
        print(f"Initial prediction error: {e}")

    while True:
        try:
            current_period = get_time_based_period()
            if current_period != last_period:
                send_prediction(current_period)
                last_period = current_period
        except Exception as error:
            print(f"Loop error: {error}")
        time.sleep(2)


# ============================================================
# COMMANDS (ALL OPEN)
# ============================================================

@bot.message_handler(commands=["add"])
def add_command(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Usage:\n/add NUMBER\n\nExample:\n/add 7")
            return
        number = int(parts[1])
        if number < 0 or number > 9:
            bot.reply_to(message, "❌ Number must be 0 to 9.")
            return

        add_to_history(number)
        bot.reply_to(
            message,
            (
                "✅ <b>RESULT ADDED</b>\n\n"
                f"🔢 Number: <code>{number}</code>\n"
                f"📊 Size: <b>{get_size(number)}</b>\n"
                f"🎨 Color: <b>{get_color(number)}</b>"
            ),
            parse_mode="HTML"
        )
    except ValueError:
        bot.reply_to(message, "❌ Correct number kudu.\nExample: /add 7")


@bot.message_handler(commands=["result"])
def result_command(message):
    global current_level
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(
                message,
                (
                    "Usage:\n"
                    "/result PERIOD NUMBER\n\n"
                    "Example:\n"
                    "/result 20260914100010001 7"
                )
            )
            return

        period = parts[1]
        number = int(parts[2])

        if number < 0 or number > 9:
            bot.reply_to(message, "❌ Number must be 0 to 9.")
            return

        with state_lock:
            if period not in predictions:
                bot.reply_to(message, "❌ Prediction record not found.")
                return

            if period in results:
                bot.reply_to(message, "⚠️ This period already processed.")
                return

            prediction = predictions[period]
            predicted_size = prediction["size"]
            actual_size = get_size(number)

            is_win = predicted_size == actual_size
            results[period] = {
                "number": number,
                "size": actual_size,
                "win": is_win,
                "time": time.time()
            }

            if is_win:
                current_level = 1
            else:
                current_level += 1
                if current_level > 8:
                    current_level = 1

        add_to_history(number)
        status = "WIN 🏆" if is_win else "LOSS ❌"

        text = (
            "╔════════════════════╗\n"
            "     📊 <b>RESULT</b>\n"
            "╚════════════════════╝\n\n"
            f"📅 Period: <code>{period}</code>\n"
            f"🎯 Recorded size: <b>{predicted_size}</b>\n"
            f"🔢 Result: <code>{number}</code>\n"
            f"📊 Actual size: <b>{actual_size}</b>\n"
            f"🎨 Color: <b>{get_color(number)}</b>\n\n"
            f"🏆 Status: <b>{status}</b>\n"
            f"📈 Level: <b>{current_level}/8</b>"
        )

        bot.reply_to(message, text, parse_mode="HTML")

        if is_win and WIN_STICKER_ID:
            try:
                bot.send_sticker(CHANNEL_ID, WIN_STICKER_ID)
            except Exception as error:
                print("Sticker error:", error)

    except ValueError:
        bot.reply_to(message, "❌ Number correct-ah kudu.")


# ============================================================
# GENERAL COMMANDS
# ============================================================

@bot.message_handler(commands=["history"])
def history_command(message):
    with state_lock:
        data = list(history)
    if not data:
        bot.reply_to(message, "❌ No history available.")
        return

    recent = data[-20:]
    lines = [
        f"{i}. {number} | {get_size(number)} | {get_color(number)}"
        for i, number in enumerate(recent, 1)
    ]
    text = "📋 <b>RECENT HISTORY</b>\n\n" + "\n".join(lines)
    bot.reply_to(message, text, parse_mode="HTML")


@bot.message_handler(commands=["analysis"])
def analysis_command(message):
    data = analyze_history()
    if not data:
        bot.reply_to(message, "❌ History empty.\nUse /add NUMBER")
        return

    patterns = ", ".join(data["patterns"])
    text = (
        "╔════════════════════╗\n"
        "      🔍 <b>ANALYSIS</b>\n"
        "╚════════════════════╝\n\n"
        f"📊 Total: <code>{data['total']}</code>\n"
        f"📈 BIG: <code>{data['big']}</code>\n"
        f"📉 SMALL: <code>{data['small']}</code>\n\n"
        f"🔁 Last: <b>{data['last']}</b>\n"
        f"🔢 Run: <code>{data['last_run']}</code>\n\n"
        f"🔍 Patterns:\n<code>{patterns}</code>"
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
        history_count = len(history)
        prediction_count = len(predictions)

    text = (
        "📊 <b>BOT STATUS</b>\n\n"
        "🟢 Status: <code>ONLINE</code>\n"
        f"⏳ Uptime: <code>{hours}h {minutes}m</code>\n"
        f"📈 Level: <code>{level}/8</code>\n"
        f"🎯 Records: <code>{rounds}</code>\n"
        f"📋 History: <code>{history_count}</code>\n"
        f"🗂 Predictions: <code>{prediction_count}</code>"
    )
    bot.reply_to(message, text, parse_mode="HTML")


@bot.message_handler(commands=["start", "help"])
def start_command(message):
    text = (
        "🤖 <b>VEER GAME BOT</b>\n\n"
        "🟢 Bot is online and ready.\n\n"
        "<b>Commands:</b>\n"
        "/status - Bot status\n"
        "/history - Recent history\n"
        "/analysis - Pattern analysis\n"
        "/add NUMBER - Add result\n"
        "/result PERIOD NUMBER - Process result"
    )
    bot.reply_to(message, text, parse_mode="HTML")


# ============================================================
# FLASK & RUNNER
# ============================================================

@app.route("/")
def home():
    return "Bot is active."

def run_bot():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as error:
            print("Telegram error:", error)
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=automatic_prediction_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
