import logging

from aiogram import Bot

from core import Settings, SupportSession

logger = logging.getLogger(__name__)


class OperatorNotifier:
    def __init__(self, bot: Bot | None, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings

    async def send_ticket(self, session: SupportSession) -> None:
        # ── Защита демо-режима ─────────────────────────────────────────────────
        # is_demo=True означает, что это web-виджет с портфолио.
        # Заявка НЕ отправляется оператору, если явно не разрешено через env.
        if session.is_demo and not self._settings.web_demo_submit_to_operator:
            logger.info(
                "Demo mode: operator notification BLOCKED for web session=%s "
                "(set WEB_DEMO_SUBMIT_TO_OPERATOR=true to enable)",
                session.web_session_id,
            )
            return
        # ──────────────────────────────────────────────────────────────────────

        ticket = session.ticket

        # Определяем источник заявки
        if session.is_web:
            source = "Web chat / Portfolio site"
            user_info = f"Web session ID: {session.web_session_id}"
        else:
            source = "Telegram"
            user_info = f"Telegram user ID: {session.user_id}"
            if session.telegram_username:
                user_info += f"\nTelegram username: @{session.telegram_username}"

        lines = [
            "=== НОВАЯ ЗАЯВКА НА ВОЗВРАТ ===",
            "",
            f"📍 Источник: {source}",
            "",
            f"Имя: {ticket.name}",
            f"Контакт: {ticket.contact}",
            "",
            f"Номер заказа: {ticket.order_number}",
            f"Товар: {ticket.product_name}",
            "",
            "Причина возврата:",
            f"{ticket.return_reason}",
            "",
            f"Дата покупки: {ticket.purchase_date or '-'}",
            f"Состояние товара: {ticket.item_condition}",
            f"Способ возврата денег: {ticket.refund_method or '-'}",
            "",
            user_info,
            "",
            "=== КОНЕЦ ===",
        ]

        if self._bot:
            await self._bot.send_message(self._settings.operator_chat_id, "\n".join(lines))
        else:
            # Для web API создаём отдельный Bot instance
            from aiogram import Bot as AiogramBot
            bot = AiogramBot(token=self._settings.telegram_bot_token)
            try:
                await bot.send_message(self._settings.operator_chat_id, "\n".join(lines))
            finally:
                await bot.session.close()
