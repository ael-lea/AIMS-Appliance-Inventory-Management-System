"""Abstract parent of every cashier page (Template Method pattern)."""
import tkinter as tk
from abc import ABC, abstractmethod

from cashier.config import Theme
from cashier.ui.widgets import make_back_button


class BasePage(ABC):
    """Builds the common page frame, then lets the subclass fill it in.

    Subclasses set HEADING / SHOW_BACK_BUTTON and implement _build().
    """

    HEADING = None             # big title at the top; None = no title
    SHOW_BACK_BUTTON = True

    def __init__(self, window, navigate, context):
        self._window = window
        self._navigate = navigate
        self._context = context
        self._frame = None

    @property
    def frame(self):
        return self._frame

    def show(self):
        """Create the frame and build the page (the template method)."""
        self._frame = tk.Frame(self._window, width=1315, height=720, bg=Theme.BG)
        self._frame.place(x=200, y=70)
        self._frame.pack_propagate(False)
        if self.HEADING:
            tk.Label(self._frame, text=self.HEADING, font=("Helvetica", 30, "bold"),
                     bg=Theme.BG, fg=Theme.NAVY).pack(anchor="w", padx=40)
        if self.SHOW_BACK_BUTTON:
            make_back_button(self._frame, self._navigate)
        self._build()
        return self

    def destroy(self):
        if self._frame is not None:
            self._frame.destroy()
            self._frame = None

    @abstractmethod
    def _build(self):
        """Create this page's widgets inside self._frame."""
