# Web Widget Integration Guide

## Описание

Web-виджет для оформления возврата товара. Позволяет посетителям сайта общаться с AI-ассистентом прямо на странице.

## Возможности

- Плавающая кнопка в правом нижнем углу
- Чат-окно с историей сообщений
- Общая бизнес-логика с Telegram-ботом
- Rate limiting для защиты от спама
- Адаптивный дизайн для мобильных устройств
- Сохранение сессии в localStorage

## Интеграция на сайт

### Вариант 1: Подключение через script tag (рекомендуется)

Добавьте этот код перед закрывающим тегом `</body>`:

```html
<script src="https://portfolio.aiworker43.ru/widget.js"></script>
```

Виджет автоматически инициализируется при загрузке страницы.

### Вариант 2: Встроенный HTML

Если нужен полный контроль, можно использовать встроенный HTML:

```html
<!-- Скопируйте содержимое файла web/widget.html -->
```

## API Endpoints

### POST /api/chat

Отправка сообщения в чат.

**Request:**
```json
{
  "session_id": "web_1234567890_abc123",
  "message": "Хочу вернуть товар"
}
```

**Response:**
```json
{
  "reply": "Здравствуйте! Как вас зовут?",
  "done": false
}
```

### GET /health

Проверка работоспособности API.

**Response:**
```json
{
  "status": "ok",
  "service": "return-bot-web-api"
}
```

### GET /widget.js

Получение JS файла виджета.

### GET /widget.html

Получение HTML файла виджета (для тестирования).

## Архитектура

### Общая логика с Telegram

Web-чат использует ту же бизнес-логику, что и Telegram-бот:

1. **SupportWorkflowService** - общий workflow для обработки сообщений
2. **OpenAISupportAssistant** - общий AI-ассистент
3. **OperatorNotifier** - отправка заявок в Telegram-чат оператора
4. **InMemorySessionRepository** - хранение сессий (отдельно для Telegram и Web)

### Web-сессии

- `session_id` генерируется на клиенте и сохраняется в localStorage
- `user_id` для web = hash(session_id) для уникальности
- Web-сессии хранятся отдельно от Telegram-сессий
- Флаг `is_web=True` отличает web-сессии от Telegram

### Отправка заявок

Когда заявка оформлена через web-чат:

- Заявка отправляется в операторский Telegram-чат
- Указывается источник: "Web chat / Portfolio site"
- Вместо Telegram username показывается Web session ID

## Настройка на сервере

### 1. Обновить код

```bash
cd /opt/apps/bots/telegram-return-bot
git pull
docker compose up -d --build
```

### 2. Проверить порты

Web API работает на порту 8000. Убедитесь, что порт открыт:

```bash
docker compose ps
```

### 3. Настроить reverse proxy (nginx)

Создайте конфигурацию nginx для проксирования запросов:

```nginx
# /etc/nginx/sites-available/portfolio-api

server {
    listen 80;
    server_name portfolio.aiworker43.ru;

    # Web API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Widget files
    location /widget.js {
        proxy_pass http://localhost:8000/widget.js;
        proxy_set_header Host $host;
    }

    location /widget.html {
        proxy_pass http://localhost:8000/widget.html;
        proxy_set_header Host $host;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
        proxy_set_header Host $host;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/portfolio-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Настроить SSL (опционально)

```bash
sudo certbot --nginx -d portfolio.aiworker43.ru
```

## Тестирование

### 1. Проверить API

```bash
curl https://portfolio.aiworker43.ru/health
```

### 2. Проверить виджет

Откройте в браузере:
```
https://portfolio.aiworker43.ru/widget.html
```

### 3. Проверить интеграцию на сайте

1. Откройте https://portfolio.aiworker43.ru/
2. Найдите кнопку виджета в правом нижнем углу
3. Нажмите на кнопку
4. Отправьте тестовое сообщение
5. Проверьте, что бот отвечает
6. Пройдите полный сценарий оформления возврата
7. Проверьте, что заявка пришла в операторский Telegram-чат

## Логи

### Просмотр логов

```bash
cd /opt/apps/bots/telegram-return-bot
docker compose logs -f
```

### Фильтрация логов Web API

```bash
docker compose logs -f | grep "web"
```

## Безопасность

- CORS настроен только для https://portfolio.aiworker43.ru
- OpenAI API key не передается на фронтенд
- Rate limiting: 20 сообщений в час на сессию
- Валидация всех входных данных
- Максимальная длина сообщения: 2000 символов

## Troubleshooting

### Виджет не загружается

1. Проверьте, что контейнер запущен: `docker compose ps`
2. Проверьте логи: `docker compose logs --tail=50`
3. Проверьте доступность API: `curl http://localhost:8000/health`

### CORS ошибки

1. Убедитесь, что сайт использует HTTPS
2. Проверьте, что домен добавлен в allowed_origins в web/api.py

### Бот не отвечает

1. Проверьте логи на ошибки
2. Проверьте, что OpenAI API key валиден
3. Проверьте, что прокси работает (если используется)

### Заявки не приходят в Telegram

1. Проверьте OPERATOR_CHAT_ID в .env
2. Проверьте, что бот добавлен в группу
3. Проверьте логи на ошибки отправки

## Мониторинг

### Проверка работоспособности

```bash
# Health check
curl https://portfolio.aiworker43.ru/health

# Проверка контейнера
docker compose ps

# Проверка логов
docker compose logs --tail=100
```

### Метрики

- Количество web-сессий: смотрите в логах "get_or_create_web"
- Количество отправленных заявок: смотрите "Ticket submitted"
- Rate limit срабатывания: смотрите "Rate limit exceeded"
