# ============================================
# CONFIG — variables locales ET variables d'environnement (cloud)
# Sur Render.com, configure ces valeurs dans "Environment Variables"
# ============================================
import os

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8953093607:AAFdR4rV3ysLo4Ky9EWPQGhj2_3__vHMoCI")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "1748018688")

# Email (Gmail recommandé)
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER",   "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "triviauxs@hotmail.fr")

# Seuils d'alerte
STOP_LOSS_PCT    = -15.0
TAKE_PROFIT_PCT  =  30.0
REFRESH_SECONDS  =  60

# IBKR
IBKR_ACCOUNT     = os.environ.get("IBKR_ACCOUNT",     "U26157956")
IBKR_GATEWAY_URL = os.environ.get("IBKR_GATEWAY_URL", "https://localhost:5000")

# Seb+ — Agent IA personnel
SEBPLUS_PASSWORD = os.environ.get("SEBPLUS_PASSWORD", "Pierre2026")
