"""Recipient dropdown + 'New Recipient' button + read-only address line.

Shared by Order Entry and the Shipments 'Add Shipment' form so both behave the same.
"""
import tkinter as tk
from tkinter import ttk

from cashier.config import Theme
from cashier.database.connection import DatabaseError
from cashier.ui.add_recipient_dialog import AddRecipientDialog
from cashier.ui.widgets import show_db_error, styled_button


class RecipientPicker(tk.Frame):
    PLACEHOLDER = "Select a recipient"
    NO_SELECTION_TEXT = "Select a recipient to see the delivery address."
    MAX_ADDRESS_CHARS = 180                     # display only; the full address is what gets saved

    def __init__(self, parent, recipients, bg=Theme.BG, width=630):
        super().__init__(parent, bg=bg)
        self._repository = recipients
        self._recipients = []                   # Recipient rows, same order as the dropdown
        self._enabled = True
        self._disabled_text = ""
        self._address_var = tk.StringVar(value=self.NO_SELECTION_TEXT)
        self.columnconfigure(0, weight=1)

        self._box = ttk.Combobox(self, state="readonly", font=("Helvetica", 10))
        self._box.grid(row=0, column=0, sticky="ew", ipady=4)
        self._box.bind("<<ComboboxSelected>>", self._on_selected)

        self._new_button = styled_button(self, "New Recipient", self._open_dialog, False,
                                         height=34, px=150)
        self._new_button.grid(row=0, column=1, padx=(10, 0))

        tk.Label(self, textvariable=self._address_var, bg=bg, fg=Theme.MUTED,
                 font=("Helvetica", 9), anchor="nw", justify=tk.LEFT,
                 wraplength=width - 10, height=2).grid(
                     row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.reload()

    # ---- what the page asks for ------------------------------------------------------
    def selected(self):
        """The chosen Recipient, or None when nothing is chosen."""
        index = self._box.current()
        return self._recipients[index] if 0 <= index < len(self._recipients) else None

    def select(self, recipient_id):
        """Choose a recipient by ID. False if they are not in the directory any more."""
        for index, recipient in enumerate(self._recipients):
            if recipient.recipient_id == recipient_id:
                self._box.current(index)
                self._refresh_address()
                return True
        return False

    def clear(self):
        self._box.set(self.PLACEHOLDER)
        self._refresh_address()

    def reload(self, select_id=None):
        """Re-read the directory, keeping the current choice (or choosing `select_id`)."""
        current = self.selected()
        keep = select_id if select_id is not None else (current.recipient_id if current else None)
        try:
            self._recipients = list(self._repository.all())
        except DatabaseError as error:
            self._recipients = []
            show_db_error(error)
        self._box.configure(values=[f"{r.name}, {r.contact}" for r in self._recipients])
        if keep is None or not self.select(keep):
            self.clear()

    def set_enabled(self, enabled, disabled_text=""):
        """Lock/unlock the picker. The choice is kept while it is locked."""
        self._enabled = enabled
        self._disabled_text = disabled_text
        self._box.configure(state="readonly" if enabled else "disabled")
        self._new_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)
        self._refresh_address()

    # ---- internals ----------------------------------------------------------------------
    def _on_selected(self, event=None):
        self._box.selection_clear()
        self._refresh_address()

    def _refresh_address(self):
        if not self._enabled:
            self._address_var.set(self._disabled_text)
            return
        recipient = self.selected()
        if recipient is None:
            self._address_var.set(self.NO_SELECTION_TEXT)
            return
        text = " ".join(recipient.address.split()) or "(no address saved)"
        if len(text) > self.MAX_ADDRESS_CHARS:
            text = text[:self.MAX_ADDRESS_CHARS - 3] + "..."
        self._address_var.set(f"Address: {text}")

    def _open_dialog(self):
        AddRecipientDialog(self.winfo_toplevel(), self._repository, self._on_recipient_saved)

    def _on_recipient_saved(self, recipient):
        self.reload(select_id=recipient.recipient_id)
