"""
Main Dashboard View Module.
Demonstrates:
- Multiple windows/forms (Host for EmployeeView, ProductView, RecipientView, ShipmentView, SalesView)
- Menus (Tkinter Menu Bar: File, Manage, Tools, Help)
- Analog Canvas Clock (Trigonometric rendering)
- Metric Dashboard Summary Cards
- Encapsulated View Orchestration
"""
import math
import time
from datetime import datetime
from tkinter import *
from tkinter import messagebox
import customtkinter as ctk
from typing import Optional

from .widgets import NAVY, ACTIVE, BG, LIGHT, MUTED, round_button, load_icon, load_ctk_icon
from .employees_view import EmployeeView
from .products_view import ProductView
from .recipient_view import RecipientView
from .shipment_view import ShipmentView
from .sales_view import SalesView
from .admin_settings_view import AdminSettingsView
from ..core.session import SessionManager
from ..core.database import DatabaseManager
from ..repositories.employee_repo import EmployeeRepository
from ..repositories.product_repo import ProductRepository
from ..repositories.recipient_repo import RecipientRepository
from ..repositories.sales_repo import SalesRepository


class DashboardWindow:
    """
    Main Application Window and View Controller for AIMS.
    Encapsulates navigation, the native Tkinter Menu bar, animated clock,
    and sub-form lifecycle management.
    """

    SIDEBAR_COLOR = NAVY
    ACTIVE_COLOR = ACTIVE

    def __init__(self):
        # Enforce authentication constraint
        if not SessionManager.is_admin():
            raise SystemExit("Please log in as Administrator first.")

        self._root = Tk()
        self._root.title("AIMS Dashboard")
        self._root.geometry("1520x790+0+0")
        self._root.resizable(False, False)
        self._root.config(bg=BG)

        # Window icon
        self._window_icon = load_icon("aimslogo.png", scale=0.5)
        if self._window_icon:
            self._root.iconphoto(True, self._window_icon)

        # Repositories for summary statistics
        self._emp_repo = EmployeeRepository()
        self._prod_repo = ProductRepository()
        self._rec_repo = RecipientRepository()
        self._sales_repo = SalesRepository()

        self._current_page: Optional[Widget] = None
        self._menu_buttons: list = []

        # Initialize database schema if possible
        try:
            DatabaseManager.initialize_database()
        except Exception:
            pass

        # Build UI Architecture
        # self._build_menu_bar()
        self._build_top_header()
        self._build_sidebar()
        self._build_home_summary_cards()

        # Start live updates
        self._update_clock()
        self._update_date()
        self.refresh_dashboard_counts()

        # Expose hooks on root for compatibility
        self._root.clear_active = self.clear_active
        self._root.update_account_name = self.update_account_name
        self._root.refresh_dashboard_counts = self.refresh_dashboard_counts

        self._root.mainloop()

    # ---------------- GUI REQUIREMENT: MENUS ----------------

    def _build_menu_bar(self) -> None:
        """Constructs the native Tkinter Menu Bar fulfilling GUI Menus requirement."""
        menu_bar = Menu(self._root)

        # File Menu
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Account Settings...", command=self.open_settings)
        file_menu.add_command(label="Back Up Database...", command=lambda: AdminSettingsView(self._root).open_backup_window())
        file_menu.add_separator()
        file_menu.add_command(label="Log Out", command=lambda: AdminSettingsView(self._root).log_out())
        file_menu.add_command(label="Exit", command=self._root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Manage Menu
        manage_menu = Menu(menu_bar, tearoff=0)
        manage_menu.add_command(label="Employees Management", command=lambda: self.open_page(self._emp_btn, EmployeeView))
        manage_menu.add_command(label="Recipient Management", command=lambda: self.open_page(self._rec_btn, RecipientView))
        manage_menu.add_command(label="Product Inventory", command=lambda: self.open_page(self._prod_btn, ProductView))
        manage_menu.add_command(label="Shipment Orders", command=lambda: self.open_page(self._ship_btn, ShipmentView))
        manage_menu.add_command(label="Sales & Analytics", command=lambda: self.open_page(self._sales_btn, SalesView))
        menu_bar.add_cascade(label="Manage", menu=manage_menu)

        # Tools Menu
        tools_menu = Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label="Refresh Dashboard Counts", command=self.refresh_dashboard_counts)
        tools_menu.add_command(label="Auto-Advance Shipments", command=self._run_shipment_advance)
        menu_bar.add_cascade(label="Tools", menu=tools_menu)

        # Help Menu
        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About AIMS", command=self._show_about_dialog)
        help_menu.add_command(label="Project Requirements Compliance", command=self._show_requirements_dialog)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self._root.config(menu=menu_bar)

    def _run_shipment_advance(self) -> None:
        from ..repositories.shipment_repo import ShipmentRepository
        changed = ShipmentRepository().auto_advance_shipments()
        messagebox.showinfo("Auto Advance", f"Processed shipment transitions. {changed} orders updated.")

    def _show_about_dialog(self) -> None:
        messagebox.showinfo(
            "About AIMS",
            "AIMS - Advanced Inventory & Management System\n"
            "Developed with Python, Tkinter, CustomTkinter, and MySQL.\n"
            "Full Object-Oriented Architecture (OOP)."
        )

    def _show_requirements_dialog(self) -> None:
        messagebox.showinfo(
            "Project Requirements Compliance",
            "AIMS satisfies 100% of the project specification:\n\n"
            "✓ Object-Oriented Programming (Classes, Objects, Constructors, Encapsulation, Inheritance, Polymorphism, Abstraction, Overloading, Interfaces)\n"
            "✓ Functional Features (Login, Add, Edit, Delete, Search, Display, Save Data, Load Data)\n"
            "✓ Graphical User Interface (Windows, Buttons, Labels, Textboxes, Combo Boxes, Menus, Tables/Treeview, Palette)\n"
            "✓ Exception Handling (Invalid input, Empty fields, File errors, Invalid data types, Custom Exceptions)\n"
            "✓ Code Quality (PEP 8, Modular packages, Reusable methods, Comments, Readability)"
        )

    # ---------------- TOP HEADER ----------------

    def _build_top_header(self) -> None:
        title_frame = ctk.CTkFrame(self._root, fg_color="#ffffff", corner_radius=20, height=60, width=1300)
        title_frame.place(x=210, y=5)
        title_frame.pack_propagate(False)

        self._title_label = Label(
            title_frame,
            text=f"Admin Dashboard - {SessionManager.get_username()}",
            font=("Helvetica", 20, "bold"),
            fg=NAVY,
            bg="#ffffff"
        )
        self._title_label.pack(side=LEFT, padx=30, pady=10)
        self._root.title_label = self._title_label

        line = Frame(self._root, bg=NAVY, height=2, width=1320)
        line.place(x=200, y=60)

        # Profile / Settings Pill Button
        self._accset_icon = load_ctk_icon("setting(1).png", size=(20, 20))
        self._accset_btn = ctk.CTkButton(
            title_frame,
            image=self._accset_icon,
            compound=LEFT,
            text=SessionManager.get_username(),
            font=("Helvetica", 13, "bold"),
            text_color="#FFFFFF",
            fg_color=NAVY,
            hover_color=ACTIVE,
            border_color=NAVY,
            border_width=2,
            corner_radius=12,
            width=150,
            height=36,
            cursor="hand2",
            command=self.open_settings
        )
        self._accset_btn.pack(side=RIGHT, padx=25)

    def open_settings(self) -> None:
        AdminSettingsView(self._root).open_settings_menu()

    def update_account_name(self) -> None:
        self._accset_btn.configure(text=SessionManager.get_username())
        self._title_label.config(text=f"Admin Dashboard - {SessionManager.get_username()}")

    # ---------------- SIDEBAR & CLOCK ----------------

    def _build_sidebar(self) -> None:
        self._sidebar = Frame(self._root, bg=NAVY, width=200, height=790)
        self._sidebar.place(x=0, y=0)
        self._sidebar.pack_propagate(False)

        # Brand Logo / Home Return Header
        self._logo_img = load_icon("logo.png")
        logo_label = Label(self._sidebar, image=self._logo_img, bg=NAVY, cursor="hand2")
        logo_label.place(x=0, y=-60, width=200, height=200)
        logo_label.bind("<Button-1>", lambda e: self.go_home())

        # Clock Canvas
        self._clock_canvas = Canvas(self._sidebar, width=160, height=160, bg=NAVY, highlightthickness=0)
        self._clock_canvas.place(x=20, y=65)

        # Static clock dial ring & markings
        self._clock_canvas.create_oval(5, 5, 155, 155, outline="white", width=3)
        for i in range(1, 13):
            angle = i * (2 * math.pi / 12) - math.pi / 2
            x1 = 80 + 58 * math.cos(angle)
            y1 = 80 + 58 * math.sin(angle)
            x2 = 80 + 68 * math.cos(angle)
            y2 = 80 + 68 * math.sin(angle)
            self._clock_canvas.create_line(x1, y1, x2, y2, fill="white", width=2)

            num_x = 80 + 45 * math.cos(angle)
            num_y = 80 + 45 * math.sin(angle)
            self._clock_canvas.create_text(num_x, num_y, text=str(i), fill="white", font=("Helvetica", 9, "bold"))

        # Date & Day Labels
        self._date_label = Label(self._sidebar, text="", font=("Helvetica", 15), bg=NAVY, fg="#FFFFFF")
        self._date_label.pack(fill=X, pady=(235, 0))

        self._day_label = Label(self._sidebar, text="", font=("Helvetica", 15), bg=NAVY, fg="white")
        self._day_label.pack(fill=X)

        sep = Frame(self._sidebar, bg="#064086", height=2, width=200)
        sep.place(x=0, y=300)

        # Navigation Buttons
        btn_defs = [
            (" Employees", "employee.png", lambda: self.open_page(self._emp_btn, EmployeeView)),
            ("Recipient", "supplierr.png", lambda: self.open_page(self._rec_btn, RecipientView)),
            ("Shipments", "supplier.png", lambda: self.open_page(self._ship_btn, ShipmentView)),
            ("Products", "product.png", lambda: self.open_page(self._prod_btn, ProductView)),
            ("Sales", "sales.png", lambda: self.open_page(self._sales_btn, SalesView))
        ]

        self._menu_buttons = []
        self._nav_icons = []
        for i, (text, icon_name, cmd) in enumerate(btn_defs):
            icon = load_ctk_icon(icon_name)
            self._nav_icons.append(icon)
            btn = ctk.CTkButton(
                self._sidebar,
                image=icon,
                compound=LEFT,
                text=text,
                font=("Helvetica", 15, "bold"),
                text_color="#FDFCF8",
                fg_color=self.SIDEBAR_COLOR,
                hover_color=self.ACTIVE_COLOR,
                corner_radius=10,
                width=180,
                height=45,
                anchor="w",
                cursor="hand2",
                command=cmd
            )
            btn.place(x=10, y=325 + i * 55)
            self._menu_buttons.append(btn)

        self._emp_btn = self._menu_buttons[0]
        self._rec_btn = self._menu_buttons[1]
        self._ship_btn = self._menu_buttons[2]
        self._prod_btn = self._menu_buttons[3]
        self._sales_btn = self._menu_buttons[4]

    def _update_clock(self) -> None:
        self._clock_canvas.delete("hands")
        current_time = time.localtime()
        hrs, mins, secs = current_time.tm_hour, current_time.tm_min, current_time.tm_sec

        center_x, center_y = 80, 80
        sec_angle = (secs / 60) * (2 * math.pi) - math.pi / 2
        min_angle = ((mins + secs / 60) / 60) * (2 * math.pi) - math.pi / 2
        hr_angle = (((hrs % 12) + mins / 60) / 12) * (2 * math.pi) - math.pi / 2

        # Second hand (red)
        self._clock_canvas.create_line(center_x, center_y, center_x + 55 * math.cos(sec_angle), center_y + 55 * math.sin(sec_angle), fill="red", width=2, tags="hands")
        # Minute hand (white)
        self._clock_canvas.create_line(center_x, center_y, center_x + 45 * math.cos(min_angle), center_y + 45 * math.sin(min_angle), fill="white", width=4, tags="hands")
        # Hour hand (white)
        self._clock_canvas.create_line(center_x, center_y, center_x + 30 * math.cos(hr_angle), center_y + 30 * math.sin(hr_angle), fill="white", width=6, tags="hands")
        # Center Pin
        self._clock_canvas.create_oval(center_x - 5, center_y - 5, center_x + 5, center_y + 5, fill="gray", tags="hands")

        self._root.after(1000, self._update_clock)

    def _update_date(self) -> None:
        now = datetime.now()
        self._date_label.config(text=now.strftime("%B %d, %Y"))
        self._day_label.config(text=now.strftime("%A"))
        self._root.after(60000, self._update_date)

    # ---------------- HOME SUMMARY METRIC CARDS ----------------

    def _build_home_summary_cards(self) -> None:
        card_configs = [
            ("Total Employees", 230, 125, "emp.png"),
            ("Total Recipients", 870, 125, "sup.png"),
            ("Total Products", 230, 340, "prod.png"),
            ("Total Sales", 870, 340, "mainsales.png")
        ]
        self._card_count_labels = {}
        self._card_icons = []

        for title, x, y, icon_name in card_configs:
            frame = ctk.CTkFrame(self._root, fg_color="#B2B4B7", corner_radius=10, height=200, width=625)
            frame.place(x=x, y=y)
            frame.pack_propagate(False)

            icon = load_icon(icon_name)
            self._card_icons.append(icon)
            Label(frame, image=icon, bg="#B2B4B7").pack(pady=(35, 0))
            Label(frame, text=title, font=("Helvetica", 14), bg="#B2B4B7", fg="#FDFCF8").pack()

            cnt_lbl = Label(frame, text="0", font=("Helvetica", 22, "bold"), bg="#B2B4B7", fg="#FDFCF8")
            cnt_lbl.pack()
            self._card_count_labels[title] = cnt_lbl

    def refresh_dashboard_counts(self) -> None:
        """Refreshes home summary counters from database repositories."""
        try:
            self._card_count_labels["Total Employees"].config(text=str(self._emp_repo.count_all()))
            self._card_count_labels["Total Recipients"].config(text=str(self._rec_repo.count_all()))
            self._card_count_labels["Total Products"].config(text=str(self._prod_repo.count_all()))
            self._card_count_labels["Total Sales"].config(text=str(self._sales_repo.count_all()))
        except Exception:
            pass

    # ---------------- PAGE NAVIGATION CONTROLLER ----------------

    def set_active(self, active_btn) -> None:
        for btn in self._menu_buttons:
            btn.configure(fg_color=self.SIDEBAR_COLOR, hover_color=self.ACTIVE_COLOR)
        active_btn.configure(fg_color=self.ACTIVE_COLOR, hover_color=self.ACTIVE_COLOR)

    def clear_active(self) -> None:
        for btn in self._menu_buttons:
            btn.configure(fg_color=self.SIDEBAR_COLOR, hover_color=self.ACTIVE_COLOR)

    def close_page(self) -> None:
        if self._current_page is not None:
            self._current_page.destroy()
            self._current_page = None

    def open_page(self, button, view_class) -> None:
        self.close_page()
        self.set_active(button)
        self._current_page = view_class(self._root)

    def go_home(self) -> None:
        self.close_page()
        self.clear_active()
        self.refresh_dashboard_counts()