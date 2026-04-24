from core import SupportTicket


def format_collected_ticket(ticket: SupportTicket) -> str:
    lines = [
        f"Имя: {ticket.name or '-'}",
        f"Контакт: {ticket.contact or '-'}",
        f"Номер заказа: {ticket.order_number or '-'}",
        f"Товар: {ticket.product_name or '-'}",
        f"Причина возврата: {ticket.return_reason or '-'}",
        f"Дата покупки: {ticket.purchase_date or '-'}",
        f"Состояние товара: {ticket.item_condition or '-'}",
        f"Способ возврата денег: {ticket.refund_method or '-'}",
    ]
    return "\n".join(lines)
