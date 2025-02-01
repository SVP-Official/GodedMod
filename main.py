import requests
import pandas as pd
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Load config
config = {
    "telegram": {
        "api_key": os.getenv("TELEGRAM_API_KEY"),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "owner_id": int(os.getenv("TELEGRAM_OWNER_ID"))  # Add your Telegram user ID here
    },
    "crypto_list": ["bitcoin", "ethereum", "binancecoin", "cardano", "solana", "ripple", "polkadot", "dogecoin", "avalanche-2", "matic-network"]  # Mainstream cryptos
}

# Fetch crypto data from CoinGecko API
def fetch_crypto_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(config["crypto_list"]).lower(),
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data: {response.status_code}")
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
    await application.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

# Run bot
async def run_bot():
    try:
        data = fetch_crypto_data()
        if data:
            alerts = detect_patterns(data)
            if alerts:
                message = "🔔 **Crypto Alerts** 🔔\n\n" + "\n".join(alerts)
                await send_telegram_message(config["telegram"]["chat_id"], message)
    except Exception as e:
        error_message = f"⚠️ **Error in run_bot:** {str(e)}"
        await send_telegram_message(config["telegram"]["owner_id"], error_message)

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Crypto Alert Bot is running! Use /check to get alerts.")

# Handle /check command
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking for alerts...")
    await run_bot()
    await update.message.reply_text("Alerts sent. Check your notifications.")

# Start Telegram bot
def start_telegram_bot():
    api_key = config["telegram"]["api_key"]
    application = Application.builder().token(api_key).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))

    # Start polling
    application.run_polling()

# Main function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_telegram_bot()
