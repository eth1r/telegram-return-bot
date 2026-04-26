import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
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
    
    # Инициализация
    session_repository = InMemorySessionRepository()
    assistant = OpenAISupportAssistant(settings=settings)
    notifier = OperatorNotifier(bot=None, settings=settings)
    workflow = SupportWorkflowService(assistant=assistant, notifier=notifier)
    
    logger.info("Web API services initialized")
    
    yield
    
    # Очистка
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

# CORS - разрешаем только наш сайт
settings = get_settings()
allowed_origins = [
    "https://portfolio.aiworker43.ru",
    "http://localhost:3000",  # для локальной разработки
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    return {"status": "ok", "service": "return-bot-web-api"}


@app.get("/widget.js")
async def get_widget_js():
    """Раздача JS файла виджета"""
    widget_path = Path(__file__).parent / "widget.js"
    if not widget_path.exists():
        raise HTTPException(status_code=404, detail="Widget file not found")
    return FileResponse(widget_path, media_type="application/javascript")


@app.get("/widget.html")
async def get_widget_html():
    """Раздача HTML файла виджета (для тестирования)"""
    widget_path = Path(__file__).parent / "widget.html"
    if not widget_path.exists():
        raise HTTPException(status_code=404, detail="Widget file not found")
    return FileResponse(widget_path, media_type="text/html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Обработка сообщения от web-чата
    
    - session_id: уникальный идентификатор web-сессии (например, UUID)
    - message: текст сообщения от пользователя
    """
    if not session_repository or not workflow:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Создаем web-сессию с префиксом для отличия от Telegram
        # user_id для web = hash(session_id) для уникальности
        web_user_id = hash(f"web_{request.session_id}") & 0x7FFFFFFF  # положительное число
        
        session = session_repository.get_or_create_web(
            session_id=request.session_id,
            user_id=web_user_id,
        )
        
        # Обрабатываем сообщение через общий workflow
        reply = await workflow.process_message(session, request.message)
        
        # Если reply пустой (rate limit), возвращаем сообщение об ограничении
        if not reply:
            reply = "Вы отправили слишком много сообщений. Пожалуйста, подождите."
        
        # Проверяем, завершена ли заявка
        done = session.submitted
        
        return ChatResponse(reply=reply, done=done)
        
    except Exception as e:
        logger.exception("Failed to process web chat message")
        raise HTTPException(
            status_code=500,
            detail="Не удалось обработать сообщение. Попробуйте позже."
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
