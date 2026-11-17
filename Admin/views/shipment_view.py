"""
Shipment Management View.
Demonstrates:
- Inheritance (ShipmentView inherits from BaseFormView)
- Encapsulation (Encapsulates ShipmentRepository and RecipientRepository)
- Polymorphism (Overrides build_ui, refresh_data, clear_fields)
- Functional Features: Add, Edit, Delete, Search, Display
- Status cards and auto-updating shipment metrics
"""
from tkinter import *
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import date, datetime
from typing import Dict, Any, Optional
from .base_view import BaseFormView
from .widgets import round_button, NAVY, ACTIVE, BG, LIGHT, MUTED
from .recipient_view import RecipientView
from ..models.shipment import Shipment
from ..repositories.shipment_repo import ShipmentRepository
from ..repositories.recipient_repo import RecipientRepository
from ..core.exceptions import (
    ValidationError,
    EmptyFieldException,
    RecordNotFoundException
)

class ShipmentView(BaseFormView):
    """
    Form view managing order dispatches, delivery statuses, tracking numbers, and fulfillment counters.
    """

    def __init__(self, parent_window: Tk):
        self._shipment_repo = ShipmentRepository()
        self._recipient_repo = RecipientRepository()
        self._recipient_lookup: Dict[str, Any] = {}
        super().__init__(parent_window, title="Shipment Details")

    def build_ui(self) -> None:
        """Constructs Shipment form components."""

        # Search Frame
        search_frame = Frame(self, bg=BG)
        search_frame.pack(pady=(75, 10)) 

        self._search_combobox = ttk.Combobox(
            search_frame,
            values=("Order ID", "Recipient", "Status", "Tracking"),
            state="readonly",
            width=15
        )
        self._search_combobox.set("Order ID")
        self._search_combobox.pack(side=LEFT, padx=5)

        self._search_entry = Entry(search_frame, font=("Helvetica", 11), width=20)
        self._search_entry.pack(side=LEFT, padx=5)

        round_button(search_frame, "Search", self.search_records, width=95).pack(side=LEFT, padx=5)
        round_button(search_frame, "Show All", self.refresh_data, width=95, secondary=True).pack(side=LEFT, padx=5)

        # Treeview / Table
        table_frame = Frame(self, bg=BG)
        table_frame.pack(fill=X, padx=40, pady=5)

        y_scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL)
        x_scrollbar = ttk.Scrollbar(table_frame, orient=HORIZONTAL)

        self._treeview = ttk.Treeview(
            table_frame,
            columns=("order_id", "recipient_id", "recipient_name", "order_date", "status", "tracking_number", "delivery_date"),
            show="headings",
            height=7,
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )

        y_scrollbar.config(command=self._treeview.yview)
        x_scrollbar.config(command=self._treeview.xview)
        y_scrollbar.pack(side=RIGHT, fill=Y)
        x_scrollbar.pack(side=BOTTOM, fill=X)
        self._treeview.pack(fill=BOTH, expand=True)

        headings = {
            "order_id": ("Order ID", 110),
            "recipient_id": ("Recipient ID", 90),
            "recipient_name": ("Recipient Name", 180),
            "order_date": ("Order Date", 110),
            "status": ("Status", 130),
            "tracking_number": ("Tracking Number", 160),
            "delivery_date": ("Delivery Date", 110)
        }
        for col_id, (col_text, col_width) in headings.items():
            self._treeview.heading(col_id, text=col_text)
            self._treeview.column(col_id, width=col_width, anchor=CENTER)

        self._treeview.bind("<ButtonRelease-1>", self.on_select_row)

        # Status counters (below the table)
        stats_frame = Frame(self, bg=BG)
        stats_frame.pack(fill=X, padx=40, pady=(10, 0))    

        self._pending_lbl = Label(stats_frame, text="Pending: 0", font=("Helvetica", 11, "bold"), fg="#b9770e", bg="#FCF3CF", padx=10, pady=5)
        self._pending_lbl.pack(side=LEFT, padx=5)

        self._processing_lbl = Label(stats_frame, text="Being Processed: 0", font=("Helvetica", 11, "bold"), fg="#053e87", bg="#D4E6F1", padx=10, pady=5)
        self._processing_lbl.pack(side=LEFT, padx=5)

        self._delivered_lbl = Label(stats_frame, text="Delivered: 0", font=("Helvetica", 11, "bold"), fg="#1e8449", bg="#D5F5E3", padx=10, pady=5)
        self._delivered_lbl.pack(side=LEFT, padx=5)

        self._old_pending_lbl = Label(stats_frame, text="Old Pending: 0", font=("Helvetica", 11, "bold"), fg="#8B1E2D", bg="#FADBD8", padx=10, pady=5)
        self._old_pending_lbl.pack(side=LEFT, padx=5)

        # Form Input Fields Frame
        form_frame = Frame(self, bg=BG)
        form_frame.place(x=200, y=395)

        # Order ID
        Label(form_frame, text="Order ID:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=0, column=0, sticky=E, padx=5, pady=8)
        self._order_id_entry = Entry(form_frame, font=("Helvetica", 11), bg="#E2F7FC", state="readonly", width=22)
        self._order_id_entry.grid(row=0, column=1, padx=5, pady=8)

        # Recipient combobox
        Label(form_frame, text="Recipient:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=0, column=2, sticky=E, padx=5, pady=8)
        self._recipient_combobox = ttk.Combobox(form_frame, font=("Helvetica", 11), width=20, state="readonly")
        self._recipient_combobox.grid(row=0, column=3, padx=5, pady=8)
        self._recipient_combobox.bind("<<ComboboxSelected>>", self.on_recipient_changed)

        # Address Label
        self._address_lbl = Label(form_frame, text="Address: -", font=("Helvetica", 10), bg=BG, fg=MUTED, wraplength=450, justify=LEFT)
        self._address_lbl.grid(row=1, column=1, columnspan=4, sticky="w", padx=5)

        # Tracking Number
        Label(form_frame, text="Tracking Number:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=2, column=0, sticky=E, padx=5, pady=8)
        self._tracking_entry = Entry(form_frame, font=("Helvetica", 11), bg="#E2F7FC", width=22)
        self._tracking_entry.grid(row=2, column=1, padx=5, pady=8)

        # Status
        Label(form_frame, text="Status:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=2, column=2, sticky=E, padx=5, pady=8)
        self._status_combobox = ttk.Combobox(form_frame, values=Shipment.VALID_STATUSES, font=("Helvetica", 11), width=20, state="readonly")
        self._status_combobox.set("Pending")
        self._status_combobox.grid(row=2, column=3, padx=5, pady=8)

        # Action Buttons Frame
        button_frame = Frame(self, bg=BG)
        button_frame.pack(side=BOTTOM, pady=(10, 80))

        round_button(button_frame, "Add Shipment", self.add_record, width=140).pack(side=LEFT, padx=10)
        round_button(button_frame, "Update Status", self.update_record, width=140).pack(side=LEFT, padx=10)
        round_button(button_frame, "Delete", self.delete_record, width=140).pack(side=LEFT, padx=10)
        round_button(button_frame, "Clear", self.clear_fields, width=140, secondary=True).pack(side=LEFT, padx=10)

        # Initial data fetch & auto advance
        self._shipment_repo.auto_advance_shipments()
        self.refresh_recipients()
        self.refresh_data()

    def refresh_recipients(self) -> None:
        """Fetches active recipients from repository into combobox."""
        try:
            recipients = self._recipient_repo.get_all()
            self._recipient_lookup.clear()
            values = []
            for r in recipients:
                display = f"{r.invoice} - {r.name}"
                self._recipient_lookup[display] = r
                values.append(display)

            self._recipient_combobox["values"] = values
            if self._recipient_combobox.get() not in self._recipient_lookup:
                self._recipient_combobox.set("")
                self._address_lbl.config(text="Address: -")
        except Exception:
            pass

    def on_recipient_changed(self, event=None) -> None:
        selected = self._recipient_combobox.get().strip()
        recipient = self._recipient_lookup.get(selected)
        if recipient and recipient.address:
            self._address_lbl.config(text=f"Address: {recipient.address}")
        else:
            self._address_lbl.config(text="Address: -")

    def open_new_recipient(self) -> None:
        RecipientView.open_quick_add_dialog(self, on_saved=lambda new_id: (self.refresh_recipients(), self._select_recipient_by_id(new_id)))

    def _select_recipient_by_id(self, recipient_id: int) -> None:
        for display, r in self._recipient_lookup.items():
            if r.invoice == recipient_id:
                self._recipient_combobox.set(display)
                self.on_recipient_changed()
                break

    def add_record(self) -> None:
        """Functional Feature: Add Records."""
        selected_display = self._recipient_combobox.get().strip()
        recipient = self._recipient_lookup.get(selected_display)
        if not recipient:
            messagebox.showerror("Error", "Please select a valid recipient.")
            return

        if not recipient.address:
            messagebox.showerror("Error", "This recipient has no address saved. Add one first.")
            return

        tracking_num = self._tracking_entry.get().strip()

        try:
            shipment = Shipment(
                recipient_id=recipient.invoice,
                recipient_name=recipient.name,
                address=recipient.address,
                order_date=date.today(),
                status="Pending",
                tracking_number=tracking_num
            )
            order_id = self._shipment_repo.add(shipment)
            messagebox.showinfo("Success", f"Shipment added successfully!\nOrder ID: {order_id}\nTracking: {shipment.tracking_number}")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def update_record(self) -> None:
        """Functional Feature: Edit Records."""
        order_id = self._order_id_entry.get().strip()
        if not order_id:
            messagebox.showerror("Error", "Please select a shipment from the table to update.")
            return

        try:
            shipment = self._shipment_repo.get_by_id(order_id)
            if not shipment:
                raise RecordNotFoundException(f"Shipment {order_id} not found.")

            new_status = self._status_combobox.get()
            new_tracking = self._tracking_entry.get().strip()

            shipment.status = new_status
            if new_tracking:
                shipment.tracking_number = new_tracking

            self._shipment_repo.update(shipment)
            messagebox.showinfo("Success", f"Shipment {order_id} updated successfully!")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def delete_record(self) -> None:
        """Functional Feature: Delete Records."""
        order_id = self._order_id_entry.get().strip()
        if not order_id:
            messagebox.showerror("Error", "Please select a shipment to delete.")
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete shipment {order_id}?")
        if not confirm:
            return

        try:
            self._shipment_repo.delete(order_id)
            messagebox.showinfo("Success", f"Shipment {order_id} deleted successfully.")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def search_records(self) -> None:
        """Functional Feature: Search Records."""
        search_by = self._search_combobox.get()
        query = self._search_entry.get().strip()
        if not query:
            messagebox.showwarning("Search Error", "Please enter a value to search.")
            return

        try:
            shipments = self._shipment_repo.search(search_by, query)
            self._display_records(shipments)
            if not shipments:
                messagebox.showinfo("Search Results", "No matching shipments found.")
        except Exception as err:
            self.handle_error(err)

    def refresh_data(self) -> None:
        """Functional Feature: Display Records."""
        try:
            self._shipment_repo.auto_advance_shipments()
            shipments = self._shipment_repo.get_all()
            self._display_records(shipments)
            self.refresh_stats()
            self._search_entry.delete(0, END)
            self._search_combobox.set("Order ID")
        except Exception as err:
            self.handle_error(err)

    def refresh_stats(self) -> None:
        """Updates status metric counters."""
        try:
            stats = self._shipment_repo.get_stats()
            self._pending_lbl.config(text=f"Pending: {stats['pending']}")
            self._processing_lbl.config(text=f"Being Processed: {stats['processing']}")
            self._delivered_lbl.config(text=f"Delivered: {stats['delivered']}")
            self._old_pending_lbl.config(text=f"Old Pending: {stats['old_pending']}")
        except Exception:
            pass

    def _display_records(self, shipments: list) -> None:
        self._treeview.delete(*self._treeview.get_children())
        for s in shipments:
            self._treeview.insert("", "end", values=s.to_treeview_tuple())

    def on_select_row(self, event=None) -> None:
        selection = self._treeview.selection()
        if not selection:
            return

        row = self._treeview.item(selection[0])["values"]
        if not row:
            return

        self._order_id_entry.config(state="normal")
        self._order_id_entry.delete(0, END)
        self._order_id_entry.insert(0, str(row[0]))
        self._order_id_entry.config(state="readonly")

        recipient_id = row[1]
        self._select_recipient_by_id(recipient_id)

        self._status_combobox.set(str(row[4]))
        self._tracking_entry.delete(0, END)
        self._tracking_entry.insert(0, str(row[5]))

    def clear_fields(self) -> None:
        self._order_id_entry.config(state="normal")
        self._order_id_entry.delete(0, END)
        self._order_id_entry.config(state="readonly")
        self._recipient_combobox.set("")
        self._address_lbl.config(text="Address: -")
        self._tracking_entry.delete(0, END)
        self._status_combobox.set("Pending")
        if self._treeview.selection():
            self._treeview.selection_remove(*self._treeview.selection())