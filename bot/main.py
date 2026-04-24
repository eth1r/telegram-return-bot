import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from bot.handlers import router
from core import get_settings, setup_logging
from services import SupportWorkflowService
from services.assistant import OpenAISupportAssistant
from services.storage import InMemorySessionRepository
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)


async def run_bot() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    # Configure Telegram session with proxy if available
    session = None
    if settings.https_proxy or settings.http_proxy:
        proxy_url = settings.https_proxy or settings.http_proxy
        logger.info(f"Telegram Bot configured with proxy: {proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url}")
        session = AiohttpSession(proxy=proxy_url)
    
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(),
        session=session
    )
    session_repository = InMemorySessionRepository()
    assistant = OpenAISupportAssistant(settings)
    notifier = OperatorNotifier(bot, settings)
    workflow = SupportWorkflowService(assistant=assistant, notifier=notifier)

    dp = Dispatcher()
    dp.include_router(router)
    dp["session_repository"] = session_repository
    dp["workflow"] = workflow

    logger.info("Starting support intake bot")
    try:
        await dp.start_polling(bot)
    finally:
        await workflow.close()
        await bot.session.close()
