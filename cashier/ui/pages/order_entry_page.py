"""Order Entry page: pick products, build the cart, take payment.

Layout:  LEFT = product selection (x 20-620)   RIGHT = current order (x 650-1280)
"""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from cashier.card_number import (
    CARD_METHOD, MAX_DIGITS, card_number_problem, clean_card_number, last_four)
from cashier.config import Settings, Theme
from cashier.database.connection import DatabaseError
from cashier.models import Cart
from cashier.payments import PaymentFactory
from cashier.services.checkout_service import InsufficientStockError, ShipTo
from cashier.ui.base_page import BasePage
from cashier.ui.recipient_picker import RecipientPicker
from cashier.ui.widgets import make_tree, show_db_error, styled_button
from cashier.utils import peso


class OrderEntryPage(BasePage):
    HEADING = "Order Entry"
    CARDS_PER_ROW = 3

    def __init__(self, window, navigate, context):
        super().__init__(window, navigate, context)
        self._cart = Cart()
        self._payment = PaymentFactory.create("Cash")     # current PaymentMethod
        self._search_term = ""
        self._category = "All"
        self._resumed_order_id = None                      # set when resuming a held order
        self._card_actions = []                            # "add" callbacks of visible cards
        self._chip_buttons = {}
        self._method_buttons = {}

    # ==================================================================
    # Building the page
    # ==================================================================
    def _build(self):
        self._restore_held_order()
        self._build_product_panel()
        self._build_cart_panel()
        self._apply_held_shipping()
        self._build_totals_panel()
        self._build_payment_panel()
        self._build_action_buttons()
        self._tender_var.trace_add("write", self._on_tender_changed)
        self._build_chips()
        self._frame.after(100, self._search_entry.focus_set)
        self.refresh_cart()                  # also loads the product cards

    def _restore_held_order(self):
        """If the cashier pressed 'Resume' in Order History, reload that cart."""
        order_id, items = self._context.pending_order.take()
        if items:
            self._cart.replace_with(items)
            self._resumed_order_id = order_id

    def _apply_held_shipping(self):
        """A resumed held order gets back the recipient / 'Ship this order' choice it was saved with."""
        if self._resumed_order_id is None:
            return
        try:
            recipient_id, ship = self._context.orders.get_shipping(self._resumed_order_id)
        except DatabaseError as error:
            show_db_error(error)
            return
        self._ship_var.set(ship)
        if recipient_id is not None:
            self._recipient_picker.select(recipient_id)    # stays empty if they were deleted
        self._sync_shipping_ui()

    def _sync_shipping_ui(self):
        """Ticked: the recipient picker is active. Unticked: it is locked and no shipment is made."""
        self._recipient_picker.set_enabled(
            self._ship_var.get(), "This order will not be shipped (counter sale).")

    # ---- left side: product selection ----------------------------------------------
    def _build_product_panel(self):
        frame = self._frame
        tk.Label(frame, text="Product Selection", font=("Helvetica", 13, "bold"),
                 bg=Theme.BG, fg=Theme.NAVY).place(x=20, y=48)

        search_bar = tk.Frame(frame, bg=Theme.BG)
        search_bar.place(x=20, y=80, width=600, height=36)
        self._search_entry = ctk.CTkEntry(
            search_bar, width=380, height=36, corner_radius=10, border_width=1,
            border_color=Theme.ENTRY_BORDER, fg_color="white", text_color=Theme.TEXT,
            placeholder_text="Search name or ID", font=ctk.CTkFont("Helvetica", 13))
        self._search_entry.pack(side=tk.LEFT)
        styled_button(search_bar, "Search", self._search_products, True, px=100).pack(side=tk.LEFT, padx=(10, 0))
        styled_button(search_bar, "Show All", self._show_all_products, False, px=100).pack(side=tk.LEFT, padx=(10, 0))
        self._search_entry.bind("<Return>", self._on_search_enter)

        self._chip_bar = tk.Frame(frame, bg=Theme.BG)
        self._chip_bar.place(x=20, y=126)

        area = tk.Frame(frame, bg=Theme.BG)
        area.place(x=20, y=166, width=600, height=504)
        self._product_canvas = tk.Canvas(area, bg=Theme.BG, highlightthickness=0)
        scroll = ttk.Scrollbar(area, orient=tk.VERTICAL, command=self._product_canvas.yview)
        self._product_canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._product_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._product_grid = tk.Frame(self._product_canvas, bg=Theme.BG)
        self._grid_window = self._product_canvas.create_window((0, 0), window=self._product_grid, anchor="nw")
        self._product_grid.bind("<Configure>", self._update_product_scroll)
        self._product_canvas.bind(
            "<Configure>", lambda e: self._product_canvas.itemconfigure(self._grid_window, width=e.width))

    def _update_product_scroll(self, _event=None):
        self._product_canvas.configure(scrollregion=self._product_canvas.bbox("all"))

    # ---- right side: cart ------------------------------------------------------------
    def _build_cart_panel(self):
        frame = self._frame
        self._cart_title = tk.Label(frame, text="Current Order", font=("Helvetica", 13, "bold"),
                                    bg=Theme.BG, fg=Theme.NAVY)
        self._cart_title.place(x=650, y=48)
        wrap, self._cart_tree = make_tree(
            frame, ("name", "qty", "price", "line"),
            ("Product", "Qty", "Unit Price", "Subtotal"), (190, 55, 105, 120), height=5)
        wrap.place(x=650, y=85, width=630, height=150)
        # product name on the left, numbers on the right
        self._cart_tree.column("name", anchor=tk.W)
        self._cart_tree.heading("name", anchor=tk.W)
        for column in ("qty", "price", "line"):
            self._cart_tree.column(column, anchor=tk.E)
            self._cart_tree.heading(column, anchor=tk.E)
        self._empty_label = tk.Label(self._cart_tree, text="No items yet.\nSelect a product to begin.",
                                     bg="white", fg=Theme.MUTED, font=("Helvetica", 11),
                                     justify=tk.CENTER)

        actions = tk.Frame(frame, bg=Theme.BG)
        actions.place(x=650, y=243)
        styled_button(actions, "+", lambda: self._adjust_quantity(1), False, px=44).pack(side=tk.LEFT, padx=(0, 8))
        styled_button(actions, "−", lambda: self._adjust_quantity(-1), False, px=44).pack(side=tk.LEFT, padx=(0, 8))
        styled_button(actions, "Remove Item", self._remove_item, False, px=120, danger=True).pack(side=tk.LEFT)

        # "Ship this order": only shipped orders need a recipient and create a shipment
        self._ship_var = tk.BooleanVar(value=True)
        self._ship_check = ctk.CTkCheckBox(
            frame, text="Ship this order", variable=self._ship_var, command=self._sync_shipping_ui,
            width=150, height=28, checkbox_width=22, checkbox_height=22,
            fg_color=Theme.NAVY, hover_color=Theme.ACTIVE, text_color=Theme.TEXT,
            font=ctk.CTkFont("Helvetica", 12, "bold"))
        self._ship_check.place(x=1130, y=247)

        # recipient dropdown + New Recipient button, with the read-only address underneath
        self._recipient_picker = RecipientPicker(frame, self._context.recipients,
                                                 bg=Theme.BG, width=630)
        self._recipient_picker.place(x=650, y=285, width=630)
        self._sync_shipping_ui()

    def _build_totals_panel(self):
        self._totals = tk.Frame(self._frame, bg=Theme.BG)
        self._totals.place(x=650, y=368, width=630)
        self._subtotal_var, self._vat_var, self._total_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self._total_row(0, "Subtotal", self._subtotal_var)
        self._total_row(1, f"VAT ({int(Settings.VAT_RATE * 100)}%)", self._vat_var)
        tk.Frame(self._totals, bg=Theme.NAVY, height=2).grid(row=2, column=0, columnspan=2,
                                                             sticky="ew", pady=(6, 0))
        self._total_row(3, "TOTAL", self._total_var, 17, "bold", fill=Theme.BG, ipady=4)
        self._totals.columnconfigure(1, weight=1)

    def _total_row(self, row, text, variable, size=11, weight="normal", fill=Theme.BG, ipady=0):
        """One label + amount line (same 10 px side padding so everything lines up)."""
        tk.Label(self._totals, text=text, bg=fill, fg=Theme.TEXT, font=("Helvetica", size, weight),
                 anchor="w", padx=10).grid(row=row, column=0, sticky="nsew", pady=2, ipady=ipady)
        tk.Label(self._totals, textvariable=variable, bg=fill, fg=Theme.NAVY,
                 font=("Helvetica", size, weight), anchor="e", padx=10).grid(
                     row=row, column=1, sticky="nsew", pady=2, ipady=ipady)

    def _build_payment_panel(self):
        pay = tk.Frame(self._frame, bg=Theme.BG)
        pay.place(x=650, y=474, width=630)
        pay.columnconfigure(1, weight=1)
        self._tender_var = tk.StringVar()
        self._change_var = tk.StringVar(value=peso(0))

        tk.Label(pay, text="Payment Method:", bg=Theme.BG, fg=Theme.TEXT,
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky=tk.W, padx=(10, 0), pady=4)
        method_row = tk.Frame(pay, bg=Theme.BG)
        method_row.grid(row=0, column=1, sticky=tk.E, pady=4)
        for name in PaymentFactory.NAMES:
            button = ctk.CTkButton(
                method_row, text=name, width=100, height=34, corner_radius=10,
                font=ctk.CTkFont("Helvetica", 13, "bold"), cursor="hand2",
                command=lambda n=name: self._choose_method(n))
            button.pack(side=tk.LEFT, padx=(8, 0))
            self._method_buttons[name] = button

        amount_label = tk.Label(pay, text="Amount Received:", bg=Theme.BG, fg=Theme.TEXT,
                                font=("Helvetica", 10))
        amount_label.grid(row=1, column=0, sticky=tk.W, padx=(10, 0), pady=4)
        self._tender_entry = ctk.CTkEntry(
            pay, textvariable=self._tender_var, width=208, height=36, corner_radius=10,
            border_width=1, border_color=Theme.ENTRY_BORDER, fg_color="white",
            text_color=Theme.TEXT, justify="right", font=ctk.CTkFont("Helvetica", 14),
            validate="key", validatecommand=(pay.register(self._validate_amount), "%P"))
        self._tender_entry.grid(row=1, column=1, sticky=tk.E, pady=4)

        change_label = tk.Label(pay, text="Change:", bg=Theme.BG, fg=Theme.TEXT,
                                font=("Helvetica", 15, "bold"))
        change_label.grid(row=2, column=0, sticky=tk.W, padx=(10, 0), pady=4)
        self._change_value = tk.Label(pay, textvariable=self._change_var, bg=Theme.BG,
                                      fg=Theme.GREEN, font=("Helvetica", 15, "bold"))
        self._change_value.grid(row=2, column=1, sticky=tk.E, padx=(0, 10), pady=4)
        self._cash_only_widgets = [amount_label, self._tender_entry, change_label, self._change_value]

        # card number row: only visible when the Card method is selected
        # (the cash rows above are hidden then, so this row moves up under the method buttons)
        card_label = tk.Label(pay, text="Card Number:", bg=Theme.BG, fg=Theme.TEXT,
                              font=("Helvetica", 10))
        card_label.grid(row=3, column=0, sticky=tk.W, padx=(10, 0), pady=4)
        self._card_var = tk.StringVar()
        # self._card_var.trace_add("write", self._format_card_number)
        self._card_entry = ctk.CTkEntry(
            pay, textvariable=self._card_var, width=208, height=36, corner_radius=10,
            border_width=1, border_color=Theme.ENTRY_BORDER, fg_color="white",
            text_color=Theme.TEXT, justify="right", placeholder_text="13-19 digits",
            font=ctk.CTkFont("Helvetica", 14),
            validate="key", validatecommand=(pay.register(self._validate_card_input), "%P"))
        self._card_entry.grid(row=3, column=1, sticky=tk.E, pady=4)
        self._card_only_widgets = [card_label, self._card_entry]

    @staticmethod
    def _validate_amount(value):
        """Only digits and one decimal point may be typed."""
        return value == "" or (value.isascii() and value.replace(".", "", 1).isdigit())

    @staticmethod
    def _validate_card_input(value):
        """Only digits, spaces and dashes may be typed, and no more than MAX_DIGITS digits."""
        if not all((ch.isascii() and ch.isdigit()) or ch in " -" for ch in value):
            return False
        return len(clean_card_number(value)) <= MAX_DIGITS and len(value) <= MAX_DIGITS + 6

    def _build_action_buttons(self):
        """Clear / Hold / Confirm: centred under the order panel."""
        bar = tk.Frame(self._frame, bg=Theme.BG)
        bar.place(x=650 + 315, y=630, anchor="n")
        self._clear_btn = styled_button(bar, "Clear Order", self._clear_order, False, height=44, px=130, danger=True)
        self._hold_btn = styled_button(bar, "Hold Order", self._hold_order, False, height=44, px=150)
        self._confirm_btn = styled_button(bar, "Confirm Order", self._confirm_order, True, height=44, px=210)
        self._confirm_btn.configure(font=ctk.CTkFont("Helvetica", 14, "bold"))
        for button in (self._clear_btn, self._hold_btn, self._confirm_btn):
            button.pack(side=tk.LEFT, padx=5)

    # ==================================================================
    # Products: search, categories, cards
    # ==================================================================
    def load_products(self, term=None):
        """Rebuild the product cards (term=None keeps the current search text)."""
        if term is not None:
            self._search_term = term
        try:
            products = self._context.products.search_available(self._search_term, self._category)
        except DatabaseError as error:
            show_db_error(error)
            return

        for child in self._product_grid.winfo_children():
            child.destroy()
        self._card_actions = []
        visible = 0
        for product in products:
            available = product.stock - self._cart.quantity_of(product.product_id)
            if available > 0:
                self._create_product_card(product, available, visible)
                visible += 1

        for column in range(self.CARDS_PER_ROW):
            self._product_grid.grid_columnconfigure(column, weight=1)
        if visible == 0:
            tk.Label(self._product_grid, text="No available products found.", bg=Theme.BG,
                     fg=Theme.MUTED, font=("Helvetica", 10)).grid(
                         row=0, column=0, columnspan=self.CARDS_PER_ROW, pady=25)
        self._update_product_scroll()

    def _create_product_card(self, product, available, position):
        """ID + stock on the top row, name, price, then quantity box + Add button."""
        card = tk.Frame(self._product_grid, bg=Theme.CARD, highlightbackground=Theme.BORDER,
                        highlightthickness=1, width=185, height=165)
        card.grid(row=position // self.CARDS_PER_ROW, column=position % self.CARDS_PER_ROW,
                  padx=5, pady=5, sticky="nsew")
        card.grid_propagate(False)

        id_label = tk.Label(card, text=f"ID: {product.product_id}", bg=Theme.CARD,
                            fg=Theme.MUTED, font=("Helvetica", 8))
        id_label.place(x=10, y=8)
        low = available <= Settings.LOW_STOCK_LEVEL
        stock_label = tk.Label(card, text=f"{available} in stock", bg=Theme.CARD,
                               fg=Theme.ORANGE if low else Theme.MUTED, font=("Helvetica", 8))
        stock_label.place(relx=1.0, x=-10, y=8, anchor="ne")
        name_label = tk.Label(card, text=str(product.name), bg=Theme.CARD, fg=Theme.TEXT,
                              font=("Helvetica", 10, "bold"), anchor="nw", justify=tk.LEFT,
                              wraplength=160)
        name_label.place(x=10, y=30, width=165, height=38)
        price_label = tk.Label(card, text=peso(product.price), bg=Theme.CARD, fg=Theme.NAVY,
                               font=("Helvetica", 13, "bold"))
        price_label.place(x=10, y=74)

        quantity_entry = ctk.CTkEntry(
            card, width=48, height=32, corner_radius=8, border_width=1,
            border_color=Theme.ENTRY_BORDER, fg_color="white", text_color=Theme.TEXT,
            justify="center", font=ctk.CTkFont("Helvetica", 13))
        quantity_entry.insert(0, "1")
        quantity_entry.place(x=10, y=122)
        quantity_entry._entry.configure(
            validate="key",
            validatecommand=(card.register(lambda v: v.isascii() and (v == "" or v.isdigit()) and len(v) <= 4), "%P"))

        add_now = lambda: self._add_to_cart(product, quantity_entry)
        ctk.CTkButton(card, text="Add to Order", width=108, height=32, corner_radius=8,
                      fg_color=Theme.NAVY, hover_color=Theme.ACTIVE, text_color="white",
                      font=ctk.CTkFont("Helvetica", 12, "bold"), cursor="hand2",
                      command=add_now).place(x=64, y=122)

        # the whole card is clickable too: one click = Add to Order (uses the quantity box)
        self._card_actions.append(add_now)
        for clickable in (card, id_label, stock_label, name_label, price_label):
            clickable.bind("<Button-1>", lambda event, run=add_now: run())
            clickable.configure(cursor="hand2")

    def _add_to_cart(self, product, quantity_entry):
        try:
            quantity = int(quantity_entry.get().strip())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Quantity", "Enter a whole number greater than zero.")
            return
        available = product.stock - self._cart.quantity_of(product.product_id)
        if quantity > available:
            messagebox.showwarning("Not Enough Stock", f"Only {available} more unit(s) are available.")
            return

        self._cart.add(product, quantity)
        quantity_entry.delete(0, tk.END)
        quantity_entry.insert(0, "1")
        self.refresh_cart(reload_products=False)
        # Rebuild the cards a moment later, so the button that was just clicked
        # is not destroyed while it is still handling its own click.
        self._window.after(150, self._reload_products_later)

    def _reload_products_later(self):
        if self._frame is not None and self._frame.winfo_exists():
            self.load_products()

    # ---- category chips ---------------------------------------------------------------
    def _build_chips(self):
        for widget in self._chip_bar.winfo_children():
            widget.destroy()
        self._chip_buttons.clear()
        names = ["All"]
        try:
            names += self._context.products.categories()
        except DatabaseError:
            pass                                   # chips are optional; keep "All"
        for name in names:
            chip = ctk.CTkButton(
                self._chip_bar, text=name, width=len(name) * 8 + 32, height=28, corner_radius=14,
                font=ctk.CTkFont("Helvetica", 12, "bold"), cursor="hand2",
                command=lambda n=name: self._set_category(n))
            chip.pack(side=tk.LEFT, padx=(0, 8))
            self._chip_buttons[name] = chip
        self._style_chips()

    def _style_chips(self):
        for name, chip in self._chip_buttons.items():
            active = name == self._category
            chip.configure(fg_color=Theme.NAVY if active else Theme.LIGHT_BTN,
                           hover_color=Theme.ACTIVE if active else Theme.LIGHT_ACTIVE,
                           text_color="white" if active else Theme.TEXT)

    def _set_category(self, name):
        self._category = name
        self._style_chips()
        self.load_products()

    # ---- search -------------------------------------------------------------------------
    def _search_products(self):
        self.load_products(self._search_entry.get().strip())

    def _show_all_products(self):
        self._search_entry.delete(0, tk.END)
        self._category = "All"
        self._style_chips()
        self.load_products("")

    def _on_search_enter(self, event=None):
        """Enter runs the search; if exactly one product matches it is added right away."""
        term = self._search_entry.get().strip()
        self.load_products(term)
        if term and len(self._card_actions) == 1:
            self._card_actions[0]()
            self._search_entry.delete(0, tk.END)
            self.load_products("")
            self._search_entry.focus_set()

    # ==================================================================
    # Cart
    # ==================================================================
    def refresh_cart(self, reload_products=True):
        """Refresh table, totals, change, buttons and (optionally) the product cards."""
        self._cart_tree.delete(*self._cart_tree.get_children())
        for index, item in enumerate(self._cart):
            self._cart_tree.insert("", tk.END, iid=str(index), values=(
                item.name, item.quantity, peso(item.unit_price), peso(item.line_total)))

        figures = self._cart.breakdown()
        self._subtotal_var.set(peso(figures.subtotal))
        self._vat_var.set(peso(figures.vat))
        self._total_var.set(peso(figures.total))

        if not self._payment.requires_tender:
            self._tender_var.set(self._payment.default_tender(figures.total))
        self._refresh_change()

        count = self._cart.item_count
        if count:
            self._cart_title.configure(text=f"Current Order ({count} item{'s' if count != 1 else ''})")
            self._empty_label.place_forget()
        else:
            self._cart_title.configure(text="Current Order")
            self._empty_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self._sync_payment_ui()
        self._update_hold_count()
        if reload_products:
            self.load_products()

    def _selected_cart_index(self):
        selection = self._cart_tree.selection()
        return int(selection[0]) if selection else None

    def _remove_item(self):
        index = self._selected_cart_index()
        if index is None:
            messagebox.showwarning("Selection Required", "Select a cart item to remove.")
            return
        self._cart.remove(index)                  # overload: remove(int)
        self.refresh_cart()

    def _adjust_quantity(self, delta):
        index = self._selected_cart_index()
        if index is None:
            messagebox.showwarning("Selection Required", "Select a cart item first.")
            return
        item = self._cart[index]
        if delta > 0:
            try:
                stock = self._context.products.stock_of(item.product_id)
            except DatabaseError as error:
                show_db_error(error)
                self.refresh_cart()
                return
            if item.quantity >= stock:
                messagebox.showwarning("Not Enough Stock",
                                       f"Only {stock} unit(s) are currently in stock.")
                return
        self._cart.change_quantity(index, delta)
        self.refresh_cart()

    # ==================================================================
    # Payment
    # ==================================================================
    def _choose_method(self, name):
        if self._payment.name == name:
            return
        self._payment = PaymentFactory.create(name)
        if name != CARD_METHOD:
            self._card_var.set("")                # leaving Card: forget the typed number
        self._apply_method_to_entry()
        self._sync_payment_ui()
        if name == CARD_METHOD:
            self._card_entry.focus_set()          # ready to type the card number

    def _apply_method_to_entry(self):
        """Cash: editable box. Card: box is locked and shows the exact total."""
        if self._payment.requires_tender:
            self._tender_entry.configure(state=tk.NORMAL)
        self._tender_var.set(self._payment.default_tender(self._cart.total))
        if not self._payment.requires_tender:
            self._tender_entry.configure(state=tk.DISABLED)
        self._refresh_change()

    def _on_tender_changed(self, *args):
        self._refresh_change()
        self._sync_payment_ui()

    def _refresh_change(self):
        try:
            change = max(0.0, float(self._tender_var.get() or 0) - self._cart.total)
        except ValueError:
            change = 0.0
        self._change_var.set(peso(change))

    def _sync_payment_ui(self):
        """Highlight the method, show/hide cash and card rows, colour Change, enable Confirm."""
        for name, button in self._method_buttons.items():
            active = name == self._payment.name
            button.configure(fg_color=Theme.NAVY if active else Theme.LIGHT_BTN,
                             hover_color=Theme.ACTIVE if active else Theme.LIGHT_ACTIVE,
                             text_color="white" if active else Theme.TEXT)
        for widget in self._cash_only_widgets:        # polymorphic: depends on the method
            widget.grid() if self._payment.requires_tender else widget.grid_remove()

        is_card = self._payment.name == CARD_METHOD   # card number row: Card only
        for widget in self._card_only_widgets:
            widget.grid() if is_card else widget.grid_remove()

        ready = not self._cart.is_empty
        change_color = Theme.GREEN
        if ready:
            result = self._payment.evaluate(self._cart.total, self._tender_var.get())
            if not result.is_valid:
                ready = False
                if result.short_by > 0:
                    self._change_var.set(f"Short {peso(result.short_by)}")
                    change_color = Theme.DANGER
        self._change_value.configure(fg=change_color)
        self._confirm_btn.configure(state=tk.NORMAL if ready else tk.DISABLED,
                                    fg_color=Theme.NAVY if ready else Theme.DISABLED_BG)

    def _update_hold_count(self):
        try:
            pending = self._context.orders.count_pending()
        except DatabaseError:
            return
        self._hold_btn.configure(text=f"Hold Order ({pending})" if pending else "Hold Order")

    # ==================================================================
    # Order actions
    # ==================================================================
    def _reset_order(self):
        self._cart.clear()
        self._resumed_order_id = None
        self._payment = PaymentFactory.create("Cash")
        self._tender_entry.configure(state=tk.NORMAL)
        self._tender_var.set("")
        self._card_var.set("")
        self._recipient_picker.clear()
        self._ship_var.set(True)
        self._sync_shipping_ui()
        self.refresh_cart()

    def _clear_order(self):
        if not self._cart.is_empty and not messagebox.askyesno(
                "Clear Order", "Remove all items from this order?"):
            return
        self._reset_order()

    def _hold_order(self):
        if self._cart.is_empty:
            messagebox.showwarning("Empty Order", "Add at least one product first.")
            return
        recipient = self._recipient_picker.selected()
        try:
            order_id = self._context.checkout.hold(
                self._cart, self._resumed_order_id,
                recipient.recipient_id if recipient else None, self._ship_var.get())
        except DatabaseError as error:
            show_db_error(error)
            return
        messagebox.showinfo("Order Saved",
                            f"Order {order_id} was saved as pending.\nStock has not been deducted.")
        self._reset_order()

    def _confirm_order(self):
        if self._cart.is_empty:
            messagebox.showwarning("Empty Order", "Add at least one product first.")
            return
        ship_to = None
        if self._ship_var.get():
            recipient = self._recipient_picker.selected()
            if recipient is None:
                messagebox.showwarning(
                    "Recipient Required",
                    "Select a recipient for this shipment, or untick \"Ship this order\".")
                return
            ship_to = ShipTo(recipient.recipient_id, recipient.name, recipient.address)
        result = self._payment.evaluate(self._cart.total, self._tender_var.get())
        if not result.is_valid:
            messagebox.showwarning("Payment Error", result.error)
            return

        # Card payments need a valid card number; only the last 4 digits are kept
        card_last4 = None
        if self._payment.name == CARD_METHOD:
            problem = card_number_problem(self._card_var.get())
            if problem:
                messagebox.showwarning("Card Number", problem)
                self._card_entry.focus_set()
                return
            card_last4 = last_four(self._card_var.get())

        try:
            order = self._context.checkout.confirm(
                self._cart, self._payment, result,
                ship_to=ship_to, resumed_order_id=self._resumed_order_id)
        except InsufficientStockError as error:
            messagebox.showwarning("Stock Validation", str(error))
            self.load_products()
            return
        except DatabaseError as error:
            show_db_error(error)
            return

        message = f"Order {order.order_id} confirmed.\nTotal: {peso(order.total)}"
        if self._payment.name == "Cash":
            message += f"\nChange: {peso(result.change)}"
        if card_last4:
            message += f"\nCard ending in {card_last4}"
        if ship_to is not None:
            message += "\nShipment record created (Pending)."
        messagebox.showinfo("Order Confirmed", message)
        if messagebox.askyesno("Receipt", "Would you like to print the receipt?"):
            self._context.receipts.print_receipt(order)
        self._reset_order()