"""
PDF Exporter Module - Standalone PDF Generation System
Handles all PDF export functionality with 3 formats and cleanup
"""

import re
from typing import List, Dict
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from config import config

class PDFExporter:
    """Standalone PDF export manager with cleanup and 3 formats"""
    
    def __init__(self):
        self.pdf_sessions = {}  # {user_id: {'questions': [...], 'waiting_for_name': True}}
    
    @staticmethod
    def cleanup_text(text: str) -> str:
        """Remove [TSS] tags and similar patterns, and links"""
        if not text:
            return text
        
        # Remove [anything] patterns
        text = re.sub(r'\[[^\]]+\]', '', text)
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)
        text = re.sub(r't\.me/\S+', '', text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def cleanup_questions(questions: List[Dict]) -> List[Dict]:
        """Clean all questions and options"""
        cleaned = []
        for q in questions:
            cleaned_q = {
                'question_description': PDFExporter.cleanup_text(q.get('question_description', '')),
                'options': [PDFExporter.cleanup_text(opt) for opt in q.get('options', [])],
                'correct_answer_index': q.get('correct_answer_index', 0),
                'correct_option': q.get('correct_option', 'A'),
                'explanation': PDFExporter.cleanup_text(q.get('explanation', ''))
            }
            cleaned.append(cleaned_q)
        return cleaned
    
    def start_pdf_export(self, user_id: int, questions: List[Dict]):
        """Initialize PDF export session"""
        self.pdf_sessions[user_id] = {
            'questions': questions,
            'waiting_for_name': True,
            'waiting_for_format': False
        }
    
    def is_waiting_for_name(self, user_id: int) -> bool:
        """Check if waiting for PDF name"""
        return self.pdf_sessions.get(user_id, {}).get('waiting_for_name', False)
    
    def set_pdf_name(self, user_id: int, name: str):
        """Set PDF name and mark ready for format selection"""
        if user_id in self.pdf_sessions:
            self.pdf_sessions[user_id]['pdf_name'] = name
            self.pdf_sessions[user_id]['waiting_for_name'] = False
            self.pdf_sessions[user_id]['waiting_for_format'] = True
    
    def get_session(self, user_id: int) -> Dict:
        """Get PDF session data"""
        return self.pdf_sessions.get(user_id, {})
    
    def clear_session(self, user_id: int):
        """Clear PDF session"""
        if user_id in self.pdf_sessions:
            del self.pdf_sessions[user_id]
    
    # ==================== PDF FORMAT 1: COMPACT ====================
    
    @staticmethod
    def generate_format_1(questions: List[Dict], output_path, title: str):
        """Format 1: Compact - Question and options in single line"""
        doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                               topMargin=0.5*inch, bottomMargin=0.5*inch,
                               leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Questions
        for idx, q in enumerate(questions, 1):
            # Question number and text
            q_style = ParagraphStyle('Question', parent=styles['Normal'], 
                                    fontSize=10, spaceAfter=4, textColor=colors.HexColor('#000000'))
            story.append(Paragraph(f"<b>{idx}.</b> {q['question_description']}", q_style))
            
            # Options in compact format
            opts_text = " | ".join([f"({chr(65+i)}) {opt}" for i, opt in enumerate(q['options'])])
            opt_style = ParagraphStyle('Options', parent=styles['Normal'], 
                                      fontSize=9, spaceAfter=2, leftIndent=15)
            story.append(Paragraph(opts_text, opt_style))
            
            # Answer
            ans_style = ParagraphStyle('Answer', parent=styles['Normal'], 
                                      fontSize=9, spaceAfter=8, leftIndent=15, 
                                      textColor=colors.HexColor('#006400'))
            story.append(Paragraph(f"<b>Answer:</b> {q['correct_option']}", ans_style))
            
            if idx % 15 == 0 and idx < len(questions):
                story.append(PageBreak())
        
        doc.build(story)
    
    # ==================== PDF FORMAT 2: DETAILED ====================
    
    @staticmethod
    def generate_format_2(questions: List[Dict], output_path, title: str):
        """Format 2: Detailed - Each option on new line with explanation"""
        doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                               topMargin=0.5*inch, bottomMargin=0.5*inch,
                               leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                     fontSize=16, spaceAfter=12, alignment=TA_CENTER,
                                     textColor=colors.HexColor('#1a1a1a'))
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.3*inch))
        
        for idx, q in enumerate(questions, 1):
            # Question
            q_style = ParagraphStyle('Question', parent=styles['Normal'],
                                    fontSize=11, spaceAfter=8, textColor=colors.HexColor('#000000'),
                                    fontName='Helvetica-Bold')
            story.append(Paragraph(f"{idx}. {q['question_description']}", q_style))
            
            # Options - each on new line
            for i, opt in enumerate(q['options']):
                opt_letter = chr(65 + i)
                is_correct = (i == q['correct_answer_index'])
                opt_style = ParagraphStyle('Option', parent=styles['Normal'],
                                          fontSize=10, spaceAfter=3, leftIndent=20,
                                          textColor=colors.HexColor('#006400') if is_correct else colors.black)
                marker = "✓" if is_correct else "○"
                story.append(Paragraph(f"{marker} <b>{opt_letter}.</b> {opt}", opt_style))
            
            # Explanation
            if q.get('explanation'):
                exp_style = ParagraphStyle('Explanation', parent=styles['Normal'],
                                          fontSize=9, spaceAfter=15, leftIndent=20,
                                          textColor=colors.HexColor('#555555'),
                                          fontName='Helvetica-Oblique')
                story.append(Paragraph(f"<i>Explanation: {q['explanation']}</i>", exp_style))
            else:
                story.append(Spacer(1, 0.1*inch))
            
            if idx % 8 == 0 and idx < len(questions):
                story.append(PageBreak())
        
        doc.build(story)
    
    # ==================== PDF FORMAT 3: TABLE ====================
    
    @staticmethod
    def generate_format_3(questions: List[Dict], output_path, title: str):
        """Format 3: Table - Structured table format"""
        doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                               topMargin=0.5*inch, bottomMargin=0.5*inch,
                               leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                     fontSize=16, spaceAfter=12, alignment=TA_CENTER)
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Create table data
        for idx, q in enumerate(questions, 1):
            # Header row
            data = [[Paragraph(f"<b>Q{idx}:</b> {q['question_description']}", 
                             ParagraphStyle('QText', parent=styles['Normal'], fontSize=10))]]
            
            # Options rows
            for i, opt in enumerate(q['options']):
                opt_letter = chr(65 + i)
                is_correct = (i == q['correct_answer_index'])
                opt_para = Paragraph(
                    f"<b>{opt_letter}.</b> {opt}" + (" ✓" if is_correct else ""),
                    ParagraphStyle('OptText', parent=styles['Normal'], fontSize=9)
                )
                data.append([opt_para])
            
            # Answer row
            data.append([Paragraph(f"<b>Answer: {q['correct_option']}</b>",
                                 ParagraphStyle('Ans', parent=styles['Normal'], 
                                              fontSize=9, textColor=colors.green))])
            
            # Create table
            t = Table(data, colWidths=[6.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f2ff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#000000')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(t)
            story.append(Spacer(1, 0.15*inch))
            
            if idx % 5 == 0 and idx < len(questions):
                story.append(PageBreak())
        
        doc.build(story)
    
    # ==================== COMMAND HANDLERS ====================
    
    async def handle_pdf_export_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, questions: List[Dict]):
        """Start PDF export process"""
        user_id = update.effective_user.id if hasattr(update, 'effective_user') else update.callback_query.from_user.id
        
        self.start_pdf_export(user_id, questions)
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(
                "📄 *PDF Export*\n\n"
                "Please send the PDF name\n"
                "(without .pdf extension)\n\n"
                "Example: `MCQ_Questions_2024`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📄 *PDF Export*\n\n"
                "Please send the PDF name\n"
                "(without .pdf extension)\n\n"
                "Example: `MCQ_Questions_2024`",
                parse_mode='Markdown'
            )
    
    async def handle_pdf_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle PDF name input"""
        user_id = update.effective_user.id
        pdf_name = update.message.text.strip()
        
        # Clean filename
        pdf_name = re.sub(r'[<>:"/\|?*]', '', pdf_name)
        if not pdf_name:
            pdf_name = f"MCQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.set_pdf_name(user_id, pdf_name)
        
        # Show format selection
        keyboard = [
            [InlineKeyboardButton("📋 Compact Format", callback_data="pdf_format_1")],
            [InlineKeyboardButton("📝 Detailed Format", callback_data="pdf_format_2")],
            [InlineKeyboardButton("📊 Table Format", callback_data="pdf_format_3")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ PDF Name: `{pdf_name}.pdf`\n\n"
            f"📄 *Choose PDF Format:*\n\n"
            f"📋 *Compact* - Questions & options in lines\n"
            f"📝 *Detailed* - Each option separate with explanation\n"
            f"📊 *Table* - Structured table layout\n\n"
            f"Select format below:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, format_num: int):
        """Handle PDF format selection and generate"""
        query = update.callback_query
        user_id = query.from_user.id
        
        session = self.get_session(user_id)
        if not session or 'questions' not in session:
            await query.answer("❌ Session expired!")
            return
        
        questions = session['questions']
        pdf_name = session.get('pdf_name', f"MCQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        await query.edit_message_text("⏳ Generating PDF... Please wait...")
        
        # Clean questions
        cleaned_questions = self.cleanup_questions(questions)
        
        # Generate PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{pdf_name}_{timestamp}.pdf"
        pdf_path = config.OUTPUT_DIR / filename
        
        try:
            if format_num == 1:
                self.generate_format_1(cleaned_questions, pdf_path, pdf_name)
            elif format_num == 2:
                self.generate_format_2(cleaned_questions, pdf_path, pdf_name)
            elif format_num == 3:
                self.generate_format_3(cleaned_questions, pdf_path, pdf_name)
            
            # Send PDF
            with open(pdf_path, 'rb') as f:
                await context.bot.send_document(
                    user_id, f, filename=filename,
                    caption=f"✅ *PDF Generated!*\n\n"
                            f"📄 Name: {pdf_name}\n"
                            f"📊 Questions: {len(cleaned_questions)}\n"
                            f"🎨 Format: {'Compact' if format_num == 1 else 'Detailed' if format_num == 2 else 'Table'}",
                    parse_mode='Markdown'
                )
            
            # Cleanup
            pdf_path.unlink(missing_ok=True)
            self.clear_session(user_id)
            
            await query.answer("✅ PDF sent!")
            await query.message.reply_text("✅ PDF export complete!")
            
        except Exception as e:
            await query.answer("❌ Error!")
            await query.message.reply_text(f"❌ Error generating PDF: {e}")
            self.clear_session(user_id)

# Global instance
pdf_exporter = PDFExporter()
