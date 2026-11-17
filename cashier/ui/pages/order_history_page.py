"""Order History page: search, view details, resume pending orders, reprint receipts."""
import tkinter as tk
from tkinter import messagebox, ttk

from cashier.config import Settings, Theme
from cashier.database.connection import DatabaseError
from cashier.models import CartItem
from cashier.ui.base_page import BasePage
from cashier.ui.widgets import make_tree, show_db_error, styled_button
from cashier.utils import peso


class OrderDetailsDialog(tk.Toplevel):
    """Pop-up window with the lines and totals of one order (inherits Toplevel)."""

    def __init__(self, parent, order, printer):
        super().__init__(parent)
        self._order = order
        self._printer = printer
        self.title(f"Order {order.order_id}")
        if order.payment_method == "Card":
            self.geometry("570x480")
        elif order.payment_method == "Cash":
            self.geometry("570x530")
        else:
            self.geometry("570x510")
        self.resizable(False, False)
        self.config(bg=Theme.BG)
        self.transient(parent)
        self.grab_set()
        self._build()
        self._build()
        self.center_window()


    def center_window(self):
        self.update_idletasks()

        width = self.winfo_width()
        height = self.winfo_height()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")

    
    def _build(self):
        order = self._order
        tk.Label(self, text=f"Order {order.order_id}", font=("Helvetica", 15, "bold"),
                 bg=Theme.BG, fg=Theme.NAVY).pack(pady=(15, 2))
        tk.Label(self, text=f"{order.order_date.strftime('%B %d, %Y %I:%M %p')}  |  {order.status}",
                 font=("Helvetica", 10), bg=Theme.BG, fg=Theme.MUTED).pack()
        wrap, item_tree = make_tree(
            self, ("name", "qty", "price", "line"),
            ("Product", "Qty", "Unit Price", "Total"), (230, 55, 110, 110), height=9)
        wrap.pack(fill=tk.X, padx=15, pady=15)
        for line in order.lines:
            item_tree.insert("", tk.END, values=(line.product_name, line.quantity,
                                                 peso(line.unit_price), peso(line.line_total)))
        summary = tk.Frame(self, bg=Theme.BG)
        summary.pack(fill=tk.X, padx=25)
        for index, (label, value) in enumerate(self._summary_rows()):
            tk.Label(summary, text=label, bg=Theme.BG, font=("Helvetica", 10)).grid(
                row=index, column=0, sticky=tk.W, pady=2)
            tk.Label(summary, text=value, bg=Theme.BG, font=("Helvetica", 10, "bold")).grid(
                row=index, column=1, sticky=tk.E, pady=2)
        summary.columnconfigure(1, weight=1)
        styled_button(self, "Print Receipt", lambda: self._printer.print_receipt(order),
                      True, 16).pack(pady=15)

    def _summary_rows(self):
        order = self._order
        rows = [("Subtotal", peso(order.subtotal)),
                (f"VAT ({int(Settings.VAT_RATE * 100)}%)", peso(order.vat)),
                ("Total", peso(order.total))]
        if not order.is_pending:
            rows.append(("Payment", order.payment_method or ""))
            if order.payment_method == "Cash":
                rows.extend([("Received", peso(order.amount_paid)),
                             ("Change", peso(order.change_amount))])
        return rows


class OrderHistoryPage(BasePage):
    HEADING = "Order History"

    def _build(self):
        self._build_search_bar()
        self._build_table()
        self._build_actions()
        self.load_orders()

    # ---- layout ---------------------------------------------------------------
    def _build_search_bar(self):
        bar = tk.Frame(self._frame, bg=Theme.BG)
        bar.pack(pady=(20, 12))
        tk.Label(bar, text="Search order ID or product:", bg=Theme.BG,
                 font=("Helvetica", 10)).pack(side=tk.LEFT, padx=5)
        self._search_entry = tk.Entry(bar, font=("Helvetica", 11), width=24,
                                      bg="white", relief=tk.SOLID, bd=1)
        self._search_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(bar, text="Status:", bg=Theme.BG, font=("Helvetica", 10)).pack(
            side=tk.LEFT, padx=(12, 5))
        self._status_box = ttk.Combobox(bar, state="readonly", width=12,
                                        values=("All", "Pending", "Completed"))
        self._status_box.set("All")
        self._status_box.pack(side=tk.LEFT, padx=5)
        styled_button(bar, "Search", self.load_orders, True, 9).pack(side=tk.LEFT, padx=4)
        styled_button(bar, "Show All", self._show_all, False, 9).pack(side=tk.LEFT, padx=4)
        self._search_entry.bind("<Return>", self.load_orders)
        self._status_box.bind("<<ComboboxSelected>>", self.load_orders)

    def _build_table(self):
        wrap, self._tree = make_tree(
            self._frame, ("id", "date", "items", "total", "method", "status"),
            ("Order ID", "Date", "Items", "Total", "Payment", "Status"),
            (150, 190, 80, 130, 120, 110), height=16)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self._tree.tag_configure("Pending", foreground=Theme.ORANGE)

    def _build_actions(self):
        actions = tk.Frame(self._frame, bg=Theme.BG)
        actions.pack(pady=12)
        styled_button(actions, "View Details", self._view_details, True, 15).pack(side=tk.LEFT, padx=5)
        styled_button(actions, "Resume Pending Order", self._resume_order, False, 22).pack(side=tk.LEFT, padx=5)
        styled_button(actions, "Print Receipt", self._print_selected, False, 15).pack(side=tk.LEFT, padx=5)

    # ---- data -------------------------------------------------------------------
    def load_orders(self, event=None):
        try:
            rows = self._context.orders.search(self._search_entry.get().strip(),
                                               self._status_box.get())
        except DatabaseError as error:
            show_db_error(error)
            return
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            self._tree.insert("", tk.END, iid=row.order_id, values=(
                row.order_id, row.order_date.strftime("%b %d, %Y %I:%M %p"),
                row.item_count, peso(row.total), row.payment_method, row.status),
                tags=(row.status,))

    def _show_all(self):
        self._search_entry.delete(0, tk.END)
        self._status_box.set("All")
        self.load_orders()

    def _selected_order_id(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Select an order first.")
            return None
        return selected[0]

    def _fetch_selected_order(self):
        """Load the full Order of the selected row (None if nothing/failed)."""
        order_id = self._selected_order_id()
        if not order_id:
            return None
        try:
            return self._context.orders.get(order_id)
        except DatabaseError as error:
            show_db_error(error)
            return None

    # ---- actions --------------------------------------------------------------------
    def _view_details(self):
        order = self._fetch_selected_order()
        if order:
            OrderDetailsDialog(self._window, order, self._context.receipts)

    def _print_selected(self):
        order = self._fetch_selected_order()
        if order:
            self._context.receipts.print_receipt(order)

    def _resume_order(self):
        order = self._fetch_selected_order()
        if not order:
            return
        if not order.is_pending:
            messagebox.showinfo("Order Completed", "Only pending orders can be resumed.")
            return
        items = [CartItem.from_order_line(line) for line in order.lines]
        self._context.pending_order.store(order.order_id, items)
        self._navigate("Order Entry")
