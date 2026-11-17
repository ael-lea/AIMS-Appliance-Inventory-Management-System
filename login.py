"""
AIMS Login and Authentication Application.
Demonstrates:
- Object-Oriented Programming (Classes: LoginWindow, CreateAccountDialog, ForgotPasswordDialog, AdminVerificationDialog, DatePicker, Dropdown, PopupField)
- Constructors (__init__)
- Encapsulation (Window widgets, glass card geometry, authentication controller)
- Inheritance (BaseAuthDialog inherits from Toplevel; Dropdown and DatePicker inherit from PopupField)
- Polymorphism (Overriding render(), handle_submit(), dialog lifecycles)
- Exception Handling (EmptyFieldException, InvalidDataTypeException, ValidationError, AuthenticationException, DatabaseOperationException)
- Graphical User Interface (Frosted glass canvas, CustomTkinter fields, Show/Hide password toggle, Role switch, DatePicker, Dropdowns)
"""
import calendar
import importlib
import importlib.util
import math
import os
import string
import sys
from abc import ABC, abstractmethod
from datetime import date
from tkinter import *
from tkinter import messagebox
import customtkinter as ctk
import pymysql
from PIL import Image as PILImage, ImageDraw, ImageFilter, ImageOps, ImageTk
from tkinter import font as tkfont

import session
from auth import get_connection, hash_password, verify_password
from core_exceptions import (
    AIMSException,
    EmptyFieldException,
    InvalidDataTypeException,
    ValidationError,
    AuthenticationException,
    DatabaseOperationException
)

# ---------------- CONFIGURATION & DESIGN TOKENS ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

ICON_DIR = os.path.join(BASE_DIR, 'photos') + os.sep
BG_PATH = os.path.join(ICON_DIR, 'background.jpg')
DASHBOARDS = {'Admin': 'Admin.dashboard', 'Cashier': 'cashier.ui.app'}

NAVY = '#012148'
BLUE_HOVER = '#243372'
BLACK = "#000000"
MUTED = '#475569'
FIELD_BG = '#F3F5F9'
FIELD_BORDER = '#C3CCDA'
PLACEHOLDER = '#5F6B7A'

WIN_W, WIN_H = 1520, 790
CARD_W, CARD_H, CARD_R = 600, 710, 40
CARD_X = 793
CARD_Y = (WIN_H - CARD_H) // 2
FORM_W = 480
FORM_X = 60

SHOW_SPHERES = False
SPHERES = [(1405, 55, 115), (780, 835, 175), (690, 130, 38)]
ACCENT = '#012148'
ACCENT_HOVER = '#243372'
GLASS_PLACEHOLDER = '#DCE4F4'
ASTERISK = '#FF7A7A'
MIN_PASSWORD_LENGTH = 8
CONTACT_MAX_LENGTH = 10


# ---------------- UTILITY FUNCTIONS ----------------

def check_password_rules(password: str) -> list:
    """Return a list of validation rules the password violates."""
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f'At least {MIN_PASSWORD_LENGTH} characters')
    if not any(c.islower() for c in password):
        problems.append('At least one lowercase letter (a-z)')
    if not any(c.isupper() for c in password):
        problems.append('At least one uppercase letter (A-Z)')
    if not any(c in string.punctuation for c in password):
        problems.append('At least one special character (! @ # $ % ...)')
    return problems


def validate_empid(value: str) -> bool:
    return value == '' or (value.isascii() and value.isdigit())


def validate_contact(value: str) -> bool:
    return value == '' or (value.isascii() and value.isdigit() and len(value) <= CONTACT_MAX_LENGTH)


def validate_name(value: str) -> bool:
    return value == '' or all(char.isalpha() or char.isspace() for char in value)


def validate_salary(value: str) -> bool:
    if value == '' or value == '.':
        return True
    if value.count('.') > 1:
        return False
    value_without_dot = value.replace('.', '', 1)
    return (value_without_dot.isascii() and value_without_dot.isdigit()) or value.endswith('.')


def latest_birth_date(min_age=18) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - min_age)
    except ValueError:
        return today.replace(year=today.year - min_age, day=28)


def typing_rule(widget, placeholder, rule):
    def check(value):
        return value == placeholder or rule(value)
    return {'validate': 'key', 'validatecommand': (widget.register(check), '%P')}


# ---------------- PILLOW GLASS RENDERING HELPERS ----------------

def cover_resize(img, w, h):
    scale = max(w / img.width, h / img.height)
    img = img.resize((math.ceil(img.width * scale), math.ceil(img.height * scale)), PILImage.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def make_sphere(r):
    s = 3
    layer = PILImage.new('RGBA', (2 * r * s, 2 * r * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    edge, light = (22, 44, 140), (150, 190, 255)
    steps = r * s
    for i in range(steps):
        t = i / steps
        rad = r * s * (1 - t)
        c = r * s - 0.38 * r * s * t
        k = t ** 1.4
        col = tuple(int(edge[j] + (light[j] - edge[j]) * k) for j in range(3))
        d.ellipse((c - rad, c - rad, c + rad, c + rad), fill=col + (255,))
    return layer.resize((2 * r, 2 * r), PILImage.LANCZOS)


def rounded_mask(w, h, radius):
    s = 4
    m = PILImage.new('L', (w * s, h * s), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius * s, fill=255)
    return m.resize((w, h), PILImage.LANCZOS)


def make_glass_background(bg_path):
    try:
        base = cover_resize(PILImage.open(bg_path).convert('RGB'), WIN_W, WIN_H)
    except (FileNotFoundError, OSError):
        base = PILImage.linear_gradient('L').resize((WIN_W, WIN_H))
        base = ImageOps.colorize(base, (4, 12, 32), (60, 90, 140))
    base = base.convert('RGBA')

    if SHOW_SPHERES:
        for cx, cy, r in SPHERES:
            base.alpha_composite(make_sphere(r), (cx - r, cy - r))

    x0, y0, x1, y1 = CARD_X, CARD_Y, CARD_X + CARD_W, CARD_Y + CARD_H
    pad = 60
    px0, py0 = max(0, x0 - pad), max(0, y0 - pad)
    px1, py1 = min(WIN_W, x1 + pad), min(WIN_H, y1 + pad)
    blurred = base.crop((px0, py0, px1, py1)).filter(ImageFilter.GaussianBlur(40))
    card = blurred.crop((x0 - px0, y0 - py0, x0 - px0 + CARD_W, y0 - py0 + CARD_H))
    card.alpha_composite(PILImage.new('RGBA', card.size, (8, 22, 58, 150)))
    card.alpha_composite(PILImage.new('RGBA', card.size, (255, 255, 255, 22)))
    sheen = ImageOps.invert(PILImage.linear_gradient('L').resize(card.size)).point(lambda v: int(v * 0.12))
    shine = PILImage.new('RGBA', card.size, (255, 255, 255, 255))
    shine.putalpha(sheen)
    card.alpha_composite(shine)

    shadow = PILImage.new('RGBA', (WIN_W, WIN_H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0, y0 + 18, x1, y1 + 18), CARD_R, fill=(0, 0, 0, 120))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))

    base.paste(card, (x0, y0), rounded_mask(CARD_W, CARD_H, CARD_R))
    s = 4
    border = PILImage.new('RGBA', (CARD_W * s, CARD_H * s), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle((1, 1, CARD_W * s - 2, CARD_H * s - 2), CARD_R * s,
                                             outline=(255, 255, 255, 120), width=2 * s)
    base.alpha_composite(border.resize((CARD_W, CARD_H), PILImage.LANCZOS), (x0, y0))
    return base.convert('RGB')


def tone(img, x, y, w=40, h=40, lighten=0.0):
    box = (max(0, x - w // 2), max(0, y - h // 2), min(img.width, x + w // 2), min(img.height, y + h // 2))
    r, g, b = img.crop(box).resize((1, 1), PILImage.BOX).getpixel((0, 0))
    r, g, b = (int(c + (255 - c) * lighten) for c in (r, g, b))
    return '#%02x%02x%02x' % (r, g, b)


def white_icon(path):
    if not os.path.isfile(path):
        return None
    try:
        img = PILImage.open(path).convert('RGBA')
        alpha = img.getchannel('A')
        if alpha.getextrema()[0] == 255:
            alpha = ImageOps.invert(img.convert('L'))
        white = PILImage.new('RGBA', img.size, (255, 255, 255, 255))
        white.putalpha(alpha)
        return ImageTk.PhotoImage(white)
    except Exception:
        return None


# ---------------- POPUP FIELDS: DROPDOWN & DATEPICKER ----------------

class PopupField(ctk.CTkFrame):
    """Abstract Base Class for dropdown and date picker popups."""
    HOVER = '#E4E9F2'
    DISABLED = '#A3ACB9'

    def __init__(self, master, width=400, height=44, text='', text_color=BLACK):
        super().__init__(master, width=width, height=height, corner_radius=10, border_width=1,
                         border_color=FIELD_BORDER, fg_color=FIELD_BG)
        self.popup = None

        self.text = ctk.CTkLabel(self, text=text, anchor='w', text_color=text_color,
                                 font=ctk.CTkFont('Segoe UI', 14))
        self.text.place(x=12, rely=0.5, anchor='w')

        self.arrow = ctk.CTkFrame(self, width=42, height=height - 4, corner_radius=8, fg_color=NAVY, cursor='hand2')
        self.arrow.place(x=width - 44, y=2)
        self.chevron = Canvas(self.arrow, width=24, height=24, bg=NAVY, highlightthickness=0, bd=0)
        self.chevron.place(relx=0.5, rely=0.5, anchor='center')
        self.chevron.create_line(6, 9, 12, 15, 18, 9, fill='white', width=2, capstyle='round', joinstyle='round')

        for w in (self, self.text, self.arrow, self.chevron):
            w.bind('<Button-1>', lambda e: self.toggle())
        for w in (self.arrow, self.chevron):
            w.bind('<Enter>', lambda e: self._hover(BLUE_HOVER))
            w.bind('<Leave>', lambda e: self._hover(NAVY))

        self.winfo_toplevel().bind('<Button-1>', self._outside_click, add='+')

    def _hover(self, color):
        self.arrow.configure(fg_color=color, cursor='hand2')
        self.chevron.configure(bg=color)

    def toggle(self):
        if self.popup is not None:
            self.close()
        else:
            self.open()

    def open(self):
        self.popup = Toplevel(self.winfo_toplevel())
        self.popup.overrideredirect(True)
        self.popup.attributes('-topmost', True)
        self.popup.config(bg=FIELD_BORDER)
        self.popup.bind('<Escape>', lambda e: self.close())
        self.body = Frame(self.popup, bg='white')
        self.body.pack(fill='both', expand=True, padx=1, pady=1)
        self.render()
        self.popup.lift()
        self.popup.focus_set()

    def close(self):
        if self.popup is not None:
            try:
                self.popup.destroy()
            except TclError:
                pass
            self.popup = None

    def _outside_click(self, event):
        if self.popup is None:
            return
        clicked, mine = str(event.widget), str(self)
        if clicked == mine or clicked.startswith(mine + '.'):
            return
        self.close()

    def _later(self, command):
        self.after(1, command)

    def render(self):
        raise NotImplementedError

    def _place(self):
        self.popup.update_idletasks()
        w = max(self.winfo_width(), self.popup.winfo_reqwidth())
        h = self.popup.winfo_reqheight()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        if y + h > self.winfo_screenheight():
            y = max(0, self.winfo_rooty() - h - 4)
        self.popup.geometry(f'{w}x{h}+{x}+{y}')


class Dropdown(PopupField):
    """Dropdown list component."""
    def __init__(self, master, values, placeholder, width=400, height=44):
        super().__init__(master, width=width, height=height, text=placeholder, text_color=PLACEHOLDER)
        self.values = list(values)
        self.placeholder = placeholder
        self.value = placeholder

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        self.text.configure(text=value, text_color=PLACEHOLDER if value == self.placeholder else BLACK)

    def pick(self, value):
        self.set(value)
        self.close()

    def render(self):
        if self.popup is None:
            return
        for child in self.body.winfo_children():
            child.destroy()
        for value in self.values:
            selected = (value == self.value)
            row = Label(self.body, text=value, anchor='w', padx=14, pady=9, cursor='hand2',
                        bg=self.HOVER if selected else 'white', fg=BLACK,
                        font=('Segoe UI', 10, 'bold' if selected else 'normal'))
            row.pack(fill='x')
            row.bind('<Button-1>', lambda e, v=value: self._later(lambda: self.pick(v)))
            if not selected:
                row.bind('<Enter>', lambda e, r=row: r.config(bg=self.HOVER))
                row.bind('<Leave>', lambda e, r=row: r.config(bg='white'))
        self._place()


class DatePicker(PopupField):
    """Calendar DatePicker component."""
    MONTHS = list(calendar.month_name)[1:]
    MONTHS_SHORT = list(calendar.month_abbr)[1:]
    DAY_NAMES = ('Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa')

    def __init__(self, master, width=400, height=44, default=None, mindate=None, maxdate=None):
        mindate = mindate or date(1900, 1, 1)
        maxdate = maxdate or date(2100, 12, 31)
        value = min(max(default or date.today(), mindate), maxdate)
        super().__init__(master, width=width, height=height, text=value.strftime('%Y-%m-%d'))
        self.mindate, self.maxdate, self.value = mindate, maxdate, value
        self.mode = 'days'

    def get_date(self):
        return self.value

    def set_date(self, d):
        self.value = min(max(d, self.mindate), self.maxdate)
        self.text.configure(text=self.value.strftime('%Y-%m-%d'))

    def open(self):
        self.view_year, self.view_month = self.value.year, self.value.month
        self.mode = 'days'
        super().open()

    def _allowed(self, d):
        return self.mindate <= d <= self.maxdate

    def _month_ok(self, y, m):
        return (self.mindate.year, self.mindate.month) <= (y, m) <= (self.maxdate.year, self.maxdate.month)

    def _year_ok(self, y):
        return self.mindate.year <= y <= self.maxdate.year

    def _shift_month(self, delta):
        index = self.view_year * 12 + (self.view_month - 1) + delta
        y, m = index // 12, index % 12 + 1
        if self._month_ok(y, m):
            self.view_year, self.view_month = y, m
            self.render()

    def _shift_year(self, delta):
        if self._year_ok(self.view_year + delta):
            self.view_year += delta
            self.render()

    def _shift_page(self, delta):
        start = self.year_start + 12 * delta
        if start + 11 >= self.mindate.year and start <= self.maxdate.year:
            self.year_start = start
            self.render()

    def _set_mode(self, mode):
        self.mode = mode
        if mode == 'years':
            self.year_start = self.view_year - self.view_year % 12
        self.render()

    def _pick_year(self, y):
        self.view_year = y
        self.mode = 'months'
        self.render()

    def _pick_month(self, m):
        self.view_month = m
        self.mode = 'days'
        self.render()

    def pick(self, d):
        self.set_date(d)
        self.close()

    def render(self):
        if self.popup is None:
            return
        for child in self.body.winfo_children():
            child.destroy()
        if self.mode == 'days':
            self._render_days()
        elif self.mode == 'months':
            self._render_months()
        else:
            self._render_years()
        self._place()

    def _header(self, title, prev_cmd, next_cmd, prev_ok, next_ok, title_cmd=None):
        bar = Frame(self.body, bg=NAVY)
        bar.pack(fill='x')
        for side, symbol, cmd, ok in (('left', '\u2039', prev_cmd, prev_ok), ('right', '\u203a', next_cmd, next_ok)):
            arrow = Label(bar, text=symbol, bg=NAVY, fg='white' if ok else '#58709A',
                        font=('Segoe UI', 18, 'bold'), padx=16)
            arrow.pack(side=side)
            if ok:
                arrow.config(cursor='hand2')
                arrow.bind('<Button-1>', lambda e, c=cmd: self._later(c))
        heading = Label(bar, text=title, bg=NAVY, fg='white', font=('Segoe UI', 12, 'bold'), pady=10)
        heading.pack(side='left', expand=True, fill='x')
        if title_cmd:
            heading.config(cursor='hand2')
            heading.bind('<Button-1>', lambda e: self._later(title_cmd))

    def _grid(self, columns):
        grid = Frame(self.body, bg='white', padx=8, pady=6)
        grid.pack(fill='both', expand=True)
        for c in range(columns):
            grid.grid_columnconfigure(c, weight=1, uniform='c')
        return grid

    def _cell(self, parent, text, row, col, command=None, selected=False, disabled=False, bold=False, pady=8):
        bg = NAVY if selected else 'white'
        fg = 'white' if selected else (self.DISABLED if disabled else BLACK)
        weight = 'bold' if (bold or selected) else 'normal'
        cell = Label(parent, text=text, bg=bg, fg=fg, font=('Segoe UI', 11, weight), pady=pady)
        cell.grid(row=row, column=col, sticky='nsew', padx=2, pady=2)
        if command is not None and not disabled:
            cell.config(cursor='hand2')
            cell.bind('<Button-1>', lambda e: self._later(command))
            if not selected:
                cell.bind('<Enter>', lambda e: cell.config(bg=self.HOVER))
                cell.bind('<Leave>', lambda e: cell.config(bg='white'))
        return cell

    def _render_days(self):
        y, m = self.view_year, self.view_month
        prev_index, next_index = y * 12 + (m - 1) - 1, y * 12 + (m - 1) + 1
        self._header(f'{self.MONTHS[m - 1]} {y}',
                     lambda: self._shift_month(-1), lambda: self._shift_month(1),
                     self._month_ok(prev_index // 12, prev_index % 12 + 1),
                     self._month_ok(next_index // 12, next_index % 12 + 1),
                     title_cmd=lambda: self._set_mode('months'))
        grid = self._grid(7)
        for c, name in enumerate(self.DAY_NAMES):
            Label(grid, text=name, bg='white', fg=MUTED, font=('Segoe UI', 10, 'bold'), pady=4).grid(
                row=0, column=c, sticky='nsew')
        today = date.today()
        for r, week in enumerate(calendar.Calendar(firstweekday=6).monthdatescalendar(y, m), start=1):
            for c, d in enumerate(week):
                if d.month != m:
                    continue
                self._cell(grid, str(d.day), r, c, command=lambda d=d: self.pick(d),
                           selected=(d == self.value), disabled=not self._allowed(d), bold=(d == today))

    def _render_months(self):
        y = self.view_year
        self._header(str(y),
                     lambda: self._shift_year(-1), lambda: self._shift_year(1),
                     self._year_ok(y - 1), self._year_ok(y + 1),
                     title_cmd=lambda: self._set_mode('years'))
        grid = self._grid(3)
        for i, name in enumerate(self.MONTHS_SHORT):
            month = i + 1
            self._cell(grid, name, i // 3, i % 3, command=lambda month=month: self._pick_month(month),
                       selected=((y, month) == (self.value.year, self.value.month)),
                       disabled=not self._month_ok(y, month), pady=14)

    def _render_years(self):
        start = self.year_start
        self._header(f'{start} - {start + 11}',
                     lambda: self._shift_page(-1), lambda: self._shift_page(1),
                     start - 1 >= self.mindate.year, start + 12 <= self.maxdate.year)
        grid = self._grid(3)
        for i in range(12):
            year = start + i
            self._cell(grid, str(year), i // 3, i % 3, command=lambda year=year: self._pick_year(year),
                       selected=(year == self.value.year), disabled=not self._year_ok(year), pady=14)


# ---------------- BASE MODAL DIALOG CLASS ----------------

class BaseAuthDialog(Toplevel, ABC):
    """
    Abstract Base Class for modal dialogs.
    Demonstrates Abstraction and Inheritance from Toplevel.
    """

    def __init__(self, parent_window, title: str, geometry: str):
        super().__init__(parent_window)
        self.title(title)
        self.geometry(geometry)
        self.resizable(False, False)
        self.config(bg='white')
        self.transient(parent_window)
        self._parent = parent_window
        self.build_ui()
        self.grab_set()

        self.build_ui()

    @abstractmethod
    def build_ui(self) -> None:
        pass


class ForgotPasswordDialog(BaseAuthDialog):
    """
    Password Reset Dialog.
    Demonstrates Inheritance and Exception Handling.
    """

    def __init__(self, parent_window):
        super().__init__(parent_window, title='Change Password', geometry='480x720+520+30')

    def build_ui(self) -> None:
        RX, RW = 50, 380

        def field_label(text, y):
            row = Frame(self, bg='white')
            row.place(x=RX, y=y)
            Label(row, text=text, font=('Segoe UI', 12, 'bold'), bg='white', fg=BLACK).pack(side='left')
            Label(row, text=' *', font=('Segoe UI', 12, 'bold'), bg='white', fg='#C62828').pack(side='left')

        def reset_entry(y, placeholder, show='', rule=None):
            options = typing_rule(self, placeholder, rule) if rule else {}
            entry = ctk.CTkEntry(
                self, width=RW, height=50, corner_radius=10, border_width=1,
                border_color=FIELD_BORDER, fg_color=FIELD_BG, text_color=BLACK, show=show,
                placeholder_text=placeholder, placeholder_text_color=PLACEHOLDER,
                font=ctk.CTkFont('Segoe UI', 14), **options)
            entry.place(x=RX, y=y)
            return entry

        Label(self, text='Reset Password', font=('Segoe UI', 26, 'bold'), bg='white', fg=BLACK).place(x=RX, y=40)
        Label(self, text='Verify your details, then choose a new password.',
              font=('Segoe UI', 11), bg='white', fg=MUTED).place(x=RX, y=90)

        field_label('Employee ID', 130)
        self._empid_entry = reset_entry(158, 'Enter your employee ID', rule=validate_empid)

        field_label('Username', 228)
        self._username_entry = reset_entry(256, 'Enter your username', rule=validate_name)

        field_label('Email', 326)
        self._email_entry = reset_entry(354, 'Enter the email saved on your account')

        field_label('New Password', 424)
        self._new_entry = reset_entry(452, 'Input new password', show='*')

        field_label('Confirm Password', 522)
        self._confirm_entry = reset_entry(550, 'Confirm new password', show='*')

        ctk.CTkButton(
            self, text='Submit', width=RW, height=54, corner_radius=10,
            fg_color='#012148', hover_color=BLUE_HOVER, text_color='white',
            font=ctk.CTkFont('Segoe UI', 17, 'bold'), command=self.submit_change
        ).place(x=RX, y=636)

    def submit_change(self) -> None:
        empid = self._empid_entry.get().strip()
        username = self._username_entry.get().strip()
        email = self._email_entry.get().strip()
        new_password = self._new_entry.get()
        confirm_password = self._confirm_entry.get()

        try:
            if not empid or not username or not email or not new_password or not confirm_password:
                raise EmptyFieldException('All fields are required.')
            if not empid.isdigit():
                raise InvalidDataTypeException('Employee ID must contain digits only.')
            if new_password != confirm_password:
                raise ValidationError('New Password and Confirm Password should be the same.')

            problems = check_password_rules(new_password)
            if problems:
                raise ValidationError('The password must have:\n\n- ' + '\n- '.join(problems))

            con = None
            try:
                con = get_connection()
                cur = con.cursor()
                cur.execute('SELECT empid FROM employee_data WHERE empid = %s AND name = %s AND email = %s',
                            (empid, username, email))
                if cur.fetchone() is None:
                    raise AuthenticationException('The details you entered do not match our records.')

                cur.execute('UPDATE employee_data SET password = %s WHERE empid = %s',
                            (hash_password(new_password), empid))
                con.commit()
                messagebox.showinfo('Success', 'Password changed successfully', parent=self)
                self.destroy()

            except pymysql.MySQLError as e:
                raise DatabaseOperationException(str(e))
            finally:
                if con is not None:
                    con.close()

        except (EmptyFieldException, InvalidDataTypeException, ValidationError, AuthenticationException, DatabaseOperationException) as err:
            messagebox.showerror('Error', str(err.message), parent=self)


class AdminVerificationDialog(BaseAuthDialog):
    """Admin credentials verification step before account creation."""

    def __init__(self, parent_window, on_success_callback):
        self._on_success = on_success_callback
        super().__init__(parent_window, title='Admin Verification', geometry='480x470+520+120')

    def build_ui(self) -> None:
        RX, RW = 50, 380

        def lbl(text, y):
            row = Frame(self, bg='white')
            row.place(x=RX, y=y)
            Label(row, text=text, font=('Segoe UI', 12, 'bold'), bg='white', fg=BLACK).pack(side='left')
            Label(row, text=' *', font=('Segoe UI', 12, 'bold'), bg='white', fg='#C62828').pack(side='left')

        def ent(y, placeholder, show='', rule=None):
            options = typing_rule(self, placeholder, rule) if rule else {}
            e = ctk.CTkEntry(self, width=RW, height=50, corner_radius=10, border_width=1,
                             border_color=FIELD_BORDER, fg_color=FIELD_BG, text_color=BLACK, show=show,
                             placeholder_text=placeholder, placeholder_text_color=PLACEHOLDER,
                             font=ctk.CTkFont('Segoe UI', 14), **options)
            e.place(x=RX, y=y)
            return e

        Label(self, text='Admin Verification', font=('Segoe UI', 26, 'bold'), bg='white', fg=BLACK).place(x=RX, y=40)
        Label(self, text='Only an Admin can create new accounts.', font=('Segoe UI', 11), bg='white', fg=MUTED).place(x=RX, y=90)

        lbl('Admin Employee ID', 140)
        self._empid_entry = ent(168, 'Enter your employee ID', rule=validate_empid)
        lbl('Admin Password', 238)
        self._pw_entry = ent(266, 'Input your password', show='*')

        ctk.CTkButton(self, text='Continue', width=RW, height=54, corner_radius=10,
                      fg_color='#012148', hover_color=BLUE_HOVER, text_color='white',
                      font=ctk.CTkFont('Segoe UI', 17, 'bold'), command=self.verify).place(x=RX, y=352)

        self.bind('<Return>', lambda event: self.verify())
        self._empid_entry.focus()

    def verify(self) -> None:
        empid = self._empid_entry.get().strip()
        password = self._pw_entry.get()

        try:
            if not empid or not password:
                raise EmptyFieldException('All fields are required.')
            if not empid.isdigit():
                raise InvalidDataTypeException('Employee ID must contain digits only.')

            con = None
            try:
                con = get_connection()
                cur = con.cursor()
                cur.execute('SELECT role, password FROM employee_data WHERE empid = %s', (empid,))
                row = cur.fetchone()
            except pymysql.MySQLError as e:
                raise DatabaseOperationException(str(e))
            finally:
                if con is not None:
                    con.close()

            role = (row[0] or '').strip().capitalize() if row else ''
            password_ok = bool(row and row[1]) and verify_password(row[1], password)[0]

            if not password_ok or role != 'Admin':
                raise AuthenticationException('Admin verification failed. Only Admin accounts can create new accounts.')

            self.destroy()
            if self._on_success:
                self._on_success()

        except (EmptyFieldException, InvalidDataTypeException, AuthenticationException, DatabaseOperationException) as err:
            messagebox.showerror('Access Denied', str(err.message), parent=self)


class CreateAccountDialog(BaseAuthDialog):
    """
    Admin Account Activation Dialog.
    The person must ALREADY be listed in employee_data with the Admin role; nothing is inserted here.
    The details are checked against that row and the password is set so they can log in.
    """

    def __init__(self, parent_window):
        super().__init__(parent_window, title='Create Account', geometry='480x700+520+30')

    def build_ui(self) -> None:
        RX, RW = 50, 380

        def field_label(text, y):
            row = Frame(self, bg='white')
            row.place(x=RX, y=y)
            Label(row, text=text, font=('Segoe UI', 12, 'bold'), bg='white', fg=BLACK).pack(side='left')
            Label(row, text=' *', font=('Segoe UI', 12, 'bold'), bg='white', fg='#C62828').pack(side='left')

        def field_entry(y, placeholder, show='', rule=None):
            options = typing_rule(self, placeholder, rule) if rule else {}
            e = ctk.CTkEntry(self, width=RW, height=50, corner_radius=10, border_width=1,
                             border_color=FIELD_BORDER, fg_color=FIELD_BG, text_color=BLACK, show=show,
                             placeholder_text=placeholder, placeholder_text_color=PLACEHOLDER,
                             font=ctk.CTkFont('Segoe UI', 14), **options)
            e.place(x=RX, y=y)
            return e

        Label(self, text='Create Account', font=('Segoe UI', 26, 'bold'), bg='white', fg=BLACK).place(x=RX, y=30)
        Label(self, text='The admin must already be listed in the employee records.',
              font=('Segoe UI', 10), bg='white', fg=MUTED).place(x=RX, y=80)

        field_label('Employee ID', 120)
        self._empid_entry = field_entry(148, 'Enter the employee ID', rule=validate_empid)

        field_label('Name', 218)
        self._name_entry = field_entry(246, 'Enter full name', rule=validate_name)

        field_label('Email', 316)
        self._email_entry = field_entry(344, 'Enter the email saved on the record')

        field_label('Password', 414)
        self._pw_entry = field_entry(442, 'Create a password', show='*')
        Label(self, text=f'Min. {MIN_PASSWORD_LENGTH} characters, with uppercase, lowercase and a special character.',
              font=('Segoe UI', 9), bg='white', fg=MUTED).place(x=RX, y=498)

        field_label('Confirm Password', 524)
        self._confirm_entry = field_entry(552, 'Confirm your password', show='*')

        ctk.CTkButton(self, text='Create Account', width=RW, height=54, corner_radius=10,
                      fg_color='#012148', hover_color=BLUE_HOVER, text_color='white',
                      font=ctk.CTkFont('Segoe UI', 17, 'bold'), command=self.create_account).place(x=RX, y=620)

    def create_account(self) -> None:
        empid = self._empid_entry.get().strip()
        name = self._name_entry.get().strip()
        email = self._email_entry.get().strip()
        password = self._pw_entry.get()
        confirm = self._confirm_entry.get()

        try:
            if not empid or not name or not email or not password or not confirm:
                raise EmptyFieldException('All fields must be answered.')
            if not (empid.isascii() and empid.isdigit()):
                raise InvalidDataTypeException('Employee ID must contain digits only.')
            if not all(ch.isalpha() or ch.isspace() for ch in name):
                raise InvalidDataTypeException('Name must contain letters only.')
            if '@' not in email or '.' not in email.split('@')[-1]:
                raise InvalidDataTypeException('Enter a valid email address.')
            if password != confirm:
                raise ValidationError('Password and Confirm Password should be the same.')

            problems = check_password_rules(password)
            if problems:
                raise ValidationError('The password must have:\n\n- ' + '\n- '.join(problems))

            con = None
            try:
                con = get_connection()
                cur = con.cursor()
                cur.execute('SELECT empid, role, password FROM employee_data '
                            'WHERE empid = %s AND name = %s AND email = %s', (int(empid), name, email))
                row = cur.fetchone()
                if row is None:
                    raise ValidationError('No employee matches that ID, name and email.\n\n'
                                          'The admin must be added to the employee records first.')
                _, role, existing_password = row
                if (role or '').strip().capitalize() != 'Admin':
                    raise ValidationError(f"This employee's role is '{role or 'not set'}', not Admin.")
                if existing_password:
                    raise ValidationError('This admin already has an account.\n'
                                          'Use Forgot Password on the login screen if the password was forgotten.')

                cur.execute('UPDATE employee_data SET password = %s WHERE empid = %s',
                            (hash_password(password), int(empid)))
                con.commit()
                messagebox.showinfo('Success', f'Account created.\n\nEmployee ID: {empid}\nUse this ID to log in.', parent=self)
                self.destroy()

            except pymysql.MySQLError as e:
                raise DatabaseOperationException(str(e))
            finally:
                if con is not None:
                    con.close()

        except (EmptyFieldException, InvalidDataTypeException, ValidationError, DatabaseOperationException) as err:
            messagebox.showerror('Error', str(err.message), parent=self)

# ---------------- MAIN APPLICATION WINDOW CLASS ----------------

class LoginWindow:
    """Main login window: same layout as the original login screen, wrapped in a class."""

    SIDE_MARGIN = 48          # space above the logo = space under the footer = space left of the logo
    LEFT_CX = 390             # horizontal centre of the left side
    HL_X = 212                # left edge of the highlights list
    HIGHLIGHTS = (
        'Keep track of your stock',
        'Manage products and employees',
        'Keep your records organized',
    )

    def __init__(self):
        self._root = Tk()
        self._root.geometry(f'{WIN_W}x{WIN_H}+0+0')
        self._root.resizable(False, False)
        self._root.title('AIMS - Login')
        self._root.config(bg=NAVY)

        logo_path = os.path.join(ICON_DIR, 'aimslogo.png')
        if os.path.isfile(logo_path):
            try:
                self._logo = PhotoImage(file=logo_path).subsample(2, 2)
                self._root.iconphoto(True, self._logo)
            except Exception:
                pass

        self._pw_visible = False
        self._build_background()
        self._build_left_side()
        self._build_form()
        self._root.bind('<Return>', lambda event: self.authenticate())

    # ---------- background ----------
    def _build_background(self) -> None:
        self._glass_img = make_glass_background(BG_PATH)
        self._glass_photo = ImageTk.PhotoImage(self._glass_img)
        self._canvas = Canvas(self._root, width=WIN_W, height=WIN_H, highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0)
        self._canvas.create_image(0, 0, image=self._glass_photo, anchor='nw')

    def _glass_tone(self, x, y, w=40, h=40, lighten=0.0) -> str:
        return tone(self._glass_img, x, y, w, h, lighten)      # window coordinates, as in the original

    def _text(self, x, y, text, size, family='Segoe UI', bold=False, fill='white',
              anchor='nw', justify='left', shadow=False) -> None:
        spec = (family, size, 'bold') if bold else (family, size)
        if shadow:
            self._canvas.create_text(x + 2, y + 2, text=text, font=spec, fill='#07122B',
                                     anchor=anchor, justify=justify)
        self._canvas.create_text(x, y, text=text, font=spec, fill=fill, anchor=anchor, justify=justify)

    # ---------- left side: logo, title, tagline, highlights, footer ----------
    def _build_left_side(self) -> None:
        logo = PILImage.open(os.path.join(ICON_DIR, 'logo (1).png')).convert('RGBA')
        box = logo.getchannel('A').getbbox()
        if box:
            logo = logo.crop(box)
        self._title_photo = ImageTk.PhotoImage(logo)
        self._canvas.create_image(self.SIDE_MARGIN, self.SIDE_MARGIN, image=self._title_photo, anchor='nw')

        cx = self.LEFT_CX
        self._text(cx, 300, 'INVENTORY MANAGEMENT\nSYSTEM', 30, bold=True, anchor='center', justify='center')
        self._text(cx, 366, 'Manage your inventory with ease and efficiency.', 14, bold=True,
                   anchor='n', justify='center')

        for i, line in enumerate(self.HIGHLIGHTS):
            y = 440 + i * 46
            x = self.HL_X
            self._canvas.create_oval(x, y - 13, x + 26, y + 13, outline='#9FB3DA', width=2)
            self._canvas.create_line(x + 7, y, x + 11, y + 4, x + 19, y - 5, fill='white', width=2,
                                     capstyle='round', joinstyle='round')
            self._text(x + 42, y, line, 14, fill='#E6ECF8', anchor='w')

        self._text(cx, WIN_H - self.SIDE_MARGIN - 20,
                   'Authorized personnel only. Need an account? Contact your administrator.',
                   11, fill='#D3DCEE', anchor='s', justify='center')
        self._text(cx, WIN_H - self.SIDE_MARGIN + 4, f'\u00a9 {date.today().year} AIMS. All rights reserved.',
                   11, fill='#B9C6E0', anchor='s', justify='center')

    # ---------- glass card content ----------
    def _build_form(self) -> None:
        left = CARD_X + FORM_X
        self._label_font = tkfont.Font(family='Segoe UI', size=12, weight='bold')
        field_font = ctk.CTkFont('Segoe UI', 14)

        self._text(left, CARD_Y + 40, 'Welcome Back!', 32, bold=True)
        self._text(left, CARD_Y + 100, 'Please enter your details.', 12, fill='#D3DCEE')

        def field_label(text, y):
            self._canvas.create_text(left, y, text=text, font=self._label_font, fill='white', anchor='nw')
            self._canvas.create_text(left + self._label_font.measure(text), y, text=' *',
                                     font=self._label_font, fill=ASTERISK, anchor='nw')

        def glass_entry(y, placeholder, mask='', rule=None):
            w, h = FORM_W, 56
            cx, cy = left + w // 2, y + h // 2
            options = typing_rule(self._root, placeholder, rule) if rule else {}
            e = ctk.CTkEntry(
                self._canvas, width=w, height=h, corner_radius=10, border_width=1,
                bg_color=self._glass_tone(cx, cy, w + 10, h + 10),
                fg_color=self._glass_tone(cx, cy, w, h, 0.10),
                border_color=self._glass_tone(cx, cy, w, h, 0.38),
                text_color='white', show=mask,
                placeholder_text=placeholder, placeholder_text_color=GLASS_PLACEHOLDER,
                font=field_font, **options)
            e.place(x=left, y=y)
            return e

        # role: Admin or Cashier
        role_y = CARD_Y + 136
        rcx, rcy = left + FORM_W // 2, role_y + 20
        track = self._glass_tone(rcx, rcy, FORM_W, 40, 0.14)
        self._role_selector = ctk.CTkSegmentedButton(
            self._canvas, values=['Admin', 'Cashier'], width=FORM_W, height=40, corner_radius=10,
            dynamic_resizing=False, bg_color=self._glass_tone(rcx, rcy, FORM_W + 10, 50),
            fg_color=track, unselected_color=track,
            unselected_hover_color=self._glass_tone(rcx, rcy, FORM_W, 40, 0.24),
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            text_color='white', font=ctk.CTkFont('Segoe UI', 14, 'bold'),
            command=self.on_role_change)
        self._role_selector.set('Admin')
        self._role_selector.place(x=left, y=role_y)

        field_label('Employee ID', CARD_Y + 194)
        self._empid_entry = glass_entry(CARD_Y + 224, 'Enter your employee ID', rule=validate_empid)

        field_label('Username', CARD_Y + 294)
        self._username_entry = glass_entry(CARD_Y + 324, 'Enter your username', rule=validate_name)

        field_label('Password', CARD_Y + 394)
        self._password_entry = glass_entry(CARD_Y + 424, 'Input password', mask='*')

        # eye icon (created after the entry so it sits on top)
        self._eye_closed = white_icon(os.path.join(ICON_DIR, 'closeye.png'))
        self._eye_open = white_icon(os.path.join(ICON_DIR, 'openeye.png'))
        eye_bg = self._password_entry.cget('fg_color')
        eye_opts = {'image': self._eye_closed} if self._eye_closed else {'text': '\U0001F441', 'fg': 'white'}
        self._eye_btn = Button(self._canvas, bd=0, bg=eye_bg, activebackground=eye_bg,
                               cursor='hand2', command=self.toggle_password, **eye_opts)
        self._eye_btn.place(x=left + FORM_W - 46, y=CARD_Y + 424 + 14)

        # forgot password
        forget_y = CARD_Y + 490
        fcx = left + FORM_W - 60
        ctk.CTkButton(
            self._canvas, text='Forgot password?', width=0, height=24, fg_color='transparent',
            bg_color=self._glass_tone(fcx, forget_y + 12, 140, 30),
            hover_color=self._glass_tone(fcx, forget_y + 12, 140, 30, 0.12),
            text_color='#CFE0FF', font=ctk.CTkFont('Segoe UI', 12, 'bold'), cursor='hand2',
            command=lambda: ForgotPasswordDialog(self._root)
        ).place(x=left + FORM_W, y=forget_y, anchor='ne')

        # log in
        login_y = CARD_Y + 536
        ctk.CTkButton(
            self._canvas, text='Log In', width=FORM_W, height=50, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color='white',
            bg_color=self._glass_tone(left + FORM_W // 2, login_y + 25, FORM_W + 10, 60),
            font=ctk.CTkFont('Segoe UI', 18, 'bold'), command=self.authenticate
        ).place(x=left, y=login_y)

        # sign up (asks for an Admin first; switched off while Cashier is selected)
        signup_y = CARD_Y + 606
        scx, scy = left + FORM_W // 2, signup_y + 25
        self._signup_btn = ctk.CTkButton(
            self._canvas, text='Sign Up', width=FORM_W, height=50, corner_radius=10,
            fg_color='transparent', bg_color=self._glass_tone(scx, scy, FORM_W + 10, 60),
            hover_color=self._glass_tone(scx, scy, FORM_W, 50, 0.10),
            border_width=2, border_color='#9FB3DA', text_color='white', text_color_disabled='#7F8FB0',
            font=ctk.CTkFont('Segoe UI', 16, 'bold'), command=self.open_signup)
        self._signup_btn.place(x=left, y=signup_y)

    # ---------- small handlers ----------
    def on_role_change(self, role: str) -> None:
        if role == 'Admin':
            self._signup_btn.configure(state='normal', border_color='#9FB3DA')
        else:
            self._signup_btn.configure(state='disabled', border_color='#56668A')

    def open_signup(self) -> None:
        AdminVerificationDialog(self._root, on_success_callback=lambda: CreateAccountDialog(self._root))

    def toggle_password(self) -> None:
        self._pw_visible = not self._pw_visible
        self._password_entry.configure(show='' if self._pw_visible else '*')
        if self._eye_open and self._eye_closed:
            self._eye_btn.config(image=self._eye_open if self._pw_visible else self._eye_closed)

    # ---------- login ----------
    def authenticate(self) -> None:
        empid = self._empid_entry.get().strip()
        username = self._username_entry.get().strip()
        password = self._password_entry.get()

        try:
            if not empid or not username or not password:
                raise EmptyFieldException('All fields are required.')
            if not empid.isdigit():
                raise InvalidDataTypeException('Employee ID must contain digits only.')

            con = None
            try:
                con = get_connection()
                cur = con.cursor()
                cur.execute('SELECT empid, name, role, password FROM employee_data WHERE empid = %s AND name = %s',
                            (empid, username))
                row = cur.fetchone()
                if row is None:
                    raise AuthenticationException('Invalid Employee ID, Username or Password.')

                emp_id, emp_name, role, stored_hash = row
                role = (role or '').strip().capitalize()

                is_correct, needs_upgrade = verify_password(stored_hash, password)
                if not is_correct:
                    raise AuthenticationException('Invalid Employee ID, Username or Password.')
                if role not in DASHBOARDS:
                    raise AuthenticationException('Only Admin and Cashier accounts are authorized to use this program.')

                selected_role = self._role_selector.get()
                if role != selected_role:
                    raise AuthenticationException(f'This is not a {selected_role} account. Please choose the correct role.')

                target = DASHBOARDS[role]
                if importlib.util.find_spec(target) is None:
                    messagebox.showinfo('Not available yet', f'The {role} dashboard has not been set up yet.')
                    return

                if needs_upgrade:
                    try:
                        cur.execute('UPDATE employee_data SET password = %s WHERE empid = %s',
                                    (hash_password(password), emp_id))
                        con.commit()
                    except pymysql.MySQLError:
                        con.rollback()

                session.current_user["id"] = emp_id
                session.current_user["name"] = emp_name
                session.current_user["role"] = role

            except pymysql.MySQLError as e:
                raise DatabaseOperationException(str(e))
            finally:
                if con is not None:
                    con.close()

            messagebox.showinfo('Success', 'Login Successful', parent=self._root)
            self._root.destroy()

        except (EmptyFieldException, InvalidDataTypeException, AuthenticationException,
                DatabaseOperationException) as err:
            messagebox.showerror('Error', getattr(err, 'message', str(err)), parent=self._root)
            return

        dashboard = importlib.import_module(target)
        if role == 'Cashier':
            dashboard.CashierApp(session.current_user).run()
        elif hasattr(dashboard, 'main'):
            dashboard.main()

    def run(self) -> None:
        self._root.mainloop()

# Global execution
if __name__ == '__main__':
    app = LoginWindow()
    app.run()
