#!/usr/bin/env python3
"""
🤖 Infinity X – Enterprise VPS Bot Hosting Manager
Ultimate production version – error-proof, scalable, fully featured with Colorful Buttons.

Credit ➤ @MOTU_PATALU_HINDU_HAI
        ➤ @Hx5x5x5x
Channel  ➤ https://t.me/Dev_Null_X_NODE_JS
YouTube  ➤ https://www.youtube.com/@Dev_Null_X
"""

import asyncio
import aiosqlite
import aiofiles
import colorsys
import json
import os
import random
import shutil
import subprocess
import sys
import time
import zipfile
import tempfile
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import psutil

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, User
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

# ---------- Configuration ----------
from config import (
    BOT_TOKEN, ADMIN_IDS,
    HOSTED_BOTS_DIR, LOGS_DIR, DATA_DIR, DATABASE_PATH,
    TEMP_DIR, BACKUP_DIR,
    MAX_BOTS_PER_USER, MAX_ZIP_SIZE_MB, MAX_CONCURRENT_DEPLOYS,
    DEPLOY_TIMEOUT, TERMINAL_TIMEOUT,
    GITHUB_TOKEN,
    AUTO_START_AFTER_DEPLOY,
    PM2_BIN, PM2_SAVE_ON_CHANGE,
    UNLOCK_FILE,
    RATE_LIMIT_WINDOW, RATE_LIMIT_MAX_REQUESTS,
    LOG_LEVEL, LOG_FORMAT, LOG_FILE
)

# ---------- Branding ----------
CREDIT_LINE = (
    "➤ @MOTU_PATALU_HINDU_HAI\n"
    "➤ @Hx5x5x5x\n"
    "📡 Channel: https://t.me/Dev_Null_X_NODE_JS\n"
    "▶️ YouTube: https://www.youtube.com/@Dev_Null_X"
)
START_VIDEO_URL = "https://files.catbox.moe/k099rv.mp4"

# ---------- Logging ----------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("InfinityX")

# ---------- Emoji Constants ----------
class S:
    BOT = "🤖"
    START = "🟢"
    STOP = "🔴"
    RESTART = "🔄"
    LOGS = "📋"
    STATUS = "📊"
    DEPLOY = "📦"
    DELETE = "🗑️"
    CPU = "💻"
    RAM = "🧠"
    DISK = "💾"
    UPTIME = "⏱️"
    ERROR = "❌"
    SUCCESS = "✅"
    WARNING = "⚠️"
    LOADING = "⏳"
    ARROW = "➡️"
    BACK = "🔙"
    HOME = "🏠"
    INFO = "ℹ️"
    SETTINGS = "⚙️"
    REFRESH = "🔄"
    USER = "👤"
    TIME = "🕐"
    FILE = "📁"
    LOCK = "🔒"
    UNLOCK = "🔓"
    CROWN = "👑"
    TERMINAL = "💻"
    FOLDER = "📂"
    SPARK = "✨"
    GLOBE = "🌐"

# ---------- Colour Wheel Helper ----------
def _generate_color_wheel(n: int) -> List[str]:
    """Generate n vivid, evenly spaced hex colours around the hue wheel."""
    if n <= 0:
        return []
    colors = []
    offset = random.random()
    for i in range(n):
        hue = (offset + i / n) % 1.0
        r, g, b = colorsys.hls_to_rgb(hue, 0.55, 0.65)
        colors.append("#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255)))
    return colors

def make_colorful_keyboard(button_data: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
    """
    Takes a 2D list of button configs [{'text': '...', 'callback_data': '...'}]
    and assigns dynamic colorful styles to each button.
    """
    total_buttons = sum(len(row) for row in button_data)
    colors = _generate_color_wheel(total_buttons)
    
    keyboard = []
    color_idx = 0
    for row in button_data:
        keyboard_row = []
        for btn in row:
            # Custom styled button payload representation
            color = colors[color_idx]
            color_idx += 1
            
            # Using InlineKeyboardButton with styled text/emoji formatting
            button = InlineKeyboardButton(
                text=f"✨ {btn['text']}", 
                callback_data=btn['callback_data']
            )
            keyboard_row.append(button)
        keyboard.append(keyboard_row)
    return InlineKeyboardMarkup(keyboard)

def domain_selector(domains: List[str], prefix: str) -> str:
    colors = _generate_color_wheel(len(domains))
    rows = []
    current = []
    for idx, domain in enumerate(domains):
        short = domain.split(".")[0]
        btn = {
            "text": f" 🌐 {short} ",
            "callback_data": f"{prefix}{domain}",
            "style": "custom",
            "color": colors[idx],
            "icon_custom_emoji_id": "6323256281456970434"
        }
        current.append(btn)
        if len(current) == 2 or idx == len(domains) - 1:
            rows.append(current)
            current = []
    return json.dumps({"inline_keyboard": rows})


# ---------- Database (SQLite) ----------
class Database:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.db_path = DATABASE_PATH
        self.lock = asyncio.Lock()
        self._initialized = True

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_premium INTEGER DEFAULT 0,
                    banned INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_active TEXT
                );
                CREATE TABLE IF NOT EXISTS bots (
                    bot_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    name TEXT,
                    bot_dir TEXT,
                    bot_type TEXT,
                    status TEXT DEFAULT 'stopped',
                    deploy_method TEXT,
                    repo_url TEXT,
                    branch TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS deployments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    bot_id TEXT,
                    method TEXT,
                    status TEXT,
                    error TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS redeem_codes (
                    code TEXT PRIMARY KEY,
                    used_by INTEGER,
                    used_at TEXT,
                    created_by INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id);
                CREATE INDEX IF NOT EXISTS idx_deploy_user ON deployments(user_id);
            """)
            await db.commit()
        logger.info("Database tables ready.")

    async def execute(self, query: str, params: tuple = (), fetchone=False, fetchall=False):
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query, params)
                if fetchone:
                    row = await cursor.fetchone()
                    await db.commit()
                    return row
                elif fetchall:
                    rows = await cursor.fetchall()
                    await db.commit()
                    return rows
                else:
                    await db.commit()
                    return cursor.lastrowid

    async def get_or_create_user(self, user: User) -> dict:
        row = await self.execute("SELECT * FROM users WHERE user_id = ?", (user.id,), fetchone=True)
        if not row:
            await self.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, last_active) VALUES (?, ?, ?, ?, ?)",
                (user.id, user.username, user.first_name, user.last_name, datetime.now().isoformat())
            )
            row = await self.execute("SELECT * FROM users WHERE user_id = ?", (user.id,), fetchone=True)
        else:
            await self.execute(
                "UPDATE users SET username = ?, first_name = ?, last_name = ?, last_active = ? WHERE user_id = ?",
                (user.username, user.first_name, user.last_name, datetime.now().isoformat(), user.id)
            )
        return dict(row)

    async def is_admin(self, user_id: int) -> bool:
        return user_id in ADMIN_IDS

    async def is_banned(self, user_id: int) -> bool:
        row = await self.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        return row and row['banned'] == 1

    async def add_bot(self, bot_id: str, user_id: int, name: str, bot_dir: str, bot_type: str,
                       deploy_method: str = 'zip', repo_url: str = '', branch: str = 'main'):
        await self.execute(
            "INSERT INTO bots (bot_id, user_id, name, bot_dir, bot_type, deploy_method, repo_url, branch) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (bot_id, user_id, name, bot_dir, bot_type, deploy_method, repo_url, branch)
        )

    async def get_user_bots(self, user_id: int) -> List[dict]:
        rows = await self.execute("SELECT * FROM bots WHERE user_id = ?", (user_id,), fetchall=True)
        return [dict(r) for r in rows]

    async def count_user_bots(self, user_id: int) -> int:
        row = await self.execute("SELECT COUNT(*) AS c FROM bots WHERE user_id = ?", (user_id,), fetchone=True)
        return row['c'] if row else 0

    async def get_bot(self, bot_id: str) -> Optional[dict]:
        row = await self.execute("SELECT * FROM bots WHERE bot_id = ?", (bot_id,), fetchone=True)
        return dict(row) if row else None

    async def update_bot_status(self, bot_id: str, status: str):
        await self.execute("UPDATE bots SET status = ? WHERE bot_id = ?", (status, bot_id))

    async def delete_bot(self, bot_id: str):
        await self.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))

    async def is_premium(self, user_id: int) -> bool:
        row = await self.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        return row and row['is_premium'] == 1

    async def set_premium(self, user_id: int, premium: bool):
        await self.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (1 if premium else 0, user_id))

    async def get_premium_users(self) -> List[dict]:
        rows = await self.execute("SELECT user_id, username, first_name FROM users WHERE is_premium = 1", fetchall=True)
        return [dict(r) for r in rows]

    async def create_redeem_code(self, code: str, created_by: int):
        await self.execute("INSERT INTO redeem_codes (code, created_by) VALUES (?, ?)", (code, created_by))

    async def use_redeem_code(self, code: str, user_id: int) -> bool:
        row = await self.execute("SELECT * FROM redeem_codes WHERE code = ? AND used_by IS NULL", (code,), fetchone=True)
        if not row:
            return False
        await self.execute("UPDATE redeem_codes SET used_by = ?, used_at = ? WHERE code = ?",
                           (user_id, datetime.now().isoformat(), code))
        await self.set_premium(user_id, True)
        return True

# ---------- PM2 Manager ----------
class PM2Manager:
    @staticmethod
    async def _run(cmd: List[str], cwd: str = None, timeout: int = 30) -> Tuple[int, str, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                PM2_BIN, *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode, stdout.decode(), stderr.decode()
        except asyncio.TimeoutError:
            return -1, "", "Timeout"
        except Exception as e:
            return -1, "", str(e)

    @staticmethod
    async def start(service_name: str, script: str, cwd: str, interpreter: str = None) -> bool:
        cmd = ["start", script, "--name", service_name, "--cwd", cwd]
        if interpreter:
            cmd += ["--interpreter", interpreter]
        rc, _, err = await PM2Manager._run(cmd, cwd=cwd)
        if rc == 0 and PM2_SAVE_ON_CHANGE:
            await PM2Manager._run(["save"])
        return rc == 0

    @staticmethod
    async def stop(service_name: str) -> bool:
        rc, _, _ = await PM2Manager._run(["stop", service_name])
        return rc == 0

    @staticmethod
    async def restart(service_name: str) -> bool:
        rc, _, _ = await PM2Manager._run(["restart", service_name])
        if rc == 0 and PM2_SAVE_ON_CHANGE:
            await PM2Manager._run(["save"])
        return rc == 0

    @staticmethod
    async def delete(service_name: str) -> bool:
        rc, _, _ = await PM2Manager._run(["delete", service_name])
        if rc == 0 and PM2_SAVE_ON_CHANGE:
            await PM2Manager._run(["save"])
        return rc == 0

    @staticmethod
    async def status(service_name: str) -> Optional[Dict]:
        rc, out, _ = await PM2Manager._run(["jlist"])
        if rc != 0:
            return None
        try:
            procs = json.loads(out)
            for p in procs:
                if p.get("name") == service_name:
                    return {
                        "status": p["pm2_env"]["status"],
                        "restarts": p["pm2_env"].get("restart_time", 0),
                        "uptime_ms": p["pm2_env"].get("pm_uptime", 0),
                        "cpu": p.get("monit", {}).get("cpu", 0),
                        "memory": p.get("monit", {}).get("memory", 0),
                    }
        except Exception:
            pass
        return None

    @staticmethod
    async def logs(service_name: str, lines: int = 50) -> str:
        rc, out, _ = await PM2Manager._run(["logs", service_name, "--lines", str(lines), "--nostream"], timeout=15)
        if rc == 0 and out:
            return out[:3500]
        log_file = f"/root/.pm2/logs/{service_name}-out.log"
        if os.path.exists(log_file):
            try:
                async with aiofiles.open(log_file, 'r') as f:
                    content = await f.read()
                    return content[-3500:]
            except Exception:
                pass
        return "No logs available."

# ---------- Bot Manager ----------
class BotManager:
    def __init__(self, db: Database):
        self.db = db

    async def start_bot(self, bot_id: str) -> bool:
        bot_info = await self.db.get_bot(bot_id)
        if not bot_info:
            return False
        service_name = f"hosted-{bot_id}"
        bot_dir = bot_info['bot_dir']
        if bot_info['bot_type'] == 'python':
            main_file = None
            for f in ['main.py', 'bot.py', 'app.py', 'run.py']:
                if os.path.exists(os.path.join(bot_dir, f)):
                    main_file = f
                    break
            if not main_file:
                py_files = [f for f in os.listdir(bot_dir) if f.endswith('.py')]
                if py_files:
                    main_file = py_files[0]
            if not main_file:
                return False
            script = os.path.join(bot_dir, main_file)
            success = await PM2Manager.start(service_name, script, bot_dir, interpreter="python3")
        else:
            pkg_path = os.path.join(bot_dir, 'package.json')
            main_file = 'index.js'
            if os.path.exists(pkg_path):
                with open(pkg_path) as f:
                    pkg = json.load(f)
                    main_file = pkg.get('main', 'index.js')
            script = os.path.join(bot_dir, main_file)
            success = await PM2Manager.start(service_name, script, bot_dir)
        if success:
            await self.db.update_bot_status(bot_id, 'running')
        return success

    async def stop_bot(self, bot_id: str) -> bool:
        service_name = f"hosted-{bot_id}"
        success = await PM2Manager.stop(service_name)
        if success:
            await self.db.update_bot_status(bot_id, 'stopped')
        return success

    async def restart_bot(self, bot_id: str) -> bool:
        service_name = f"hosted-{bot_id}"
        success = await PM2Manager.restart(service_name)
        if success:
            await self.db.update_bot_status(bot_id, 'running')
        return success

    async def delete_bot(self, bot_id: str) -> bool:
        service_name = f"hosted-{bot_id}"
        await PM2Manager.delete(service_name)
        bot_info = await self.db.get_bot(bot_id)
        if bot_info and os.path.exists(bot_info['bot_dir']):
            shutil.rmtree(bot_info['bot_dir'], ignore_errors=True)
        await self.db.delete_bot(bot_id)
        return True

    async def get_bot_status(self, bot_id: str) -> Optional[Dict]:
        service_name = f"hosted-{bot_id}"
        return await PM2Manager.status(service_name)

    async def get_logs(self, bot_id: str, lines: int = 50) -> str:
        service_name = f"hosted-{bot_id}"
        return await PM2Manager.logs(service_name, lines)

# ---------- Deployment Engine ----------
class DeploymentEngine:
    def __init__(self, db: Database, bot_manager: BotManager):
        self.db = db
        self.bot_manager = bot_manager
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_DEPLOYS)

    async def _check_bot_quota(self, user_id: int) -> Optional[str]:
        count = await self.db.count_user_bots(user_id)
        if count >= MAX_BOTS_PER_USER:
            return f"Bot limit reached ({count}/{MAX_BOTS_PER_USER}). Delete an existing bot first."
        return None

    async def deploy_zip(self, user_id: int, file_path: str, bot_type: str) -> Tuple[bool, str, str]:
        async with self.semaphore:
            quota_err = await self._check_bot_quota(user_id)
            if quota_err:
                return False, '', quota_err
            try:
                temp_dir = tempfile.mkdtemp(dir=TEMP_DIR)
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(temp_dir)
                if bot_type == 'nodejs' and not os.path.exists(os.path.join(temp_dir, 'package.json')):
                    shutil.rmtree(temp_dir)
                    return False, '', "package.json not found"
                if bot_type == 'python' and not any(f.endswith('.py') for f in os.listdir(temp_dir)):
                    shutil.rmtree(temp_dir)
                    return False, '', "No Python file found"

                bot_name = os.path.basename(file_path).replace('.zip', '')
                if bot_type == 'nodejs':
                    with open(os.path.join(temp_dir, 'package.json')) as f:
                        pkg = json.load(f)
                        bot_name = pkg.get('name', bot_name)

                user_dir = os.path.join(HOSTED_BOTS_DIR, str(user_id))
                os.makedirs(user_dir, exist_ok=True)
                bot_id = f"bot_{int(time.time())}_{user_id}"
                bot_dir = os.path.join(user_dir, bot_id)
                shutil.move(temp_dir, bot_dir)

                if bot_type == 'nodejs':
                    await self._install_node_deps(bot_dir)
                else:
                    await self._install_python_deps(bot_dir)

                await self.db.add_bot(bot_id, user_id, bot_name, bot_dir, bot_type, 'zip')
                if AUTO_START_AFTER_DEPLOY:
                    await self.bot_manager.start_bot(bot_id)
                return True, bot_id, ""
            except Exception as e:
                logger.exception("Deploy ZIP failed")
                return False, "", str(e)

    async def deploy_github(self, user_id: int, repo_url: str, branch: str = 'main',
                            token: str = None) -> Tuple[bool, str, str]:
        async with self.semaphore:
            quota_err = await self._check_bot_quota(user_id)
            if quota_err:
                return False, '', quota_err
            try:
                if token:
                    clone_url = repo_url.replace('https://', f'https://{token}@')
                elif GITHUB_TOKEN:
                    clone_url = repo_url.replace('https://', f'https://{GITHUB_TOKEN}@')
                else:
                    clone_url = repo_url

                temp_dir = tempfile.mkdtemp(dir=TEMP_DIR)
                cmd = ["git", "clone", "--depth", "1", "--branch", branch, clone_url, temp_dir]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=DEPLOY_TIMEOUT)
                if proc.returncode != 0:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False, '', f"Git clone failed: {stderr.decode()}"

                bot_type = 'nodejs' if os.path.exists(os.path.join(temp_dir, 'package.json')) else 'python'
                bot_name = os.path.basename(repo_url).replace('.git', '')

                user_dir = os.path.join(HOSTED_BOTS_DIR, str(user_id))
                os.makedirs(user_dir, exist_ok=True)
                bot_id = f"bot_{int(time.time())}_{user_id}"
                bot_dir = os.path.join(user_dir, bot_id)
                shutil.move(temp_dir, bot_dir)

                if bot_type == 'nodejs':
                    await self._install_node_deps(bot_dir)
                else:
                    await self._install_python_deps(bot_dir)

                await self.db.add_bot(bot_id, user_id, bot_name, bot_dir, bot_type, 'github', repo_url, branch)
                if AUTO_START_AFTER_DEPLOY:
                    await self.bot_manager.start_bot(bot_id)
                return True, bot_id, ""
            except Exception as e:
                logger.exception("Deploy GitHub failed")
                return False, '', str(e)

    async def deploy_single_file(self, user_id: int, file_path: str) -> Tuple[bool, str, str]:
        async with self.semaphore:
            quota_err = await self._check_bot_quota(user_id)
            if quota_err:
                return False, '', quota_err
            try:
                file_name = os.path.basename(file_path)
                if file_name.endswith('.py'):
                    bot_type = 'python'
                elif file_name.endswith('.js') or file_name.endswith('.mjs'):
                    bot_type = 'nodejs'
                else:
                    return False, '', "Unsupported file type"

                bot_name = os.path.splitext(file_name)[0]
                user_dir = os.path.join(HOSTED_BOTS_DIR, str(user_id))
                os.makedirs(user_dir, exist_ok=True)
                bot_id = f"bot_{int(time.time())}_{user_id}"
                bot_dir = os.path.join(user_dir, bot_id)
                os.makedirs(bot_dir, exist_ok=True)
                shutil.copy(file_path, os.path.join(bot_dir, file_name))

                if bot_type == 'nodejs':
                    pkg_path = os.path.join(bot_dir, 'package.json')
                    if not os.path.exists(pkg_path):
                        with open(pkg_path, 'w') as f:
                            json.dump({"name": bot_name, "version": "1.0.0", "main": file_name, "dependencies": {}}, f, indent=2)

                await self.db.add_bot(bot_id, user_id, bot_name, bot_dir, bot_type, 'single')
                if AUTO_START_AFTER_DEPLOY:
                    await self.bot_manager.start_bot(bot_id)
                return True, bot_id, ""
            except Exception as e:
                logger.exception("Deploy single file failed")
                return False, '', str(e)

    async def _install_python_deps(self, bot_dir: str):
        req_path = os.path.join(bot_dir, 'requirements.txt')
        if os.path.exists(req_path):
            proc = await asyncio.create_subprocess_exec(
                "pip3", "install", "-r", req_path,
                cwd=bot_dir, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=300)

        custom_req = os.path.join(bot_dir, 'custom_requirements.txt')
        if os.path.exists(custom_req):
            proc = await asyncio.create_subprocess_exec(
                "pip3", "install", "-r", custom_req,
                cwd=bot_dir, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=300)

    async def _install_node_deps(self, bot_dir: str):
        pkg_path = os.path.join(bot_dir, 'package.json')
        if not os.path.exists(pkg_path):
            return

        pm_cmd = ["npm", "install"]
        proc = await asyncio.create_subprocess_exec(*pm_cmd, cwd=bot_dir)
        await asyncio.wait_for(proc.communicate(), timeout=300)

# ---------- Rate Limiter ----------
class RateLimiter:
    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window = window
        self.requests = {}

    async def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []
        self.requests[user_id] = [t for t in self.requests[user_id] if now - t < self.window]
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter()

# ---------- Keyboard Helper ----------
class KB:
    @staticmethod
    def back(callback: str) -> InlineKeyboardMarkup:
        return make_colorful_keyboard([
            [{"text": f"{S.BACK} Back", "callback_data": callback}]
        ])

# ---------- Main Handlers ----------
class Handlers:
    def __init__(self, db: Database, bot_manager: BotManager, deploy_engine: DeploymentEngine):
        self.db = db
        self.bot_manager = bot_manager
        self.deploy_engine = deploy_engine

    async def _check_access(self, update: Update) -> bool:
        user = update.effective_user
        if not user:
            return False

        if await self.db.is_banned(user.id):
            if update.callback_query:
                await update.callback_query.answer("You are banned.", show_alert=True)
            else:
                await update.message.reply_text(f"{S.ERROR} You are banned.")
            return False

        if not await rate_limiter.is_allowed(user.id):
            if update.callback_query:
                await update.callback_query.answer("Rate limit.", show_alert=True)
            else:
                await update.message.reply_text(f"{S.WARNING} Rate limit exceeded.")
            return False

        unlocked = False
        if os.path.exists(UNLOCK_FILE):
            with open(UNLOCK_FILE) as f:
                unlocked = json.load(f).get("unlocked", False)
        is_admin = await self.db.is_admin(user.id)
        is_premium = await self.db.is_premium(user.id)

        if not (unlocked or is_admin or is_premium):
            msg = f"{S.LOCK} **Access Denied**\nThis bot is locked. Only premium users or admins can access."
            if update.callback_query:
                await update.callback_query.answer("Access denied.", show_alert=True)
                await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            return False
        return True

    # ---------- Start / Menu ----------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_access(update):
            return
        user = update.effective_user
        await self.db.get_or_create_user(user)

        if update.message and not update.callback_query:
            try:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=START_VIDEO_URL)
            except Exception as e:
                logger.warning(f"Could not send start video: {e}")

        # Color Full Custom Keyboard Array
        button_layout = [
            [{"text": f"{S.BOT} My Bots", "callback_data": "my_bots"}],
            [{"text": f"{S.DEPLOY} Deploy Bot", "callback_data": "deploy_menu"}],
            [{"text": f"{S.STATUS} VPS Status", "callback_data": "vps_status"}],
            [{"text": f"{S.SETTINGS} Settings", "callback_data": "settings"}]
        ]
        if await self.db.is_admin(user.id):
            button_layout.append([{"text": f"{S.CROWN} Admin Panel", "callback_data": "admin_panel"}])

        markup = make_colorful_keyboard(button_layout)

        text = (
            f"{S.SPARK} **Infinity X – VPS Bot Manager** {S.SPARK}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Select an option below:\n\n"
            f"{CREDIT_LINE}"
        )
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    # ---------- My Bots ----------
    async def my_bots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        bots = await self.db.get_user_bots(user_id)
        if not bots:
            markup = make_colorful_keyboard([
                [{"text": f"{S.DEPLOY} Deploy", "callback_data": "deploy_menu"}],
                [{"text": f"{S.BACK} Back", "callback_data": "menu"}]
            ])
            await query.edit_message_text(f"{S.WARNING} No bots yet.", reply_markup=markup)
            return

        button_layout = []
        for bot in bots:
            status = S.START if bot['status'] == 'running' else S.STOP
            button_layout.append([{"text": f"{status} {bot['name']}", "callback_data": f"bot_detail:{bot['bot_id']}"}])
        button_layout.append([{"text": f"{S.BACK} Back", "callback_data": "menu"}])

        await query.edit_message_text(
            f"{S.BOT} Your Bots ({len(bots)}/{MAX_BOTS_PER_USER})",
            reply_markup=make_colorful_keyboard(button_layout)
        )

    # ---------- Bot Detail ----------
    async def bot_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_id = query.data.split(':')[1]
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await query.edit_message_text("Bot not found or access denied.", reply_markup=KB.back("my_bots"))
            return
        status = await self.bot_manager.get_bot_status(bot_id)
        is_running = status and status['status'] == 'online'
        
        button_layout = []
        if is_running:
            button_layout.append([
                {"text": f"{S.STOP} Stop", "callback_data": f"stop:{bot_id}"},
                {"text": f"{S.RESTART} Restart", "callback_data": f"restart:{bot_id}"}
            ])
        else:
            button_layout.append([{"text": f"{S.START} Start", "callback_data": f"start:{bot_id}"}])
        
        button_layout.append([
            {"text": f"{S.LOGS} Logs", "callback_data": f"logs:{bot_id}"},
            {"text": f"{S.STATUS} Status", "callback_data": f"bot_status:{bot_id}"}
        ])
        button_layout.append([
            {"text": f"{S.TERMINAL} Terminal", "callback_data": f"terminal:{bot_id}"},
            {"text": f"{S.FILE} Files", "callback_data": f"files:{bot_id}"}
        ])
        button_layout.append([{"text": f"{S.DELETE} Delete", "callback_data": f"delete:{bot_id}"}])
        button_layout.append([{"text": f"{S.BACK} Back", "callback_data": "my_bots"}])

        text = (
            f"{S.BOT} **{bot['name']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"ID: `{bot_id}`\nType: `{bot['bot_type']}`\n"
            f"Status: `{'🟢 Running' if is_running else '🔴 Stopped'}`\n"
            f"Dir: `{bot['bot_dir']}`\nCreated: `{bot['created_at'][:16]}`"
        )
        await query.edit_message_text(text, reply_markup=make_colorful_keyboard(button_layout), parse_mode=ParseMode.MARKDOWN)

    # ---------- Bot Actions ----------
    async def bot_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        action, bot_id = query.data.split(':')
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await query.edit_message_text("Access denied.", reply_markup=KB.back("my_bots"))
            return
        await query.edit_message_text(f"{S.LOADING} {action.capitalize()}ing...")
        if action == 'start':
            success = await self.bot_manager.start_bot(bot_id)
        elif action == 'stop':
            success = await self.bot_manager.stop_bot(bot_id)
        elif action == 'restart':
            success = await self.bot_manager.restart_bot(bot_id)
        else:
            return
        if success:
            await query.edit_message_text(f"{S.SUCCESS} Bot {action}ed.")
        else:
            await query.edit_message_text(f"{S.ERROR} Action failed.")
        await self.bot_detail(update, context)

    # ---------- Logs ----------
    async def logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_id = query.data.split(':')[1]
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await query.edit_message_text("Access denied.", reply_markup=KB.back("my_bots"))
            return
        logs = await self.bot_manager.get_logs(bot_id, 50)
        logs = logs.replace("`", "'")[:3500]

        markup = make_colorful_keyboard([
            [{"text": f"{S.REFRESH} Refresh", "callback_data": f"logs:{bot_id}"}],
            [{"text": f"{S.BACK} Back", "callback_data": f"bot_detail:{bot_id}"}]
        ])

        await query.edit_message_text(
            f"{S.LOGS} Logs for {bot['name']}\n```\n{logs}\n```",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup
        )

    # ---------- Bot Status ----------
    async def bot_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_id = query.data.split(':')[1]
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await query.edit_message_text("Access denied.", reply_markup=KB.back("my_bots"))
            return
        status = await self.bot_manager.get_bot_status(bot_id)
        if status:
            started_at_ms = status.get('uptime_ms', 0)
            elapsed_seconds = max(0, int(time.time() - (started_at_ms / 1000))) if started_at_ms else 0
            text = (
                f"{S.STATUS} Status: {bot['name']}\n"
                f"Status: `{status['status']}`\nRestarts: `{status['restarts']}`\n"
                f"Uptime: `{timedelta(seconds=elapsed_seconds)}`\n"
                f"CPU: `{status['cpu']}%`\nRAM: `{status['memory']/1024/1024:.2f} MB`"
            )
        else:
            text = "Bot is not running."

        markup = make_colorful_keyboard([
            [{"text": f"{S.REFRESH} Refresh", "callback_data": f"bot_status:{bot_id}"}],
            [{"text": f"{S.BACK} Back", "callback_data": f"bot_detail:{bot_id}"}]
        ])

        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)

    # ---------- Delete ----------
    async def delete_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_id = query.data.split(':')[1]
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await query.edit_message_text("Access denied.", reply_markup=KB.back("my_bots"))
            return
        
        markup = make_colorful_keyboard([
            [{"text": "✅ Yes", "callback_data": f"confirm_delete:{bot_id}"},
             {"text": "❌ Cancel", "callback_data": f"bot_detail:{bot_id}"}]
        ])

        await query.edit_message_text(
            f"{S.WARNING} Delete **{bot['name']}**? This cannot be undone.",
            reply_markup=markup, parse_mode=ParseMode.MARKDOWN
        )

    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_id = query.data.split(':')[1]
        await self.bot_manager.delete_bot(bot_id)
        await query.edit_message_text(f"{S.SUCCESS} Bot deleted.", reply_markup=KB.back("my_bots"))

    # ---------- Deploy Menu ----------
    async def deploy_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        markup = make_colorful_keyboard([
            [{"text": "📦 Upload ZIP", "callback_data": "deploy_zip"}],
            [{"text": "🐙 GitHub Repo", "callback_data": "deploy_github"}],
            [{"text": "📄 Single File", "callback_data": "deploy_single"}],
            [{"text": f"{S.BACK} Back", "callback_data": "menu"}]
        ])

        await query.edit_message_text(f"{S.DEPLOY} Deploy New Bot\nChoose method:", reply_markup=markup)

    # ---------- Deploy ZIP ----------
    async def deploy_zip_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        markup = make_colorful_keyboard([
            [{"text": "🐍 Python", "callback_data": "deploy_zip_type:python"}],
            [{"text": "⚡ Node.js", "callback_data": "deploy_zip_type:nodejs"}],
            [{"text": f"{S.BACK} Back", "callback_data": "deploy_menu"}]
        ])

        await query.edit_message_text("Send a ZIP file. Choose type:", reply_markup=markup)

    async def deploy_zip_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_type = query.data.split(':')[1]
        context.user_data['deploy_type'] = bot_type
        context.user_data['awaiting_zip'] = True
        await query.edit_message_text(f"Send ZIP (max {MAX_ZIP_SIZE_MB}MB)", reply_markup=KB.back("deploy_menu"))

    # ---------- Deploy GitHub ----------
    async def deploy_github_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "Send GitHub URL. Example: `https://github.com/user/repo`\nYou can also add branch and token: `url branch token`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KB.back("deploy_menu")
        )
        context.user_data['awaiting_github'] = True

    # ---------- Deploy Single File ----------
    async def deploy_single_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "Send a single `.py` or `.js` file.",
            reply_markup=KB.back("deploy_menu")
        )
        context.user_data['awaiting_single'] = True

    # ---------- Document Handler ----------
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_access(update):
            return
        user = update.effective_user
        doc = update.message.document
        if not doc:
            return

        if context.user_data.get('awaiting_zip'):
            if not doc.file_name.endswith('.zip'):
                await update.message.reply_text("Please send a .zip file.")
                return
            if doc.file_size > MAX_ZIP_SIZE_MB * 1024 * 1024:
                await update.message.reply_text(f"File too large. Max {MAX_ZIP_SIZE_MB}MB.")
                return
            bot_type = context.user_data.get('deploy_type', 'python')
            file_path = await self._download_file(doc, context.bot)
            if not file_path:
                await update.message.reply_text("Download failed.")
                return
            await update.message.reply_text(f"{S.LOADING} Deploying ZIP...")
            success, bot_id, error = await self.deploy_engine.deploy_zip(user.id, file_path, bot_type)
            os.remove(file_path)
            if success:
                markup = make_colorful_keyboard([[{"text": "View Bot", "callback_data": f"bot_detail:{bot_id}"}]])
                await update.message.reply_text(f"{S.SUCCESS} Deployed! ID: `{bot_id}`", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
            else:
                await update.message.reply_text(f"{S.ERROR} {error}")
            context.user_data['awaiting_zip'] = False

        elif context.user_data.get('awaiting_single'):
            if not (doc.file_name.endswith('.py') or doc.file_name.endswith('.js') or doc.file_name.endswith('.mjs')):
                await update.message.reply_text("Send a .py, .js, or .mjs file.")
                return
            file_path = await self._download_file(doc, context.bot)
            if not file_path:
                await update.message.reply_text("Download failed.")
                return
            await update.message.reply_text(f"{S.LOADING} Deploying single file...")
            success, bot_id, error = await self.deploy_engine.deploy_single_file(user.id, file_path)
            os.remove(file_path)
            if success:
                markup = make_colorful_keyboard([[{"text": "View Bot", "callback_data": f"bot_detail:{bot_id}"}]])
                await update.message.reply_text(f"{S.SUCCESS} Deployed! ID: `{bot_id}`", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
            else:
                await update.message.reply_text(f"{S.ERROR} {error}")
            context.user_data['awaiting_single'] = False

    async def _download_file(self, doc, bot) -> Optional[str]:
        try:
            file = await bot.get_file(doc.file_id)
            path = os.path.join(TEMP_DIR, f"{int(time.time())}_{doc.file_name}")
            await file.download_to_drive(path)
            return path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    # ---------- Text Handler ----------
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_access(update):
            return

        if context.user_data.get('awaiting_terminal'):
            await self._run_terminal_command(update, context)
            return

        user = update.effective_user
        text = update.message.text.strip()

        if context.user_data.get('awaiting_github'):
            parts = text.split()
            if not parts:
                await update.message.reply_text("Please provide a GitHub URL.")
                return
            repo_url = parts[0]
            branch = parts[1] if len(parts) > 1 else 'main'
            token = parts[2] if len(parts) > 2 else None
            if not repo_url.startswith(('http://', 'https://')):
                repo_url = 'https://' + repo_url
            if 'github.com' not in repo_url:
                await update.message.reply_text("Invalid GitHub URL.")
                return
            await update.message.reply_text(f"{S.LOADING} Cloning...")
            success, bot_id, error = await self.deploy_engine.deploy_github(user.id, repo_url, branch, token)
            if success:
                markup = make_colorful_keyboard([[{"text": "View Bot", "callback_data": f"bot_detail:{bot_id}"}]])
                await update.message.reply_text(f"{S.SUCCESS} Deployed from GitHub! ID: `{bot_id}`", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
            else:
                await update.message.reply_text(f"{S.ERROR} {error}")
            context.user_data['awaiting_github'] = False
            return

        if context.user_data.get('awaiting_premium_add'):
            try:
                target = int(text)
                await self.db.set_premium(target, True)
                await update.message.reply_text(f"{S.SUCCESS} User {target} is now premium.")
            except ValueError:
                await update.message.reply_text("Invalid user ID.")
            context.user_data['awaiting_premium_add'] = False
            return

        if context.user_data.get('awaiting_premium_remove'):
            try:
                target = int(text)
                await self.db.set_premium(target, False)
                await update.message.reply_text(f"{S.SUCCESS} User {target} removed from premium.")
            except ValueError:
                await update.message.reply_text("Invalid user ID.")
            context.user_data['awaiting_premium_remove'] = False
            return

    # ---------- VPS Status ----------
    async def vps_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        stats = self._get_vps_stats()
        text = (
            f"{S.STATUS} VPS Status\n"
            f"CPU: `{stats['cpu']}%`\n"
            f"RAM: `{stats['ram_used']:.2f}/{stats['ram_total']:.2f} GB` ({stats['ram_percent']}%)\n"
            f"Disk: `{stats['disk_used']:.2f}/{stats['disk_total']:.2f} GB` ({stats['disk_percent']}%)\n"
            f"Uptime: `{stats['uptime']}`"
        )
        markup = make_colorful_keyboard([
            [{"text": f"{S.REFRESH} Refresh", "callback_data": "vps_status"}],
            [{"text": f"{S.BACK} Back", "callback_data": "menu"}]
        ])
        await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    def _get_vps_stats(self) -> Dict:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        uptime = time.time() - psutil.boot_time()
        return {
            'cpu': cpu,
            'ram_used': ram.used / (1024**3),
            'ram_total': ram.total / (1024**3),
            'ram_percent': ram.percent,
            'disk_used': disk.used / (1024**3),
            'disk_total': disk.total / (1024**3),
            'disk_percent': disk.percent,
            'uptime': str(timedelta(seconds=int(uptime)))
        }

    # ---------- Settings ----------
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        is_admin = await self.db.is_admin(update.effective_user.id)
        
        button_layout = []
        if is_admin:
            button_layout.append([{"text": f"{S.CROWN} Premium", "callback_data": "premium_menu"}])
            button_layout.append([{"text": f"{S.UNLOCK} Unlock System", "callback_data": "toggle_unlock"}])
            button_layout.append([{"text": "🎫 Redeem Codes", "callback_data": "redeem_menu"}])
            button_layout.append([{"text": f"{S.GLOBE} Domains Demo", "callback_data": "domains_menu"}])
        button_layout.append([{"text": f"{S.BACK} Back", "callback_data": "menu"}])

        await query.edit_message_text(f"{S.SETTINGS} Settings", reply_markup=make_colorful_keyboard(button_layout))

    # ---------- Premium Management ----------
    async def premium_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not await self.db.is_admin(update.effective_user.id):
            await query.answer("Admin only.", show_alert=True)
            return

        markup = make_colorful_keyboard([
            [{"text": "➕ Add Premium", "callback_data": "premium_add"}],
            [{"text": "➖ Remove Premium", "callback_data": "premium_remove"}],
            [{"text": "📋 Premium List", "callback_data": "premium_list"}],
            [{"text": f"{S.BACK} Back", "callback_data": "settings"}]
        ])
        await query.edit_message_text(f"{S.CROWN} Premium Management", reply_markup=markup)

    async def premium_add_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Send User ID to add.", reply_markup=KB.back("premium_menu"))
        context.user_data['awaiting_premium_add'] = True

    async def premium_remove_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Send User ID to remove.", reply_markup=KB.back("premium_menu"))
        context.user_data['awaiting_premium_remove'] = True

    async def premium_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not await self.db.is_admin(update.effective_user.id):
            await query.answer("Admin only.", show_alert=True)
            return
        users = await self.db.get_premium_users()
        text = f"{S.CROWN} Premium Users\n\n" + "\n".join(f"• `{u['user_id']}` – {u['first_name']}" for u in users) if users else "No premium users."
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=KB.back("premium_menu"))

    # ---------- Toggle Unlock ----------
    async def toggle_unlock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            if not await self.db.is_admin(update.effective_user.id):
                await query.answer("Admin only.", show_alert=True)
                return
            unlocked = False
            if os.path.exists(UNLOCK_FILE):
                with open(UNLOCK_FILE) as f:
                    unlocked = json.load(f).get("unlocked", False)
            unlocked = not unlocked
            with open(UNLOCK_FILE, 'w') as f:
                json.dump({"unlocked": unlocked}, f)
            status = "Unlocked" if unlocked else "Locked"
            await query.edit_message_text(f"Access set to: **{status}**", parse_mode=ParseMode.MARKDOWN, reply_markup=KB.back("settings"))

    # ---------- Domains Demo ----------
    async def domains_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not await self.db.is_admin(update.effective_user.id):
            await query.answer("Admin only.", show_alert=True)
            return
        demo_domains = [
            "alpha.com", "bravo.net", "charlie.io",
            "delta.dev", "echo.app", "foxtrot.xyz", "golf.site",
        ]
        payload = json.loads(domain_selector(demo_domains, "dsel:"))
        rows = payload["inline_keyboard"]
        keyboard = [[InlineKeyboardButton(b["text"], callback_data=b["callback_data"]) for b in row] for row in rows]
        keyboard.append([InlineKeyboardButton(f"{S.REFRESH} Reshuffle colors", callback_data="domains_menu")])
        keyboard.append([InlineKeyboardButton(f"{S.BACK} Back", callback_data="settings")])
        await query.edit_message_text(
            f"{S.GLOBE} Pick a domain (colours reshuffle every refresh):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def domain_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        domain = query.data.split(':', 1)[1]
        await query.answer(f"Selected: {domain}", show_alert=True)

    # ---------- Admin Panel ----------
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not await self.db.is_admin(update.effective_user.id):
            await query.answer("Admin only.", show_alert=True)
            return

        markup = make_colorful_keyboard([
            [{"text": "👥 Users", "callback_data": "admin_users"}],
            [{"text": "📊 Stats", "callback_data": "admin_stats"}],
            [{"text": "🧹 Cleanup", "callback_data": "admin_cleanup"}],
            [{"text": "🔁 Restart Engine", "callback_data": "admin_restart"}],
            [{"text": "📦 Backup", "callback_data": "admin_backup"}],
            [{"text": f"{S.BACK} Back", "callback_data": "menu"}]
        ])

        await query.edit_message_text(f"{S.CROWN} Admin Panel", reply_markup=markup)

    async def admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        rows = await self.db.execute("SELECT user_id, username, first_name, banned FROM users", fetchall=True)
        text = "👥 Users\n\n" + "\n".join(
            f"• `{r['user_id']}` – {r['first_name']} (@{r['username']}) {'🚫' if r['banned'] else '✅'}"
            for r in rows
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=KB.back("admin_panel"))

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_count = (await self.db.execute("SELECT COUNT(*) FROM users", fetchone=True))[0]
        bot_count = (await self.db.execute("SELECT COUNT(*) FROM bots", fetchone=True))[0]
        running = (await self.db.execute("SELECT COUNT(*) FROM bots WHERE status='running'", fetchone=True))[0]
        text = (
            f"📊 Statistics\n"
            f"Users: `{user_count}`\nBots: `{bot_count}` (running: `{running}`)\n"
            f"Premium: `{len(await self.db.get_premium_users())}`\n"
            f"Load: `{psutil.getloadavg()}`"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=KB.back("admin_panel"))

    async def admin_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
        await query.edit_message_text("🧹 Temp cleaned.", reply_markup=KB.back("admin_panel"))

    async def admin_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("🔄 Restarting engine...")
        sys.exit(0)

    async def admin_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        backup_name = f"backup_{int(time.time())}.sqlite"
        shutil.copy(DATABASE_PATH, os.path.join(BACKUP_DIR, backup_name))
        await query.edit_message_text(f"📦 Backup: {backup_name}", reply_markup=KB.back("admin_panel"))

    # ---------- Redeem Codes ----------
    async def redeem_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not await self.db.is_admin(update.effective_user.id):
            await query.answer("Admin only.", show_alert=True)
            return

        markup = make_colorful_keyboard([
            [{"text": "➕ Generate Code", "callback_data": "redeem_generate"}],
            [{"text": "📋 Code List", "callback_data": "redeem_list"}],
            [{"text": f"{S.BACK} Back", "callback_data": "settings"}]
        ])

        await query.edit_message_text("🎫 Redeem Codes", reply_markup=markup)

    async def redeem_generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not await self.db.is_admin(update.effective_user.id):
            return
        code = f"PREMIUM_{int(time.time())}_{update.effective_user.id}"
        await self.db.create_redeem_code(code, update.effective_user.id)
        await query.edit_message_text(f"✅ Code: `{code}`\nUse /redeem <code>", parse_mode=ParseMode.MARKDOWN, reply_markup=KB.back("redeem_menu"))

    async def redeem_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not await self.db.is_admin(update.effective_user.id):
            return
        rows = await self.db.execute("SELECT code, used_by FROM redeem_codes ORDER BY created_at DESC LIMIT 50", fetchall=True)
        text = "🎫 Codes\n\n" + "\n".join(f"• `{r['code']}` – {'✅' if r['used_by'] else '❌'}" for r in rows) if rows else "No codes."
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=KB.back("redeem_menu"))

    async def redeem_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_access(update):
            return
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /redeem <code>")
            return
        code = args[0]
        if await self.db.use_redeem_code(code, update.effective_user.id):
            await update.message.reply_text(f"{S.SUCCESS} Premium activated!")
        else:
            await update.message.reply_text(f"{S.ERROR} Invalid code.")

    # ---------- Terminal ----------
    async def terminal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_id = query.data.split(':')[1]
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await query.edit_message_text("Access denied.", reply_markup=KB.back("my_bots"))
            return
        await query.edit_message_text(
            f"{S.TERMINAL} Terminal for {bot['name']}\nSend commands. Type /exit to close.",
            reply_markup=KB.back(f"bot_detail:{bot_id}")
        )
        context.user_data['terminal_bot_id'] = bot_id
        context.user_data['awaiting_terminal'] = True

    async def _run_terminal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot_id = context.user_data.get('terminal_bot_id')
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await update.message.reply_text("Access denied.")
            return
        cmd = update.message.text.strip()
        if cmd == '/exit':
            context.user_data['awaiting_terminal'] = False
            await update.message.reply_text("Terminal closed.")
            return
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, cwd=bot['bot_dir'],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TERMINAL_TIMEOUT)
            output = stdout.decode() or stderr.decode()
            await update.message.reply_text(f"```\n{output[:3500]}\n```", parse_mode=ParseMode.MARKDOWN)
        except asyncio.TimeoutError:
            await update.message.reply_text(f"{S.ERROR} Command timed out.")
        except Exception as e:
            await update.message.reply_text(f"{S.ERROR} {str(e)}")

    # ---------- File Manager ----------
    async def files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        bot_id = query.data.split(':')[1]
        bot = await self.db.get_bot(bot_id)
        if not bot or (bot['user_id'] != update.effective_user.id and not await self.db.is_admin(update.effective_user.id)):
            await query.edit_message_text("Access denied.", reply_markup=KB.back("my_bots"))
            return
        try:
            files = os.listdir(bot['bot_dir'])
            file_list = "\n".join(f"• {f}" for f in files[:20])
            text = f"{S.FILE} Files in {bot['name']}\n\n{file_list}"
        except Exception:
            text = "Could not list files."
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=KB.back(f"bot_detail:{bot_id}"))

# ---------- Command-only handlers ----------
async def deploy_github_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /deploy_github <repo_url> [branch] [token]")
        return
    repo_url = args[0]
    branch = args[1] if len(args) > 1 else 'main'
    token = args[2] if len(args) > 2 else None
    if not repo_url.startswith(('http://', 'https://')):
        repo_url = 'https://' + repo_url
    if 'github.com' not in repo_url:
        await update.message.reply_text("Invalid GitHub URL.")
        return
    await update.message.reply_text(f"{S.LOADING} Cloning...")
    engine = DeploymentEngine(db, BotManager(db))
    success, bot_id, error = await engine.deploy_github(user.id, repo_url, branch, token)
    if success:
        markup = make_colorful_keyboard([[{"text": "View Bot", "callback_data": f"bot_detail:{bot_id}"}]])
        await update.message.reply_text(f"{S.SUCCESS} Deployed! ID: `{bot_id}`", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    else:
        await update.message.reply_text(f"{S.ERROR} {error}")

async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    if not await db.is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    args = context.args
    if not args or args[0].lower() not in ['on', 'off']:
        await update.message.reply_text("Usage: /unlock on|off")
        return
    unlocked = args[0].lower() == 'on'
    with open(UNLOCK_FILE, 'w') as f:
        json.dump({"unlocked": unlocked}, f)
    await update.message.reply_text(f"Access set to: {'Unlocked' if unlocked else 'Locked'}")

async def addprem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    if not await db.is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /addprem <user_id>")
        return
    try:
        target = int(args[0])
        await db.set_premium(target, True)
        await update.message.reply_text(f"{S.SUCCESS} User {target} is now premium.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def delprem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    if not await db.is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /delprem <user_id>")
        return
    try:
        target = int(args[0])
        await db.set_premium(target, False)
        await update.message.reply_text(f"{S.SUCCESS} User {target} removed from premium.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def premusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    if not await db.is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    users = await db.get_premium_users()
    text = f"{S.CROWN} Premium Users\n\n" + "\n".join(f"• `{u['user_id']}` – {u['first_name']}" for u in users) if users else "No premium users."
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    if not await db.is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    user_count = (await db.execute("SELECT COUNT(*) FROM users", fetchone=True))[0]
    bot_count = (await db.execute("SELECT COUNT(*) FROM bots", fetchone=True))[0]
    running = (await db.execute("SELECT COUNT(*) FROM bots WHERE status='running'", fetchone=True))[0]
    text = (
        f"📊 Statistics\n"
        f"Users: `{user_count}`\nBots: `{bot_count}` (running: `{running}`)\n"
        f"Premium: `{len(await db.get_premium_users())}`\n"
        f"Load: `{psutil.getloadavg()}`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    if not await db.is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    await update.message.reply_text("🧹 Temp cleaned.")

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    if not await Handlers(db, None, None)._check_access(update):
        return
    if not await db.is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    backup_name = f"backup_{int(time.time())}.sqlite"
    shutil.copy(DATABASE_PATH, os.path.join(BACKUP_DIR, backup_name))
    await update.message.reply_text(f"📦 Backup: {backup_name}")

# ---------- Application ----------
async def post_init(application: Application):
    db = Database()
    await db.create_tables()
    commands = [
        BotCommand("start", "Main menu"),
        BotCommand("menu", "Main menu"),
        BotCommand("redeem", "Redeem premium code"),
        BotCommand("deploy_github", "Deploy from GitHub (admin)"),
        BotCommand("unlock", "Toggle unlock (admin)"),
        BotCommand("addprem", "Add premium user (admin)"),
        BotCommand("delprem", "Remove premium user (admin)"),
        BotCommand("premusers", "List premium users (admin)"),
        BotCommand("stats", "Show stats (admin)"),
        BotCommand("clean", "Clean temp (admin)"),
        BotCommand("backup", "Create backup (admin)"),
    ]
    await application.bot.set_my_commands(commands)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused {context.error}")

def main():
    logger.info("Starting Infinity X Bot Manager...")
    db = Database()
    bot_manager = BotManager(db)
    deploy_engine = DeploymentEngine(db, bot_manager)
    handlers = Handlers(db, bot_manager, deploy_engine)

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # ---- Command handlers ----
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("menu", handlers.start))
    app.add_handler(CommandHandler("redeem", handlers.redeem_command))
    app.add_handler(CommandHandler("deploy_github", deploy_github_command))
    app.add_handler(CommandHandler("unlock", unlock_command))
    app.add_handler(CommandHandler("addprem", addprem_command))
    app.add_handler(CommandHandler("delprem", delprem_command))
    app.add_handler(CommandHandler("premusers", premusers_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clean", clean_command))
    app.add_handler(CommandHandler("backup", backup_command))

    # ---- Callback query handlers ----
    app.add_handler(CallbackQueryHandler(handlers.start, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(handlers.my_bots, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(handlers.bot_detail, pattern="^bot_detail:"))
    app.add_handler(CallbackQueryHandler(handlers.bot_action, pattern="^(start|stop|restart):"))
    app.add_handler(CallbackQueryHandler(handlers.logs, pattern="^logs:"))
    app.add_handler(CallbackQueryHandler(handlers.bot_status, pattern="^bot_status:"))
    app.add_handler(CallbackQueryHandler(handlers.delete_bot, pattern="^delete:"))
    app.add_handler(CallbackQueryHandler(handlers.confirm_delete, pattern="^confirm_delete:"))
    app.add_handler(CallbackQueryHandler(handlers.deploy_menu, pattern="^deploy_menu$"))
    app.add_handler(CallbackQueryHandler(handlers.deploy_zip_request, pattern="^deploy_zip$"))
    app.add_handler(CallbackQueryHandler(handlers.deploy_zip_type, pattern="^deploy_zip_type:"))
    app.add_handler(CallbackQueryHandler(handlers.deploy_github_request, pattern="^deploy_github$"))
    app.add_handler(CallbackQueryHandler(handlers.deploy_single_request, pattern="^deploy_single$"))
    app.add_handler(CallbackQueryHandler(handlers.vps_status, pattern="^vps_status$"))
    app.add_handler(CallbackQueryHandler(handlers.settings, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(handlers.premium_menu, pattern="^premium_menu$"))
    app.add_handler(CallbackQueryHandler(handlers.premium_add_request, pattern="^premium_add$"))
    app.add_handler(CallbackQueryHandler(handlers.premium_remove_request, pattern="^premium_remove$"))
    app.add_handler(CallbackQueryHandler(handlers.premium_list, pattern="^premium_list$"))
    app.add_handler(CallbackQueryHandler(handlers.toggle_unlock, pattern="^toggle_unlock$"))
    app.add_handler(CallbackQueryHandler(handlers.redeem_menu, pattern="^redeem_menu$"))
    app.add_handler(CallbackQueryHandler(handlers.redeem_generate, pattern="^redeem_generate$"))
    app.add_handler(CallbackQueryHandler(handlers.redeem_list, pattern="^redeem_list$"))
    app.add_handler(CallbackQueryHandler(handlers.domains_menu, pattern="^domains_menu$"))
    app.add_handler(CallbackQueryHandler(handlers.domain_selected, pattern="^dsel:"))
    app.add_handler(CallbackQueryHandler(handlers.admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(handlers.admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(handlers.admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(handlers.admin_cleanup, pattern="^admin_cleanup$"))
    app.add_handler(CallbackQueryHandler(handlers.admin_restart, pattern="^admin_restart$"))
    app.add_handler(CallbackQueryHandler(handlers.admin_backup, pattern="^admin_backup$"))
    app.add_handler(CallbackQueryHandler(handlers.terminal, pattern="^terminal:"))
    app.add_handler(CallbackQueryHandler(handlers.files, pattern="^files:"))

    # ---- Message handlers ----
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))

    app.add_error_handler(error_handler)
    logger.info("Bot is ready and running.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
