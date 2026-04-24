# Rate Limiting - Защита от спама

## Описание

Система rate limiting защищает бота от спама и чрезмерного использования OpenAI API. Проверка лимитов выполняется **ДО вызова LLM**, что экономит токены и деньги.

## Ключевые особенности

1. **Проверка ДО LLM** - лимит проверяется перед вызовом OpenAI API
2. **Локальный ответ** - сообщение об отказе отправляется без обращения к модели
3. **Одно уведомление** - пользователь получает уведомление о лимите только один раз
4. **Молчаливое игнорирование** - последующие сообщения игнорируются без ответа
5. **Автоматический сброс** - счетчик сбрасывается после истечения временного окна

## Где проверяется лимит

### Файл: `services/workflow.py`

**Метод проверки лимита:**
```python
def _check_rate_limit(self, session: SupportSession) -> bool:
    """
    Проверяет, не превышен ли лимит сообщений для пользователя.
    
    Returns:
        True если лимит превышен, False если можно продолжать
    """
    current_time = time.time()
    
    # Проверяем, нужно ли сбросить счетчик
    if current_time >= session.rate_limit_reset_time:
        # Окно истекло, сбрасываем счетчик
        session.message_count = 0
        session.rate_limit_notified = False
        session.rate_limit_reset_time = current_time + self._settings.rate_limit_window_seconds
        logger.info("Rate limit reset for user_id=%s", session.user_id)
    
    # Увеличиваем счетчик
    session.message_count += 1
    
    # Проверяем лимит
    if session.message_count > self._settings.rate_limit_messages:
        logger.warning(
            "Rate limit exceeded for user_id=%s: %d/%d messages",
            session.user_id,
            session.message_count,
            self._settings.rate_limit_messages
        )
        return True
    
    return False
```

**Проверка в начале `process_message()` (ДО вызова LLM):**
```python
async def process_message(self, session: SupportSession, message_text: str) -> str:
    # ВАЖНО: Проверка лимита ДО вызова LLM
    if self._check_rate_limit(session):
        # Лимит превышен
        if not session.rate_limit_notified:
            # Отправляем уведомление только один раз
            session.rate_limit_notified = True
            logger.info("Sending rate limit notification to user_id=%s", session.user_id)
            return RATE_LIMIT_MESSAGE
        else:
            # Уведомление уже было отправлено, молча игнорируем
            logger.info("Ignoring message from rate-limited user_id=%s", session.user_id)
            return ""  # Пустая строка = не отправляем ответ
    
    # Далее идет обычная обработка с вызовом LLM
    ...
```

## Где хранится флаг уведомления

### Файл: `core/schemas.py`

**Класс `SupportSession`:**
```python
class SupportSession(BaseModel):
    user_id: int
    chat_id: int
    ...
    
    # Rate limiting
    message_count: int = 0  # Счетчик сообщений в текущем окне
    rate_limit_notified: bool = False  # ✅ Флаг: уведомление уже отправлено
    rate_limit_reset_time: float = 0.0  # Время сброса лимита (unix timestamp)
```

**Важно:** Флаг `rate_limit_notified` НЕ сбрасывается при `reset()` диалога, только при истечении временного окна.

## Локальный текст отказа

### Файл: `services/workflow.py`

```python
RATE_LIMIT_MESSAGE = (
    "Вы отправили слишком много сообщений. "
    "Пожалуйста, подождите некоторое время перед продолжением."
)
```

Это сообщение:
- Отправляется **без вызова OpenAI API**
- Отправляется **только один раз** в рамках лимитного окна
- Формируется локально в коде

## Обработка пустого ответа

### Файл: `bot/handlers/support.py`

```python
@router.message(F.text)
async def handle_text_message(...) -> None:
    ...
    try:
        reply = await workflow.process_message(session, message.text)
        # Если reply пустой, значит сообщение игнорируется (rate limit)
        if reply:
            await message.answer(reply)
    except Exception:
        ...
```

Если `reply` пустой (`""`), бот не отправляет ответ пользователю.

## Настройки

### Файл: `core/config.py`

```python
class Settings(BaseSettings):
    ...
    # Rate limiting settings
    rate_limit_messages: int = Field(default=20, alias="RATE_LIMIT_MESSAGES")
    rate_limit_window_seconds: int = Field(default=3600, alias="RATE_LIMIT_WINDOW_SECONDS")
```

### Переменные окружения (.env)

```bash
# Rate limiting (optional) - защита от спама
# Максимальное количество сообщений от одного пользователя в окне времени
RATE_LIMIT_MESSAGES=20

# Размер окна в секундах (по умолчанию 3600 = 1 час)
RATE_LIMIT_WINDOW_SECONDS=3600
```

**По умолчанию:**
- Лимит: 20 сообщений
- Окно: 3600 секунд (1 час)

## Логика работы

### Первое сообщение после превышения лимита:
1. Пользователь отправляет 21-е сообщение (лимит = 20)
2. `_check_rate_limit()` возвращает `True`
3. `rate_limit_notified = False` → отправляем `RATE_LIMIT_MESSAGE`
4. Устанавливаем `rate_limit_notified = True`
5. **LLM НЕ вызывается**

### Последующие сообщения до сброса лимита:
1. Пользователь отправляет 22-е, 23-е сообщение...
2. `_check_rate_limit()` возвращает `True`
3. `rate_limit_notified = True` → возвращаем пустую строку `""`
4. Бот молча игнорирует сообщение (не отправляет ответ)
5. **LLM НЕ вызывается**

### После истечения временного окна:
1. Проходит 1 час (или настроенное время)
2. `current_time >= session.rate_limit_reset_time`
3. Сбрасываем: `message_count = 0`, `rate_limit_notified = False`
4. Пользователь может снова отправлять сообщения

## Логирование

### Сброс лимита:
```
INFO | Rate limit reset for user_id=123456789
```

### Превышение лимита:
```
WARNING | Rate limit exceeded for user_id=123456789: 21/20 messages
```

### Отправка уведомления:
```
INFO | Sending rate limit notification to user_id=123456789
```

### Игнорирование сообщения:
```
INFO | Ignoring message from rate-limited user_id=123456789
```

## Пример работы

### Сценарий: Пользователь отправляет 25 сообщений за 10 минут

```
Сообщение 1-20: Обрабатываются нормально через LLM
Сообщение 21:
  → Проверка лимита: ПРЕВЫШЕН
  → rate_limit_notified = False
  → Бот: "Вы отправили слишком много сообщений. Пожалуйста, подождите некоторое время перед продолжением."
  → rate_limit_notified = True
  → LLM НЕ вызывается

Сообщение 22-25:
  → Проверка лимита: ПРЕВЫШЕН
  → rate_limit_notified = True
  → Бот: (молчит, не отправляет ответ)
  → LLM НЕ вызывается

Через 1 час:
  → Сброс счетчика
  → message_count = 0
  → rate_limit_notified = False
  → Пользователь может снова отправлять сообщения
```

## Преимущества

1. **Экономия токенов** - LLM не вызывается при превышении лимита
2. **Экономия денег** - не тратятся деньги на OpenAI API
3. **Защита от спама** - злоумышленники не могут перегрузить систему
4. **Хороший UX** - пользователь получает понятное уведомление
5. **Нет спама** - повторные сообщения игнорируются молча
6. **Автоматический сброс** - не требует ручного вмешательства

## Настройка под свои нужды

### Более строгий лимит (для production):
```bash
RATE_LIMIT_MESSAGES=10
RATE_LIMIT_WINDOW_SECONDS=1800  # 30 минут
```

### Более мягкий лимит (для тестирования):
```bash
RATE_LIMIT_MESSAGES=50
RATE_LIMIT_WINDOW_SECONDS=7200  # 2 часа
```

### Отключение лимитов (не рекомендуется):
```bash
RATE_LIMIT_MESSAGES=999999
RATE_LIMIT_WINDOW_SECONDS=86400  # 24 часа
```

## Важные замечания

1. **Лимит НЕ сбрасывается при `/reset`** - только по истечении временного окна
2. **Счетчик увеличивается для каждого сообщения** - включая команды `/start`, `/reset`
3. **Лимит применяется per-user** - каждый пользователь имеет свой счетчик
4. **Проверка ВСЕГДА перед LLM** - гарантирует экономию ресурсов
5. **Пустой ответ = молчание** - бот не отправляет сообщение пользователю
