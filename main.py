import requests
import pandas as pd
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Load config
config = {
    "telegram": {
        "api_key": os.getenv("TELEGRAM_API_KEY"),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "owner_id": int(os.getenv("TELEGRAM_OWNER_ID")),  # Add your Telegram user ID here
    },
    "crypto_list": [
        "bitcoin",
        "ethereum",
        "binancecoin",
        "cardano",
        "solana",
        "ripple",
        "polkadot",
        "dogecoin",
        "avalanche-2",
        "matic-network",
    ],  # Mainstream cryptos
}

# Track bot start time for uptime calculation
start_time = time.time()

# Fetch crypto data from CoinGecko API
def fetch_crypto_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(config["crypto_list"]).lower(),
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch data from CoinGecko: {e}")
        return []

# Detect breakout/breakdown patterns
def detect_patterns(data):
    alerts = []
    for crypto in data:
        price_change_24h = crypto["price_change_percentage_24h"]
        if price_change_24h > 5:  # Breakout (price increase > 5%)
            alerts.append(f"🚀 **{crypto['symbol'].upper()}** is breaking out! (+{price_change_24h:.2f}%)")
        elif price_change_24h < -5:  # Breakdown (price decrease > 5%)
            alerts.append(f"🔻 **{crypto['symbol'].upper()}** is breaking down! ({price_change_24h:.2f}%)")
    return alerts

# Send Telegram notification
async def send_telegram_message(chat_id, message):
    api_key = config["telegram"]["api_key"]
    application = Application.builder().token(api_key).build()
    try:
        await application.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logger.info(f"Message sent to chat {chat_id}: {message}")
    except Exception as e:
        logger.error(f"Failed to send message to chat {chat_id}: {e}")

# Run bot
async def run_bot(chat_id):
    try:
        data = fetch_crypto_data()
        if data:
            alerts = detect_patterns(data)
            if alerts:
                message = "🔔 **Crypto Alerts** 🔔\n\n" + "\n".join(alerts)
                await send_telegram_message(chat_id, message)
            else:
                await send_telegram_message(chat_id, "No alerts found.")
    except Exception as e:
        error_message = f"⚠️ **Error in run_bot:** {str(e)}"
        await send_telegram_message(config["telegram"]["owner_id"], error_message)

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start command used by {update.message.from_user.username}")
    await update.message.reply_text("Crypto Alert Bot is running! Use /check to get alerts.")

# Handle /check command
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/check command used by {update.message.from_user.username}")
    chat_id = update.message.chat_id
    await update.message.reply_text("Checking for alerts...")
    await run_bot(chat_id)
    await update.message.reply_text("Alerts sent. Check your notifications.")

# Handle /ping command
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/ping command used by {update.message.from_user.username}")
    await update.message.reply_text("Pong! 🏓")

# Handle /uptime command
async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/uptime command used by {update.message.from_user.username}")
    uptime_seconds = int(time.time() - start_time)
    uptime_hours = uptime_seconds // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60
    uptime_seconds = uptime_seconds % 60
    await update.message.reply_text(f"⏰ Uptime: {uptime_hours}h {uptime_minutes}m {uptime_seconds}s")

# Handle /price command (in USDT)
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        crypto_name = context.args[0].lower() if context.args else None
        if not crypto_name:
            logger.info(f"/price command used without arguments by {update.message.from_user.username}")
            await update.message.reply_text("Please specify a cryptocurrency. Example: /price bitcoin")
            return

        logger.info(f"/price command used for {crypto_name} by {update.message.from_user.username}")

        # Fetch data for the specified cryptocurrency in USDT
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_name}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if crypto_name in data:
            price = data[crypto_name]["usd"]
            await update.message.reply_text(f"💰 The current price of {crypto_name.capitalize()} is {price:.2f} USDT.")
        else:
            await update.message.reply_text(f"❌ Could not find data for {crypto_name.capitalize()}.")
    except Exception as e:
        logger.error(f"Error in /price command: {e}")
        await update.message.reply_text("⚠️ An error occurred while fetching the price. Please try again later.")

# Periodic task for alerts
async def periodic_task(context: ContextTypes.DEFAULT_TYPE):
    await run_bot(config["telegram"]["chat_id"])

# Start Telegram bot
def start_telegram_bot():
    api_key = config["telegram"]["api_key"]
    application = Application.builder().token(api_key).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("uptime", uptime_command))
    application.add_handler(CommandHandler("price", price))

    # Start the periodic task
    application.job_queue.run_repeating(periodic_task, interval=300, first=0)  # Run every 5 minutes

    # Start polling
    application.run_polling()

# Main function
if __name__ == "__main__":
    start_telegram_bot()
