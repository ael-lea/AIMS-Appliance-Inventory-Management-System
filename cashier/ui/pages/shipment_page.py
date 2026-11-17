"""Shipment Management page (cashier view, matches the Admin shipment page)."""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from cashier.config import Theme
from cashier.database.connection import DatabaseError
from cashier.database.shipment_repository import ShipmentError, ShipmentRepository
from cashier.ui.base_page import BasePage
# OLD (only needed for Add Shipment / recipient picker) - uncomment to restore:
# from cashier.ui.recipient_picker import RecipientPicker
from cashier.ui.widgets import make_tree, show_db_error, styled_button
from cashier.utils import format_date
# OLD (only needed for Add Shipment) - uncomment to restore:
# from cashier.tracking import generate_tracking_number


class ShipmentPage(BasePage):
    HEADING = "Shipment Management"

    def __init__(self, window, navigate, context):
        super().__init__(window, navigate, context)
        self._selected_id = None

    def _build(self):
        self._build_search_bar()
        self._build_table()
        # self._build_details_panel()
        self.load_shipments()

    # ---- layout ----------------------------------------------------------------
    def _build_search_bar(self):
        bar = tk.Frame(self._frame, bg=Theme.BG)
        bar.place(x=35, y=70, width=1235, height=42)
        self._search_by = ttk.Combobox(
            bar, state="readonly", width=19, font=("Helvetica", 10),
            values=tuple(ShipmentRepository.SEARCH_COLUMNS))
        self._search_by.set("Order ID")
        self._search_by.pack(side=tk.LEFT, padx=(0, 10))
        self._search_entry = ctk.CTkEntry(
            bar, width=390, height=36, corner_radius=9, border_width=1,
            border_color=Theme.ENTRY_BORDER, fg_color="white", text_color=Theme.TEXT,
            placeholder_text="Enter search value", font=ctk.CTkFont("Helvetica", 12))
        self._search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self._search_entry.bind("<Return>", self._search)
        styled_button(bar, "Search", self._search, True, px=105).pack(side=tk.LEFT, padx=(0, 8))
        styled_button(bar, "Show All", self._show_all, False, px=105).pack(side=tk.LEFT)


        # self._search_by = ctk.CTkComboBox(
        #     bar, values=list(ShipmentRepository.SEARCH_COLUMNS), state="readonly",
        #     width=160, height=36, corner_radius=9, border_width=1,
        #     border_color=Theme.ENTRY_BORDER, fg_color="white", text_color=Theme.TEXT,
        #     button_color=Theme.NAVY, button_hover_color=Theme.ACTIVE,
        #     dropdown_fg_color="white", dropdown_text_color=Theme.TEXT,
        #     font=ctk.CTkFont("Helvetica", 12))
        # self._search_by.set("Order ID")
        # self._search_by.pack(side=tk.LEFT, padx=(0, 10))

    def _build_table(self):
        # OLD (smaller table, height=12):
        # wrap, self._tree = make_tree(
        #     self._frame,
        #     ("order_id", "customer", "order_date", "status", "tracking", "delivery_date"),
        #     ("Order ID", "Customer Name", "Order Date", "Status", "Tracking Number", "Delivery Date"),
        #     (145, 210, 135, 175, 220, 135), height=12)
        # wrap.place(x=35, y=125, width=1235, height=310)

        # NEW (bigger table, height=17):
        wrap, self._tree = make_tree(
            self._frame,
            ("order_id", "customer", "order_date", "status", "tracking", "delivery_date"),
            ("Order ID", "Customer Name", "Order Date", "Status", "Tracking Number", "Delivery Date"),
            (145, 210, 135, 175, 220, 135), height=17)
        wrap.place(x=35, y=125, width=1235, height=550)

        self._tree.column("customer", anchor=tk.W)
        self._tree.column("tracking", anchor=tk.W)
        self._tree.tag_configure("Pending", foreground=Theme.ORANGE)
        self._tree.tag_configure("Being Processed", foreground=Theme.ACTIVE)
        self._tree.tag_configure("Delivered", foreground=Theme.GREEN)
        # self._tree.bind("<<TreeviewSelect>>", self._on_select)

    # OLD details panel (two rows, recipient picker, Add Shipment, Refresh) - kept for restoring:
    # def _build_details_panel(self):
    #     details = ctk.CTkFrame(self._frame, fg_color=Theme.CARD, corner_radius=12,
    #                            border_width=1, border_color=Theme.BORDER,
    #                            width=1235, height=205)
    #     details.place(x=35, y=455)
    #     details.pack_propagate(False)
    #     tk.Label(details, text="Shipment Details", bg=Theme.CARD, fg=Theme.NAVY,
    #              font=("Helvetica", 15, "bold")).place(x=20, y=12)
    #
    #     tk.Label(details, text="Recipient", bg=Theme.CARD, fg=Theme.TEXT,
    #              font=("Helvetica", 10)).place(x=22, y=58)
    #     self._recipient_picker = RecipientPicker(details, self._context.recipients,
    #                                              bg=Theme.CARD, width=550)
    #     self._recipient_picker.place(x=22, y=82, width=550)
    #     self._tracking_entry = self._labelled_entry(details, "Tracking Number",
    #                                                 "Optional tracking number", 600)
    #     tk.Label(details, text="Shipping Status", bg=Theme.CARD, fg=Theme.TEXT,
    #              font=("Helvetica", 10)).place(x=600, y=126)
    #     self._status_box = ttk.Combobox(details, state="readonly", width=22,
    #                                     values=ShipmentRepository.STATUSES,
    #                                     font=("Helvetica", 10))
    #     self._status_box.set("Pending")
    #     self._status_box.place(x=600, y=150, height=32)
    #
    #     styled_button(details, "Add Shipment", self._add_shipment, True, px=135).place(x=900, y=82)
    #     styled_button(details, "Update Status", self._update_status, False, px=135).place(x=900, y=128)
    #     styled_button(details, "Clear Fields", self._clear_fields, False, px=135).place(x=1050, y=82)
    #     styled_button(details, "Refresh", self.load_shipments, False, px=135).place(x=1050, y=128)

    # NEW details panel (one row: Tracking Number | Shipping Status | buttons)
    def _build_details_panel(self):
        details = ctk.CTkFrame(self._frame, fg_color=Theme.CARD, corner_radius=12,
                               border_width=1, border_color=Theme.BORDER,
                               width=1235, height=110)
        details.place(x=35, y=550)
        details.pack_propagate(False)
        tk.Label(details, text="Shipment Details", bg=Theme.CARD, fg=Theme.NAVY,
                 font=("Helvetica", 13, "bold")).place(x=20, y=6)

        # Recipient section disabled (see OLD panel above to restore it):
        # self._recipient_picker = RecipientPicker(details, self._context.recipients,
        #                                          bg=Theme.CARD, width=550)

        self._tracking_entry = self._labelled_entry(details, "Tracking Number",
                                                    "Optional tracking number", 22)
        tk.Label(details, text="Shipping Status", bg=Theme.CARD, fg=Theme.TEXT,
                 font=("Helvetica", 10)).place(x=310, y=36)
        self._status_box = ttk.Combobox(details, state="readonly", width=22,
                                        values=ShipmentRepository.STATUSES,
                                        font=("Helvetica", 10))
        self._status_box.set("Pending")
        self._status_box.place(x=310, y=60, height=32)



# CURVE NA COMBO BOX 
        # self._status_box = ctk.CTkComboBox(
        #     details, values=list(ShipmentRepository.STATUSES), state="readonly",
        #     width=190, height=32, corner_radius=8, border_width=1, cursor = "hand2",
        #     border_color=Theme.ENTRY_BORDER, fg_color="white", text_color=Theme.TEXT,
        #     button_color=Theme.NAVY, button_hover_color=Theme.ACTIVE,
        #     dropdown_fg_color="white", dropdown_text_color=Theme.TEXT,
        #     dropdown_hover_color=Theme.BG, font=ctk.CTkFont("Helvetica", 12),
        #     dropdown_font=ctk.CTkFont("Helvetica", 12))
        # self._status_box.set("Pending")
        # self._status_box.place(x=310, y=60)

        styled_button(details, "Update Status", self._update_status, True, px=135).place(x=520, y=60)
        styled_button(details, "Clear Fields", self._clear_fields, False, px=135).place(x=670, y=60)

        # Buttons disabled for now (uncomment to bring them back; adjust x/y as needed):
        # styled_button(details, "Add Shipment", self._add_shipment, True, px=135).place(x=820, y=60)
        # styled_button(details, "Refresh", self.load_shipments, False, px=135).place(x=970, y=60)

    # OLD helper (taller layout) - kept for restoring:
    # @staticmethod
    # def _labelled_entry(parent, label, placeholder, x):
    #     """A small caption with a rounded entry underneath (reusable)."""
    #     tk.Label(parent, text=label, bg=Theme.CARD, fg=Theme.TEXT,
    #              font=("Helvetica", 10)).place(x=x, y=58)
    #     entry = ctk.CTkEntry(parent, width=260, height=36, corner_radius=8, border_width=1,
    #                          border_color=Theme.ENTRY_BORDER, fg_color="white",
    #                          text_color=Theme.TEXT, placeholder_text=placeholder)
    #     entry.place(x=x, y=82)
    #     return entry

    # NEW helper (fits the shorter one-row panel)
    @staticmethod
    def _labelled_entry(parent, label, placeholder, x):
        """A small caption with a rounded entry underneath (reusable)."""
        tk.Label(parent, text=label, bg=Theme.CARD, fg=Theme.TEXT,
                 font=("Helvetica", 10)).place(x=x, y=36)
        entry = ctk.CTkEntry(parent, width=260, height=32, corner_radius=8, border_width=1,
                             border_color=Theme.ENTRY_BORDER, fg_color="white",
                             text_color=Theme.TEXT, placeholder_text=placeholder)
        entry.place(x=x, y=60)
        return entry

    # ---- data ---------------------------------------------------------------------
    def load_shipments(self, term="", option="Order ID"):
        try:
            records = self._context.shipments.search(term, option)
        except DatabaseError as error:
            messagebox.showerror("Database Error", f"Unable to load shipments.\n\n{error}")
            return
        self._tree.delete(*self._tree.get_children())
        for r in records:
            self._tree.insert("", tk.END, values=(
                r.order_id, r.customer_name, format_date(r.order_date), r.status,
                r.tracking_number, format_date(r.delivery_date)), tags=(r.status,))

    def _search(self, event=None):
        self.load_shipments(self._search_entry.get().strip(), self._search_by.get())

    def _show_all(self):
        self._search_entry.delete(0, tk.END)
        self._search_by.set("Order ID")
        self.load_shipments()

    # ---- form handling -----------------------------------------------------------------
    def _clear_fields(self):
        self._selected_id = None
        # OLD (needs the recipient picker):
        # self._recipient_picker.clear()
        self._tracking_entry.delete(0, tk.END)
        self._status_box.set("Pending")
        self._tree.selection_remove(self._tree.selection())

    def _on_select(self, event=None):
        selection = self._tree.selection()
        if not selection:
            return
        values = self._tree.item(selection[0], "values")
        self._selected_id = values[0]
        self._tracking_entry.delete(0, tk.END)
        self._tracking_entry.insert(0, values[4])
        self._status_box.set(values[3])

    # OLD Add Shipment (needs the recipient picker + Add Shipment button) - kept for restoring:
    # def _add_shipment(self):
    #     recipient = self._recipient_picker.selected()
    #     if recipient is None:
    #         messagebox.showwarning("Required Field", "Please select a recipient.")
    #         return
    #     tracking = self._tracking_entry.get().strip() or generate_tracking_number()
    #     try:
    #         order_id = self._context.shipments.add(
    #             recipient.recipient_id, recipient.name, recipient.address, tracking)
    #     except (DatabaseError, ShipmentError) as error:
    #         messagebox.showerror("Database Error", f"Unable to add shipment.\n\n{error}")
    #         return
    #     self.load_shipments()
    #     self._clear_fields()
    #     messagebox.showinfo("Shipment Added",
    #                         f"Shipment record created successfully.\n"
    #                         f"Order ID: {order_id}\nTracking Number: {tracking}")

    # OLD Update Status (saved only the status, ignored the tracking box, didn't catch ShipmentError):
    # def _update_status(self):
    #     if not self._selected_id:
    #         messagebox.showwarning("Selection Required",
    #                                "Select a shipment record from the table first.")
    #         return
    #     new_status = self._status_box.get()
    #     if new_status not in ShipmentRepository.STATUSES:
    #         messagebox.showwarning("Invalid Status", "Choose a valid shipping status.")
    #         return
    #     try:
    #         self._context.shipments.update_status(self._selected_id, new_status)
    #     except DatabaseError as error:
    #         messagebox.showerror("Database Error", f"Unable to update shipment.\n\n{error}")
    #         return
    #     self.load_shipments(self._search_entry.get().strip(), self._search_by.get())
    #     messagebox.showinfo("Status Updated",
    #                         f"Shipment {self._selected_id} is now marked as {new_status}.")

    # NEW Update Status: saves status AND tracking number, shows rule errors nicely
    def _update_status(self):
        if not self._selected_id:
            messagebox.showwarning("Selection Required",
                                   "Select a shipment record from the table first.")
            return
        new_status = self._status_box.get()
        if new_status not in ShipmentRepository.STATUSES:
            messagebox.showwarning("Invalid Status", "Choose a valid shipping status.")
            return
        tracking = self._tracking_entry.get().strip()
        try:
            self._context.shipments.update(self._selected_id, new_status, tracking=tracking)
        except ShipmentError as error:
            messagebox.showwarning("Not Allowed", str(error))
            return
        except DatabaseError as error:
            messagebox.showerror("Database Error", f"Unable to update shipment.\n\n{error}")
            return
        self.load_shipments(self._search_entry.get().strip(), self._search_by.get())
        messagebox.showinfo("Shipment Updated",
                            f"Shipment {self._selected_id} saved.\n"
                            f"Status: {new_status}\nTracking Number: {tracking or '(none)'}")