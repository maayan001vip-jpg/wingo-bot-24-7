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
WIN_STICKER_ID = "CAACAgUAAxkBAAEG_8pqpxMonFOAxGhTf1PjBPQzORf2UwACxiAAAlKt-FSX-5IBfGtcPz0E"

# ============================================================
# INITIALIZATION
# ============================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

total_rounds_played = 0
predictions = {}
last_prediction_size = None
history = []  # Stores "B" or "S"
bot_start_time = time.time()
state_lock = threading.Lock()

# ============================================================
# PERIOD & PATTERNS
# ============================================================

def get_time_based_period():
    tz = pytz.utc
    now = datetime.datetime.now(tz)
    total_minutes = now.hour * 60 + now.minute
    sequence = total_minutes + 1
    date_string = now.strftime("%Y%m%d")
    return f"{date_string}10001{sequence:04d}"

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

# ============================================================
# TELEGRAM DISPATCH
# ============================================================

def send_prediction(period):
    global total_rounds_played, last_prediction_size
    try:
        options = ["BIG", "SMALL"]
        if last_prediction_size in options:
            options.remove(last_prediction_size)

        size = random.choice(options)
        last_prediction_size = size

        with state_lock:
            total_rounds_played += 1
            predictions[period] = {"size": size, "created_at": time.time()}

            if len(predictions) > 20:
                oldest = next(iter(predictions))
                del predictions[oldest]

        message = (
            "👑 𝕍𝔼𝔼ℝ 𝔾𝔸𝕄𝔼 👑\n"
            "🔥 <b>WINGO 1 MIN</b> 🔥\n\n"
            f"📅 <b>PERIOD NUMBER:</b> <code>{period}</code>\n\n"
            f"📊 <b>PREDICTION:</b> <b>{size}</b>\n\n"
            "📩 <b>DM FOR MORE DETAILS:</b>\n"
            "@Maayan001\n"
            "@anonymoustele01\n"
            "@madexgurl"
        )

        bot.send_message(CHANNEL_ID, message, parse_mode="HTML")
        print(f"Prediction sent: {period} ({size})")
    except Exception as error:
        print(f"Prediction error: {error}")

def automatic_prediction_loop():
    print("Prediction loop started.")
    last_period = None

    while True:
        try:
            current_period = get_time_based_period()

            if current_period != last_period:
                if last_period is not None:
                    # Simulation: 55% win chance
                    is_win = (random.random() < 0.55)

                    with state_lock:
                        if last_period in predictions:
                            predicted = predictions[last_period]["size"]
                            actual_size = predicted if is_win else ("SMALL" if predicted == "BIG" else "BIG")

                            # Add to history for Pattern logic
                            history.append("B" if actual_size == "BIG" else "S")
                            if len(history) > 50:
                                history.pop(0)

                    if is_win:
                        try:
                            bot.send_sticker(CHANNEL_ID, WIN_STICKER_ID)
                        except Exception:
                            pass
                        print(f"Period {last_period}: WIN!")
                    else:
                        print(f"Period {last_period}: LOSS.")

                send_prediction(current_period)
                last_period = current_period

        except Exception as error:
            print(f"Loop error: {error}")

        time.sleep(2)

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

@bot.message_handler(commands=["start", "help"])
def start_command(message):
    text = (
        "🤖 <b>Veer Game Bot</b>\n\n"
        "🟢 Bot is online and running smoothly.\n\n"
        "<b>Commands:</b>\n"
        "/status - View uptime & records\n"
        "/history - View recent BIG/SMALL results\n"
        "/analysis - View detected trends & patterns"
    )
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=["history"])
def history_command(message):
    with state_lock:
        data = list(history)
    if not data:
        bot.reply_to(message, "❌ No history available yet.")
        return

    recent = data[-20:]
    lines = [f"{i}. {'BIG' if x == 'B' else 'SMALL'}" for i, x in enumerate(recent, 1)]
    text = "📋 <b>RECENT HISTORY</b>\n\n" + "\n".join(lines)
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=["analysis"])
def analysis_command(message):
    with state_lock:
        seq = list(history)

    if len(seq) < 3:
        bot.reply_to(message, "❌ Not enough history for analysis. Wait for a few rounds.")
        return

    big_count = seq.count("B")
    small_count = seq.count("S")
    runs = get_runs(seq)
    last_value = "BIG" if runs[-1][0] == "B" else "SMALL"
    last_run = runs[-1][1]
    patterns = detect_patterns(seq)

    text = (
        "╔════════════════════╗\n"
        "      🔍 <b>PATTERN ANALYSIS</b>\n"
        "╚════════════════════╝\n\n"
        f"📊 Total Rounds: <code>{len(seq)}</code>\n"
        f"📈 BIG Count: <code>{big_count}</code>\n"
        f"📉 SMALL Count: <code>{small_count}</code>\n\n"
        f"🔁 Last Result: <b>{last_value}</b>\n"
        f"🔢 Current Streak: <code>{last_run}</code>\n\n"
        f"🔍 Detected Patterns:\n<code>{', '.join(patterns)}</code>"
    )
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=["status"])
def status_command(message):
    uptime = int(time.time() - bot_start_time)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    text = (
        "📊 <b>BOT STATUS</b>\n\n"
        "🟢 Status: <code>ONLINE</code>\n"
        f"⏳ Uptime: <code>{hours}h {minutes}m</code>\n"
        f"🎯 Records Played: <code>{total_rounds_played}</code>\n"
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
