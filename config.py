"""
⚙️ Infinity X - Enterprise VPS Bot Manager Configuration
Edit this file with your bot token, admin IDs, and advanced settings
"""

import os

# ==================== BOT SETTINGS ====================
BOT_TOKEN = "8610655917:AAHecRtc0DLlG5dDlYDKvwNwUK8-r7ZatwM"  # @BotFather
ADMIN_IDS = [8100453801]  # Your Telegram user IDs

# ==================== SYSTEM PATHS ====================
BASE_DIR = "/opt/infinity-x"
HOSTED_BOTS_DIR = os.path.join(BASE_DIR, "bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATABASE_PATH = os.path.join(DATA_DIR, "infinity.db")
TEMP_DIR = os.path.join(BASE_DIR, "tmp")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# ==================== LIMITS ====================
MAX_BOTS_PER_USER = 100           # Maximum bots per user
MAX_ZIP_SIZE_MB = 500             # Max zip file size in MB
MAX_CONCURRENT_DEPLOYS = 5        # Simultaneous deployments
DEPLOY_TIMEOUT = 600              # Seconds per deployment
TERMINAL_TIMEOUT = 60             # Seconds per terminal command

# ==================== GITHUB ====================
ALLOW_GITHUB_PUBLIC = True
ALLOW_GITHUB_PRIVATE = True
GITHUB_TOKEN = ""                 # Optional: for private repos (or use user-provided)

# ==================== DEPLOYMENT ====================
AUTO_START_AFTER_DEPLOY = True
RESTART_DELAY = 5                 # Seconds between restarts
MAX_RESTARTS_PER_HOUR = 10
AUTO_CLEANUP_INTERVAL = 3600      # Cleanup temp files every hour
ENABLE_AUTO_RESTART = True

# ==================== PM2 ====================
PM2_BIN = "pm2"                   # Path to PM2 binary
PM2_SAVE_ON_CHANGE = True

# ==================== PREMIUM & LOCK ====================
PREMIUM_FILE = os.path.join(DATA_DIR, "premium.json")
UNLOCK_FILE = os.path.join(DATA_DIR, "unlock.json")
REDEEM_CODES_FILE = os.path.join(DATA_DIR, "redeem.json")

# ==================== RATE LIMITING ====================
RATE_LIMIT_WINDOW = 60            # seconds
RATE_LIMIT_MAX_REQUESTS = 30      # per window

# ==================== ADMIN PANEL ====================
ADMIN_STATS_REFRESH = 10          # seconds

# ==================== DATABASE ====================
DB_POOL_SIZE = 10
DB_TIMEOUT = 30

# ==================== LOGGING ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(LOGS_DIR, "infinity.log")
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "errors.log")
DEPLOY_LOG_DIR = os.path.join(LOGS_DIR, "deploys")

# Ensure directories exist
for d in [HOSTED_BOTS_DIR, LOGS_DIR, DATA_DIR, TEMP_DIR, BACKUP_DIR, DEPLOY_LOG_DIR]:
    os.makedirs(d, exist_ok=True)
