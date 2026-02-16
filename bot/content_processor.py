import asyncio
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import config
from database import db
from processors.csv_processor import CSVGenerator
from processors.image_processor import ImageProcessor
from processors.quiz_poster import QuizPoster
from processors.pdf_processor import PDFProcessor

class ContentProcessor:
    def __init__(self, bot_handlers):
        self.bot_handlers = bot_handlers
    
    async def process_content(self, user_id, content_type, content_paths, page_range, mode, context):
        try:
            mode_emoji = "📤" if mode == "extraction" else "✨"
            
            if content_type == 'pdf':
                msg = await context.bot.send_message(user_id, "🔄 Processing PDF...")
                images = await PDFProcessor.pdf_to_images(content_paths[0], page_range)
            else:
                msg = await context.bot.send_message(user_id, "🔄 Processing images...")
                images = [await ImageProcessor.load_image(p) for p in content_paths]
            
            async def progress(current, total):
                try:
                    await msg.edit_text(f"🔍 {current}/{total}")
                except:
                    pass
            
            questions = await self.bot_handlers.pdf_processor.process_images_parallel(images, mode, progress)
            if not questions:
                await msg.edit_text("❌ No questions found")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"gen_{user_id}_{timestamp}"
            csv_path = config.OUTPUT_DIR / f"questions_{session_id}.csv"
            CSVGenerator.questions_to_csv(questions, csv_path)
            
            self.bot_handlers.user_states[user_id] = {
                'questions': questions,
                'session_id': session_id,
                'csv_path': csv_path,
                'source': 'generated'
            }
            
            # Add PDF export button
            keyboard = [
                [InlineKeyboardButton("📢 Post Quizzes", callback_data=f"post_{session_id}")],
                [InlineKeyboardButton("📄 Export PDF", callback_data=f"export_pdf_{session_id}")]
            ]
            with open(csv_path, 'rb') as f:
                await context.bot.send_document(
                    user_id, f, filename=f"mcq_{timestamp}.csv",
                    caption=f"✅ {len(questions)} questions!\n\nChoose an action below:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            await msg.edit_text(f"✅ Done! {len(questions)} questions")
            
            for p in content_paths:
                if p.exists():
                    p.unlink(missing_ok=True)
        except Exception as e:
            await context.bot.send_message(user_id, f"❌ Error: {e}")
    
    async def post_quizzes_to_destination(self, user_id, chat_id, thread_id, context, status_msg):
        if user_id not in self.bot_handlers.user_states:
            return
        
        questions = self.bot_handlers.user_states[user_id]['questions']
        settings = db.get_user_settings(user_id)
        
        await status_msg.edit_text(f"📢 Posting {len(questions)} quizzes...")
        
        async def progress(current, total):
            try:
                await status_msg.edit_text(f"📢 {current}/{total}")
            except:
                pass
        
        result = await QuizPoster.post_quizzes_batch(
            context, chat_id, questions,
            settings['quiz_marker'], settings['explanation_tag'],
            thread_id, progress
        )
        
        await status_msg.edit_text(f"✅ Complete!\nSuccess: {result['success']}\nFailed: {result['failed']}")
        
        if user_id in self.bot_handlers.user_states:
            del self.bot_handlers.user_states[user_id]
