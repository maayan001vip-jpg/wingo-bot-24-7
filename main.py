import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

# Telegram Sticker File IDs (Replace with your actual Sticker IDs)
STICKER_BIG = "CAACAgIAAxkBAAE..."   
STICKER_SMALL = "CAACAgIAAxkBAAE..." 

# State tracking (Base values setup)
current_period = 20260913100010941
current_level = 1

# Alternate between BIG and SMALL for predictions (or connect your algorithm logic)
def get_next_prediction(period: int) -> str:
    return "BIG" if period % 2 == 0 else "SMALL"

# Command Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends start instructions."""
    msg = (
        "🔥 **WINGO 1 MIN SIGNAL BOT** 🔥\n\n"
        "Use `/signal` to generate the current period signal with sticker.\n"
        "Use `/win` to reset level to 1.\n"
        "Use `/loss` to increase level up to 8."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates prediction signal matching specified format and sends sticker."""
    global current_period, current_level

    prediction = get_next_prediction(current_period)
    pred_text = "📈 BIG" if prediction == "BIG" else "📉 SMALL"

    # Construct the exact requested layout format
    signal_message = (
        f"🔥 WINGO 1 MIN 🔥\n"
        f"📅 PERIOD NUMBER: {current_period}\n"
        f"📊 PREDICTION: {pred_text}\n"
        f"📈 LEVEL: {current_level} / 8\n"
        f"📩 DM FOR MORE DETAILS:\n"
        f"@Maayan001\n"
        f"@anonymoustele01\n"
        f"@madexgurl"
    )

    # Send Signal Text
    await update.message.reply_text(signal_message)

    # Send Result Sticker
    sticker_to_send = STICKER_BIG if prediction == "BIG" else STICKER_SMALL
    try:
        await update.message.reply_sticker(sticker=sticker_to_send)
    except Exception as e:
        logging.error(f"Failed to send sticker: {e}")

    # Auto increment period for next round
    current_period += 1

async def win_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resets prediction level to 1 on WIN."""
    global current_level
    current_level = 1
    await update.message.reply_text("✅ WIN recorded! Level reset to 1 / 8.")

async def loss_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Increments level step on LOSS (Max 8)."""
    global current_level
    if current_level < 8:
        current_level += 1
    else:
        current_level = 1
    await update.message.reply_text(f"❌ LOSS recorded! Next Level: {current_level} / 8.")

# Application Launcher
def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("win", win_command))
    app.add_handler(CommandHandler("loss", loss_command))

    logging.info("Wingo signal bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
