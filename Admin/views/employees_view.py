"""
Employee Management View.
Demonstrates:
- Inheritance (EmployeeView inherits from BaseFormView)
- Encapsulation (Encapsulates EmployeeRepository and UI state)
- Polymorphism (Overrides build_ui, refresh_data, clear_fields)
- Functional Features: Add, Edit, Delete, Search, Display
- Exception Handling: Catches and processes custom exceptions
"""
from tkinter import *
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import date, datetime
from typing import Optional
from .base_view import BaseFormView
from .widgets import round_button, NAVY, BG, LIGHT, apply_rule, letters_only, contact_only, money_only
from ..models.employee import Employee
from ..repositories.employee_repo import EmployeeRepository
from ..core.exceptions import (
    ValidationError,
    EmptyFieldException,
    InvalidDataTypeException,
    DuplicateRecordException,
    RecordNotFoundException
)

class EmployeeView(BaseFormView):
    """
    Form view managing employee records, authentication accounts, and payroll details.
    """

    def __init__(self, parent_window: Tk):
        self._repository = EmployeeRepository()
        super().__init__(parent_window, title="Employee Details")

    @staticmethod
    def _latest_dob() -> date:
        """Latest allowed date of birth: exactly 18 years ago today (employees must be 18+)."""
        today = date.today()
        try:
            return today.replace(year=today.year - 18)
        except ValueError:                      # today is Feb 29
            return today.replace(year=today.year - 18, day=28)

    def build_ui(self) -> None:
        """Constructs all Employee form components."""
        # Top Search Frame
        top_frame = Frame(self, bg=BG)
        top_frame.place(x=0, y=55, relwidth=1, height=240)

        search_frame = Frame(top_frame, bg=BG)
        search_frame.pack()

        self._search_combobox = ttk.Combobox(
            search_frame,
            values=("ID", "Name", "Email", "Employment Type", "Work Shift"),
            font=("Helvetica", 10),
            state="readonly",
            width=15
        )
        self._search_combobox.set("Search By")
        self._search_combobox.grid(row=0, column=0, padx=10)

        self._search_entry = Entry(search_frame, font=("Helvetica", 12), bg="#E2F7FC", width=22)
        self._search_entry.grid(row=0, column=1, padx=5)

        round_button(
            search_frame, text="Search", width=100, height=32,
            command=self.search_records
        ).grid(row=0, column=2, padx=10)

        round_button(
            search_frame, text="Show All", width=100, height=32, secondary=True,
            command=self.refresh_data
        ).grid(row=0, column=3, padx=5)

        # Treeview / Table
        table_frame = Frame(top_frame, bg=BG)
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=(10, 0))

        hor_sb = ttk.Scrollbar(table_frame, orient=HORIZONTAL)
        ver_sb = ttk.Scrollbar(table_frame, orient=VERTICAL)

        self._treeview = ttk.Treeview(
            table_frame,
            columns=("empid", "name", "email", "sex", "dob", "contact", "employment_type", "work_shift", "address", "dj", "salary", "role"),
            show="headings",
            yscrollcommand=ver_sb.set,
            xscrollcommand=hor_sb.set
        )
        hor_sb.pack(side=BOTTOM, fill=X)
        ver_sb.pack(side=RIGHT, fill=Y)
        hor_sb.config(command=self._treeview.xview)
        ver_sb.config(command=self._treeview.yview)
        self._treeview.pack(fill=BOTH, expand=True)

        # Headings and Columns
        headings = {
            "empid": ("ID", 60),
            "name": ("Name", 140),
            "email": ("Email", 180),
            "sex": ("Sex", 80),
            "dob": ("Date of Birth", 100),
            "contact": ("Contact", 100),
            "employment_type": ("Employment Type", 120),
            "work_shift": ("Work Shift", 100),
            "address": ("Address", 200),
            "dj": ("Date Joined", 100),
            "salary": ("Salary", 120),
            "role": ("Role", 110)
        }
        for col_id, (col_text, col_width) in headings.items():
            self._treeview.heading(col_id, text=col_text)
            self._treeview.column(col_id, width=col_width, anchor=W if col_id in ("name", "email", "address") else CENTER)

        self._treeview.bind("<ButtonRelease-1>", self.on_select_row)

        # Form Input Fields Frame
        detail_frame = Frame(self, bg=BG)
        detail_frame.place(x=180, y=305)

        # Row 0: ID, Name, Email
        Label(detail_frame, text="ID", font=("Helvetica", 12), bg=BG).grid(row=0, column=0, padx=10, pady=12, sticky="w")
        self._empid_entry = Entry(detail_frame, font=("Helvetica", 12), bg="#E2F7FC", state="readonly", width=18)
        self._empid_entry.grid(row=0, column=1, padx=5, pady=12)

        Label(detail_frame, text="Name", font=("Helvetica", 12), bg=BG).grid(row=0, column=2, padx=10, pady=12, sticky="w")
        self._name_entry = Entry(detail_frame, font=("Helvetica", 12), bg="#E2F7FC", width=18)
        self._name_entry.grid(row=0, column=3, padx=5, pady=12)
        apply_rule(self._name_entry, letters_only)  

        Label(detail_frame, text="Email", font=("Helvetica", 12), bg=BG).grid(row=0, column=4, padx=10, pady=12, sticky="w")
        self._email_entry = Entry(detail_frame, font=("Helvetica", 12), bg="#E2F7FC", width=18)
        self._email_entry.grid(row=0, column=5, padx=5, pady=12)

        # Row 1: Sex, DOB, Contact
        Label(detail_frame, text="Sex", font=("Helvetica", 12), bg=BG).grid(row=1, column=0, padx=10, pady=12, sticky="w")
        self._sex_combobox = ttk.Combobox(detail_frame, values=("Male", "Female", "Prefer not to say"), font=("Helvetica", 11), width=16, state="readonly")
        self._sex_combobox.set("Select Sex")
        self._sex_combobox.grid(row=1, column=1)

        Label(detail_frame, text="Date of Birth", font=("Helvetica", 12), bg=BG).grid(row=1, column=2, padx=10, pady=12, sticky="w")
        self._dob_date_entry = DateEntry(
            detail_frame, width=16, font=("Helvetica", 11),
            date_pattern="yyyy-mm-dd", maxdate=self._latest_dob()
        )
        self._dob_date_entry.set_date(self._latest_dob())
        self._dob_date_entry.grid(row=1, column=3)

        Label(detail_frame, text="Contact", font=("Helvetica", 12), bg=BG).grid(row=1, column=4, padx=10, pady=12, sticky="w")
        self._contact_entry = Entry(detail_frame, font=("Helvetica", 12), bg="#E2F7FC", width=18)
        self._contact_entry.grid(row=1, column=5, padx=5, pady=12)
        apply_rule(self._contact_entry, contact_only)

        # Row 2: Employment Type, Work Shift, Address
        Label(detail_frame, text="Employment Type", font=("Helvetica", 12), bg=BG).grid(row=2, column=0, padx=10, pady=12, sticky="w")
        self._employment_combobox = ttk.Combobox(detail_frame, values=("Full Time", "Part Time", "Casual", "Contract", "Intern"), font=("Helvetica", 11), width=16, state="readonly")
        self._employment_combobox.set("Select Type")
        self._employment_combobox.grid(row=2, column=1)

        Label(detail_frame, text="Work Shift", font=("Helvetica", 12), bg=BG).grid(row=2, column=2, padx=10, pady=12, sticky="w")
        self._shift_combobox = ttk.Combobox(detail_frame, values=("Morning", "Afternoon", "Evening", "Night"), font=("Helvetica", 11), width=16, state="readonly")
        self._shift_combobox.set("Select Work Shift")
        self._shift_combobox.grid(row=2, column=3)

        Label(detail_frame, text="Address", font=("Helvetica", 12), bg=BG).grid(row=2, column=4, padx=10, pady=12, sticky="w")
        self._address_text = Text(detail_frame, width=20, height=3, font=("Helvetica", 11), bg="#E2F7FC")
        self._address_text.grid(row=2, column=5)

        # Row 3: Date Joined, Salary, Role
        Label(detail_frame, text="Date Joined", font=("Helvetica", 12), bg=BG).grid(row=3, column=0, padx=10, pady=12, sticky="w")
        self._dj_date_entry = DateEntry(detail_frame, width=16, font=("Helvetica", 11), date_pattern="yyyy-mm-dd")
        self._dj_date_entry.grid(row=3, column=1)

        Label(detail_frame, text="Salary", font=("Helvetica", 12), bg=BG).grid(row=3, column=2, padx=10, pady=12, sticky="w")
        self._salary_entry = Entry(detail_frame, font=("Helvetica", 12), bg="#E2F7FC", width=18)
        self._salary_entry.grid(row=3, column=3, padx=5, pady=12)
        apply_rule(self._salary_entry, money_only)

        Label(detail_frame, text="Role", font=("Helvetica", 12), bg=BG).grid(row=3, column=4, padx=10, pady=12, sticky="w")
        self._role_combobox = ttk.Combobox(detail_frame, values=("Admin", "Manager", "Cashier", "Inventory Staff", "Receiving Staff"), font=("Helvetica", 11), width=16, state="readonly")
        self._role_combobox.set("Select Role")
        self._role_combobox.grid(row=3, column=5)

        # Action Buttons
        button_frame = Frame(self, bg=BG)
        button_frame.place(x=380, y=595)

        round_button(button_frame, text="Add", width=110, command=self.add_record).grid(row=0, column=0, padx=15)
        round_button(button_frame, text="Update", width=110, command=self.update_record).grid(row=0, column=1, padx=15)
        round_button(button_frame, text="Delete", width=110, command=self.delete_record).grid(row=0, column=2, padx=15)
        round_button(button_frame, text="Clear", width=110, secondary=True, command=self.clear_fields).grid(row=0, column=3, padx=15)

        # Initial data fetch
        self.refresh_data()

    def _extract_model_from_inputs(self, require_id: bool = False) -> Employee:
        """Constructs an Employee instance from current form inputs."""
        empid_val = self._empid_entry.get().strip()
        empid = int(empid_val) if empid_val and empid_val.isdigit() else None
        if require_id and not empid:
            raise RecordNotFoundException("Please select an employee row from the table first.")

        return Employee(
            empid=empid,
            name=self._name_entry.get(),
            email=self._email_entry.get(),
            sex=self._sex_combobox.get(),
            dob=self._dob_date_entry.get_date(),
            contact=self._contact_entry.get(),
            employment_type=self._employment_combobox.get(),
            work_shift=self._shift_combobox.get(),
            address=self._address_text.get("1.0", END).strip(),
            dj=self._dj_date_entry.get_date(),
            salary=self._salary_entry.get(),
            role=self._role_combobox.get()
        )

    def add_record(self) -> None:
        """Functional Feature: Add Records."""
        try:
            employee = self._extract_model_from_inputs(require_id=False)
            new_id = self._repository.add(employee)
            messagebox.showinfo("Success", f"Employee '{employee.name}' added successfully (ID: {new_id}).")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def update_record(self) -> None:
        """Functional Feature: Edit Records."""
        try:
            employee = self._extract_model_from_inputs(require_id=True)
            self._repository.update(employee)
            messagebox.showinfo("Success", f"Employee ID {employee.empid} updated successfully.")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def delete_record(self) -> None:
        """Functional Feature: Delete Records."""
        selected = self._treeview.selection()
        if not selected:
            messagebox.showerror("Error", "Row not selected.")
            return

        empid_val = self._empid_entry.get().strip()
        if not empid_val:
            messagebox.showerror("Error", "Row not selected.")
            return

        confirm = messagebox.askyesno("Confirm Delete", "Do you really want to delete this employee record?")
        if not confirm:
            return

        try:
            self._repository.delete(int(empid_val))
            messagebox.showinfo("Success", "Record deleted successfully.")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def search_records(self) -> None:
        """Functional Feature: Search Records."""
        search_by = self._search_combobox.get()
        query = self._search_entry.get().strip()

        if search_by == "Search By":
            messagebox.showerror("Error", "No search option selected.")
            return
        if not query:
            messagebox.showerror("Error", "Enter a value in the search box.")
            return

        try:
            employees = self._repository.search(search_by, query)
            self._display_records(employees)
            if not employees:
                messagebox.showinfo("Search Results", "No matching employees found.")
        except Exception as err:
            self.handle_error(err)

    def refresh_data(self) -> None:
        """Functional Feature: Display Records."""
        try:
            employees = self._repository.get_all()
            self._display_records(employees)
            self._search_entry.delete(0, END)
            self._search_combobox.set("Search By")
        except Exception as err:
            self.handle_error(err)

    def _display_records(self, employees: list) -> None:
        self._treeview.delete(*self._treeview.get_children())
        for emp in employees:
            self._treeview.insert("", END, values=emp.to_treeview_tuple())

    def on_select_row(self, event=None) -> None:
        """Populates form fields when clicking a row in the table."""
        selection = self._treeview.selection()
        if not selection:
            return

        row = self._treeview.item(selection[0])["values"]
        if not row:
            return

        self._empid_entry.config(state="normal")
        self._empid_entry.delete(0, END)
        self._empid_entry.insert(0, str(row[0]))
        self._empid_entry.config(state="readonly")

        self._name_entry.delete(0, END)
        self._name_entry.insert(0, str(row[1]))

        self._email_entry.delete(0, END)
        self._email_entry.insert(0, str(row[2]))

        self._sex_combobox.set(str(row[3]))

        try:
            self._dob_date_entry.set_date(datetime.strptime(str(row[4]), "%Y-%m-%d"))
        except Exception:
            pass

        self._contact_entry.delete(0, END)
        self._contact_entry.insert(0, str(row[5]))

        self._employment_combobox.set(str(row[6]))
        self._shift_combobox.set(str(row[7]))

        self._address_text.delete("1.0", END)
        self._address_text.insert("1.0", str(row[8]))

        try:
            self._dj_date_entry.set_date(datetime.strptime(str(row[9]), "%Y-%m-%d"))
        except Exception:
            pass

        self._salary_entry.delete(0, END)
        self._salary_entry.insert(0, str(row[10]))

        self._role_combobox.set(str(row[11]))

    def clear_fields(self) -> None:
        """Resets all input fields."""
        self._empid_entry.config(state="normal")
        self._empid_entry.delete(0, END)
        self._empid_entry.config(state="readonly")
        self._name_entry.delete(0, END)
        self._email_entry.delete(0, END)
        self._sex_combobox.set("Select Sex")
        self._dob_date_entry.set_date(self._latest_dob())
        self._contact_entry.delete(0, END)
        self._employment_combobox.set("Select Type")
        self._shift_combobox.set("Select Work Shift")
        self._address_text.delete("1.0", END)
        self._dj_date_entry.set_date(date.today())
        self._salary_entry.delete(0, END)
        self._role_combobox.set("Select Role")
        self._treeview.selection_remove(*self._treeview.selection())