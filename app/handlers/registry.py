from app.handlers.base import BaseTicketHandler

class HandlerRegistry:
    """Maps ticket categories to their processing handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, BaseTicketHandler] = {}
        self._default: BaseTicketHandler | None = None

    def register(self, handler: BaseTicketHandler) -> None:
        """Register ``handler`` for its declared category."""
        self._handlers[handler.category] = handler
        if handler.category == "default":
            self._default = handler

    def get(self, category: str | None) -> BaseTicketHandler:
        """Return the handler for ``category``, falling back to the default."""
        if category and category in self._handlers:
            return self._handlers[category]
        if self._default is not None:
            return self._default
        raise ValueError(f"No handler registered for category {category!r}")

    def __contains__(self, category: str) -> bool:
        return category in self._handlers
