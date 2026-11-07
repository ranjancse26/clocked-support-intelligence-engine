from abc import ABC, abstractmethod

from app.adapters.clocked import ClockedAdapter
from app.adapters.typellm import TypeLLMAdapter
from app.adapters.payment import DemoPaymentProvider

clocked = ClockedAdapter()
typellm = TypeLLMAdapter()
payments = DemoPaymentProvider()


def plain(x):
    """Recursively coerce SDK/model objects into JSON-serializable dicts.

    typellm's SDK returns Generation objects whose nested fields (e.g.
    category value/probabilities, Usage) are not plain dicts, so a shallow
    conversion is not enough for the JSON ticket columns.
    """
    if isinstance(x, dict):
        return {k: plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [plain(v) for v in x]
    for attr in ("model_dump", "dict"):  # pydantic v2, then pydantic v1
        if hasattr(x, attr):
            try:
                return plain(getattr(x, attr)())
            except Exception:
                pass
    if hasattr(x, "__dict__"):
        return plain(vars(x))
    return x


class BaseTicketHandler(ABC):
    """Base class for category-specific ticket processing.

    Subclass this to add support for new ticket categories (technical,
    account, feature_request, ...) without touching the shared pipeline in
    :func:`app.service.process_ticket`.
    """

    category: str = "default"

    def handles(self, category: str | None) -> bool:
        """Return True when this handler owns the given ticket category."""
        return category == self.category

    @abstractmethod
    def process(self, db, ticket, context: str, result: dict, response: dict) -> None:
        """Run category-specific work after TypeLLM classification.

        Mutates ``ticket`` in place and commits persistent state changes.
        ``result`` is the plain TypeLLM result dict; ``response`` is the raw
        SDK response (useful for resume-style multi-turn calls).
        """
        raise NotImplementedError

    def approve(self, db, ticket, reviewer_id: str, decision: str, reason: str | None):
        """Handle a human review/approval decision for this ticket type."""
        raise NotImplementedError(f"{self.category!r} handler does not support approval decisions")


