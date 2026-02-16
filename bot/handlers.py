"""
Bot Handlers - Main command handlers
Poll collection logic is in processors/poll_collector.py
"""

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import config
from database import db
from processors.csv_processor import CSVParser
from processors.poll_collector import poll_collector  # Import standalone module
from utils.queue_manager import task_queue
from utils.auth import require_auth, require_sudo

class BotHandlers:
    def __init__(self, pdf_processor):
        self.user_states = {}
        self.pdf_processor = pdf_processor
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.first_name or "User"
        
        if not db.is_authorized(user_id):
            await update.message.reply_text(
                f"🔒 *Access Denied*\n\n"
                f"Hello {username}!\n\n"
                f"You are not authorized to use {config.BOT_NAME}.\n"
                f"Please contact an administrator for access.",
                parse_mode='Markdown'
            )
            return
        
        settings = db.get_user_settings(user_id)
        is_sudo = db.is_sudo(user_id)
        
        welcome = f"👋 *Welcome to {config.BOT_NAME}!*\n\n"
        welcome += f"Hello {username}! 🎓\n\n"
        welcome += "📚 *What I can do:*\n"
        welcome += "• 📄 Process PDF files\n"
        welcome += "• 🖼️ Analyze images\n"
        welcome += "• 📊 Import CSV files\n"
        welcome += "• 📮 Collect Telegram polls\n"
        welcome += "• 🤖 Generate MCQs with AI\n"
        welcome += "• 📢 Post to channels/groups\n\n"
        
        welcome += "⚙️ *Your Settings:*\n"
        welcome += f"📢 Quiz Marker: `{settings['quiz_marker']}`\n"
        welcome += f"🔗 Tag: `{settings['explanation_tag']}`\n\n"
        
        welcome += "📋 *Commands:*\n"
        welcome += "/help - Detailed help\n"
        welcome += "/settings - Configure\n"
        welcome += "/info - Chat info\n"
        welcome += "/collectpolls - Start poll collection\n"
        welcome += "/queue - Queue status\n"
        welcome += "/cancel - Cancel task\n"
        
        if is_sudo:
            welcome += "\n🔐 *Admin:*\n"
            welcome += "/authorize /revoke /users\n"
        
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    @require_auth
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = f"📚 *{config.BOT_NAME} - Help*\n\n"
        help_text += "🎯 *Generate from PDF/Images:*\n"
        help_text += "1️⃣ Send PDF/images\n"
        help_text += "2️⃣ Choose mode (Extraction/Generation)\n"
        help_text += "3️⃣ Get CSV\n"
        help_text += "4️⃣ Post quizzes\n\n"
        
        help_text += "📮 *Collect Polls:*\n"
        help_text += "1️⃣ /collectpolls\n"
        help_text += "2️⃣ Forward polls\n"
        help_text += "3️⃣ Auto-deleted\n"
        help_text += "4️⃣ Export CSV\n\n"
        
        help_text += "📊 *Post from CSV:*\n"
        help_text += "1️⃣ Send CSV\n"
        help_text += "2️⃣ Select destination\n"
        help_text += "3️⃣ Auto-post\n\n"
        
        help_text += "✨ *Features:*\n"
        help_text += "✓ AI-powered\n"
        help_text += "✓ Fast processing\n"
        help_text += "✓ Multi-channel\n"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    @require_auth
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        message = update.message
        
        info_text = f"📊 *Chat Info*\n\n"
        info_text += f"🆔 ID: `{chat.id}`\n"
        info_text += f"📛 Title: {chat.title or 'N/A'}\n"
        info_text += f"📝 Type: {chat.type}\n"
        
        if message.message_thread_id:
            info_text += f"🧵 Topic ID: `{message.message_thread_id}`\n"
        
        try:
            if chat.type in ['supergroup', 'group']:
                chat_full = await context.bot.get_chat(chat.id)
                is_forum = getattr(chat_full, 'is_forum', False)
                info_text += f"📑 Topics: {'Yes' if is_forum else 'No'}\n"
                
                if is_forum and not message.message_thread_id:
                    info_text += f"\n💡 Send /info in a topic to get its ID!\n"
        except:
            pass
        
        await update.message.reply_text(info_text, parse_mode='Markdown')
    
    @require_auth
    async def collectpolls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delegate to standalone poll_collector module"""
        await poll_collector.handle_start_command(update, context)
    
    @require_auth
    async def handle_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delegate to standalone poll_collector module"""
        await poll_collector.handle_poll_message(update, context)
    
    @require_sudo
    async def authorize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: /authorize <user_id>")
            return
        try:
            target_user_id = int(context.args[0])
            db.authorize_user(target_user_id, update.effective_user.id)
            await update.message.reply_text(f"✅ User {target_user_id} authorized!")
        except:
            await update.message.reply_text("❌ Invalid user ID.")
    
    @require_sudo
    async def revoke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: /revoke <user_id>")
            return
        try:
            target_user_id = int(context.args[0])
            if db.is_sudo(target_user_id):
                await update.message.reply_text("❌ Cannot revoke sudo!")
                return
            db.revoke_user(target_user_id)
            await update.message.reply_text(f"✅ Revoked {target_user_id}!")
        except:
            await update.message.reply_text("❌ Invalid user ID.")
    
    @require_sudo
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users = db.get_authorized_users()
        if not users:
            await update.message.reply_text("No users.")
            return
        text = f"👥 *Authorized ({len(users)}):*\n\n"
        for user in users:
            badge = "🔐" if user.get('is_sudo') else "👤"
            text += f"{badge} `{user['user_id']}`\n"
        await update.message.reply_text(text, parse_mode='Markdown')
    
    @require_auth
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)
        channels = db.get_user_channels(user_id)
        groups = db.get_user_groups(user_id)
        
        keyboard = [
            [InlineKeyboardButton("➕ Channel", callback_data="settings_add_channel")],
            [InlineKeyboardButton("➕ Group", callback_data="settings_add_group")],
            [InlineKeyboardButton("📺 Channels", callback_data="settings_manage_channels")],
            [InlineKeyboardButton("👥 Groups", callback_data="settings_manage_groups")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚙️ *Settings*\n\n"
            f"📢 Marker: `{settings['quiz_marker']}`\n"
            f"🔗 Tag: `{settings['explanation_tag']}`\n\n"
            f"📺 Channels: {len(channels)}\n"
            f"👥 Groups: {len(groups)}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @require_auth
    async def model_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"🤖 Model: `{config.GEMINI_MODEL}`\n"
            f"Workers: {config.MAX_CONCURRENT_IMAGES}\n"
            f"Queue: {task_queue.get_queue_size()}/{config.MAX_QUEUE_SIZE}",
            parse_mode='Markdown'
        )
    
    @require_auth
    async def queue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if task_queue.is_processing(user_id):
            await update.message.reply_text("⚙️ Processing...")
        else:
            pos = task_queue.get_position(user_id)
            msg = f"📋 Position: {pos}" if pos > 0 else "❌ No tasks"
            await update.message.reply_text(msg)
    
    @require_auth
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        task_queue.clear_user(user_id)
        if user_id in self.user_states:
            del self.user_states[user_id]
        await update.message.reply_text("✅ Cancelled!")
    
    @require_auth
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        doc = update.message.document
        
        if doc.file_name.endswith('.csv'):
            await self.handle_csv(update, context)
            return
        
        if not doc.file_name.endswith('.pdf'):
            await update.message.reply_text("❌ Send PDF or CSV only.")
            return
        
        if user_id in self.user_states or task_queue.is_processing(user_id):
            await update.message.reply_text("⚠️ Task in progress. Use /cancel")
            return
        
        msg = await update.message.reply_text("📥 Downloading...")
        try:
            file = await context.bot.get_file(doc.file_id)
            path = config.TEMP_DIR / f"{user_id}_{doc.file_name}"
            await file.download_to_drive(path)
            
            keyboard = [
                [InlineKeyboardButton("📤 Extraction", callback_data="mode_extraction")],
                [InlineKeyboardButton("✨ Generation", callback_data="mode_generation")]
            ]
            self.user_states[user_id] = {'content_type': 'pdf', 'content_paths': [path]}
            await msg.edit_text("📄 PDF received! Choose mode:", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await msg.edit_text(f"❌ Error: {e}")
    
    @require_auth
    async def handle_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.user_states or task_queue.is_processing(user_id):
            await update.message.reply_text("⚠️ Task in progress.")
            return
        
        msg = await update.message.reply_text("📊 Processing...")
        try:
            file = await context.bot.get_file(update.message.document.file_id)
            content = await file.download_as_bytearray()
            questions = CSVParser.parse_csv_file(bytes(content))
            
            if not questions:
                await msg.edit_text("❌ No valid questions.")
                return
            
            session_id = f"csv_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.user_states[user_id] = {'questions': questions, 'session_id': session_id, 'source': 'csv'}
            
            keyboard = [
                [InlineKeyboardButton("📢 Post Quizzes", callback_data=f"post_{session_id}")],
                [InlineKeyboardButton("📄 Convert to PDF", callback_data=f"csv_to_pdf_{session_id}")]
            ]
            await msg.edit_text(
                f"✅ CSV Processed!\n📊 Questions: {len(questions)}\n\nChoose an action:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            await msg.edit_text(f"❌ Error: {e}")
    
    @require_auth
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.user_states or task_queue.is_processing(user_id):
            await update.message.reply_text("⚠️ Task in progress.")
            return
        
        msg = await update.message.reply_text("📥 Downloading...")
        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            path = config.TEMP_DIR / f"{user_id}_image.jpg"
            await file.download_to_drive(path)
            
            keyboard = [
                [InlineKeyboardButton("📤 Extraction", callback_data="mode_extraction")],
                [InlineKeyboardButton("✨ Generation", callback_data="mode_generation")]
            ]
            self.user_states[user_id] = {'content_type': 'images', 'content_paths': [path]}
            await msg.edit_text("🖼️ Choose mode:", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await msg.edit_text(f"❌ Error: {e}")
    
    async def add_to_queue_direct(self, user_id, page_range, context):
        if user_id not in self.user_states:
            return
        mode = self.user_states[user_id].get('mode', 'extraction')
        task_data = {
            'content_type': self.user_states[user_id]['content_type'],
            'content_paths': self.user_states[user_id]['content_paths'],
            'page_range': page_range,
            'mode': mode,
            'context': context
        }
        pos = task_queue.add_task(user_id, task_data)
        msg = "❌ Queue full" if pos == -1 else ("⚠️ Already queued" if pos == -2 else f"✅ Queued! Position: {pos}")
        await context.bot.send_message(user_id, msg)
