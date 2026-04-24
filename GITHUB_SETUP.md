# Инструкция по переносу проекта на GitHub

## Шаг 1: Создайте новый репозиторий на GitHub

1. Перейдите на https://github.com/eth1r
2. Нажмите кнопку **"New"** (зеленая кнопка справа вверху)
3. Заполните форму:
   - **Repository name**: `telegram-return-bot` (или любое другое название)
   - **Description**: `Intelligent Telegram bot for automated product return processing powered by OpenAI`
   - **Visibility**: Public или Private (на ваш выбор)
   - **НЕ ставьте галочки** на:
     - ❌ Add a README file
     - ❌ Add .gitignore
     - ❌ Choose a license
4. Нажмите **"Create repository"**
5. **Скопируйте URL** репозитория (будет показан на следующей странице):
   ```
   https://github.com/eth1r/telegram-return-bot.git
   ```

## Шаг 2: Выполните команды в терминале

Откройте терминал в папке проекта `incoming_lids` и выполните следующие команды:

### 2.1. Добавьте все изменения в Git

```bash
git add .
```

### 2.2. Создайте коммит с описанием изменений

```bash
git commit -m "feat: adapt bot for product returns with advanced features

- Adapted data schema for product return requests
- Implemented soft follow-up for optional fields
- Added protection against data overwriting
- Added proxy support for OpenAI and Telegram API
- Implemented rate limiting with pre-LLM check
- Updated documentation (RU/EN)
- Added Docker deployment configuration"
```

### 2.3. Удалите старый remote (исходный репозиторий)

```bash
git remote remove origin
```

### 2.4. Добавьте ваш новый GitHub репозиторий

**ВАЖНО:** Замените `YOUR_REPO_NAME` на название вашего репозитория!

```bash
git remote add origin https://github.com/eth1r/YOUR_REPO_NAME.git
```

Например, если вы назвали репозиторий `telegram-return-bot`:
```bash
git remote add origin https://github.com/eth1r/telegram-return-bot.git
```

### 2.5. Отправьте код на GitHub

```bash
git push -u origin main
```

Если GitHub попросит авторизацию:
- **Username**: eth1r
- **Password**: используйте **Personal Access Token** (не обычный пароль!)

## Шаг 3: Создайте Personal Access Token (если нужно)

Если у вас еще нет токена:

1. Перейдите на https://github.com/settings/tokens
2. Нажмите **"Generate new token"** → **"Generate new token (classic)"**
3. Заполните:
   - **Note**: `Telegram Bot Deploy`
   - **Expiration**: 90 days (или на ваш выбор)
   - **Scopes**: поставьте галочку на **repo** (полный доступ к репозиториям)
4. Нажмите **"Generate token"**
5. **СКОПИРУЙТЕ ТОКЕН** (он больше не будет показан!)
6. Используйте этот токен вместо пароля при `git push`

## Шаг 4: Проверьте результат

1. Перейдите на https://github.com/eth1r/YOUR_REPO_NAME
2. Убедитесь, что все файлы загружены
3. Проверьте, что README.md отображается корректно

## Альтернативный способ (через SSH)

Если вы используете SSH-ключи:

```bash
# Добавьте remote через SSH
git remote add origin git@github.com:eth1r/YOUR_REPO_NAME.git

# Отправьте код
git push -u origin main
```

## Что будет загружено на GitHub

✅ Весь код проекта
✅ Документация (README.md, CHANGELOG.md и т.д.)
✅ Docker-конфигурация
✅ Скрипты деплоя
✅ .gitignore (защищает .env от загрузки)

❌ НЕ будет загружено:
- `.env` (секреты защищены .gitignore)
- `__pycache__/` (временные файлы)
- `.git/` (история Git)

## Troubleshooting

### Ошибка: "remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/eth1r/YOUR_REPO_NAME.git
```

### Ошибка: "Authentication failed"

Используйте Personal Access Token вместо пароля (см. Шаг 3)

### Ошибка: "Permission denied"

Убедитесь, что:
1. Вы залогинены в GitHub как eth1r
2. Репозиторий создан под вашим аккаунтом
3. Используете правильный токен с правами на repo

## После успешной загрузки

1. Обновите описание репозитория на GitHub
2. Добавьте topics/tags: `telegram-bot`, `openai`, `python`, `product-returns`, `aiogram`
3. Опционально: добавьте LICENSE файл (MIT рекомендуется)
4. Опционально: настройте GitHub Actions для CI/CD

---

**Готово!** Ваш проект теперь на GitHub 🎉
