# ИНСТРУКЦИЯ ПО ДЕПЛОЮ БОТА ВОЗВРАТА ТОВАРА

## ТРЕБОВАНИЯ

- Docker и Docker Compose установлены на сервере
- Доступ к серверу по SSH
- Telegram Bot Token (получить у @BotFather)
- OpenAI API Key
- ID чата операторов в Telegram

---

## БЫСТРЫЙ СТАРТ

### 1. Клонирование проекта на сервер

```bash
# Подключение к серверу
ssh user@your-server.com

# Клонирование репозитория
git clone https://github.com/MrGAN12009/incoming_lids.git
cd incoming_lids
```

### 2. Настройка переменных окружения

```bash
# Копирование шаблона
cp .env.example .env

# Редактирование .env
nano .env
```

Заполните обязательные переменные:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPERATOR_CHAT_ID=-1001234567890
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
LOG_LEVEL=INFO
```

### 3. Запуск бота

```bash
# Сделать скрипт исполняемым
chmod +x deploy.sh

# Запустить деплой
./deploy.sh
```

---

## УПРАВЛЕНИЕ БОТОМ

### Просмотр логов

```bash
# Все логи
docker-compose logs

# Логи в реальном времени
docker-compose logs -f

# Последние 100 строк
docker-compose logs --tail=100
```

### Перезапуск бота

```bash
# Перезапуск контейнера
docker-compose restart

# Полный перезапуск (пересборка)
docker-compose down
docker-compose up -d --build
```

### Остановка бота

```bash
# Остановка контейнера
docker-compose stop

# Остановка и удаление контейнера
docker-compose down
```

### Проверка статуса

```bash
# Статус контейнера
docker-compose ps

# Детальная информация
docker inspect return-bot
```

---

## ОБНОВЛЕНИЕ ПРОЕКТА

### Обновление кода

```bash
# Остановка бота
docker-compose down

# Получение обновлений
git pull origin main

# Пересборка и запуск
docker-compose up -d --build

# Проверка логов
docker-compose logs -f
```

### Обновление зависимостей

```bash
# Пересборка образа без кэша
docker-compose build --no-cache

# Запуск
docker-compose up -d
```

---

## ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

### Обязательные

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `OPERATOR_CHAT_ID` | ID чата операторов | `-1001234567890` |
| `OPENAI_API_KEY` | API ключ OpenAI | `sk-proj-...` |

### Опциональные

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OPENAI_MODEL` | Модель OpenAI | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | URL API OpenAI | `https://api.openai.com/v1` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

---

## ПОЛУЧЕНИЕ ID ЧАТА ОПЕРАТОРОВ

1. Создайте группу в Telegram
2. Добавьте бота в группу
3. Отправьте любое сообщение в группу
4. Откройте в браузере:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
5. Найдите `"chat":{"id":-1001234567890}` в ответе
6. Используйте это значение в `OPERATOR_CHAT_ID`

---

## МОНИТОРИНГ

### Проверка работы бота

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Бот должен ответить приветствием

### Проверка логов на ошибки

```bash
# Поиск ошибок в логах
docker-compose logs | grep -i error

# Поиск предупреждений
docker-compose logs | grep -i warning
```

### Проверка использования ресурсов

```bash
# Статистика контейнера
docker stats return-bot

# Использование диска
docker system df
```

---

## TROUBLESHOOTING

### Бот не запускается

```bash
# Проверить логи
docker-compose logs

# Проверить .env
cat .env

# Проверить статус контейнера
docker-compose ps
```

### Бот не отвечает в Telegram

1. Проверьте правильность `TELEGRAM_BOT_TOKEN`
2. Убедитесь, что контейнер запущен: `docker-compose ps`
3. Проверьте логи: `docker-compose logs -f`

### Заявки не отправляются операторам

1. Проверьте правильность `OPERATOR_CHAT_ID`
2. Убедитесь, что бот добавлен в группу операторов
3. Проверьте права бота в группе (должен иметь право отправлять сообщения)

### Ошибки OpenAI API

1. Проверьте правильность `OPENAI_API_KEY`
2. Проверьте баланс на аккаунте OpenAI
3. Проверьте доступность API: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

---

## БЕЗОПАСНОСТЬ

### Рекомендации

1. **Не коммитьте .env в Git** — файл уже в .gitignore
2. **Используйте сильные токены** — не делитесь ими
3. **Ограничьте доступ к серверу** — используйте SSH ключи
4. **Регулярно обновляйте зависимости** — следите за уязвимостями
5. **Настройте firewall** — ограничьте входящие подключения

### Ротация токенов

Если токен скомпрометирован:

1. Получите новый токен у @BotFather
2. Обновите `.env`
3. Перезапустите бота: `docker-compose restart`

---

## BACKUP

### Backup конфигурации

```bash
# Создать backup .env
cp .env .env.backup.$(date +%Y%m%d)

# Создать архив проекта
tar -czf backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

### Восстановление

```bash
# Восстановить .env
cp .env.backup.20240315 .env

# Перезапустить бота
docker-compose restart
```

---

## МАСШТАБИРОВАНИЕ

### Запуск нескольких ботов

Если нужно запустить несколько ботов (для разных магазинов):

1. Создайте отдельные директории для каждого бота
2. Используйте разные `.env` файлы
3. Измените `container_name` в `docker-compose.yml`

```bash
# Бот 1
cd /opt/return-bot-shop1
docker-compose up -d

# Бот 2
cd /opt/return-bot-shop2
docker-compose up -d
```

---

## КОНТАКТЫ И ПОДДЕРЖКА

При возникновении проблем:

1. Проверьте логи: `docker-compose logs -f`
2. Проверьте документацию: `README.md`
3. Проверьте отчёт об адаптации: `ADAPTATION_REPORT.md`

---

## CHANGELOG

### v1.0.0 (2024)
- Адаптация под возврат товара
- Добавлен Docker Compose
- Добавлены скрипты деплоя
- Обновлена документация
