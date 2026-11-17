"""The main cashier window: title bar, sidebar, navigation and page switching."""
import os
import tkinter as tk
from tkinter import messagebox
import session

import customtkinter as ctk

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# from account_bar import log_out
from cashier.app_context import AppContext
from cashier.config import Settings, Theme
from cashier.database.connection import DatabaseError
from cashier.ui.clock import AnalogClock, DateDisplay
from cashier.ui.pages.dashboard_page import DashboardPage
from cashier.ui.pages.order_entry_page import OrderEntryPage
from cashier.ui.pages.order_history_page import OrderHistoryPage
from cashier.ui.pages.sales_overview_page import SalesOverviewPage
from cashier.ui.pages.shipment_page import ShipmentPage
from cashier.ui.settings_menu import SettingsMenu
from cashier.ui.widgets import load_icon, make_nav_icon

class CashierApp:
    """Owns the Tk window and switches between the page objects."""

    # (menu label, y position, icon kind, page class)
    NAV_ITEMS = (
        ("Dashboard", 325, "home", DashboardPage),
        ("Order Entry", 380, "cart", OrderEntryPage),
        ("Shipments", 435, "truck", ShipmentPage),
        ("Order History", 490, "history", OrderHistoryPage),
        ("Sales Overview", 545, "chart", SalesOverviewPage),
    )
    # To use your own picture for a menu button, e.g. {"Order History": "history.png"}
    NAV_ICON_FILES = {}

    def __init__(self, user, context=None):
        self._user = user
        self._context = context or AppContext()
        self._window = None
        self._nav_buttons = {}
        self._pages = {label: page_class for label, _, _, page_class in self.NAV_ITEMS}
        self._current_page = None
        self._icons = []                    # keeps the menu pictures alive

    # ---- start-up -----------------------------------------------------------------
    def run(self):
        try:
            self._context.initialize_schema()
        except DatabaseError as error:
            messagebox.showerror("Database Error", str(error))
            return

        ctk.set_appearance_mode("light")
        self._window = tk.Tk()
        self._window.title("AIMS Cashier Dashboard")
        self._window.geometry("1520x790+0+0")
        self._window.resizable(False, False)
        self._window.config(bg=Theme.BG)

        self._set_window_icon()
        self._build_title_bar()
        self._build_sidebar()
        self.open_page("Dashboard")
        self._window.mainloop()

    def _set_window_icon(self):
        try:
            logo_path = os.path.join(Settings.ICON_DIR, "aimslogo.png")
            if os.path.exists(logo_path):
                self._window.iconphoto(True, tk.PhotoImage(file=logo_path).subsample(2, 2))
        except tk.TclError:
            pass

    # ---- layout ------------------------------------------------------------------------

    def _build_title_bar(self):
        title_frame = ctk.CTkFrame(
            self._window,
            fg_color=Theme.BG,
            corner_radius=20,
            height=60,
            width=1300
        )
        title_frame.place(x=210, y=5)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="Cashier Dashboard",
            font=("Helvetica", 20, "bold"),
            fg=Theme.NAVY,
            bg=Theme.BG,
            compound="left"
        ).pack(side="left", padx=30, pady=10)

        # Settings Icon
        accset_image = Image.open(os.path.join(Settings.ICON_DIR, 'setting(1).png'))
        accset_image = accset_image.resize((20, 20))
        self.accset_icon = ImageTk.PhotoImage(
            accset_image,
            master=self._window
        )

        # Account Settings Button
        self.accset_btn = ctk.CTkButton(
            title_frame,
            image=self.accset_icon,
            text=session.current_user.get('name', 'Cashier'),
            font=('Helvetica', 13, 'bold'),
            text_color='#FFFFFF',
            fg_color='#012148',
            hover_color='#0a56b3',
            border_color='#012148',
            border_width=2,
            corner_radius=10,
            width=150,
            height=36,
            cursor='hand2',
            compound=tk.LEFT,
            command=lambda: SettingsMenu(self._window, self._context)
        )
        self.accset_btn.pack(side="right", padx=25)

        # Update the button name when account details change
        self._window.update_account_name = self.update_account_name

        tk.Frame(
            self._window,
            bg=Theme.NAVY,
            height=2,
            width=1320
        ).place(x=200, y=60)


    def update_account_name(self):
        self.accset_btn.configure(
            text=session.current_user.get('name', 'Cashier')
        )


    def _build_sidebar(self):
        sidebar = tk.Frame(self._window, bg=Theme.NAVY)
        sidebar.place(x=0, y=0, width=200, height=790)

        logo_label = self._build_logo(sidebar)
        AnalogClock(sidebar).place(x=20, y=65)
        DateDisplay(sidebar).pack(fill=tk.X, pady=(235, 0))
        tk.Frame(sidebar, bg="#064086", height=2, width=200).place(x=0, y=300)

        for label, y, kind, _ in self.NAV_ITEMS:
            self._make_nav_button(sidebar, label, y, kind)
        # self._build_logout_button(sidebar)

        # Clicking the logo goes back to the dashboard (like the Admin dashboard)
        logo_label.config(cursor="hand2")
        logo_label.bind("<Button-1>", lambda event: self.open_page("Dashboard"))

    def _build_logo(self, sidebar):
        logo_path = os.path.join(Settings.ICON_DIR, "logo.png")
        try:
            if Image and os.path.exists(logo_path):
                image = Image.open(logo_path)
                image.thumbnail((400, 400))
                self._sidebar_logo = ImageTk.PhotoImage(image)
                label = tk.Label(sidebar, image=self._sidebar_logo, bg=Theme.NAVY)
                label.place(x=0, y=-60, width=200, height=200)
                return label
        except Exception:
            pass
        label = tk.Label(sidebar, text="AIMS", font=("Helvetica", 25, "bold"),
                         bg=Theme.NAVY, fg="white")
        label.place(x=0, y=35, width=200)
        return label

    def _make_nav_button(self, sidebar, label, y, kind):
        icon = load_icon(self.NAV_ICON_FILES.get(label)) or make_nav_icon(kind)
        if icon:
            self._icons.append(icon)
        button = ctk.CTkButton(
            sidebar, image=icon, compound=tk.LEFT, text=f" {label}",
            font=("Helvetica", 15, "bold"), text_color=Theme.BG,
            fg_color=Theme.NAVY, hover_color='#053E87', corner_radius=10,
            width=180, height=45, anchor="w", cursor="hand2",
            command=lambda name=label: self.open_page(name))
        button.place(x=10, y=y)
        self._nav_buttons[label] = button

    # def _build_logout_button(self, sidebar):
    #     icon = load_icon("exit.png")
    #     if icon:
    #         self._icons.append(icon)
    #     ctk.CTkButton(
    #         sidebar, image=icon, compound=tk.LEFT, text=" Log out",
    #         font=("Helvetica", 15, "bold"), text_color=Theme.BG,
    #         fg_color=Theme.NAVY, hover_color=Theme.ACTIVE, corner_radius=10,
    #         width=180, height=45, anchor="w", cursor="hand2",
    #         command=lambda: log_out(self._window)).place(x=10, y=720)

    # ---- navigation ---------------------------------------------------------------------
    def open_page(self, page_name):
        if self._current_page is not None:
            self._current_page.destroy()
            self._current_page = None
        for button in self._nav_buttons.values():
            button.configure(fg_color=Theme.NAVY, hover_color=Theme.ACTIVE)
        self._nav_buttons[page_name].configure(fg_color=Theme.ACTIVE, hover_color=Theme.ACTIVE)

        page_class = self._pages[page_name]                  # polymorphism: all pages are BasePage
        self._current_page = page_class(self._window, self.go, self._context).show()

    def go(self, page_name):
        """Used by buttons inside pages: switch a moment after the click, so a rounded
        button is never destroyed while it is still handling its own click."""
        self._window.after(150, self.open_page, page_name)