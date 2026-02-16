"""
Bot Callbacks - Button callback handlers
Poll collection callbacks delegated to processors/poll_collector.py
PDF export callbacks delegated to processors/pdf_exporter.py
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from processors.poll_collector import poll_collector
from processors.pdf_exporter import pdf_exporter

class CallbackHandlers:
    def __init__(self, bot_handlers):
        self.bot_handlers = bot_handlers
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        data = query.data
        
        # Poll collection callbacks - delegate to standalone module
        if data == "poll_export_csv":
            await poll_collector.handle_export_csv_callback(update, context)
        
        elif data == "poll_export_pdf":
            await poll_collector.handle_export_pdf_callback(update, context)
        
        elif data == "poll_clear":
            await poll_collector.handle_clear_callback(update, context)
        
        elif data == "poll_stop":
            await poll_collector.handle_stop_callback(update, context)
        
        # PDF export callbacks - delegate to pdf_exporter
        elif data.startswith("export_pdf_"):
            session_id = data[11:]
            if user_id not in self.bot_handlers.user_states:
                await query.edit_message_text("❌ Session expired.")
                return
            questions = self.bot_handlers.user_states[user_id].get('questions', [])
            if not questions:
                await query.answer("❌ No questions available!")
                return
            await pdf_exporter.handle_pdf_export_start(update, context, questions)
        
        elif data.startswith("pdf_format_"):
            format_num = int(data.split("_")[-1])
            await pdf_exporter.handle_format_selection(update, context, format_num)
        
        # CSV to PDF conversion
        elif data.startswith("csv_to_pdf_"):
            session_id = data[11:]
            if user_id not in self.bot_handlers.user_states:
                await query.edit_message_text("❌ Session expired.")
                return
            questions = self.bot_handlers.user_states[user_id].get('questions', [])
            if not questions:
                await query.answer("❌ No questions available!")
                return
            await pdf_exporter.handle_pdf_export_start(update, context, questions)
        
        # Mode selection
        elif data.startswith("mode_"):
            mode = data.split("_")[1]
            if user_id not in self.bot_handlers.user_states:
                await query.edit_message_text("❌ Session expired.")
                return
            self.bot_handlers.user_states[user_id]['mode'] = mode
            await query.edit_message_text(f"✅ Mode: {mode}\nAdding to queue...")
            await self.bot_handlers.add_to_queue_direct(user_id, None, context)
        
        # Post quizzes
        elif data.startswith("post_"):
            session_id = data[5:]
            if user_id not in self.bot_handlers.user_states:
                await query.edit_message_text("❌ Session expired.")
                return
            channels = db.get_user_channels(user_id)
            groups = db.get_user_groups(user_id)
            if not channels and not groups:
                await query.edit_message_text("❌ No channels/groups. Use /settings")
                return
            keyboard = []
            for ch in channels:
                keyboard.append([InlineKeyboardButton(f"📺 {ch['channel_name']}", callback_data=f"dest_ch_{ch['channel_id']}_{session_id}")])
            for gr in groups:
                keyboard.append([InlineKeyboardButton(f"👥 {gr['group_name']}", callback_data=f"dest_gr_{gr['group_id']}_{session_id}")])
            await query.edit_message_text("📢 Select destination:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith("dest_ch_"):
            parts = data.split("_")
            channel_id = int(parts[2])
            await query.edit_message_text("📺 Posting...")
            from bot.content_processor import ContentProcessor
            processor = ContentProcessor(self.bot_handlers)
            await processor.post_quizzes_to_destination(user_id, channel_id, None, context, query.message)
        
        elif data.startswith("dest_gr_"):
            parts = data.split("_")
            group_id = int(parts[2])
            session_id = "_".join(parts[3:])
            self.bot_handlers.user_states[user_id]['selected_group'] = group_id
            self.bot_handlers.user_states[user_id]['post_session'] = session_id
            await query.edit_message_text("🔢 Send *Topic ID* (or 0):", parse_mode='Markdown')
            self.bot_handlers.user_states[user_id]['waiting_for'] = 'topic_id'
        
        # Settings
        elif data == "settings_add_channel":
            await query.edit_message_text("📺 Send: `channel_id channel_name`", parse_mode='Markdown')
            self.bot_handlers.user_states[user_id] = {'waiting_for': 'add_channel'}
        
        elif data == "settings_add_group":
            await query.edit_message_text("👥 Send: `group_id group_name`", parse_mode='Markdown')
            self.bot_handlers.user_states[user_id] = {'waiting_for': 'add_group'}
        
        elif data == "settings_manage_channels":
            channels = db.get_user_channels(user_id)
            if not channels:
                await query.edit_message_text("❌ No channels.")
                return
            keyboard = [[InlineKeyboardButton(f"❌ {ch['channel_name']}", callback_data=f"del_ch_{str(ch['_id'])}")] for ch in channels]
            await query.edit_message_text("📺 Manage:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data == "settings_manage_groups":
            groups = db.get_user_groups(user_id)
            if not groups:
                await query.edit_message_text("❌ No groups.")
                return
            keyboard = [[InlineKeyboardButton(f"❌ {gr['group_name']}", callback_data=f"del_gr_{str(gr['_id'])}")] for gr in groups]
            await query.edit_message_text("👥 Manage:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith("del_ch_"):
            db.delete_channel(data[7:])
            await query.answer("✅ Deleted!")
        
        elif data.startswith("del_gr_"):
            db.delete_group(data[7:])
            await query.answer("✅ Deleted!")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Check if waiting for PDF name
        if pdf_exporter.is_waiting_for_name(user_id):
            await pdf_exporter.handle_pdf_name_input(update, context)
            return
        
        if user_id not in self.bot_handlers.user_states:
            return
        
        waiting_for = self.bot_handlers.user_states[user_id].get('waiting_for')
        text = update.message.text.strip()
        
        if waiting_for == 'add_channel':
            try:
                parts = text.split(" ", 1)
                if len(parts) < 2:
                    await update.message.reply_text("❌ Invalid format.")
                    return
                db.add_channel(user_id, int(parts[0]), parts[1])
                await update.message.reply_text("✅ Channel added!")
                del self.bot_handlers.user_states[user_id]
            except:
                await update.message.reply_text("❌ Invalid ID.")
        
        elif waiting_for == 'add_group':
            try:
                parts = text.split(" ", 1)
                if len(parts) < 2:
                    await update.message.reply_text("❌ Invalid format.")
                    return
                db.add_group(user_id, int(parts[0]), parts[1])
                await update.message.reply_text("✅ Group added!")
                del self.bot_handlers.user_states[user_id]
            except:
                await update.message.reply_text("❌ Invalid ID.")
        
        elif waiting_for == 'topic_id':
            try:
                topic_id = int(text)
                group_id = self.bot_handlers.user_states[user_id]['selected_group']
                thread_id = topic_id if topic_id > 0 else None
                msg = await update.message.reply_text("👥 Posting...")
                from bot.content_processor import ContentProcessor
                processor = ContentProcessor(self.bot_handlers)
                await processor.post_quizzes_to_destination(user_id, group_id, thread_id, context, msg)
                del self.bot_handlers.user_states[user_id]
            except:
                await update.message.reply_text("❌ Invalid topic ID.")
