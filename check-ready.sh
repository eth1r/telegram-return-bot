#!/bin/bash

# Скрипт проверки готовности проекта к деплою

echo "=== Проверка готовности к деплою ==="
echo ""

ERRORS=0

# Проверка Docker
echo -n "Проверка Docker... "
if command -v docker &> /dev/null; then
    echo "✓ Установлен ($(docker --version))"
else
    echo "✗ НЕ УСТАНОВЛЕН"
    ERRORS=$((ERRORS + 1))
fi

# Проверка Docker Compose
echo -n "Проверка Docker Compose... "
if command -v docker-compose &> /dev/null; then
    echo "✓ Установлен ($(docker-compose --version))"
else
    echo "✗ НЕ УСТАНОВЛЕН"
    ERRORS=$((ERRORS + 1))
fi

# Проверка файлов проекта
echo ""
echo "Проверка файлов проекта:"

FILES=(
    "Dockerfile"
    "docker-compose.yml"
    "requirements.txt"
    "main.py"
    ".env.example"
    "deploy.sh"
)

for file in "${FILES[@]}"; do
    echo -n "  $file... "
    if [ -f "$file" ]; then
        echo "✓"
    else
        echo "✗ ОТСУТСТВУЕТ"
        ERRORS=$((ERRORS + 1))
    fi
done

# Проверка .env
echo ""
echo -n "Проверка .env... "
if [ -f ".env" ]; then
    echo "✓ Существует"
    
    # Проверка обязательных переменных
    echo "Проверка переменных:"
    
    source .env
    
    echo -n "  TELEGRAM_BOT_TOKEN... "
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ "$TELEGRAM_BOT_TOKEN" != "" ]; then
        echo "✓"
    else
        echo "✗ НЕ УСТАНОВЛЕН"
        ERRORS=$((ERRORS + 1))
    fi
    
    echo -n "  OPERATOR_CHAT_ID... "
    if [ -n "$OPERATOR_CHAT_ID" ] && [ "$OPERATOR_CHAT_ID" != "" ]; then
        echo "✓"
    else
        echo "✗ НЕ УСТАНОВЛЕН"
        ERRORS=$((ERRORS + 1))
    fi
    
    echo -n "  OPENAI_API_KEY... "
    if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "" ]; then
        echo "✓"
    else
        echo "✗ НЕ УСТАНОВЛЕН"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "✗ ОТСУТСТВУЕТ"
    echo "  Создайте .env из .env.example: cp .env.example .env"
    ERRORS=$((ERRORS + 1))
fi

# Проверка структуры проекта
echo ""
echo "Проверка структуры проекта:"

DIRS=(
    "bot"
    "core"
    "services"
)

for dir in "${DIRS[@]}"; do
    echo -n "  $dir/... "
    if [ -d "$dir" ]; then
        echo "✓"
    else
        echo "✗ ОТСУТСТВУЕТ"
        ERRORS=$((ERRORS + 1))
    fi
done

# Итоги
echo ""
echo "=== Результат проверки ==="
if [ $ERRORS -eq 0 ]; then
    echo "✓ Проект готов к деплою!"
    echo ""
    echo "Запустите деплой командой:"
    echo "  ./deploy.sh"
    exit 0
else
    echo "✗ Обнаружено ошибок: $ERRORS"
    echo ""
    echo "Исправьте ошибки перед деплоем."
    exit 1
fi
