"""Small shared state between pages."""


class PendingOrderBuffer:
    """Carries a held order from Order History back into Order Entry."""

    def __init__(self):
        self._order_id = None
        self._items = []

    def store(self, order_id, items):
        self._order_id = order_id
        self._items = list(items)

    def take(self):
        """Return (order_id, items) and empty the buffer."""
        order_id, items = self._order_id, self._items
        self._order_id, self._items = None, []
        return order_id, items
