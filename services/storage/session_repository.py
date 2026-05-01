from core import SupportSession


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[int, SupportSession] = {}
        self._web_sessions: dict[str, SupportSession] = {}  # session_id -> SupportSession

    def get_or_create(
        self,
        user_id: int,
        chat_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> SupportSession:
        session = self._sessions.get(user_id)
        if session is None:
            session = SupportSession(
                user_id=user_id,
                chat_id=chat_id,
                telegram_username=telegram_username,
                telegram_first_name=telegram_first_name,
            )
            self._sessions[user_id] = session
            return session

        session.chat_id = chat_id
        session.telegram_username = telegram_username
        session.telegram_first_name = telegram_first_name
        return session

    def get_or_create_web(
        self,
        session_id: str,
        user_id: int,
    ) -> SupportSession:
        """Создает или возвращает web-сессию"""
        session = self._web_sessions.get(session_id)
        if session is None:
            session = SupportSession(
                user_id=user_id,
                chat_id=0,  # для web-сессий chat_id не используется
                telegram_username=None,
                telegram_first_name=None,
                web_session_id=session_id,
                is_web=True,
                is_demo=True,  # web-сессии всегда демо: заявка не уйдёт оператору
            )
            self._web_sessions[session_id] = session
        return session

    def reset(self, user_id: int) -> None:
        if user_id in self._sessions:
            self._sessions[user_id].reset()

    def delete_web_session(self, session_id: str) -> None:
        """Удаляет web-сессию. Следующее сообщение создаст новую чистую сессию."""
        self._web_sessions.pop(session_id, None)
