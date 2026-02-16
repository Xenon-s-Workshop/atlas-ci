"""
Poll Collector Module - Completely Independent Poll Collection System
Handles all poll collection functionality without database storage
NOW WITH CSV CLEANUP
"""

from typing import List, Dict
from datetime import datetime
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from processors.csv_processor import CSVGenerator
from processors.pdf_exporter import PDFExporter  # Import for cleanup
from config import config

class PollCollector:
    """Standalone poll collection manager with in-memory storage"""
    
    def __init__(self):
        self.collections = {}  # {user_id: [poll_data, ...]}
        self.status_messages = {}  # {user_id: message_id}
    
    def is_collecting(self, user_id: int) -> bool:
        """Check if user is in collection mode"""
        return user_id in self.collections
    
    def start_collection(self, user_id: int):
        """Initialize collection for user"""
        self.collections[user_id] = []
        return True
    
    def stop_collection(self, user_id: int):
        """Stop collection and cleanup"""
        if user_id in self.collections:
            del self.collections[user_id]
        if user_id in self.status_messages:
            del self.status_messages[user_id]
        return True
    
    def add_poll(self, user_id: int, poll: Poll) -> int:
        """Add poll to collection and return count"""
        if user_id not in self.collections:
            return 0
        
        options = [opt.text for opt in poll.options]
        correct_index = -1
        
        if poll.type == 'quiz':
            correct_index = poll.correct_option_id if poll.correct_option_id is not None else 0
        
        poll_data = {
            'question': poll.question,
            'options': options,
            'correct_index': correct_index,
            'explanation': poll.explanation or ''
        }
        
        self.collections[user_id].append(poll_data)
        return len(self.collections[user_id])
    
    def get_count(self, user_id: int) -> int:
        """Get total polls collected"""
        return len(self.collections.get(user_id, []))
    
    def get_polls(self, user_id: int) -> List[Dict]:
        """Get all collected polls"""
        return self.collections.get(user_id, [])
    
    def clear_polls(self, user_id: int):
        """Clear all polls but keep collection active"""
        if user_id in self.collections:
            self.collections[user_id] = []
    
    def set_status_message(self, user_id: int, message_id: int):
        """Track status message for live updates"""
        self.status_messages[user_id] = message_id
    
    def get_status_message(self, user_id: int) -> int:
        """Get status message ID"""
        return self.status_messages.get(user_id)
    
    # ==================== COMMAND HANDLERS ====================
    
    async def handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /collectpolls command"""
        user_id = update.effective_user.id
        
        if self.is_collecting(user_id):
            # Already collecting - show status
            count = self.get_count(user_id)
            keyboard = [
                [InlineKeyboardButton("📊 Export CSV", callback_data="poll_export_csv")],
                [InlineKeyboardButton("📄 Export PDF", callback_data="poll_export_pdf")],
                [InlineKeyboardButton("🗑️ Clear & Restart", callback_data="poll_clear")],
                [InlineKeyboardButton("❌ Stop Collection", callback_data="poll_stop")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"📮 *Poll Collection Active*\n\n"
                f"📊 Collected: {count} polls\n\n"
                f"✅ Forward or send polls to collect\n"
                f"🗑️ Forwarded polls auto-deleted\n\n"
                f"Use buttons below to export or manage:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # Start new collection
            self.start_collection(user_id)
            keyboard = [[InlineKeyboardButton("❌ Stop Collection", callback_data="poll_stop")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            msg = await update.message.reply_text(
                f"📮 *Poll Collection Started!*\n\n"
                f"📊 Collected: 0 polls\n\n"
                f"✅ Forward or send polls to me\n"
                f"🗑️ Forwarded polls will be auto-deleted\n"
                f"📈 Counter updates live\n\n"
                f"Click buttons when done!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            self.set_status_message(user_id, msg.message_id)
    
    async def handle_poll_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming poll messages"""
        user_id = update.effective_user.id
        
        if not self.is_collecting(user_id):
            return
        
        poll = update.message.poll or update.poll
        if not poll:
            return
        
        # Add poll to collection
        count = self.add_poll(user_id, poll)
        
        # Delete the forwarded poll message
        try:
            await update.message.delete()
        except:
            pass
        
        # Update status message
        status_msg_id = self.get_status_message(user_id)
        if status_msg_id:
            try:
                keyboard = [
                    [InlineKeyboardButton("📊 Export CSV", callback_data="poll_export_csv")],
                    [InlineKeyboardButton("📄 Export PDF", callback_data="poll_export_pdf")],
                    [InlineKeyboardButton("🗑️ Clear & Restart", callback_data="poll_clear")],
                    [InlineKeyboardButton("❌ Stop Collection", callback_data="poll_stop")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_msg_id,
                    text=f"📮 *Poll Collection Active!*\n\n"
                         f"📊 Collected: {count} polls\n\n"
                         f"✅ Keep forwarding polls\n"
                         f"🗑️ Auto-deleting forwarded polls\n"
                         f"📈 Live counter updating\n\n"
                         f"Click buttons when done!",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except:
                pass
    
    async def handle_export_csv_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle CSV export button"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        polls = self.get_polls(user_id)
        if not polls:
            await query.answer("❌ No polls collected yet!")
            return
        
        # Convert to question format and CLEAN
        questions_raw = [
            {
                'question_description': p['question'],
                'options': p['options'],
                'correct_answer_index': p['correct_index'],
                'explanation': p['explanation']
            }
            for p in polls
        ]
        
        # CLEANUP using PDFExporter cleanup
        questions_cleaned = PDFExporter.cleanup_questions(questions_raw)
        
        # Generate CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = config.OUTPUT_DIR / f"polls_{user_id}_{timestamp}.csv"
        CSVGenerator.questions_to_csv(questions_cleaned, csv_path)
        
        # Send CSV file
        with open(csv_path, 'rb') as f:
            await context.bot.send_document(
                user_id, f, filename=f"collected_polls_{timestamp}.csv",
                caption=f"📊 *CSV Export Complete!*\n\n"
                        f"Total: {len(polls)} polls\n"
                        f"✨ Cleaned (removed [tags] & links)\n"
                        f"Format: Standard CSV",
                parse_mode='Markdown'
            )
        
        # Cleanup
        csv_path.unlink(missing_ok=True)
        await query.answer("✅ CSV exported!")
        
        await query.edit_message_text(
            f"✅ *CSV Export Complete!*\n\n"
            f"📊 Exported: {len(polls)} polls\n"
            f"✨ Cleaned data\n\n"
            f"Collection still active.\n"
            f"Use /collectpolls to manage.",
            parse_mode='Markdown'
        )
    
    async def handle_export_pdf_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle PDF export button"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        polls = self.get_polls(user_id)
        if not polls:
            await query.answer("❌ No polls collected yet!")
            return
        
        # Convert to question format
        questions = [
            {
                'question_description': p['question'],
                'options': p['options'],
                'correct_answer_index': p['correct_index'],
                'correct_option': chr(65 + p['correct_index']) if p['correct_index'] >= 0 else 'A',
                'explanation': p['explanation']
            }
            for p in polls
        ]
        
        # Delegate to PDF exporter
        from processors.pdf_exporter import pdf_exporter
        await pdf_exporter.handle_pdf_export_start(update, context, questions)
    
    async def handle_clear_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clear polls button"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        self.clear_polls(user_id)
        keyboard = [[InlineKeyboardButton("❌ Stop Collection", callback_data="poll_stop")]]
        await query.answer("🗑️ Polls cleared!")
        await query.edit_message_text(
            "🗑️ *Polls Cleared!*\n\n"
            "📊 Collected: 0 polls\n\n"
            "Start forwarding polls again!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_stop_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle stop collection button"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        count = self.get_count(user_id)
        self.stop_collection(user_id)
        await query.answer("❌ Collection stopped!")
        await query.edit_message_text(
            f"❌ *Poll Collection Stopped*\n\n"
            f"📊 Final count: {count} polls\n\n"
            f"Use /collectpolls to start again.",
            parse_mode='Markdown'
        )

# Global instance
poll_collector = PollCollector()
