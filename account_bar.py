"""
Account Bar and Profile Navigation Module.
Demonstrates:
- Object-Oriented Programming (Classes: AvatarGenerator, ChangePasswordDialog, AccountBar)
- Constructors (__init__)
- Inheritance (ChangePasswordDialog inherits Toplevel; AccountBar inherits CTkFrame)
- Encapsulation (User credentials, Dialog geometry and inputs)
- Exception Handling (EmptyFieldException, ValidationError, AuthenticationException)
- GUI Components (Menus, Buttons, Dialogs, Appropriate Fonts & Colors)
"""
import os
import subprocess
import sys
from tkinter import Menu, Toplevel, Label, messagebox
from typing import Optional, Callable
import customtkinter as ctk
import pymysql
from PIL import Image, ImageDraw, ImageFont

import session
from auth import get_connection, hash_password, verify_password
from core_exceptions import EmptyFieldException, ValidationError, AuthenticationException, DatabaseOperationException

NAVY = '#012148'
BLUE = '#053e87'
BLUE_HOVER = '#0a52ad'
CREAM = '#FDFCF8'


class AvatarGenerator:
    """Encapsulates image generation of circular user profile avatars."""

    @staticmethod
    def create_avatar(initial: str, size: int = 35) -> Optional[ctk.CTkImage]:
        try:
            scale = 4
            big = size * scale
            img = Image.new('RGBA', (big, big), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((0, 0, big - 1, big - 1), fill=CREAM)
            font = ImageFont.truetype('arialbd.ttf', int(big * 0.5))
            draw.text((big / 2, big / 2), initial, fill=NAVY, font=font, anchor='mm')
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        except Exception:
            return None


class ChangePasswordDialog(Toplevel):
    """
    Dialog window for updating user password.
    Demonstrates Inheritance from Toplevel, Constructors, and Exception Handling.
    """

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.title('Change Password')
        self.geometry('380x420+560+180')
        self.resizable(False, False)
        self.config(bg=CREAM)
        self.transient(parent_window)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        Label(self, text='Change Password', font=('Helvetica', 18, 'bold'),
              bg=CREAM, fg=NAVY).pack(pady=(30, 20))

        self._current_entry = self._create_entry('Current password')
        self._new_entry = self._create_entry('New password')
        self._confirm_entry = self._create_entry('Confirm new password')

        ctk.CTkButton(
            self, text='Save changes', width=300, height=40, fg_color=NAVY,
            hover_color=BLUE, font=('Helvetica', 14, 'bold'), cursor='hand2',
            command=self.save_password
        ).pack(pady=(18, 6))

        ctk.CTkButton(
            self, text='Cancel', width=300, height=40, fg_color='#E3E6EB',
            hover_color='#D2D6DD', text_color=NAVY, font=('Helvetica', 14, 'bold'),
            cursor='hand2', command=self.destroy
        ).pack()

        self.bind('<Return>', lambda event: self.save_password())
        self._current_entry.focus()

    def _create_entry(self, placeholder: str) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(self, width=300, height=40, placeholder_text=placeholder, show='*')
        entry.pack(pady=6)
        return entry

    def save_password(self) -> None:
        """Validates inputs and commits password change to MySQL."""
        current = self._current_entry.get().strip()
        new = self._new_entry.get().strip()
        confirm = self._confirm_entry.get().strip()

        try:
            if not current or not new or not confirm:
                raise EmptyFieldException('All fields are required.')
            if new != confirm:
                raise ValidationError('New password and confirmation do not match.')
            if new == current:
                raise ValidationError('New password must be different from current password.')
            if len(new) < 6:
                raise ValidationError('New password must be at least 6 characters.')

            emp_id = session.current_user.get('id')
            if not emp_id:
                raise AuthenticationException('No active user logged in.')

            con = None
            try:
                con = get_connection()
                cur = con.cursor()
                cur.execute('SELECT password FROM employee_data WHERE empid = %s', (emp_id,))
                row = cur.fetchone()

                is_correct = verify_password(row[0], current)[0] if row else False
                if not is_correct:
                    raise AuthenticationException('Current password is incorrect.')

                cur.execute(
                    'UPDATE employee_data SET password = %s WHERE empid = %s',
                    (hash_password(new), emp_id)
                )
                con.commit()
                messagebox.showinfo('Success', 'Password changed successfully', parent=self)
                self.destroy()

            except pymysql.MySQLError as e:
                raise DatabaseOperationException(str(e))
            finally:
                if con is not None:
                    con.close()

        except (EmptyFieldException, ValidationError, AuthenticationException, DatabaseOperationException) as err:
            messagebox.showerror('Error', str(err.message), parent=self)


class AccountBar(ctk.CTkFrame):
    """
    Encapsulated Account Pill Widget.
    Demonstrates Inheritance from CTkFrame, GUI Menus, and Event Handling.
    """

    def __init__(self, parent, main_window, on_manage_accounts: Optional[Callable] = None):
        super().__init__(parent, fg_color="transparent")
        self._window = main_window
        self._on_manage_accounts = on_manage_accounts
        self.pack(side='right', padx=(0, 15), pady=8)
        self._build_ui()

    def _build_ui(self) -> None:
        name = session.current_user.get('name') or 'User'
        role = session.current_user.get('role') or ''
        short_name = name if len(name) <= 16 else name[:15] + '…'
        avatar = AvatarGenerator.create_avatar(name.strip()[:1].upper() or '?')

        self._chip = ctk.CTkButton(
            self,
            text=f'  {short_name}  ·  {role}  ▾',
            image=avatar,
            compound='left',
            font=('Helvetica', 13, 'bold'),
            text_color='#FFFFFF',
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            corner_radius=22,
            width=260,
            height=44,
            cursor='hand2',
            command=self.show_menu
        )
        self._chip.pack()

    def show_menu(self) -> None:
        """Pops up the native Tkinter dropdown menu."""
        name = session.current_user.get('name') or 'User'
        role = session.current_user.get('role') or ''

        menu = Menu(self._window, tearoff=0, bg=NAVY, fg='#FFFFFF', bd=0,
                    activebackground=BLUE, activeforeground='#FFFFFF',
                    disabledforeground='#D5DCE8', font=('Helvetica', 11))
        menu.add_command(label=f'Signed in as {name} ({role})', state='disabled')
        menu.add_separator()
        if role == 'Admin' and self._on_manage_accounts is not None:
            menu.add_command(label='Manage Accounts', command=self._on_manage_accounts)
        menu.add_command(label='Change Password', command=lambda: ChangePasswordDialog(self._window))

        x = self._chip.winfo_rootx()
        y = self._chip.winfo_rooty() + self._chip.winfo_height() + 4
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()


def log_out(window):
    """Confirm, clear the session, close the dashboard and reopen the login screen."""
    if not messagebox.askyesno('Log out', 'Are you sure you want to log out?', parent=window):
        return

    session.current_user.clear()

    login_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'login.py')
    subprocess.Popen([sys.executable, login_path])
    window.destroy()


def change_password_dialog(window):
    return ChangePasswordDialog(window)


def build_account_bar(parent, window, on_manage_accounts=None):
    return AccountBar(parent, window, on_manage_accounts=on_manage_accounts)
