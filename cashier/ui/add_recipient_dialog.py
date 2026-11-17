"""'New Recipient' pop-up: saves a person to the recipient directory and reports back."""
import re
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from cashier.config import Theme
from cashier.database.connection import DatabaseError
from cashier.database.recipient_repository import CONTACT_LENGTH, RecipientError
from cashier.ui.widgets import show_db_error, styled_button


class AddRecipientDialog(tk.Toplevel):
    """Modal dialog. `on_saved(recipient)` is called once the new recipient is stored."""

    def __init__(self, parent, recipients, on_saved):
        super().__init__(parent, bg=Theme.BG)
        self._recipients = recipients
        self._on_saved = on_saved
        self.title("New Recipient")
        self.resizable(False, False)
        self.transient(parent)

        body = tk.Frame(self, bg=Theme.BG)
        body.pack(padx=24, pady=20)
        tk.Label(body, text="New Recipient", bg=Theme.BG, fg=Theme.NAVY,
                 font=("Helvetica", 15, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 12))

        self._name = self._add_entry(body, 1, "Recipient Name", "Full name",
                                     self.register(self._name_allowed))
        self._contact = self._add_entry(body, 3, f"Contact Number ({CONTACT_LENGTH} digits)",
                                        "e.g. 9171234567", self.register(self._contact_allowed))

        tk.Label(body, text="Address", bg=Theme.BG, fg=Theme.TEXT,
                 font=("Helvetica", 10)).grid(row=5, column=0, sticky="w")
        self._address = ctk.CTkTextbox(
            body, width=340, height=90, corner_radius=8, border_width=1,
            border_color=Theme.ENTRY_BORDER, fg_color="white", text_color=Theme.TEXT,
            font=ctk.CTkFont("Helvetica", 12))
        self._address.grid(row=6, column=0, sticky="w", pady=(2, 14))

        buttons = tk.Frame(body, bg=Theme.BG)
        buttons.grid(row=7, column=0, sticky="e")
        styled_button(buttons, "Cancel", self.destroy, False, px=110).pack(side=tk.LEFT, padx=(0, 8))
        styled_button(buttons, "Save Recipient", self._save, True, px=150).pack(side=tk.LEFT)

        self.bind("<Escape>", lambda event: self.destroy())
        self._center_on(parent)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass                                   # the dialog still works without the grab
        self._name.focus_set()

    # ---- helpers ------------------------------------------------------------------
    @staticmethod
    def _add_entry(parent, row, label, placeholder, validator):
        tk.Label(parent, text=label, bg=Theme.BG, fg=Theme.TEXT,
                 font=("Helvetica", 10)).grid(row=row, column=0, sticky="w")
        entry = ctk.CTkEntry(
            parent, width=340, height=36, corner_radius=8, border_width=1,
            border_color=Theme.ENTRY_BORDER, fg_color="white", text_color=Theme.TEXT,
            placeholder_text=placeholder, font=ctk.CTkFont("Helvetica", 12),
            validate="key", validatecommand=(validator, "%P"))
        entry.grid(row=row + 1, column=0, sticky="w", pady=(2, 12))
        return entry

    @staticmethod
    def _name_allowed(value):
        """Live filter: letters, spaces and . , ' & - only (same as the Admin page)."""
        return re.fullmatch(r"[A-Za-z .,'&-]*", value) is not None

    @staticmethod
    def _contact_allowed(value):
        """Live filter: digits only, at most CONTACT_LENGTH of them, first digit 9 (same as Admin)."""
        return value == "" or (value.isascii() and value.isdigit()
                               and len(value) <= CONTACT_LENGTH and value[0] == "9")

    def _center_on(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    # ---- save ------------------------------------------------------------------------
    def _save(self):
        try:
            recipient = self._recipients.add(
                self._name.get(), self._contact.get(), self._address.get("1.0", "end"))
        except RecipientError as error:
            messagebox.showwarning("Check Recipient Details", str(error), parent=self)
            return
        except DatabaseError as error:
            show_db_error(error)
            return
        self.grab_release()
        self.destroy()
        self._on_saved(recipient)
