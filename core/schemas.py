import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ItemCondition = Literal["не использовался", "вскрыт", "использовался", "повреждён"]
RefundMethod = Literal["на карту", "на исходный способ оплаты", "обмен", "уточнит оператор"]
MessageRole = Literal["user", "assistant"]


class SupportTicket(BaseModel):
    name: str | None = None
    contact: str | None = None
    order_number: str | None = None
    product_name: str | None = None
    return_reason: str | None = None
    purchase_date: str | None = None
    item_condition: ItemCondition | None = None
    refund_method: RefundMethod | None = None

    @field_validator("name", "contact", "product_name", "return_reason", "purchase_date")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    @field_validator("order_number")
    @classmethod
    def validate_order_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.match(r'^[A-Za-zА-Яа-я0-9-]{3,30}$', cleaned):
            return None
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        if len(cleaned) < 2:
            return None
        if cleaned.isdigit():
            return None
        return cleaned

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        if len(cleaned) < 2:
            return None
        return cleaned

    @field_validator("return_reason")
    @classmethod
    def validate_return_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        if len(cleaned) < 3:
            return None
        return cleaned

    def merge(self, other: "SupportTicket", protect_required: bool = False, confirmed_fields: set[str] | None = None) -> None:
        """
        Объединяет данные из другого тикета.
        
        Args:
            other: Тикет с новыми данными
            protect_required: Deprecated, используйте confirmed_fields
            confirmed_fields: Набор полей, которые уже подтверждены и не должны перезаписываться
        """
        confirmed_fields = confirmed_fields or set()
        
        for field_name, value in other.model_dump().items():
            if value not in (None, ""):
                # Если поле подтверждено - не перезаписываем
                if field_name in confirmed_fields:
                    continue
                
                setattr(self, field_name, value)

    def is_complete(self) -> bool:
        return all(
            [
                self.name,
                self.contact,
                self.order_number,
                self.product_name,
                self.return_reason,
                self.item_condition,
            ]
        )


class DialogueMessage(BaseModel):
    role: MessageRole
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            raise ValueError("Dialogue message cannot be empty")
        return cleaned


class AssistantTurn(BaseModel):
    reply: str = Field(min_length=1)
    extracted_ticket: SupportTicket = Field(default_factory=SupportTicket)
    ready_to_submit: bool = False


class SupportSession(BaseModel):
    user_id: int
    chat_id: int
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    web_session_id: str | None = None  # Для web-сессий
    is_web: bool = False  # Флаг: это web-сессия
    started: bool = False
    submitted: bool = False
    ticket: SupportTicket = Field(default_factory=SupportTicket)
    history: list[DialogueMessage] = Field(default_factory=list)
    
    # Флаги для мягкого дозапроса необязательных полей
    purchase_date_asked: bool = False
    refund_method_asked: bool = False
    
    # Флаги подтверждения обязательных полей (защита от перезаписи)
    name_confirmed: bool = False
    order_number_confirmed: bool = False
    product_name_confirmed: bool = False
    return_reason_confirmed: bool = False
    item_condition_confirmed: bool = False
    
    # Rate limiting
    message_count: int = 0
    rate_limit_notified: bool = False  # Флаг: уведомление о лимите уже отправлено
    rate_limit_reset_time: float = 0.0  # Время сброса лимита (unix timestamp)

    def add_user_message(self, text: str) -> None:
        self._append_history("user", text)

    def add_assistant_message(self, text: str) -> None:
        self._append_history("assistant", text)

    def recent_history(self, limit: int = 8) -> list[DialogueMessage]:
        return list(self.history[-limit:])

    @property
    def last_assistant_message(self) -> str | None:
        for message in reversed(self.history):
            if message.role == "assistant":
                return message.text
        return None

    def reset(self) -> None:
        self.started = False
        self.submitted = False
        self.ticket = SupportTicket()
        self.history = []
        self.purchase_date_asked = False
        self.refund_method_asked = False
        self.name_confirmed = False
        self.order_number_confirmed = False
        self.product_name_confirmed = False
        self.return_reason_confirmed = False
        self.item_condition_confirmed = False
        # Rate limiting НЕ сбрасывается при reset диалога

    def _append_history(self, role: MessageRole, text: str) -> None:
        self.history.append(DialogueMessage(role=role, text=text))
        if len(self.history) > 20:
            self.history = self.history[-20:]
