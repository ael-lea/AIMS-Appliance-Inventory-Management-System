"""
Recipient Management View.
Demonstrates:
- Inheritance (RecipientView inherits from BaseFormView)
- Encapsulation (Encapsulates RecipientRepository and dialogs)
- Polymorphism (Overrides build_ui, refresh_data, clear_fields)
- Functional Features: Add, Edit, Delete, Search, Display
"""
import re
from tkinter import *
from tkinter import ttk, messagebox
from typing import Optional, Callable
from .base_view import BaseFormView
from .widgets import round_button, NAVY, ACTIVE, BG, LIGHT
from ..models.recipient import Recipient
from ..repositories.recipient_repo import RecipientRepository
from typing import Any, Optional, Callable #
from ..core.exceptions import (
    ValidationError,
    EmptyFieldException,
    InvalidDataTypeException,
    DuplicateRecordException,
    RecordNotFoundException
)

class RecipientView(BaseFormView):
    """
    Form view managing delivery recipient details, contact verification, and shipping addresses.
    """

    def __init__(self, parent_window: Tk):
        self._repository = RecipientRepository()
        super().__init__(parent_window, title="Recipient Details")

    def build_ui(self) -> None:
        """Constructs Recipient form components."""
        # Top Search Frame
        search_frame = Frame(self, bg=BG)
        search_frame.pack(pady=(75, 10))

        self._search_combobox = ttk.Combobox(
            search_frame,
            values=("Invoice", "Name", "Contact"),
            state="readonly",
            width=15
        )
        self._search_combobox.set("Name")
        self._search_combobox.pack(side=LEFT, padx=5)

        self._search_entry = Entry(search_frame, font=("Helvetica", 11), width=25)
        self._search_entry.pack(side=LEFT, padx=5)

        round_button(search_frame, "Search", self.search_records, width=95).pack(side=LEFT, padx=5)
        round_button(search_frame, "Show All", self.refresh_data, width=95, secondary=True).pack(side=LEFT, padx=5)

        # Table Frame
        table_frame = Frame(self, bg=BG)
        table_frame.pack(fill=X, padx=20, pady=(15, 5))

        y_scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL)
        x_scrollbar = ttk.Scrollbar(table_frame, orient=HORIZONTAL)

        self._treeview = ttk.Treeview(
            table_frame,
            columns=("invoice", "name", "contact", "address", "description"),
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
            "invoice": ("Recipient ID", 100),
            "name": ("Recipient Name", 180),
            "contact": ("Contact", 130),
            "address": ("Address", 280),
            "description": ("Description", 220)
        }
        for col_id, (col_text, col_width) in headings.items():
            self._treeview.heading(col_id, text=col_text)
            self._treeview.column(col_id, width=col_width, anchor=W if col_id in ("name", "address", "description") else CENTER)

        self._treeview.bind("<ButtonRelease-1>", self.on_select_row)

        # Form Input Fields Frame
        form_frame = Frame(self, bg=BG)
        form_frame.place(x=280, y=420)

        contact_cmd = (self._parent_window.register(self._only_contact), "%P")
        letters_cmd = (self._parent_window.register(self._only_letters), "%P")

        # Row 0: ID and Name
        Label(form_frame, text="Recipient ID:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=0, column=0, sticky=E, padx=5, pady=8)
        self._invoice_entry = Entry(form_frame, font=("Helvetica", 11), bg="#E2F7FC", state="readonly", width=25)
        self._invoice_entry.grid(row=0, column=1, padx=5, pady=8)

        Label(form_frame, text="Recipient Name:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=0, column=2, sticky=E, padx=5, pady=8)
        self._name_entry = Entry(form_frame, font=("Helvetica", 11), bg="#E2F7FC", width=25, validate="key", validatecommand=letters_cmd)
        self._name_entry.grid(row=0, column=3, padx=5, pady=8)

        # Row 1: Contact
        Label(form_frame, text="Contact Number:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=1, column=0, sticky=E, padx=5, pady=8)
        self._contact_entry = Entry(form_frame, font=("Helvetica", 11), bg="#E2F7FC", width=25, validate="key", validatecommand=contact_cmd)
        self._contact_entry.grid(row=1, column=1, padx=5, pady=8)

        # Row 2: Address and Description
        Label(form_frame, text="Address:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=2, column=0, sticky=NE, padx=5, pady=8)
        self._address_text = Text(form_frame, font=("Helvetica", 11), bg="#E2F7FC", width=25, height=3)
        self._address_text.grid(row=2, column=1, padx=5, pady=8)

        Label(form_frame, text="Description:", font=("Helvetica", 11, "bold"), bg=BG).grid(row=2, column=2, sticky=NE, padx=5, pady=8)
        self._description_text = Text(form_frame, font=("Helvetica", 11), bg="#E2F7FC", width=25, height=3)
        self._description_text.grid(row=2, column=3, padx=5, pady=8)

        # Action Buttons Frame
        button_frame = Frame(self, bg=BG)
        button_frame.pack(side=BOTTOM, pady=(10, 80))

        round_button(button_frame, "Add", self.add_record, width=120).pack(side=LEFT, padx=10)
        round_button(button_frame, "Update", self.update_record, width=120).pack(side=LEFT, padx=10)
        round_button(button_frame, "Delete", self.delete_record, width=120).pack(side=LEFT, padx=10)
        round_button(button_frame, "Clear", self.clear_fields, width=120, secondary=True).pack(side=LEFT, padx=10)

        # Initial data fetch
        self.refresh_data()

    @staticmethod
    def _only_contact(value: str) -> bool:
        return value == "" or (value.isascii() and value.isdigit() and len(value) <= 10 and value[0] == "9")

    @staticmethod
    def _only_letters(value: str) -> bool:
        return value == "" or re.fullmatch(r"[A-Za-z .,'&-]*", value) is not None

    def _extract_model_from_inputs(self, require_id: bool = False) -> Recipient:
        invoice_val = self._invoice_entry.get().strip()
        invoice = int(invoice_val) if invoice_val and invoice_val.isdigit() else None
        if require_id and not invoice:
            raise RecordNotFoundException("Please select a recipient from the table first.")

        return Recipient(
            invoice=invoice,
            name=self._name_entry.get(),
            contact=self._contact_entry.get(),
            address=self._address_text.get("1.0", END).strip(),
            description=self._description_text.get("1.0", END).strip()
        )

    def add_record(self) -> None:
        """Functional Feature: Add Records."""
        try:
            recipient = self._extract_model_from_inputs(require_id=False)
            new_id = self._repository.add(recipient)
            messagebox.showinfo("Success", f"Recipient '{recipient.name}' added successfully (ID: {new_id}).")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def update_record(self) -> None:
        """Functional Feature: Edit Records."""
        try:
            recipient = self._extract_model_from_inputs(require_id=True)
            self._repository.update(recipient)
            messagebox.showinfo("Success", f"Recipient ID {recipient.invoice} updated successfully.")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def delete_record(self) -> None:
        """Functional Feature: Delete Records."""
        invoice_val = self._invoice_entry.get().strip()
        if not invoice_val or not invoice_val.isdigit():
            messagebox.showerror("Error", "Row not selected.")
            return

        confirm = messagebox.askyesno("Confirm Delete", "Do you really want to delete this recipient?")
        if not confirm:
            return

        try:
            self._repository.delete(int(invoice_val))
            messagebox.showinfo("Success", "Record deleted successfully.")
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
            recipients = self._repository.search(search_by, query)
            self._display_records(recipients)
            if not recipients:
                messagebox.showinfo("Search Results", "No matching recipients found.")
        except Exception as err:
            self.handle_error(err)

    def refresh_data(self) -> None:
        """Functional Feature: Display Records."""
        try:
            recipients = self._repository.get_all()
            self._display_records(recipients)
            self._search_entry.delete(0, END)
            self._search_combobox.set("Name")
        except Exception as err:
            self.handle_error(err)

    def _display_records(self, recipients: list) -> None:
        self._treeview.delete(*self._treeview.get_children())
        for rec in recipients:
            self._treeview.insert("", "end", iid=str(rec.invoice), values=rec.to_treeview_tuple())

    def on_select_row(self, event=None) -> None:
        selected = self._treeview.selection()
        if not selected:
            return

        recipient_id = selected[0]
        try:
            rec = self._repository.get_by_id(int(recipient_id))
            if not rec:
                return

            self._invoice_entry.config(state="normal")
            self._invoice_entry.delete(0, END)
            self._invoice_entry.insert(0, str(rec.invoice))
            self._invoice_entry.config(state="readonly")

            self._name_entry.delete(0, END)
            self._name_entry.insert(0, rec.name)

            self._contact_entry.delete(0, END)
            self._contact_entry.insert(0, rec.contact)

            self._address_text.delete("1.0", END)
            self._address_text.insert("1.0", rec.address)

            self._description_text.delete("1.0", END)
            self._description_text.insert("1.0", rec.description)
        except Exception as err:
            self.handle_error(err)

    def clear_fields(self) -> None:
        self._invoice_entry.config(state="normal")
        self._invoice_entry.delete(0, END)
        self._invoice_entry.config(state="readonly")
        self._name_entry.delete(0, END)
        self._contact_entry.delete(0, END)
        self._address_text.delete("1.0", END)
        self._description_text.delete("1.0", END)
        if self._treeview.selection():
            self._treeview.selection_remove(*self._treeview.selection())

    @classmethod
    def open_quick_add_dialog(cls, parent: Any, on_saved: Optional[Callable[[int], None]] = None) -> None:
        """
        Pop-up dialog so another window (e.g. Shipment or Cashier) can quickly register a recipient.
        """
        win = Toplevel(parent)
        win.title("New Recipient")
        win.config(bg="white")
        win.resizable(False, False)
        win.grab_set()

        contact_check = (win.register(cls._only_contact), "%P")
        letters_check = (win.register(cls._only_letters), "%P")

        Label(win, text="Recipient Name", font=("Helvetica", 12, "bold"), bg="white").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        name_entry = Entry(win, font=("Helvetica", 12), bg="#E2F7FC", validate="key", validatecommand=letters_check)
        name_entry.grid(row=0, column=1, padx=15)

        Label(win, text="Contact", font=("Helvetica", 12, "bold"), bg="white").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        contact_entry = Entry(win, font=("Helvetica", 12), bg="#E2F7FC", validate="key", validatecommand=contact_check)
        contact_entry.grid(row=1, column=1, padx=15)

        Label(win, text="Address", font=("Helvetica", 12, "bold"), bg="white").grid(row=2, column=0, padx=15, pady=10, sticky="nw")
        address_text = Text(win, width=22, height=4, font=("Helvetica", 12), bg="#E2F7FC")
        address_text.grid(row=2, column=1, padx=15)

        repo = RecipientRepository()

        def save():
            try:
                rec = Recipient(
                    name=name_entry.get(),
                    contact=contact_entry.get(),
                    address=address_text.get("1.0", END).strip()
                )
                new_id = repo.add(rec)
                messagebox.showinfo("Success", "Recipient added successfully.", parent=win)
                win.destroy()
                if on_saved:
                    on_saved(new_id)
            except Exception as err:
                messagebox.showerror("Error", str(err), parent=win)

        round_button(win, "Save", save, width=120, bg_color="white").grid(row=3, column=0, columnspan=2, pady=15)
        name_entry.focus_set()