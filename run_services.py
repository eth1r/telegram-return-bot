"""
Запускает Telegram бота и Web API одновременно
"""
import asyncio
import logging

import uvicorn
from bot.main import run_bot

logger = logging.getLogger(__name__)


async def run_web_api():
    """Запускает Web API сервер"""
    config = uvicorn.Config(
        "web.api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Запускает оба сервиса параллельно"""
    logger.info("Starting Telegram bot and Web API...")
    
    # Запускаем оба сервиса параллельно
    await asyncio.gather(
        run_bot(),
        run_web_api(),
    )


if __name__ == "__main__":
    asyncio.run(main())
