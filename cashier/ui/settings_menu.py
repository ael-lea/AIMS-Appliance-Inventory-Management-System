"""Cashier settings: the pop-up menu (upper right) and the windows it opens.

SettingsDialog is an abstract parent; AccountInfoDialog (details and change
password) and TodaySummaryDialog each fill in _build() their own way.
"""
import tkinter as tk
from abc import ABC, abstractmethod
from tkinter import messagebox

import customtkinter as ctk

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = ImageDraw = ImageTk = None

import session
from account_bar import log_out
from cashier.config import Theme
from cashier.database.connection import DatabaseError
from cashier.database.sales_repository import SalesPeriod
from cashier.ui.widgets import BACK_IMAGE_PATH, load_icon, show_db_error, styled_button
from cashier.utils import peso
from cashier.database.employee_repository import ProfileError

LOGOUT_COLOR = "#8B1E2D"
LOGOUT_HOVER = "#F5E6E8"
ENTRY_BORDER = "#C9CED6"


def _rounded_entry(parent, **extra):
    return ctk.CTkEntry(parent, height=36, corner_radius=10, border_width=1,
                        border_color=ENTRY_BORDER, fg_color="white",
                        text_color=Theme.TEXT, font=("Helvetica", 12), **extra)


def _employee_id():
    return session.current_user.get("id")


# Live typing rules (same as the Employees form) Settings Menu

def validate_name(value):
    return value == "" or all(char.isalpha() or char.isspace() for char in value)


def validate_contact(value):
    """Typing rule: digits only, must start with 9, up to 10 digits."""
    return value == "" or (value.isascii() and value.isdigit() and value.startswith("9") and len(value) <= 10)

def is_valid_contact(value):
    """Save rule: a complete 10-digit number starting with 9."""
    return value.isdigit() and (value.startswith("9") and len(value) <= 10)


def _summary_icon(size=24):
    """A small navy bar-chart icon for Today's Summary (used when summary.png is not in the photos folder)."""
    if Image is None:
        return None
    k = 4
    big = Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)
    navy = (1, 33, 72, 255)
    u = size * k / 24
    for x, top in ((3, 13), (10, 7), (17, 2)):          # three bars of growing height
        draw.rounded_rectangle((x * u, top * u, (x + 4) * u, 22 * u), radius=1 * u, fill=navy)
    return ImageTk.PhotoImage(big.resize((size, size), Image.LANCZOS))


class SettingsMenu(tk.Toplevel):
    """Small pop-up under the settings button. Click outside it to close."""

    WIDTH, HEIGHT = 270, 225    

    def __init__(self, parent, context):
        super().__init__(parent)
        self._parent = parent
        self._context = context
        self._icons = []                       # keeps the pictures alive
        self.title("Account Settings")
        self.resizable(False, False)
        self.config(bg=Theme.BG)
        self.transient(parent)
        self._place_top_right()
        self.grab_set()
        self._build()
        self.bind("<Button-1>", self._close_if_outside)

    def _place_top_right(self):
        self._parent.update_idletasks()
        x = self._parent.winfo_rootx() + self._parent.winfo_width() - self.WIDTH - 15
        y = self._parent.winfo_rooty() + 55
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{max(x, 0)}+{max(y, 0)}")

    def _icon(self, file_name):
        icon = load_icon(file_name)
        if icon:
            self._icons.append(icon)
        return icon

    def _build(self):
        tk.Label(self, text="Cashier Settings", font=("Helvetica", 9),
                 bg=Theme.BG, fg=Theme.MUTED).pack(pady=(10, 0))
        name = session.current_user.get("name") or "Cashier"
        tk.Label(self, image=self._icon("prof.png"), compound=tk.LEFT,
                 text=f" Hello, {name}!", font=("Helvetica", 15, "bold"),
                 bg=Theme.BG, fg=Theme.NAVY).pack(pady=(0, 5))
        tk.Frame(self, bg=Theme.MUTED, height=1, width=320).pack()

        self._add_item("Account Info", "acc.png",
                       lambda: self._open(AccountInfoDialog), pady=(10, 0))
        
        # Put summary.png in your photos folder to use your own picture; otherwise a drawn chart icon shows
        self._add_item("Today's Summary", "summary.png",
                       lambda: self._open(TodaySummaryDialog), fallback_icon=_summary_icon)

        tk.Frame(self, bg=Theme.MUTED, height=1, width=320).pack(pady=(10, 0))
        self._add_item("Log Out", "logout.png", self._log_out, pady=(10, 0),
                       text_color=LOGOUT_COLOR, hover=LOGOUT_HOVER)

    def _add_item(self, text, icon_file, command, pady=(6, 0),
                  text_color=Theme.NAVY, hover=Theme.LIGHT_BTN, fallback_icon=None):
        icon = self._icon(icon_file)
        if icon is None and fallback_icon is not None:
            icon = fallback_icon()
            if icon:
                self._icons.append(icon)
        ctk.CTkButton(
            self, text=text, image=icon, command=command,
            font=("Helvetica", 15, "bold"), text_color=text_color,
            fg_color=Theme.BG, hover_color=hover, bg_color=Theme.BG,
            corner_radius=10, width=260, height=34, cursor="hand2",
            compound=tk.LEFT, anchor="w").pack(padx=10, pady=pady)

    def _open(self, dialog_class):
        """Close the menu and open a dialog; its Back button reopens the menu."""
        parent, context = self._parent, self._context
        self.destroy()
        dialog_class(parent, context, on_back=lambda: SettingsMenu(parent, context))

    def _log_out(self):
        parent = self._parent
        self.destroy()
        log_out(parent)

    def _close_if_outside(self, event):
        left, top = self.winfo_rootx(), self.winfo_rooty()
        inside = (left <= event.x_root <= left + self.winfo_width()
                  and top <= event.y_root <= top + self.winfo_height())
        if not inside:
            self.destroy()


class SettingsDialog(tk.Toplevel, ABC):
    """Common window for every settings page: centred, modal, title and Back button."""

    TITLE = ""
    SIZE = (430, 400)

    def __init__(self, parent, context, on_back):
        super().__init__(parent)
        self._parent = parent
        self._context = context
        self._on_back = on_back
        width, height = self.SIZE
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2 - 30      # -30 lifts it a bit above the taskbar
        self.title(self.TITLE)
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        self.resizable(False, False)
        self.config(bg=Theme.BG)
        self.transient(parent)
        self.grab_set()

        # Header row: the Back picture on the left and the title in the middle,
        # both centred on the same line so they stay aligned.
        header = tk.Frame(self, bg=Theme.BG, height=56)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        self._back_image = tk.PhotoImage(file=BACK_IMAGE_PATH, master=self)
        tk.Button(header, image=self._back_image, command=self._go_back, cursor="hand2",
                  bd=0, bg=Theme.BG, activebackground=Theme.BG).place(x=12, rely=0.5, anchor="w")
        tk.Label(header, text=self.TITLE, font=("Helvetica", 18, "bold"),
                 bg=Theme.BG, fg=Theme.NAVY).place(relx=0.5, rely=0.5, anchor="center")
        self._build()

    def _go_back(self):
        self.destroy()
        self._on_back()

    @abstractmethod
    def _build(self):
        """Create this dialog's content."""

    # ---- helpers shared by the dialogs -----------------------------------------------
    def _info_row(self, label, value):
        """A caption with its read-only value underneath. Returns the value label."""
        tk.Label(self, text=label, font=("Helvetica", 10, "bold"), bg=Theme.BG,
                 anchor="w").pack(fill=tk.X, padx=30, pady=(12, 0))
        value_label = tk.Label(self, text=value or "—", font=("Helvetica", 12),
                               bg=Theme.BG, fg=Theme.TEXT, anchor="w")
        value_label.pack(fill=tk.X, padx=30, pady=(2, 0))
        return value_label


    def _edit_field(self, label, value, rule=None):
        """A caption with a rounded editable box. `rule` limits what can be typed. Returns the entry."""
        tk.Label(self, text=label, font=("Helvetica", 10, "bold"), bg=Theme.BG,
                 anchor="w").pack(fill=tk.X, padx=30, pady=(12, 0))
        entry = _rounded_entry(self)
        entry.insert(0, value or "")
        entry.pack(fill=tk.X, padx=30, pady=(3, 0))
        if rule is not None:
            # deleting is always allowed, so an old value that breaks the rule can still be fixed
            check = lambda proposed: rule(proposed) or len(proposed) < len(entry.get())
            # CTkEntry has no validate option of its own, so set it on the inner tk.Entry
            entry._entry.configure(validate="key",
                                   validatecommand=(self.register(check), "%P"))
        return entry

    def _password_field(self, label):
        tk.Label(self, text=label, font=("Helvetica", 10, "bold"), bg=Theme.BG,
                 anchor="w").pack(fill=tk.X, padx=30, pady=(12, 0))
        entry = _rounded_entry(self, show="*")
        entry.pack(fill=tk.X, padx=30, pady=(3, 0))
        return entry


class AccountInfoDialog(SettingsDialog):
    """The cashier's own details (name, email, contact) and Change Password, on one page."""

    TITLE = "Account Info"
    SIZE = (430, 700)

    def _build(self):
        try:
            profile = self._context.employees.get_profile(_employee_id())
        except DatabaseError as error:
            show_db_error(error, "Database Error")
            self.destroy()
            return
        if profile is None:
            messagebox.showerror("Error", "Account not found.", parent=self)
            self.destroy()
            return
        self._role = profile.role

        # "Name | Role" line under the title
        self._subtitle = tk.Label(self, text=f"{profile.name}  |  {profile.role}",
                                  font=("Helvetica", 10), bg=Theme.BG, fg=Theme.MUTED)
        self._subtitle.pack(pady=(0, 2))

        # ---- details ----
        self._name = self ._edit_field("Name", profile.name, validate_name)
        self._email = self ._edit_field("Email", profile.email)
        self._contact = self ._edit_field("Contact Number",
        str(profile.contact or ""), validate_contact)
        styled_button(self, "Save Details", self._save, True, px=370).pack(padx=30, pady=(14, 0))

        # ---- change password ----
        tk.Frame(self, bg=Theme.MUTED, height=1).pack(fill=tk.X, padx=30, pady=(18, 0))
        tk.Label(self, text="Change Password", font=("Helvetica", 14, "bold"),
                 bg=Theme.BG, fg=Theme.NAVY, anchor="w").pack(fill=tk.X, padx=30, pady=(12, 0))
        self._current = self._password_field("Current Password")
        self._new = self._password_field("New Password")
        self._confirm = self._password_field("Confirm New Password")
        styled_button(self, "Change Password", self._submit_password, True, px=370).pack(
            padx=30, pady=(16, 0))

    def _save(self):
        contact = self ._contact.get().strip()
        
        if contact and not is_valid_contact(contact):
            messagebox. showwarning( "Cannot Save", "Contact number must be 10 digits and start with 9 (e.g. 9171234567).", parent=self)
            return
        try:
            saved_name = self._context.employees.update_profile(
                _employee_id(), self._name.get(), self._email.get(), contact)
        except ProfileError as error:
            messagebox.showwarning("Cannot Save", str(error), parent=self)
            return
        except DatabaseError as error:
            show_db_error(error)
            return
        session.current_user["name"] = saved_name
        self._subtitle.config(text= f"{saved_name} | {self._role}")
        # refresh the name shown on the settings button in the top bar
        update_button = getattr(self._parent, "update_account_name", None)
        if callable(update_button):
            update_button()
        messagebox.showinfo("Saved", "Your details were updated.", parent=self)



    def _submit_password(self):
        try:
            self._context.employees.change_password(
                _employee_id(), self._current.get(), self._new.get(), self._confirm.get())
        except ProfileError as error:
            messagebox.showwarning("Cannot Change Password", str(error), parent=self)
            return
        except DatabaseError as error:
            show_db_error(error)
            return
        messagebox.showinfo("Success", "Password changed successfully.", parent=self)
        for entry in (self._current, self._new, self._confirm):
            entry.delete(0, tk.END)


class TodaySummaryDialog(SettingsDialog):
    """End-of-shift numbers: today's completed sales and pending orders."""

    TITLE = "Today's Summary"
    SIZE = (430, 460)

    def _build(self):
        self._values = {}
        for key, label in (("sales", "Total Sales"), ("orders", "Completed Orders"),
                           ("items", "Items Sold"), ("average", "Average Order"),
                           ("pending", "Pending (Held) Orders")):
            self._values[key] = self._info_row(label, "")
        tk.Label(self, text="Totals cover every completed order today (all cashiers).",
                 font=("Helvetica", 9), bg=Theme.BG, fg=Theme.MUTED).pack(pady=(18, 0))
        styled_button(self, "Refresh", self._refresh, False, px=120).pack(pady=(10, 0))
        self._refresh()

    def _refresh(self):
        try:
            summary = self._context.sales.summary(SalesPeriod("Today"))
            pending = self._context.orders.count_pending()
        except DatabaseError as error:
            show_db_error(error)
            return
        texts = {"sales": peso(summary.total_sales), "orders": str(summary.transactions),
                 "items": str(summary.items_sold), "average": peso(summary.average_order),
                 "pending": str(pending)}
        for key, text in texts.items():
            self._values[key].config(text=text)