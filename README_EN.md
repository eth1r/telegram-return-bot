# Telegram Bot for Product Return Processing

An intelligent Telegram bot powered by OpenAI for automated product return request collection. The bot conducts natural conversations with customers, gathers necessary information, and sends structured requests to operators.

## 🎯 Features

- **Natural Dialogue** - bot communicates like a human using OpenAI GPT
- **Smart Data Collection** - automatically extracts information from free-form text
- **Soft Follow-up** - gently requests additional useful data
- **Error Protection** - doesn't overwrite already collected data
- **Field Validation** - verifies correctness of entered data
- **Proxy Support** - works through proxy for OpenAI and Telegram API
- **Rate Limiting** - spam protection without unnecessary LLM calls
- **Production-Ready** - ready for deployment with Docker

## 📋 Collected Data

### Required Fields:
- **Customer Name** - minimum 2 characters
- **Contact** - phone, email, or Telegram username
- **Order Number** - format: letters, digits, hyphen (3-30 characters)
- **Product Name** - what is being returned
- **Return Reason** - detailed description
- **Item Condition** - "unused", "opened", "used", "damaged"

### Optional Fields (requested softly):
- **Purchase Date** - when the product was purchased
- **Refund Method** - "to card", "original payment method", "exchange", "operator will clarify"

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Fill in required variables:

```bash
# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Chat ID for sending requests (use /chatid command in target chat)
OPERATOR_CHAT_ID=your_chat_id_here

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Bot

```bash
python main.py
```

### 4. Configure Operator Chat

1. Add the bot to the group/chat where requests should arrive
2. Send `/chatid` command in that chat
3. Copy the received Chat ID to `.env` as `OPERATOR_CHAT_ID`
4. Restart the bot

## 🐳 Running with Docker

### Build and run:

```bash
docker-compose up -d
```

### View logs:

```bash
docker-compose logs -f
```

### Stop:

```bash
docker-compose down
```

## ⚙️ Configuration

### Basic Settings

```bash
# OpenAI model (default: gpt-4.1-mini)
OPENAI_MODEL=gpt-4.1-mini

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

### Proxy (optional)

If OpenAI API or Telegram API is blocked in your region:

```bash
HTTP_PROXY=http://username:password@host:port
HTTPS_PROXY=http://username:password@host:port
```

**Important:** If password contains special characters, use URL-encoding:
- `@` → `%40`
- `:` → `%3A`
- `/` → `%2F`
- `?` → `%3F`
- `#` → `%23`

Details: [PROXY.md](PROXY.md)

### Rate Limiting (optional)

Protection against spam and excessive API usage:

```bash
# Maximum messages from one user
RATE_LIMIT_MESSAGES=20

# Time window in seconds (default: 3600 = 1 hour)
RATE_LIMIT_WINDOW_SECONDS=3600
```

Details: [RATE_LIMITING.md](RATE_LIMITING.md)

## 💬 Example Dialogue

```
User: /start
Bot: Hello! I'll help you process a product return. What's your name?

User: Andrew
Bot: Andrew, please provide your order number.

User: ORD-12345
Bot: What product would you like to return?

User: Samsung Smartphone
Bot: What is the reason for the return?

User: Screen size doesn't fit
Bot: What is the condition of the item?

User: Opened but not used
Bot: When did you purchase the product? Please provide an approximate date.

User: April 15
Bot: How would you prefer to receive the refund: to card, original payment method, or exchange for another product?

User: To card
Bot: Thank you! I've forwarded your return request to a specialist. We'll contact you shortly.
```

## 🎛️ Bot Commands

- `/start` - start a new dialogue
- `/reset` - reset current dialogue and start over
- `/chatid` - show current chat ID (for OPERATOR_CHAT_ID configuration)

## 📁 Project Structure

```
incoming_lids/
├── bot/                    # Telegram bot
│   ├── handlers/          # Command and message handlers
│   └── utils/             # Utilities (formatting)
├── core/                  # Application core
│   ├── config.py         # Settings
│   ├── schemas.py        # Data models
│   └── logging.py        # Logging
├── services/             # Business logic
│   ├── assistant/        # OpenAI integration
│   ├── storage/          # Session storage
│   ├── telegram/         # Request sending
│   └── workflow.py       # Main workflow
├── main.py               # Entry point
├── requirements.txt      # Dependencies
├── Dockerfile           # Docker image
└── docker-compose.yml   # Docker Compose
```

## 🔧 Technologies

- **Python 3.12+**
- **aiogram 3.13+** - Telegram bot framework
- **OpenAI API** - GPT for dialogue processing
- **httpx** - HTTP client with proxy support
- **aiohttp-socks** - proxy for Telegram API
- **pydantic** - data validation

## 📚 Documentation

- [CHANGELOG.md](CHANGELOG.md) - complete change history
- [DEPLOYMENT.md](DEPLOYMENT.md) - deployment instructions
- [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) - pre-deployment checklist
- [PROXY.md](PROXY.md) - proxy configuration
- [RATE_LIMITING.md](RATE_LIMITING.md) - spam protection
- [WORKFLOW_FIX_FINAL.md](WORKFLOW_FIX_FINAL.md) - workflow details

## 🛡️ Security

- All secrets stored in `.env` (not committed to Git)
- Rate limiting protects against spam
- Validation of all input data
- Protection against overwriting collected data
- Logging for audit

## 🚨 Troubleshooting

### Bot doesn't respond to messages

1. Check if bot is running: `docker-compose ps` or check process
2. Check logs: `docker-compose logs -f` or `tail -f logs/bot.log`
3. Ensure `TELEGRAM_BOT_TOKEN` is correct

### Requests don't arrive in operator chat

1. Ensure bot is added to the chat
2. Verify `OPERATOR_CHAT_ID` using `/chatid` command in target chat
3. Ensure bot has permissions to send messages

### OpenAI API connection errors

1. Check `OPENAI_API_KEY`
2. If API is blocked, configure proxy in `.env`
3. Check OpenAI account balance

### Telegram API connection errors

1. If Telegram is blocked, configure proxy in `.env`
2. Ensure `aiohttp-socks` is installed: `pip install aiohttp-socks`

## 📝 License

MIT License

## 🤝 Support

If you have questions or issues:
1. Check documentation in project folder
2. Review bot logs
3. Create an issue in the repository

---

**Version:** 2.0  
**Last Updated:** April 2026
