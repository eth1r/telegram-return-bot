from aiogram import Bot

from core import Settings, SupportSession


class OperatorNotifier:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings

    async def send_ticket(self, session: SupportSession) -> None:
        ticket = session.ticket
        lines = [
            "=== НОВАЯ ЗАЯВКА НА ВОЗВРАТ ===",
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
            f"Telegram user id: {session.user_id}",
            f"Telegram username: @{session.telegram_username}" if session.telegram_username else "Telegram username: -",
            "",
            "=== КОНЕЦ ===",
        ]
        await self._bot.send_message(self._settings.operator_chat_id, "\n".join(lines))
