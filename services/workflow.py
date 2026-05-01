import logging
import time

from core import SupportSession, get_settings
from services.assistant import OpenAISupportAssistant
from services.assistant.condition_detector import detect_item_condition
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)

FINAL_CLIENT_MESSAGE = (
    "Спасибо! Я передал вашу заявку на возврат специалисту. "
    "Мы свяжемся с вами в ближайшее время."
)

RATE_LIMIT_MESSAGE = (
    "Вы отправили слишком много сообщений. "
    "Пожалуйста, подождите некоторое время перед продолжением."
)


class SupportWorkflowService:
    def __init__(
        self,
        assistant: OpenAISupportAssistant,
        notifier: OperatorNotifier,
    ) -> None:
        self._assistant = assistant
        self._notifier = notifier
        self._settings = get_settings()

    def _check_rate_limit(self, session: SupportSession) -> bool:
        """
        Проверяет, не превышен ли лимит сообщений для пользователя.
        
        Returns:
            True если лимит превышен, False если можно продолжать
        """
        current_time = time.time()
        
        # Проверяем, нужно ли сбросить счетчик
        if current_time >= session.rate_limit_reset_time:
            # Окно истекло, сбрасываем счетчик
            session.message_count = 0
            session.rate_limit_notified = False
            session.rate_limit_reset_time = current_time + self._settings.rate_limit_window_seconds
            logger.info("Rate limit reset for user_id=%s", session.user_id)
        
        # Увеличиваем счетчик
        session.message_count += 1
        
        # Проверяем лимит
        if session.message_count > self._settings.rate_limit_messages:
            logger.warning(
                "Rate limit exceeded for user_id=%s: %d/%d messages",
                session.user_id,
                session.message_count,
                self._settings.rate_limit_messages
            )
            return True
        
        return False

    async def process_message(self, session: SupportSession, message_text: str) -> str:
        # ВАЖНО: Проверка лимита ДО вызова LLM
        if self._check_rate_limit(session):
            # Лимит превышен
            if not session.rate_limit_notified:
                # Отправляем уведомление только один раз
                session.rate_limit_notified = True
                logger.info("Sending rate limit notification to user_id=%s", session.user_id)
                return RATE_LIMIT_MESSAGE
            else:
                # Уведомление уже было отправлено, молча игнорируем
                logger.info("Ignoring message from rate-limited user_id=%s", session.user_id)
                return ""  # Пустая строка = не отправляем ответ
        
        if session.submitted:
            session.reset()

        self._prefill_contact_from_telegram(session)
        history_before_turn = session.recent_history()
        is_new_session = not history_before_turn and not session.started

        turn = await self._assistant.generate_turn(
            current_ticket=session.ticket,
            user_message=message_text,
            is_new_session=is_new_session,
            conversation_history=history_before_turn,
            last_assistant_message=session.last_assistant_message,
            telegram_first_name=session.telegram_first_name,
            is_demo=session.is_demo,
        )

        session.add_user_message(message_text)
        
        # Автоопределение состояния товара из сообщения пользователя
        detected_condition = detect_item_condition(message_text)
        if detected_condition and not session.ticket.item_condition:
            logger.info(
                "Auto-detected item_condition='%s' for user_id=%s from message",
                detected_condition,
                session.user_id
            )
        
        # Проверяем, отказался ли пользователь от указания информации
        user_declined = self._check_user_declined(message_text)
        
        # Определяем, на каком этапе мы находимся
        required_complete = session.ticket.is_complete()
        waiting_for_purchase_date = (
            required_complete 
            and not session.ticket.purchase_date 
            and not session.purchase_date_asked
        )
        waiting_for_refund_method = (
            required_complete 
            and (session.ticket.purchase_date or session.purchase_date_asked)
            and not session.ticket.refund_method 
            and not session.refund_method_asked
        )
        
        # Обновляем ticket
        # Собираем подтвержденные поля (только те, которые уже точно заполнены и подтверждены)
        confirmed_fields = set()
        if session.name_confirmed and session.ticket.name:
            confirmed_fields.add("name")
        if session.order_number_confirmed and session.ticket.order_number:
            confirmed_fields.add("order_number")
        if session.product_name_confirmed and session.ticket.product_name:
            confirmed_fields.add("product_name")
        if session.return_reason_confirmed and session.ticket.return_reason:
            confirmed_fields.add("return_reason")
        if session.item_condition_confirmed and session.ticket.item_condition:
            confirmed_fields.add("item_condition")
        
        if user_declined:
            # Если пользователь отказался, помечаем соответствующий флаг
            if waiting_for_purchase_date:
                session.purchase_date_asked = True
                logger.info("User declined to provide purchase_date for user_id=%s", session.user_id)
            elif waiting_for_refund_method:
                session.refund_method_asked = True
                logger.info("User declined to provide refund_method for user_id=%s", session.user_id)
            else:
                # Отказ на этапе сбора обязательных полей - обновляем как обычно
                session.ticket.merge(turn.extracted_ticket, protect_required=False, confirmed_fields=confirmed_fields)
        else:
            # Пользователь дал нормальный ответ
            old_ticket = session.ticket.model_copy()
            
            # Обновляем ticket (защищаем только подтвержденные поля)
            session.ticket.merge(turn.extracted_ticket, protect_required=False, confirmed_fields=confirmed_fields)
            
            # Применяем автоопределенное состояние, если оно есть и item_condition еще не заполнен
            if detected_condition and not session.ticket.item_condition:
                session.ticket.item_condition = detected_condition
                logger.info(
                    "Applied auto-detected item_condition='%s' for user_id=%s",
                    detected_condition,
                    session.user_id
                )
            
            # Помечаем поля как подтвержденные, если они были успешно заполнены
            if not session.name_confirmed and session.ticket.name:
                session.name_confirmed = True
                logger.debug("name confirmed for user_id=%s", session.user_id)
            if not session.order_number_confirmed and session.ticket.order_number:
                session.order_number_confirmed = True
                logger.debug("order_number confirmed for user_id=%s", session.user_id)
            if not session.product_name_confirmed and session.ticket.product_name:
                session.product_name_confirmed = True
                logger.debug("product_name confirmed for user_id=%s", session.user_id)
            if not session.return_reason_confirmed and session.ticket.return_reason:
                session.return_reason_confirmed = True
                logger.debug("return_reason confirmed for user_id=%s", session.user_id)
            if not session.item_condition_confirmed and session.ticket.item_condition:
                session.item_condition_confirmed = True
                logger.debug("item_condition confirmed for user_id=%s", session.user_id)
        
        session.started = True

        # Пересчитываем после обновления (учитываем демо-режим)
        required_complete = session.ticket.is_complete(is_demo=session.is_demo)
        
        # Определяем, что нужно спросить дальше
        should_ask_optional = False
        optional_reply = None
        
        if required_complete:
            # Обязательные поля собраны, проверяем необязательные по очереди
            
            # Сначала проверяем purchase_date
            if not session.ticket.purchase_date and not session.purchase_date_asked:
                should_ask_optional = True
                optional_reply = "Когда вы приобрели товар? Укажите примерную дату покупки."
                session.purchase_date_asked = True
                logger.info("Asking for purchase_date for user_id=%s", session.user_id)
            
            # Затем проверяем refund_method (только если purchase_date уже обработан)
            elif (session.ticket.purchase_date or session.purchase_date_asked) and \
                 not session.ticket.refund_method and not session.refund_method_asked:
                should_ask_optional = True
                optional_reply = "Как вам удобнее получить возврат: на карту, на исходный способ оплаты или обмен на другой товар?"
                session.refund_method_asked = True
                logger.info("Asking for refund_method for user_id=%s", session.user_id)
        
        # Определяем, готовы ли к отправке
        # Отправляем только если:
        # 1. Обязательные поля собраны (с учетом демо-режима)
        # 2. purchase_date либо заполнен, либо уже спрашивали
        # 3. refund_method либо заполнен, либо уже спрашивали
        # 4. Ассистент подтвердил готовность (ready_to_submit)
        # 5. НЕ нужно задавать вопрос о необязательном поле прямо сейчас
        ready_to_send = (
            required_complete 
            and (session.ticket.purchase_date or session.purchase_date_asked)
            and (session.ticket.refund_method or session.refund_method_asked)
            and turn.ready_to_submit
            and not should_ask_optional  # ВАЖНО: не отправляем, если нужно задать вопрос
        )
        
        if ready_to_send:
            await self._notifier.send_ticket(session)
            session.submitted = True
            session.add_assistant_message(FINAL_CLIENT_MESSAGE)
            logger.info("Ticket submitted for user_id=%s", session.user_id)
            return FINAL_CLIENT_MESSAGE
        
        # Если нужно дозапросить необязательное поле, используем fallback-ответ
        if should_ask_optional and optional_reply:
            session.add_assistant_message(optional_reply)
            return optional_reply

        session.add_assistant_message(turn.reply)
        return turn.reply
    
    @staticmethod
    def _check_user_declined(message: str) -> bool:
        """Проверяет, отказался ли пользователь от указания информации"""
        decline_phrases = [
            "не помню", "не знаю", "уточню позже", "без разницы",
            "не важно", "пропустить", "дальше", "не указывать",
            "не хочу", "потом", "позже", "менеджер решит", "оператор решит"
        ]
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in decline_phrases)

    @staticmethod
    def _prefill_contact_from_telegram(session: SupportSession) -> None:
        if session.ticket.contact:
            return
        if session.telegram_username:
            session.ticket.contact = f"@{session.telegram_username}"

    async def close(self) -> None:
        await self._assistant.close()
