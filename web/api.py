import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core import get_settings
from services import SupportWorkflowService
from services.assistant import OpenAISupportAssistant
from services.storage import InMemorySessionRepository
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)

# Глобальные зависимости
session_repository: InMemorySessionRepository | None = None
workflow: SupportWorkflowService | None = None


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    done: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация и очистка ресурсов"""
    global session_repository, workflow

    settings = get_settings()
    logger.info("Initializing web API services...")

    session_repository = InMemorySessionRepository()
    assistant = OpenAISupportAssistant(settings=settings)
    notifier = OperatorNotifier(bot=None, settings=settings)
    workflow = SupportWorkflowService(assistant=assistant, notifier=notifier)

    logger.info("Web API services initialized")

    yield

    logger.info("Shutting down web API services...")
    if workflow:
        await workflow.close()
    logger.info("Web API services shut down")


app = FastAPI(
    title="Return Bot Web API",
    description="Web API для чат-виджета оформления возврата товара",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — разрешаем только нужные origins
settings = get_settings()
allowed_origins = [
    "https://portfolio.aiworker43.ru",
    "http://portfolio.aiworker43.ru",
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ── IP-based rate limiting (поверх session rate limit) ────────────────────
# Session rate limit защищает одну сессию, но не мешает создавать новые.
# IP rate limit ограничивает количество запросов с одного адреса за час.

_ip_requests: dict[str, list[float]] = defaultdict(list)

WEB_IP_RATE_LIMIT = 40       # максимум запросов с одного IP
WEB_IP_RATE_WINDOW = 3600    # за 1 час (секунды)


def _check_ip_rate_limit(ip: str) -> bool:
    """Возвращает True если лимит НЕ превышен и запрос можно обработать."""
    now = time.time()
    window_start = now - WEB_IP_RATE_WINDOW

    # Убираем устаревшие записи
    _ip_requests[ip] = [t for t in _ip_requests[ip] if t > window_start]

    if len(_ip_requests[ip]) >= WEB_IP_RATE_LIMIT:
        logger.warning("IP rate limit exceeded: ip=%s count=%d", ip, len(_ip_requests[ip]))
        return False

    _ip_requests[ip].append(now)
    return True


def _get_client_ip(request: Request) -> str:
    """Берём реальный IP с учётом nginx X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Вспомогательная функция обработки чата ─────────────────────────────────

async def _process_chat(request: ChatRequest) -> ChatResponse:
    """Общая логика обработки сообщения (используется в обоих роутах)."""
    if not session_repository or not workflow:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        web_user_id = hash(f"web_{request.session_id}") & 0x7FFFFFFF

        session = session_repository.get_or_create_web(
            session_id=request.session_id,
            user_id=web_user_id,
        )

        reply = await workflow.process_message(session, request.message)

        if not reply:
            reply = "Вы отправили слишком много сообщений. Пожалуйста, подождите."

        done = session.submitted

        return ChatResponse(reply=reply, done=done)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to process web chat message")
        raise HTTPException(
            status_code=500,
            detail="Не удалось обработать сообщение. Попробуйте позже.",
        )


# ── Оригинальные роуты (обратная совместимость) ─────────────────────────────

@app.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    return {"status": "ok", "service": "return-bot-web-api"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Оригинальный endpoint (оставлен для обратной совместимости)"""
    return await _process_chat(request)


@app.get("/widget.js")
async def get_widget_js():
    widget_path = Path(__file__).parent / "widget.js"
    if not widget_path.exists():
        raise HTTPException(status_code=404, detail="Widget file not found")
    return FileResponse(widget_path, media_type="application/javascript")


@app.get("/widget.html")
async def get_widget_html():
    widget_path = Path(__file__).parent / "widget.html"
    if not widget_path.exists():
        raise HTTPException(status_code=404, detail="Widget file not found")
    return FileResponse(widget_path, media_type="text/html")


# ── Роуты для портфолио-виджета (/api/return-bot/*) ────────────────────────
# Nginx проксирует /api/return-bot/* → этому сервису.
# Префикс позволяет nginx отличать return-bot от других API сервисов.

@app.get("/api/return-bot/health")
async def health_check_prefixed():
    """Health check для портфолио-виджета"""
    return {"status": "ok", "service": "return-bot-web-api"}


@app.post("/api/return-bot/chat", response_model=ChatResponse)
async def chat_prefixed(request: Request, body: ChatRequest):
    """
    Chat endpoint для портфолио-виджета.
    Вызывается через nginx-прокси с портфолио-сайта.
    Имеет дополнительный IP rate limit поверх session rate limit.
    """
    ip = _get_client_ip(request)
    if not _check_ip_rate_limit(ip):
        raise HTTPException(
            status_code=429,
            detail="Слишком много запросов. Попробуйте позже.",
        )
    return await _process_chat(body)


@app.delete("/api/return-bot/session/{session_id}", status_code=204)
async def reset_session(session_id: str):
    """
    Сброс web-сессии — пользователь нажал «Начать заново».
    Удаляет сессию из репозитория, следующее сообщение создаст новую.
    """
    if not session_repository:
        raise HTTPException(status_code=503, detail="Service not initialized")

    session_repository.delete_web_session(session_id)
    return  # 204 No Content


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
