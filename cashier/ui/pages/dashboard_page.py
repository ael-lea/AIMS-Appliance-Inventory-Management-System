"""Home page: four big summary cards."""
import tkinter as tk

import customtkinter as ctk

from cashier.config import Theme
from cashier.database.connection import DatabaseError
from cashier.ui.base_page import BasePage
from cashier.ui.widgets import load_icon, show_db_error, styled_button
from cashier.utils import peso


class DashboardPage(BasePage):
    HEADING = None
    SHOW_BACK_BUTTON = False

    # title, key, picture file, symbol used when there is no picture, x, y
    CARD_SPECS = (
        ("Today's Sales", "sales", "mainsales.png", "₱", 30, 55),
        ("Completed Orders", "completed", None, "✔", 670, 55),
        ("Pending Orders", "pending", None, "⏳", 30, 270),
        ("Available Products", "products", "prod.png", "▦", 670, 270),
    )

    def __init__(self, window, navigate, context):
        super().__init__(window, navigate, context)
        self._icons = []                       # keeps the card pictures alive
        self._value_labels = {}

    def _build(self):
        for spec in self.CARD_SPECS:
            self._build_card(*spec)
        self.refresh()
        styled_button(self._frame, "New Order", lambda: self._navigate("Order Entry"),
                      True, 14).place(x=30, y=500)
        styled_button(self._frame, "Refresh", self.refresh, False, 10).place(x=190, y=500)

    def _build_card(self, title, key, icon_file, symbol, x, y):
        card = ctk.CTkFrame(self._frame, fg_color=Theme.CARD_GRAY, corner_radius=10,
                            height=200, width=625)
        card.place(x=x, y=y)
        card.pack_propagate(False)
        icon = load_icon(icon_file)
        if icon:
            self._icons.append(icon)
            tk.Label(card, image=icon, bg=Theme.CARD_GRAY).pack(pady=(35, 0))
        else:
            tk.Label(card, text=symbol, font=("Segoe UI Symbol", 30),
                     bg=Theme.CARD_GRAY, fg=Theme.BG).pack(pady=(30, 0))
        tk.Label(card, text=title, bg=Theme.CARD_GRAY, font=("Helvetica", 14),
                 fg=Theme.BG).pack()
        value = tk.Label(card, text="0", bg=Theme.CARD_GRAY, font=("Helvetica", 20),
                         fg=Theme.BG)
        value.pack()
        self._value_labels[key] = value

    def refresh(self):
        try:
            values = {
                "sales": peso(self._context.sales.today_sales()),
                "completed": str(self._context.sales.today_completed_count()),
                "pending": str(self._context.orders.count_pending()),
                "products": str(self._context.products.count_available()),
            }
        except DatabaseError as error:
            show_db_error(error)
            return
        for key, text in values.items():
            self._value_labels[key].config(text=text)
