from aiogram import Bot

from core import Settings, SupportSession


class OperatorNotifier:
    def __init__(self, bot: Bot | None, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings

    async def send_ticket(self, session: SupportSession) -> None:
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
            # Для web API создаем отдельный Bot instance
            from aiogram import Bot as AiogramBot
            bot = AiogramBot(token=self._settings.telegram_bot_token)
            try:
                await bot.send_message(self._settings.operator_chat_id, "\n".join(lines))
            finally:
                await bot.session.close()
