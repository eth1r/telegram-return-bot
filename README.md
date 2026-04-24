# 🤖 Telegram Product Return Bot

AI-powered Telegram bot for automated product return request processing using OpenAI GPT. Conducts natural conversations, intelligently collects data, and sends structured requests to operators.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![aiogram](https://img.shields.io/badge/aiogram-3.13.1-blue.svg)](https://docs.aiogram.dev/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-green.svg)](https://openai.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 🎯 What It Does

This bot automates the product return process by:
- Having natural conversations with customers using GPT
- Extracting structured data from free-form text
- Validating all inputs with domain-specific rules
- Protecting collected data from accidental overwrites
- Sending formatted requests to operator chat

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Telegram  │─────▶│  Bot Handler │─────▶│  Workflow   │
│    User     │◀─────│   (aiogram)  │◀─────│   Service   │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                     ┌─────────────────────────────┼─────────────┐
                     │                             │             │
              ┌──────▼──────┐            ┌────────▼────────┐   ┌▼──────────┐
              │   OpenAI    │            │  Session Store  │   │ Operator  │
              │  Assistant  │            │   (in-memory)   │   │ Notifier  │
              └─────────────┘            └─────────────────┘   └───────────┘
```

## 🛠️ Tech Stack

- **Python 3.12+** - Core language
- **aiogram 3.13** - Telegram Bot framework
- **OpenAI API** - GPT-4 for natural language processing
- **httpx** - Async HTTP client with proxy support
- **pydantic** - Data validation and settings management
- **Docker** - Containerization for deployment

## ✨ Key Features

### 🧠 Intelligent Data Collection
- Extracts information from natural language
- Handles multiple data points in single message
- Validates domain-specific fields (order numbers, product names)
- Soft follow-up for optional fields without being pushy

### 🛡️ Data Protection
- **State machine** with explicit field confirmation flags
- **No overwrites** of already confirmed required fields
- **Validation** prevents accepting obviously invalid data
- **Rate limiting** protects against spam (checked before LLM call)

### 🌐 Network Features
- **Proxy support** for both OpenAI and Telegram APIs
- Works in regions where services are blocked
- URL-encoding support for special characters in credentials

### 📊 Collected Data

**Required:**
- Customer name
- Contact (phone/email/Telegram)
- Order number (validated format)
- Product name
- Return reason
- Item condition

**Optional (soft follow-up):**
- Purchase date
- Refund method

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/eth1r/telegram-return-bot.git
cd telegram-return-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - TELEGRAM_BOT_TOKEN (from @BotFather)
# - OPERATOR_CHAT_ID (use /chatid command)
# - OPENAI_API_KEY

# Run bot
python main.py
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 💬 Example Conversation

```
User: /start
Bot: Hello! I'll help you process a product return. What's your name?

User: John
Bot: John, please provide your order number.

User: ORD-12345
Bot: What product would you like to return?

User: Samsung Galaxy S23
Bot: What is the reason for the return?

User: Screen doesn't work properly
Bot: What is the condition of the item?

User: Used for 2 days
Bot: When did you purchase the product?

User: March 15
Bot: How would you prefer the refund: to card, original payment method, or exchange?

User: To card
Bot: Thank you! I've forwarded your return request to a specialist.
```

## ⚙️ Configuration

### Required Environment Variables

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
OPERATOR_CHAT_ID=your_chat_id
OPENAI_API_KEY=your_openai_key
```

### Optional Settings

```bash
# OpenAI
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# Proxy (if needed)
HTTP_PROXY=http://user:pass@host:port
HTTPS_PROXY=http://user:pass@host:port

# Rate Limiting
RATE_LIMIT_MESSAGES=20
RATE_LIMIT_WINDOW_SECONDS=3600

# Logging
LOG_LEVEL=INFO
```

## 📁 Project Structure

```
telegram-return-bot/
├── bot/                    # Telegram bot layer
│   ├── handlers/          # Command & message handlers
│   └── utils/             # Formatting utilities
├── core/                  # Core application
│   ├── config.py         # Settings management
│   ├── schemas.py        # Data models & validation
│   └── logging.py        # Logging configuration
├── services/             # Business logic
│   ├── assistant/        # OpenAI integration
│   ├── storage/          # Session management
│   ├── telegram/         # Operator notifications
│   └── workflow.py       # Main workflow logic
├── docs/                 # Documentation
├── main.py              # Entry point
├── requirements.txt     # Dependencies
├── Dockerfile          # Docker image
└── docker-compose.yml  # Docker Compose config
```

## 🔒 Security

- ✅ Secrets stored in `.env` (not committed)
- ✅ Rate limiting prevents spam
- ✅ Input validation on all fields
- ✅ State machine prevents data corruption
- ✅ Proxy credentials support URL-encoding

## 📚 Documentation

- [Deployment Guide](docs/DEPLOYMENT.md)
- [Proxy Configuration](docs/PROXY.md)
- [Rate Limiting Details](docs/RATE_LIMITING.md)
- [Changelog](docs/CHANGELOG.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [aiogram](https://docs.aiogram.dev/) - modern Telegram Bot framework
- Powered by [OpenAI](https://openai.com/) GPT models
- Inspired by real-world customer service automation needs

---

**Made with ❤️ for efficient customer service automation**
