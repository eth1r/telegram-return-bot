import asyncio
import json
import logging
import re

import httpx

from core import AssistantTurn, Settings, SupportTicket
from core.schemas import DialogueMessage
from services.assistant.prompts import ASSISTANT_RESPONSE_SCHEMA, SUPPORT_ASSISTANT_PROMPT

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


class OpenAISupportAssistant:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        
        # Настройка proxy для OpenAI API
        # httpx использует формат: {"http://": "proxy_url", "https://": "proxy_url"}
        # или просто строку для всех протоколов
        proxy = None
        if settings.https_proxy:
            proxy = settings.https_proxy
        elif settings.http_proxy:
            proxy = settings.http_proxy
        
        if proxy:
            logger.info("OpenAI client configured with proxy")
        
        self._client = httpx.AsyncClient(
            base_url=settings.openai_base_url,
            timeout=httpx.Timeout(45.0, connect=12.0),
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            proxy=proxy,  # httpx использует proxy, а не proxies
        )

    async def generate_turn(
        self,
        current_ticket: SupportTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
        is_demo: bool = False,
    ) -> AssistantTurn:
        payload = {
            "model": self._settings.openai_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SUPPORT_ASSISTANT_PROMPT},
                {
                    "role": "user",
                    "content": self._build_user_prompt(
                        current_ticket=current_ticket,
                        user_message=user_message,
                        is_new_session=is_new_session,
                        conversation_history=conversation_history,
                        last_assistant_message=last_assistant_message,
                        telegram_first_name=telegram_first_name,
                        is_demo=is_demo,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": ASSISTANT_RESPONSE_SCHEMA,
            },
        }

        try:
            response = await self._post_with_retries(payload)
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return AssistantTurn.model_validate(json.loads(content))
        except Exception:
            logger.exception("Falling back to local support turn generation")
            return self._build_fallback_turn(
                current_ticket=current_ticket,
                user_message=user_message,
                is_new_session=is_new_session,
                conversation_history=conversation_history,
                last_assistant_message=last_assistant_message,
                telegram_first_name=telegram_first_name,
                is_demo=is_demo,
            )

    async def close(self) -> None:
        await self._client.aclose()

    async def _post_with_retries(self, payload: dict) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(1, 4):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code not in RETRYABLE_STATUS_CODES or attempt == 3:
                    raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == 3:
                    break

            await asyncio.sleep(0.75 * attempt)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _build_user_prompt(
        current_ticket: SupportTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
        is_demo: bool = False,
    ) -> str:
        ticket_json = json.dumps(current_ticket.model_dump(), ensure_ascii=False, indent=2)
        history_json = json.dumps(
            [message.model_dump() for message in conversation_history],
            ensure_ascii=False,
            indent=2,
        )
        first_name = telegram_first_name or "null"
        last_bot_message = last_assistant_message or "null"

        return (
            f"is_new_session: {str(is_new_session).lower()}\n"
            f"is_demo: {str(is_demo).lower()}\n"
            f"telegram_first_name: {first_name}\n"
            f"current_ticket:\n{ticket_json}\n\n"
            f"conversation_history:\n{history_json}\n\n"
            f"last_assistant_message:\n{last_bot_message}\n\n"
            f"latest_user_message:\n{user_message}"
        )

    def _build_fallback_turn(
        self,
        current_ticket: SupportTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
        is_demo: bool = False,
    ) -> AssistantTurn:
        message = self._normalize_text(user_message)
        message_lower = message.lower()
        extracted = SupportTicket()
        requested_field = self._detect_requested_field(last_assistant_message)

        if self._is_repeat_question_request(message_lower):
            repeated_question = last_assistant_message or "Пока мы не дошли до следующего вопроса."
            return AssistantTurn(
                reply=f"Последний мой вопрос был таким: {repeated_question}",
                extracted_ticket=extracted,
                ready_to_submit=current_ticket.is_complete(),
            )

        # Извлечение имени
        if not current_ticket.name and self._looks_like_name(message):
            extracted.name = message

        # Извлечение контакта
        if not current_ticket.contact:
            contact = self._extract_contact(message)
            if contact:
                extracted.contact = contact

        # Извлечение номера заказа
        if not current_ticket.order_number:
            order_num = self._extract_order_number(message)
            if order_num:
                extracted.order_number = order_num

        # Извлечение состояния товара
        if not current_ticket.item_condition:
            condition = self._extract_item_condition(message_lower)
            if condition:
                extracted.item_condition = condition

        # Извлечение способа возврата
        if not current_ticket.refund_method:
            method = self._extract_refund_method(message_lower)
            if method:
                extracted.refund_method = method

        # Обработка по запрошенному полю
        if requested_field == "name" and not extracted.name and self._looks_like_name(message):
            extracted.name = message
        elif requested_field == "contact" and not extracted.contact:
            extracted.contact = self._extract_contact(message)
        elif requested_field == "order_number" and not extracted.order_number:
            extracted.order_number = self._extract_order_number(message)
        elif requested_field == "product_name" and not current_ticket.product_name:
            extracted.product_name = message
        elif requested_field == "return_reason" and not current_ticket.return_reason:
            extracted.return_reason = message
        elif requested_field == "purchase_date" and not current_ticket.purchase_date:
            extracted.purchase_date = message
        elif requested_field == "item_condition" and not extracted.item_condition:
            extracted.item_condition = self._extract_item_condition(message_lower)
        elif requested_field == "refund_method" and not extracted.refund_method:
            extracted.refund_method = self._extract_refund_method(message_lower)

        # Если не извлекли название товара и его нет, пробуем взять из сообщения
        if not extracted.product_name and not current_ticket.product_name and len(message) >= 2:
            if not self._looks_like_name(message) and not self._extract_contact(message):
                extracted.product_name = message

        # Если не извлекли причину возврата и её нет, пробуем взять из сообщения
        if not extracted.return_reason and not current_ticket.return_reason and len(message) >= 3:
            if not self._looks_like_name(message) and not self._extract_contact(message):
                extracted.return_reason = message

        merged_ticket = current_ticket.model_copy(deep=True)
        merged_ticket.merge(extracted)

        reply = self._build_fallback_reply(
            merged_ticket=merged_ticket,
            extracted=extracted,
            is_new_session=is_new_session,
            conversation_history=conversation_history,
            telegram_first_name=telegram_first_name,
            is_demo=is_demo,
        )

        return AssistantTurn(
            reply=reply,
            extracted_ticket=extracted,
            ready_to_submit=merged_ticket.is_complete(is_demo=is_demo),
        )

    def _build_fallback_reply(
        self,
        merged_ticket: SupportTicket,
        extracted: SupportTicket,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        telegram_first_name: str | None,
        is_demo: bool = False,
    ) -> str:
        if not conversation_history and is_new_session:
            if is_demo:
                # В демо-режиме сразу спрашиваем номер заказа
                return "Здравствуйте! Я помогу вам оформить возврат товара. Укажите, пожалуйста, номер заказа."
            else:
                # В обычном режиме спрашиваем имя
                if not extracted.name and not merged_ticket.name:
                    return "Здравствуйте! Я помогу вам оформить возврат товара. Как вас зовут?"

        # В демо-режиме пропускаем name и contact
        if not is_demo:
            if not merged_ticket.name:
                return "Подскажите, как к вам обращаться?"

            if not merged_ticket.contact:
                return "Оставьте, пожалуйста, контакт для связи: телефон, email или Telegram."

        if not merged_ticket.order_number:
            return "Укажите, пожалуйста, номер заказа."

        if not merged_ticket.product_name:
            return "Какой товар вы хотите вернуть?"

        if not merged_ticket.return_reason:
            return "Укажите, пожалуйста, причину возврата."

        if not merged_ticket.item_condition:
            return "В каком состоянии товар: не использовался, вскрыт, использовался или повреждён?"

        return "Спасибо! Проверяю, всё ли собрано по заявке."

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @staticmethod
    def _is_repeat_question_request(message_lower: str) -> bool:
        triggers = [
            "какой был прошлый вопрос",
            "какой был предыдущий вопрос",
            "повтори вопрос",
            "повтори последний вопрос",
            "что ты спрашивал",
            "что вы спрашивали",
        ]
        return any(trigger in message_lower for trigger in triggers)

    @staticmethod
    def _detect_requested_field(last_assistant_message: str | None) -> str | None:
        if not last_assistant_message:
            return None

        message = last_assistant_message.lower()
        if any(phrase in message for phrase in ["как вас зовут", "как к вам обращаться"]):
            return "name"
        if any(phrase in message for phrase in ["контакт", "телефон", "email", "telegram"]):
            return "contact"
        if any(phrase in message for phrase in ["номер заказа"]):
            return "order_number"
        if any(phrase in message for phrase in ["какой товар", "название товара"]):
            return "product_name"
        if any(phrase in message for phrase in ["причину возврата", "почему возвращаете"]):
            return "return_reason"
        if any(phrase in message for phrase in ["дата покупки", "когда купили"]):
            return "purchase_date"
        if any(phrase in message for phrase in ["состоянии товар", "использовался", "вскрыт", "повреждён"]):
            return "item_condition"
        if any(phrase in message for phrase in ["способ возврата", "вернуть деньги", "на карту"]):
            return "refund_method"
        return None

    @staticmethod
    def _looks_like_name(message: str) -> bool:
        lowered = message.lower()
        blockers = [
            "заказ",
            "товар",
            "возврат",
            "не подошл",
            "брак",
            "дефект",
            "повреж",
        ]
        if any(blocker in lowered for blocker in blockers):
            return False
        if any(char.isdigit() for char in message):
            return False
        words = [word for word in re.split(r"\s+", message) if word]
        return 1 <= len(words) <= 3

    @staticmethod
    def _extract_contact(message: str) -> str | None:
        if message.startswith("@") and len(message) > 1:
            return message

        # Проверка email
        if "@" in message and "." in message:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, message.strip()):
                return message.strip()

        # Проверка телефона
        compact = re.sub(r"[^\d+]", "", message)
        digits = re.sub(r"\D", "", compact)
        if len(digits) >= 10:
            return compact
        return None

    @staticmethod
    def _extract_order_number(message: str) -> str | None:
        cleaned = message.strip()
        if re.match(r'^[A-Za-zА-Яа-я0-9-]{3,30}$', cleaned):
            return cleaned
        return None

    @staticmethod
    def _extract_item_condition(message_lower: str) -> str | None:
        if "не использовал" in message_lower or "не открывал" in message_lower:
            return "не использовался"
        if "вскрыт" in message_lower or "открыт" in message_lower or "распаков" in message_lower:
            return "вскрыт"
        if "использовал" in message_lower or "пользовал" in message_lower:
            return "использовался"
        if "повреж" in message_lower or "сломан" in message_lower or "брак" in message_lower or "дефект" in message_lower:
            return "повреждён"
        return None

    @staticmethod
    def _extract_refund_method(message_lower: str) -> str | None:
        if "на карту" in message_lower or "карт" in message_lower:
            return "на карту"
        if "исходн" in message_lower or "как оплачивал" in message_lower or "как платил" in message_lower:
            return "на исходный способ оплаты"
        if "обмен" in message_lower or "замен" in message_lower:
            return "обмен"
        if "уточн" in message_lower or "не знаю" in message_lower or "потом" in message_lower:
            return "уточнит оператор"
        return None


