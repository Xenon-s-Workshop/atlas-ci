from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database import db
from config import config

def require_auth(func):
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not db.is_authorized(user_id):
            username = update.effective_user.username or "User"
            await update.message.reply_text(
                f"🔒 *Access Denied*\n\n"
                f"@{username}, you are not authorized to use {config.BOT_NAME}.\n\n"
                f"Please contact an administrator for access.",
                parse_mode='Markdown'
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper

def require_sudo(func):
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not db.is_sudo(user_id):
            await update.message.reply_text(
                "🔐 *Sudo Access Required*\n\n"
                "This command requires administrator privileges.",
                parse_mode='Markdown'
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper
