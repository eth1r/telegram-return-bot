# История изменений проекта

## Обзор

Этот проект был адаптирован из базового бота технической поддержки в специализированного бота для оформления возврата товаров с расширенными возможностями.

---

## Основные изменения

### 1. Адаптация под сценарий возврата товара

**Изменённые файлы:**
- `core/schemas.py` - новая схема данных для возврата
- `services/assistant/prompts.py` - новый системный промпт
- `services/telegram/operator_notifier.py` - новый формат сообщения оператору
- `bot/handlers/support.py` - обновлены UI-тексты
- `services/workflow.py` - обновлена бизнес-логика

**Новая схема заявки (SupportTicket):**
- `name` - имя клиента (обязательное)
- `contact` - контакт (обязательное)
- `order_number` - номер заказа (обязательное, формат: буквы/цифры/дефис, 3-30 символов)
- `product_name` - название товара (обязательное)
- `return_reason` - причина возврата (обязательное)
- `item_condition` - состояние товара (обязательное): "не использовался", "вскрыт", "использовался", "повреждён"
- `purchase_date` - дата покупки (необязательное)
- `refund_method` - способ возврата (необязательное): "на карту", "на исходный способ оплаты", "обмен", "уточнит оператор"

**Валидация:**
- Имя: минимум 2 символа, не только цифры
- Номер заказа: regex `[A-Za-zА-Яа-я0-9-]{3,30}`
- Название товара: минимум 2 символа
- Причина возврата: минимум 3 символа

---

### 2. Мягкий дозапрос необязательных полей

**Проблема:** Бот отправлял заявку сразу после сбора обязательных полей, не пытаясь получить дополнительную полезную информацию.

**Решение:**

**Изменённые файлы:**
- `core/schemas.py` - добавлены флаги `purchase_date_asked` и `refund_method_asked`
- `services/workflow.py` - новая логика последовательного дозапроса
- `services/assistant/prompts.py` - обновлен промпт

**Логика работы:**
1. Сначала собираются все обязательные поля
2. Затем бот спрашивает про `purchase_date` (один раз)
3. Затем бот спрашивает про `refund_method` (один раз)
4. Только после обработки ОБОИХ необязательных полей заявка отправляется

**Распознавание отказа:**
Система распознает фразы: "не помню", "не знаю", "уточню позже", "без разницы", "не важно", "пропустить", "дальше", "не хочу", "потом", "позже"

**Условие отправки заявки:**
```python
ready_to_send = (
    required_complete  # Все обязательные поля заполнены
    and (session.ticket.purchase_date or session.purchase_date_asked)
    and (session.ticket.refund_method or session.refund_method_asked)
    and turn.ready_to_submit
    and not should_ask_optional  # Не отправляем, если нужно задать вопрос
)
```

---

### 3. Защита от перезаписи обязательных полей

**Проблема:** Если пользователь в последующих сообщениях упоминал другое имя или данные, бот перезаписывал уже собранные обязательные поля.

**Решение:**

**Изменённый файл:** `core/schemas.py`

**Новый метод merge с защитой:**
```python
def merge(self, other: "SupportTicket", protect_required: bool = False) -> None:
    required_fields = {"name", "contact", "order_number", "product_name", "return_reason", "item_condition"}
    
    for field_name, value in other.model_dump().items():
        if value not in (None, ""):
            if protect_required and field_name in required_fields:
                current_value = getattr(self, field_name)
                if current_value not in (None, ""):
                    continue  # Пропускаем перезапись
            setattr(self, field_name, value)
```

**Использование:**
```python
session.ticket.merge(turn.extracted_ticket, protect_required=True)
```

**Защищённые поля:** name, contact, order_number, product_name, return_reason, item_condition

---

### 4. Поддержка Proxy для OpenAI и Telegram API

**Проблема:** В некоторых регионах OpenAI API и Telegram API заблокированы.

**Решение:**

**Изменённые файлы:**
- `core/config.py` - добавлены поля `http_proxy` и `https_proxy`
- `services/assistant/openai_support_assistant.py` - настройка proxy для httpx
- `bot/main.py` - настройка proxy для aiogram через AiohttpSession
- `requirements.txt` - добавлена зависимость `aiohttp-socks>=0.11.0`
- `.env.example`, `.env.production.example` - примеры настройки proxy

**Настройка proxy (.env):**
```bash
HTTP_PROXY=http://username:password@host:port
HTTPS_PROXY=http://username:password@host:port
```

**Особенности:**
- Proxy применяется к OpenAI API (через httpx)
- Proxy применяется к Telegram API (через aiohttp-socks)
- Поддержка URL-encoding для спецсимволов в пароле
- Работает без proxy, если не настроен (backward compatibility)

---

### 5. Rate Limiting - защита от спама

**Проблема:** Нужна защита от спама и чрезмерного использования OpenAI API.

**Решение:**

**Изменённые файлы:**
- `core/schemas.py` - добавлены поля для rate limiting в SupportSession
- `core/config.py` - добавлены настройки лимитов
- `services/workflow.py` - добавлен метод `_check_rate_limit()` и проверка ДО вызова LLM
- `bot/handlers/support.py` - обработка пустого ответа (молчаливое игнорирование)
- `.env.example`, `.env.production.example` - настройки лимитов

**Ключевые особенности:**
1. Проверка лимита выполняется **ДО вызова OpenAI API**
2. Сообщение об отказе отправляется **без обращения к LLM** (локальная строка)
3. Уведомление отправляется **только один раз** в рамках лимитного окна
4. Последующие сообщения **молча игнорируются** (не отправляется ответ)
5. Автоматический сброс счетчика после истечения временного окна

**Настройки (.env):**
```bash
RATE_LIMIT_MESSAGES=20  # Максимум сообщений
RATE_LIMIT_WINDOW_SECONDS=3600  # Окно в секундах (1 час)
```

**Локальное сообщение об отказе:**
```python
RATE_LIMIT_MESSAGE = (
    "Вы отправили слишком много сообщений. "
    "Пожалуйста, подождите некоторое время перед продолжением."
)
```

**Поля в SupportSession:**
- `message_count: int = 0` - счетчик сообщений
- `rate_limit_notified: bool = False` - флаг отправки уведомления
- `rate_limit_reset_time: float = 0.0` - время сброса лимита

---

### 6. Улучшения промпта и UX

**Изменения в промпте:**
- Четкое разделение обязательных и необязательных полей
- Правило: не использовать название товара как обращение к пользователю
- Правило: использовать нейтральные подтверждения ("Понятно", "Хорошо", "Записал")
- Обработка побочных вопросов (про сроки, гарантию) - краткий ответ и возврат к сбору данных
- Инструкции по обработке отказов на необязательные поля

**Добавлена команда `/chatid`:**
Показывает ID текущего чата для настройки `OPERATOR_CHAT_ID`

---

## Архитектура проекта

```
incoming_lids/
├── bot/
│   ├── handlers/
│   │   ├── support.py          # Обработчики команд и сообщений
│   │   └── __init__.py
│   ├── utils/
│   │   ├── formatter.py        # Форматирование сообщений
│   │   └── __init__.py
│   └── main.py                 # Инициализация бота
├── core/
│   ├── config.py               # Настройки (Settings)
│   ├── logging.py              # Настройка логирования
│   ├── schemas.py              # Модели данных (SupportTicket, SupportSession)
│   └── __init__.py
├── services/
│   ├── assistant/
│   │   ├── openai_support_assistant.py  # Интеграция с OpenAI API
│   │   ├── prompts.py          # Системный промпт
│   │   └── __init__.py
│   ├── storage/
│   │   ├── session_repository.py  # Хранение сессий (in-memory)
│   │   └── __init__.py
│   ├── telegram/
│   │   ├── operator_notifier.py  # Отправка заявок оператору
│   │   └── __init__.py
│   ├── workflow.py             # Основная бизнес-логика
│   └── __init__.py
├── main.py                     # Точка входа
├── requirements.txt            # Зависимости
├── Dockerfile                  # Docker-образ
├── docker-compose.yml          # Docker Compose конфигурация
├── .env.example                # Пример конфигурации
└── README.md                   # Документация
```

---

## Технологический стек

- **Python 3.12+**
- **aiogram 3.13+** - фреймворк для Telegram ботов
- **aiohttp-socks 0.11+** - поддержка proxy для Telegram API
- **httpx 0.26+** - HTTP-клиент для OpenAI API с поддержкой proxy
- **pydantic 2.9+** - валидация данных
- **pydantic-settings 2.12+** - управление настройками
- **OpenAI API** - LLM для обработки диалогов

---

## Зависимости

```
aiogram>=3.7.0
aiohttp-socks>=0.11.0
httpx>=0.27.0
pydantic>=2.7.0
pydantic-settings>=2.2.1
```

---

## Переменные окружения

### Обязательные:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
OPERATOR_CHAT_ID=your_chat_id
OPENAI_API_KEY=your_openai_key
```

### Необязательные:
```bash
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
LOG_LEVEL=INFO

# Proxy (если нужен)
HTTP_PROXY=http://username:password@host:port
HTTPS_PROXY=http://username:password@host:port

# Rate limiting
RATE_LIMIT_MESSAGES=20
RATE_LIMIT_WINDOW_SECONDS=3600
```

---

## Документация

- `CHANGELOG.md` (этот файл) - полная история изменений
- `DEPLOYMENT.md` - инструкции по деплою
- `DEPLOY_CHECKLIST.md` - чеклист перед деплоем
- `PROXY.md` - настройка proxy
- `RATE_LIMITING.md` - подробности о rate limiting
- `WORKFLOW_FIX_FINAL.md` - детали исправлений workflow
- `README.md` / `README_EN.md` - основная документация

---

## Итоговые улучшения

1. ✅ Адаптация под возврат товара с валидацией полей
2. ✅ Мягкий дозапрос необязательных полей без зацикливания
3. ✅ Защита от перезаписи уже собранных данных
4. ✅ Поддержка proxy для OpenAI и Telegram API
5. ✅ Rate limiting с проверкой ДО вызова LLM
6. ✅ Улучшенный UX и обработка побочных вопросов
7. ✅ Команда `/chatid` для настройки
8. ✅ Подробное логирование для отладки
9. ✅ Production-ready конфигурация
10. ✅ Docker-поддержка для деплоя
