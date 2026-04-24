# НАСТРОЙКА PROXY

## Быстрая настройка

Если OpenAI API недоступен напрямую, используйте proxy.

### 1. Добавьте в .env

```env
HTTPS_PROXY=http://username:password@proxy.example.com:8080
```

### 2. Перезапустите бота

```bash
docker-compose restart
```

### 3. Проверьте логи

```bash
docker-compose logs | grep proxy
# Должна быть строка: INFO - OpenAI client configured with proxy
```

## Формат proxy URL

```
http://username:password@host:port
```

### Спецсимволы в пароле

Если пароль содержит `@`, `:`, `/`, `?`, `#` — используйте URL-encoding:

| Символ | Код |
|--------|-----|
| @ | %40 |
| : | %3A |
| / | %2F |
| ? | %3F |
| # | %23 |

Пример:
```env
# Пароль: my@pass:word
HTTPS_PROXY=http://user:my%40pass%3Aword@proxy.example.com:8080
```

## Отключение proxy

Закомментируйте или удалите строку из .env:

```env
# HTTPS_PROXY=http://username:password@proxy.example.com:8080
```

Перезапустите бота.

## Важно

- Proxy используется ТОЛЬКО для OpenAI API
- Telegram API работает напрямую (без proxy)
- Не коммитьте .env с реальными credentials в Git
