"""
Admin Settings and System Maintenance View.
Demonstrates:
- Multiple windows/forms (Toplevel dialogs)
- System Backup and Restore (Save Data & Load Data)
- Account Profile and Cashier user provisioning
- Encapsulated Security and Confirmation checks
"""
import os
import sys
import subprocess
from datetime import datetime
from tkinter import *
from tkinter import messagebox, filedialog, simpledialog
from typing import Any, Optional
import customtkinter as ctk
import pymysql

RED = "#8B1E2D"
GREEN = "#1E8449"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .widgets import (round_button, load_icon, load_ctk_icon, NAVY, ACTIVE, BG, LIGHT, MUTED, apply_rule, letters_only, digits_only, contact_only)
from ..core.session import SessionManager
from ..core.security import PasswordSecurity
from ..core.database import DatabaseManager
from ..core.storage import SQLBackupStorage
from ..core.exceptions import DatabaseOperationException, FileStorageException


class AdminSettingsView:
    """
    Controller and View class managing administrator account settings, cashier provisioning,
    and database backup/restore operations.
    """

    BACKUP_DIR = os.path.join(PROJECT_ROOT, "system_backup")

    def __init__(self, parent_window: Tk):
        self._parent = parent_window
        os.makedirs(self.BACKUP_DIR, exist_ok=True)
        self._sql_storage = SQLBackupStorage()

    def open_settings_menu(self) -> None:
        """Opens popup menu for Admin Settings."""
        if not SessionManager.is_admin():
            messagebox.showwarning("Access Denied", "Only administrators can access settings.", parent=self._parent)
            return

        menu = self._make_window("Account Settings", "280x280", dx=560, dy=-150)
        Label(menu, text="Admin Settings", font=("Helvetica", 9), bg=BG, fg=MUTED).pack(pady=(10, 0))
        menu.hello_img = load_icon("prof.png")
        menu.info_img = load_ctk_icon("acc.png")
        menu.cashier_img = load_ctk_icon("cashier.png")
        menu.backup_img = load_ctk_icon("backup.png")
        menu.logout_img = load_ctk_icon("logout.png")
        Label(menu, image=menu.hello_img, compound=LEFT, text=f" Hello, {SessionManager.get_username()}!", font=("Helvetica", 14, "bold"), bg=BG, fg=NAVY).pack(pady=(0, 5))
        Frame(menu, bg=MUTED, height=1, width=320).pack()

        def go(opener):
            menu.destroy()
            opener()

        ctk.CTkButton(
            menu, text="Account Info", image=menu.info_img, compound=LEFT,
            command=lambda: go(self.open_info_window),
            font=("Helvetica", 14, "bold"),
            text_color=NAVY, fg_color=BG, hover_color=LIGHT, bg_color=BG,
            corner_radius=8, width=240, height=34, cursor="hand2", anchor="w"
        ).pack(padx=10, pady=(10, 0))

        ctk.CTkButton(
            menu, text="Create Cashier", image=menu.cashier_img, compound=LEFT,
            command=lambda: go(self.open_cashier_window),
            font=("Helvetica", 14, "bold"),
            text_color=NAVY, fg_color=BG, hover_color=LIGHT, bg_color=BG,
            corner_radius=8, width=240, height=34, cursor="hand2", anchor="w"
        ).pack(padx=10, pady=(6, 0))

        ctk.CTkButton(
            menu, text="Back Up System", image=menu.backup_img, compound=LEFT,
            command=lambda: go(self.open_backup_window),
            font=("Helvetica", 14, "bold"),
            text_color=NAVY, fg_color=BG, hover_color=LIGHT, bg_color=BG,
            corner_radius=8, width=240, height=34, cursor="hand2", anchor="w"
        ).pack(padx=10, pady=(6, 0))

        Frame(menu, bg=MUTED, height=1, width=320).pack(pady=(10, 0))

        ctk.CTkButton(
            menu, text="Log Out", image=menu.logout_img, compound=LEFT,
            command=lambda: (menu.destroy(), self.log_out()),
            font=("Helvetica", 14, "bold"),
            text_color="#8B1E2D", fg_color=BG, hover_color="#F5E6E8", bg_color=BG,
            corner_radius=8, width=240, height=34, cursor="hand2", anchor="w"
        ).pack(padx=10, pady=(8, 0))

    def _make_window(self, title: str, size: str, dx: int = 0, dy: int = 0) -> Toplevel:
        top = Toplevel(self._parent)
        top.title(title)
        w, h = map(int, size.split("x"))
        self._parent.update_idletasks()
        x = self._parent.winfo_rootx() + (self._parent.winfo_width() - w) // 2 + dx
        y = self._parent.winfo_rooty() + (self._parent.winfo_height() - h) // 2 + dy
        top.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        top.resizable(False, False)
        top.config(bg=BG)
        top.transient(self._parent)
        top.grab_set()
        return top

    def _add_back_button(self, top: Toplevel) -> None:
        def go_back():
            top.destroy()
            self.open_settings_menu()
        Button(top, text="← Back", command=go_back, cursor="hand2", font=("Helvetica", 10, "bold"), fg=NAVY, bg=BG, bd=0).place(x=12, y=10)

    @staticmethod
    def _create_field(tab, label: str, value: str = "", secret: bool = False, rule=None) -> Entry:
        Label(tab, text=label, font=("Helvetica", 10, "bold"), bg=BG, anchor="w").pack(fill=X, padx=30, pady=(12, 0))
        entry = Entry(tab, font=("Helvetica", 11), relief=SOLID, bd=1, show="*" if secret else "")
        entry.pack(fill=X, padx=30, pady=(3, 0), ipady=3)
        entry.insert(0, value or "")
        if rule is not None:
            apply_rule(entry, rule)
        return entry

    @staticmethod
    def _valid_email(text: str) -> bool:
        return "@" in text and "." in text.split("@")[-1]

    @staticmethod
    def _launch_login() -> None:
        subprocess.Popen([sys.executable, os.path.join(PROJECT_ROOT, "login.py")])

    def write_backup_file(self, path: str) -> int:
        cur, con = DatabaseManager.get_cursor_and_connection()
        try:
            cur.execute("SELECT DATABASE()")
            db_name = cur.fetchone()[0]
            cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
            tables = [r[0] for r in cur.fetchall()]
            lines = [f"-- AIMS backup of `{db_name}`\n-- Created {datetime.now():%Y-%m-%d %H:%M:%S}\n\nSET FOREIGN_KEY_CHECKS=0;\n"]
            for table in tables:
                cur.execute(f"SHOW CREATE TABLE `{table}`")
                lines.append(f"DROP TABLE IF EXISTS `{table}`;")
                lines.append(cur.fetchone()[1] + ";\n")
                cur.execute(f"SELECT * FROM `{table}`")
                columns = ", ".join(f"`{d[0]}`" for d in cur.description)
                for r in cur.fetchall():
                    values = ", ".join(con.escape(v) for v in r)
                    lines.append(f"INSERT INTO `{table}` ({columns}) VALUES ({values});")
                lines.append("")
            lines.append("SET FOREIGN_KEY_CHECKS=1;\n")
            self._sql_storage.save(lines, path)
            return len(tables)
        finally:
            cur.close()
            con.close()

    def confirm_admin_password(self, top: Toplevel, message: str) -> bool:
        """Prompts for current admin's password and verifies it."""
        entered = simpledialog.askstring("Confirm Password", message, show="*", parent=top)
        if not entered:
            return False

        emp_id = SessionManager.get_user_id()
        con, cur = None, None
        try:
            cur, con = DatabaseManager.get_cursor_and_connection()
            cur.execute("SELECT password FROM employee_data WHERE empid=%s", (emp_id,))
            stored = cur.fetchone()[0]
            is_valid, _ = PasswordSecurity.verify_password(stored, entered)
            if not is_valid:
                messagebox.showerror("Wrong Password", "Incorrect password. Action cancelled.", parent=top)
                return False
            return True
        except Exception as err:
            messagebox.showerror("Database Error", str(err), parent=top)
            return False
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def open_info_window(self) -> None:
        """Window for editing active account profile and password."""
        emp_id = SessionManager.get_user_id()
        con, cur = None, None
        try:
            cur, con = DatabaseManager.get_cursor_and_connection()
            cur.execute("SELECT name, email, contact FROM employee_data WHERE empid = %s", (emp_id,))
            row = cur.fetchone()
        except Exception as e:
            messagebox.showerror("Database Error", str(e), parent=self._parent)
            return
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

        if not row:
            messagebox.showerror("Error", "Account not found.", parent=self._parent)
            return

        name, email, contact = row
        top = self._make_window("Account Info", "430x620")
        self._add_back_button(top)

        Label(top, text="Account Info", font=("Helvetica", 18, "bold"), bg=BG, fg=NAVY).pack(pady=(18, 1))
        Label(top, text=f"{name}  |  Admin", font=("Helvetica", 10), bg=BG, fg=MUTED).pack()

        name_entry = self._create_field(top, "Name", name, rule=letters_only)
        email_entry = self._create_field(top, "Email", email)
        contact_entry = self._create_field(top, "Contact Number", contact, rule=contact_only)

        def save_info():
            new_name = name_entry.get().strip()
            new_email = email_entry.get().strip()
            new_contact = contact_entry.get().strip()

            if not new_name:
                messagebox.showwarning("Missing Name", "Name cannot be empty.", parent=top)
                return
            if not self._valid_email(new_email):
                messagebox.showwarning("Invalid Email", "Enter a valid email address.", parent=top)
                return
            if new_contact and (not new_contact.isdigit() or len(new_contact) != 10):
                messagebox.showwarning("Invalid Contact", "Contact number must be 10 digits.", parent=top)
                return

            con2, cur2 = None, None
            try:
                cur2, con2 = DatabaseManager.get_cursor_and_connection()
                cur2.execute("SELECT empid FROM employee_data WHERE name = %s AND empid <> %s", (new_name, emp_id))
                if cur2.fetchone():
                    messagebox.showerror("Already Exists", "Another employee already uses that name.", parent=top)
                    return

                cur2.execute("UPDATE employee_data SET name=%s, email=%s, contact=%s WHERE empid=%s",
                             (new_name, new_email, new_contact or None, emp_id))
                con2.commit()
                SessionManager.set_user(emp_id, new_name, SessionManager.get_user().get("role") or "Admin", new_email)
                if hasattr(self._parent, "update_account_name"):
                    self._parent.update_account_name()
                messagebox.showinfo("Saved", "Your account details were updated.", parent=top)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=top)
            finally:
                if cur2:
                    cur2.close()
                if con2:
                    con2.close()

        round_button(top, "Save Details", save_info, width=200).pack(pady=(16, 10))

        # Change Password Section
        Frame(top, bg="#D1D5DB", height=1).pack(fill=X, padx=30, pady=(10, 0))
        Label(top, text="Change Password", font=("Helvetica", 12, "bold"), bg=BG, fg=NAVY).pack(anchor="w", padx=30, pady=(10, 0))

        curr_pw = self._create_field(top, "Current Password", secret=True)
        new_pw = self._create_field(top, "New Password", secret=True)
        conf_pw = self._create_field(top, "Confirm New Password", secret=True)

        def change_password():
            c, n, cf = curr_pw.get(), new_pw.get(), conf_pw.get()
            if not c or not n or not cf:
                messagebox.showwarning("Missing Fields", "Fill in all password fields.", parent=top)
                return
            if n != cf:
                messagebox.showwarning("Mismatch", "New password and confirmation do not match.", parent=top)
                return
            if len(n) < 6:
                messagebox.showwarning("Too Short", "Use at least 6 characters.", parent=top)
                return

            con3, cur3 = None, None
            try:
                cur3, con3 = DatabaseManager.get_cursor_and_connection()
                cur3.execute("SELECT password FROM employee_data WHERE empid=%s", (emp_id,))
                stored = cur3.fetchone()[0]
                if not PasswordSecurity.verify_password(stored, c)[0]:
                    messagebox.showerror("Wrong Password", "Current password is incorrect.", parent=top)
                    return
                hashed = PasswordSecurity.hash_password(n)
                cur3.execute("UPDATE employee_data SET password=%s WHERE empid=%s", (hashed, emp_id))
                con3.commit()
                messagebox.showinfo("Success", "Password updated successfully.", parent=top)
                curr_pw.delete(0, END)
                new_pw.delete(0, END)
                conf_pw.delete(0, END)
            except Exception as err:
                messagebox.showerror("Error", str(err), parent=top)
            finally:
                if cur3:
                    cur3.close()
                if con3:
                    con3.close()

        round_button(top, "Change Password", change_password, width=200).pack(pady=(14, 0))

    def open_cashier_window(self) -> None:
        """Activate a Cashier account for someone who is ALREADY in employee_data."""
        top = self._make_window("Create Cashier", "430x560")
        self._add_back_button(top)
        Label(top, text="Create Cashier Account", font=("Helvetica", 18, "bold"), bg=BG, fg=NAVY).pack(pady=(18, 2))
        Label(top, text="The cashier must already be listed in Employees.",
              font=("Helvetica", 10), bg=BG, fg=MUTED).pack()

        c_empid = self._create_field(top, "Employee ID", rule=digits_only(9))
        c_name = self._create_field(top, "Full Name (used to log in)", rule=letters_only)
        c_email = self._create_field(top, "Email")
        c_pass = self._create_field(top, "Password", secret=True)
        c_confirm = self._create_field(top, "Confirm Password", secret=True)

        def create():
            empid, u, m = c_empid.get().strip(), c_name.get().strip(), c_email.get().strip()
            p, p2 = c_pass.get(), c_confirm.get()

            if not empid or not u or not m or not p or not p2:
                messagebox.showwarning("Missing Fields", "Employee ID, name, email and password are required.", parent=top)
                return
            if p != p2:
                messagebox.showwarning("Mismatch", "Passwords do not match.", parent=top)
                return
            if len(p) < 6:
                messagebox.showwarning("Too Short", "Use at least 6 characters.", parent=top)
                return

            con, cur = None, None
            try:
                cur, con = DatabaseManager.get_cursor_and_connection()
                cur.execute("SELECT empid, role, password FROM employee_data "
                            "WHERE empid = %s AND name = %s AND email = %s", (int(empid), u, m))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror(
                        "Not Found",
                        "No employee matches that ID, name and email.\n\n"
                        "Add the cashier in the Employees page first, then create the account.",
                        parent=top)
                    return
                _, role, existing_pw = row
                if (role or "").strip().lower() != "cashier":
                    messagebox.showerror("Not a Cashier",
                                         f"This employee's role is '{role or 'not set'}', not Cashier.", parent=top)
                    return
                if existing_pw:
                    messagebox.showerror("Already Exists",
                                         "This cashier already has an account.\n"
                                         "Use Reset Password on the login screen if they forgot it.", parent=top)
                    return

                cur.execute("UPDATE employee_data SET password = %s WHERE empid = %s",
                            (PasswordSecurity.hash_password(p), int(empid)))
                con.commit()
                messagebox.showinfo("Success", f"Cashier account for '{u}' created.", parent=top)
                for entry in (c_empid, c_name, c_email, c_pass, c_confirm):
                    entry.delete(0, END)
            except Exception as err:
                messagebox.showerror("Error", str(err), parent=top)
            finally:
                if cur:
                    cur.close()
                if con:
                    con.close()

        round_button(top, "Create Cashier", create, width=200).pack(pady=(20, 0))
    
    def open_backup_window(self) -> None:
        top = self._make_window("Back Up System", "470x680")
        self._add_back_button(top)
        Label(top, text="Back Up System", font=("Helvetica", 18, "bold"), bg=BG, fg=NAVY).pack(pady=(18, 2))

        def divider():
            Frame(top, bg="#D1D5DB", height=1).pack(fill=X, padx=30, pady=(16, 0))

        Label(top, text="Back Up Database", font=("Helvetica", 12, "bold"), bg=BG, fg=NAVY).pack(anchor="w", padx=30, pady=(14, 4))
        Label(top, text="Saves every table (structure and data) into one .sql file.\n"
                        "The file includes password hashes, so keep it somewhere safe.",
              font=("Helvetica", 10), bg=BG, fg=MUTED, justify=LEFT).pack(anchor="w", padx=30)
        status = Label(top, text="", font=("Helvetica", 10), bg=BG, fg=GREEN, wraplength=400, justify=LEFT)

        ERRS = (pymysql.MySQLError, OSError, DatabaseOperationException, FileStorageException)

        def backup_database():
            default = f"aims_backup_{datetime.now():%Y%m%d_%H%M}.sql"
            path = filedialog.asksaveasfilename(parent=top, defaultextension=".sql", initialfile=default,
                                                initialdir=self.BACKUP_DIR, filetypes=[("SQL file", "*.sql")],
                                                title="Save database backup")
            if not path:
                return
            try:
                count = self.write_backup_file(path)
                status.config(text=f"Backup saved ({count} tables):\n{path}", fg=GREEN)
                messagebox.showinfo("Backup Complete", "The database was backed up successfully.", parent=top)
            except ERRS as err:
                status.config(text="Backup failed.", fg=RED)
                messagebox.showerror("Backup Failed", str(err), parent=top)

        round_button(top, "Back Up Now", backup_database, width=200).pack(pady=(10, 0))

        divider()
        Label(top, text="Restore Database", font=("Helvetica", 12, "bold"), bg=BG, fg=NAVY).pack(anchor="w", padx=30, pady=(14, 4))
        Label(top, text="Replaces ALL current data with a backup file.\nA safety copy is saved first.",
              font=("Helvetica", 10), bg=BG, fg=MUTED, justify=LEFT).pack(anchor="w", padx=30)

        def restore_database():
            path = filedialog.askopenfilename(parent=top, title="Choose a backup to restore",
                                              initialdir=self.BACKUP_DIR, filetypes=[("SQL file", "*.sql")])
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    if not f.readline().startswith("-- AIMS backup"):
                        messagebox.showerror("Invalid File", "This is not an AIMS backup file.", parent=top)
                        return
            except OSError as err:
                messagebox.showerror("Error", str(err), parent=top)
                return
            if not self.confirm_admin_password(top, "Enter your admin password to continue:"):
                return
            if not messagebox.askyesno("Restore Database",
                    "This will DELETE all current data and replace it with the backup.\n\n"
                    "A safety copy of the current data will be saved first.\n"
                    "The app will return to the login screen afterward.\n\nContinue?",
                    icon="warning", parent=top):
                return
            safety = os.path.join(self.BACKUP_DIR, f"before_restore_{datetime.now():%Y%m%d_%H%M%S}.sql")
            try:
                self.write_backup_file(safety)
                statements = self._sql_storage.load(path)
            except ERRS as err:
                messagebox.showerror("Restore Cancelled", f"Could not prepare the restore:\n{err}", parent=top)
                return
            cur = con = None
            try:
                cur, con = DatabaseManager.get_cursor_and_connection()
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
                cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
                for row in cur.fetchall():
                    cur.execute(f"DROP TABLE IF EXISTS `{row[0]}`")
                for statement in statements:
                    if statement.strip():
                        cur.execute(statement)
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
                con.commit()
            except (pymysql.MySQLError, DatabaseOperationException) as err:
                messagebox.showerror("Restore Failed",
                    f"{err}\n\nYour data before the restore was saved to:\n{safety}\nRestore that file to undo.", parent=top)
                return
            finally:
                if cur:
                    cur.close()
                if con:
                    con.close()
            messagebox.showinfo("Restore Complete", "The database was restored. Please log in again.", parent=top)
            SessionManager.clear()
            top.destroy()
            self._parent.destroy()
            self._launch_login()

        round_button(top, "Restore From Backup...", restore_database, width=200).pack(pady=(10, 0))

        divider()
        Label(top, text="Delete Current Data", font=("Helvetica", 12, "bold"), bg=BG, fg=RED).pack(anchor="w", padx=30, pady=(14, 4))
        Label(top, text="Empties all tables except employee accounts.\nBackup files are not affected.",
              font=("Helvetica", 10), bg=BG, fg=MUTED, justify=LEFT).pack(anchor="w", padx=30)

        def delete_current_data():
            if not self.confirm_admin_password(top, "Enter your admin password to continue:"):
                return
            typed = simpledialog.askstring("Delete Current Data",
                "This permanently empties products, sales, orders, shipments and\n"
                "all other data. Employee accounts are kept.\n\n"
                "A safety copy is saved first.\n\nType DELETE to continue:", parent=top)
            if typed != "DELETE":
                messagebox.showinfo("Cancelled", "Nothing was deleted.", parent=top)
                return
            safety = os.path.join(self.BACKUP_DIR, f"before_delete_{datetime.now():%Y%m%d_%H%M%S}.sql")
            try:
                self.write_backup_file(safety)
            except ERRS as err:
                messagebox.showerror("Cancelled", f"Could not save the safety copy:\n{err}", parent=top)
                return
            cur = con = None
            try:
                cur, con = DatabaseManager.get_cursor_and_connection()
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
                cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
                cleared = 0
                for row in cur.fetchall():
                    if row[0].lower() == "employee_data":
                        continue
                    cur.execute(f"TRUNCATE TABLE `{row[0]}`")
                    cleared += 1
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
                con.commit()
            except (pymysql.MySQLError, DatabaseOperationException) as err:
                messagebox.showerror("Delete Failed", f"{err}\n\nA copy of your data is saved at:\n{safety}", parent=top)
                return
            finally:
                if cur:
                    cur.close()
                if con:
                    con.close()
            status.config(text=f"{cleared} tables emptied.\nSafety copy: {safety}", fg=GREEN)
            messagebox.showinfo("Done", f"{cleared} tables were emptied. Employee accounts were kept.\n\n"
                                        f"Safety copy saved to:\n{safety}", parent=top)

        delete_btn = round_button(top, "Delete Current Data...", delete_current_data, width=200)
        delete_btn.configure(fg_color=RED, hover_color="#6E1824", text_color="white")  # danger button
        delete_btn.pack(pady=(10, 0))

    def log_out(self) -> None:
        if messagebox.askyesno("Log out", "Are you sure you want to log out?", parent=self._parent):
            SessionManager.clear()
            self._parent.destroy()
            self._launch_login()