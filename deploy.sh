#!/bin/bash

# Скрипт деплоя бота возврата товара

set -e

echo "=== Деплой бота возврата товара ==="

# Проверка наличия .env
if [ ! -f .env ]; then
    echo "ОШИБКА: Файл .env не найден!"
    echo "Скопируйте .env.example в .env и заполните переменные:"
    echo "  cp .env.example .env"
    exit 1
fi

# Проверка обязательных переменных
echo "Проверка переменных окружения..."
source .env

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "ОШИБКА: TELEGRAM_BOT_TOKEN не установлен в .env"
    exit 1
fi

if [ -z "$OPERATOR_CHAT_ID" ]; then
    echo "ОШИБКА: OPERATOR_CHAT_ID не установлен в .env"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "ОШИБКА: OPENAI_API_KEY не установлен в .env"
    exit 1
fi

echo "✓ Все обязательные переменные установлены"

# Остановка старого контейнера (если есть)
echo "Остановка старого контейнера..."
docker-compose down || true

# Сборка образа
echo "Сборка Docker-образа..."
docker-compose build

# Запуск контейнера
echo "Запуск контейнера..."
docker-compose up -d

# Проверка статуса
echo "Проверка статуса контейнера..."
sleep 3
docker-compose ps

echo ""
echo "=== Деплой завершён ==="
echo ""
echo "Команды для управления:"
echo "  Логи:           docker-compose logs -f"
echo "  Остановка:      docker-compose down"
echo "  Перезапуск:     docker-compose restart"
echo "  Статус:         docker-compose ps"
echo ""
