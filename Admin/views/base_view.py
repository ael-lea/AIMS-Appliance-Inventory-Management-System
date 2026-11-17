"""
Base Form View Module.
Demonstrates:
- Inheritance (BaseFormView inherits from Frame and IView)
- Abstraction (Enforces build_ui, refresh_data, clear_fields)
- Polymorphism (Overridable UI construction)
- Exception Handling (Unified error presentation)
"""
from abc import ABC, abstractmethod
from tkinter import *
from tkinter import messagebox, filedialog
from typing import Any, Optional, List, Dict
import customtkinter as ctk
from ..core.interfaces import IView
from ..core.exceptions import (
    AIMSException,
    ValidationError,
    EmptyFieldException,
    InvalidDataTypeException,
    DuplicateRecordException,
    RecordNotFoundException,
    FileStorageException,
    DatabaseOperationException
)
from .widgets import round_button, load_icon, NAVY, ACTIVE, BG, LIGHT


class BaseFormView(Frame, IView, ABC):
    """
    Abstract Base Class for all management views/forms in AIMS.
    Demonstrates Inheritance, Abstraction, and Polymorphism.
    """

    def __init__(self, parent_window: Tk, title: str, width: int = 1315, height: int = 720):
        super().__init__(parent_window, width=width, height=height, bg=BG)
        self._parent_window = parent_window
        self._title = title

        self.place(x=200, y=70)
        self.pack_propagate(False)

        # Header Section
        self._build_header()

        # Build view content
        self.build_ui()

    def _build_header(self) -> None:
        """Constructs common header and back button."""
        # Heading Label
        self._heading_label = Label(
            self,
            text=self._title,
            font=("Helvetica", 30, "bold"),
            bg=BG,
            fg=NAVY
        )
        self._heading_label.place(x=40, y=0)

        # Back Button
        self._back_icon = load_icon("back.png")
        self._back_btn = Button(
            self,
            image=self._back_icon,
            text="←",
            font=("Helvetica", 16, "bold"),
            fg=NAVY,
            bg=BG,
            bd=0,
            cursor="hand2",
            activebackground=BG,
            command=self.close_view
        )
        self._back_btn.place(x=0, y=10)

    def close_view(self) -> None:
        """Closes this form and returns to the dashboard home view."""
        self.place_forget()
        if hasattr(self._parent_window, "clear_active"):
            self._parent_window.clear_active()
        if hasattr(self._parent_window, "refresh_dashboard_counts"):
            self._parent_window.refresh_dashboard_counts()

    def handle_error(self, error: Exception) -> None:
        """
        Unified error handler mapping custom exceptions to friendly messages.
        Demonstrates comprehensive Exception Handling.
        """
        if isinstance(error, EmptyFieldException):
            messagebox.showwarning("Empty Fields", str(error.message))
        elif isinstance(error, (InvalidDataTypeException, ValidationError)):
            messagebox.showerror("Validation Error", str(error.message))
        elif isinstance(error, DuplicateRecordException):
            messagebox.showwarning("Duplicate Record", str(error.message))
        elif isinstance(error, RecordNotFoundException):
            messagebox.showinfo("Not Found", str(error.message))
        elif isinstance(error, FileStorageException):
            messagebox.showerror("File Error", str(error.message))
        elif isinstance(error, DatabaseOperationException):
            messagebox.showerror("Database Error", str(error.message))
        elif isinstance(error, AIMSException):
            messagebox.showerror("Application Error", str(error.message))
        else:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{error}")