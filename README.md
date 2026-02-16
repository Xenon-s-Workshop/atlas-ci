# TSS Bot - Complete Telegram MCQ Quiz Bot

Advanced Telegram bot for MCQ quiz management with AI, authorization, poll collection, and PDF export.

## 🎯 Features

- 🤖 **AI-Powered**: Gemini 2.0 Flash for intelligent quiz generation
- 🔐 **Authorization System**: Sudo mode + user authorization
- 📮 **Poll Collection**: Collect Telegram polls with auto-delete & cleanup
- 📄 **PDF Export**: 3 professional formats with custom naming
- 📊 **CSV Support**: Import/export with automatic cleanup
- 📢 **Multi-Channel**: Post to multiple channels/groups
- 🧵 **Topic Support**: Group topics (forum) support
- ⚡ **Fast Processing**: 10 parallel workers
- ✨ **Data Cleanup**: Auto-remove [tags] and links

## 📁 Project Structure

```
tss-bot-final/
├── main.py                           # Entry point
├── config.py                         # Configuration
├── database.py                       # MongoDB with auth
├── requirements.txt                  # Dependencies
├── README.md                         # Complete docs
├── .gitignore                        # Git ignore
│
├── bot/                              # Bot layer
│   ├── handlers.py                  # Command handlers
│   ├── callbacks.py                 # Button callbacks
│   └── content_processor.py         # Content processing
│
├── processors/                       # Processing layer
│   ├── poll_collector.py           # ⭐ STANDALONE POLL MODULE
│   ├── pdf_exporter.py             # ⭐ STANDALONE PDF MODULE
│   ├── pdf_processor.py            # PDF image processing
│   ├── csv_processor.py            # CSV operations
│   ├── image_processor.py          # Image loading
│   └── quiz_poster.py              # Quiz posting
│
├── utils/                            # Utilities
│   ├── auth.py                     # Authorization
│   ├── api_rotator.py              # API rotation
│   └── queue_manager.py            # Task queue
│
└── prompts/                          # AI prompts
    ├── extraction_prompt.py
    └── generation_prompt.py
```

## 🎨 New Features

### 📄 PDF Export (3 Formats)

**Format 1: Compact**
- Questions and options in single lines
- Space-efficient layout
- ~15 questions per page

**Format 2: Detailed**
- Each option on separate line
- Explanations included
- Visual checkmarks for correct answers
- ~8 questions per page

**Format 3: Table**
- Structured table layout
- Color-coded sections
- Professional appearance
- ~5 questions per page

### ✨ Automatic Cleanup

All exports (CSV & PDF) automatically clean:
- ✅ Removes `[TSS]` and all `[...]` patterns
- ✅ Removes URLs and links (http://, www., t.me/)
- ✅ Cleans extra spaces
- ✅ Preserves question integrity

### 🎯 Custom PDF Names

When exporting to PDF:
1. Bot prompts for custom name
2. Enter desired name (e.g., "Biology_Quiz_2024")
3. Choose from 3 formats
4. Receive formatted PDF

## 🚀 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
GEMINI_API_KEYS=key1,key2,key3
MONGODB_URI=mongodb://localhost:27017/
SUDO_USER_IDS=123456789,987654321
AUTH_ENABLED=true
QUIZ_MARKER=[TSS]
EXPLANATION_TAG=t.me/tss
```

### 3. Run
```bash
python main.py
```

## 📋 Commands

### User Commands
- `/start` - Welcome message
- `/help` - Help guide
- `/info` - Chat/topic information (shows thread ID!)
- `/collectpolls` - **Start poll collection**
- `/settings` - Configure channels/groups
- `/queue` - Check queue
- `/cancel` - Cancel task
- `/model` - AI model info

### Admin Commands (Sudo Only)
- `/authorize <user_id>` - Authorize user
- `/revoke <user_id>` - Revoke access
- `/users` - List authorized users

## 🎯 Usage Workflows

### Generate Quizzes from PDF/Images
1. Send PDF or images
2. Choose Extraction or Generation mode
3. Receive CSV file
4. Choose action:
   - **📢 Post Quizzes** - Post to channels
   - **📄 Export PDF** - Generate formatted PDF

### Collect Polls
1. Use `/collectpolls`
2. Forward Telegram polls
3. Polls auto-deleted from chat
4. Live counter updates
5. Export options:
   - **📊 Export CSV** - Cleaned CSV format
   - **📄 Export PDF** - Custom name + format selection

### CSV to PDF Conversion
1. Send CSV file
2. Choose action:
   - **📢 Post Quizzes**
   - **📄 Convert to PDF** - Enter name + select format

### PDF Export Process
1. Click "📄 Export PDF"
2. Enter custom name (e.g., "Final_Exam_2024")
3. Choose format:
   - 📋 Compact
   - 📝 Detailed
   - 📊 Table
4. Receive formatted PDF

## ⚙️ Configuration

- **Workers**: 10 parallel image processors
- **Batch Size**: 30 quizzes per batch
- **Poll Delay**: 1.5s between polls
- **Queue**: 20 tasks maximum
- **Auth**: Toggle-able authorization
- **Cleanup**: Automatic on all exports

## 🔐 Authorization

- **AUTH_ENABLED**: Enable/disable authorization
- **Sudo Users**: Set via SUDO_USER_IDS
- **User Management**: Sudo users can authorize/revoke
- **Multi-user**: Unlimited authorized users

## 📮 Poll Collection Features

Poll collection in `processors/poll_collector.py`:
- ✅ Completely independent module
- ✅ In-memory storage (no database)
- ✅ Auto-delete forwarded polls
- ✅ Live counter updates
- ✅ **Automatic cleanup** of [tags] and links
- ✅ CSV and PDF export options
- ✅ Multi-user support

## 📄 PDF Export Features

PDF export in `processors/pdf_exporter.py`:
- ✅ Standalone module
- ✅ 3 professional formats
- ✅ Custom PDF naming
- ✅ **Automatic cleanup**
- ✅ High-quality layout
- ✅ ReportLab powered

## 📊 Data Cleanup

**What gets removed:**
- `[TSS]`, `[anything]` patterns
- URLs: `https://`, `http://`, `www.`
- Telegram links: `t.me/`
- Extra whitespace

**Applied to:**
- Questions
- Options  
- Explanations
- Both CSV and PDF exports
- Both poll collection and question generation

## 📝 CSV Format

```csv
questions,option1,option2,option3,option4,option5,answer,explanation,type,section
```

## 🛠️ Tech Stack

- Python 3.10+
- python-telegram-bot 20.7
- Google Gemini 2.0 Flash
- MongoDB
- ReportLab (PDF generation)
- PDF2Image
- Pillow

## 📁 Module Architecture

**Standalone Modules:**
1. `processors/poll_collector.py` - Complete poll collection system
2. `processors/pdf_exporter.py` - Complete PDF export system

**Integration:**
- `bot/handlers.py` - Imports and delegates to modules
- `bot/callbacks.py` - Routes callbacks to appropriate modules
- Clean separation of concerns

## 📝 License

MIT

## 💬 Support

For issues, contact the bot administrator.
