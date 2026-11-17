"""
Product Management View.
Demonstrates:
- Inheritance (ProductView inherits from BaseFormView)
- Encapsulation (Encapsulates ProductRepository and image cache)
- Polymorphism (Overrides build_ui, refresh_data, clear_fields)
- Functional Features: Add, Edit, Delete, Search, Display
- Image thumbnail rendering in Tkinter Treeview
"""
import os
import re
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict
from PIL import Image, ImageTk
from .base_view import BaseFormView
from .widgets import round_button, safe_load_image, NAVY, ACTIVE, BG, LIGHT, apply_rule, letters_only
from ..models.product import Product
from ..repositories.product_repo import ProductRepository
from ..core.exceptions import (
    ValidationError,
    EmptyFieldException,
    InvalidDataTypeException,
    DuplicateRecordException,
    RecordNotFoundException
)

class ProductView(BaseFormView):
    """
    Form view managing product inventory, stock levels, pricing, and product photos.
    """

    IMAGE_SIZE = (80, 80)

    def __init__(self, parent_window: Tk):
        self._repository = ProductRepository()
        self._product_images: Dict[int, ImageTk.PhotoImage] = {}
        super().__init__(parent_window, title="Product Details")

    def build_ui(self) -> None:
        """Constructs Product form components."""
        # Top Search Frame
        search_frame = Frame(self, bg=BG)
        search_frame.pack(pady=(30, 10))

        self._search_combobox = ttk.Combobox(
            search_frame,
            values=("Product ID", "Name", "Category"),
            state="readonly",
            width=15
        )
        self._search_combobox.set("Name")
        self._search_combobox.pack(side=LEFT, padx=5)

        self._search_entry = Entry(search_frame, font=("Helvetica", 11), width=25)
        self._search_entry.pack(side=LEFT, padx=5)

        round_button(search_frame, "Search", self.search_product, width=95).pack(side=LEFT, padx=5)
        round_button(search_frame, "Show All", self.refresh_data, width=95, secondary=True).pack(side=LEFT, padx=5)

        # Table Frame
        table_frame = Frame(self, bg=BG)
        table_frame.pack(fill=X, padx=20, pady=5)

        y_scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL)
        x_scrollbar = ttk.Scrollbar(table_frame, orient=HORIZONTAL)

        style = ttk.Style()
        style.configure("Product.Treeview", rowheight=60)

        self._treeview = ttk.Treeview(
            table_frame,
            style="Product.Treeview",
            columns=("id", "name", "category", "price", "quantity"),
            show="tree headings",
            height=6,
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )

        y_scrollbar.config(command=self._treeview.yview)
        x_scrollbar.config(command=self._treeview.xview)
        y_scrollbar.pack(side=RIGHT, fill=Y)
        x_scrollbar.pack(side=BOTTOM, fill=X)
        self._treeview.pack(fill=BOTH, expand=True)

        self._treeview.heading("#0", text="Image")
        self._treeview.column("#0", width=100, minwidth=100, stretch=False, anchor=CENTER)

        headings = {
            "id": ("Product ID", 90),
            "name": ("Product Name", 180),
            "category": ("Category", 130),
            "price": ("Price", 100),
            "quantity": ("Quantity", 100)
        }
        for col_id, (col_text, col_width) in headings.items():
            self._treeview.heading(col_id, text=col_text)
            self._treeview.column(col_id, width=col_width, anchor=CENTER)

        self._treeview.bind("<<TreeviewSelect>>", self.on_select_row)

        # Form Input Fields Frame
        form_frame = Frame(self, bg=BG)
        form_frame.place(x=230, y=500)

        # Input filters
        only_price_cmd = (self._parent_window.register(self._only_price), "%P")
        only_qty_cmd = (self._parent_window.register(self._only_quantity), "%P")

        # Row 0: Name, Category, Price
        Label(form_frame, text="Product Name:", font=("Helvetica", 11), bg=BG).grid(row=0, column=0, sticky=E, padx=3, pady=10)
        self._name_entry = Entry(form_frame, font=("Helvetica", 11), width=22)
        self._name_entry.grid(row=0, column=1, padx=3, pady=10)

        Label(form_frame, text="Category:", font=("Helvetica", 11), bg=BG).grid(row=0, column=2, sticky=E, padx=3, pady=10)
        self._category_entry = Entry(form_frame, font=("Helvetica", 11), width=22)
        self._category_entry.grid(row=0, column=3, padx=3, pady=10)
        apply_rule(self._category_entry, letters_only)

        Label(form_frame, text="Price:", font=("Helvetica", 11), bg=BG).grid(row=0, column=4, sticky=E, padx=3, pady=10)
        self._price_entry = Entry(form_frame, font=("Helvetica", 11), width=15, validate="key", validatecommand=only_price_cmd)
        self._price_entry.grid(row=0, column=5, padx=3, pady=10)

        # Row 1: Quantity, Image Path, Browse
        Label(form_frame, text="Quantity:", font=("Helvetica", 11), bg=BG).grid(row=1, column=0, sticky=E, padx=3, pady=10)
        self._qty_entry = Entry(form_frame, font=("Helvetica", 11), width=22, validate="key", validatecommand=only_qty_cmd)
        self._qty_entry.grid(row=1, column=1, padx=3, pady=10)

        Label(form_frame, text="Product Image:", font=("Helvetica", 11), bg=BG).grid(row=1, column=2, sticky=E, padx=3, pady=10)
        self._image_path_entry = Entry(form_frame, font=("Helvetica", 10), width=30)
        self._image_path_entry.grid(row=1, column=3, columnspan=2, padx=3, pady=10)

        round_button(form_frame, "Browse", self.browse_image, width=100, secondary=True).grid(row=1, column=5, padx=3, pady=5)

        # Action Buttons Frame
        button_frame = Frame(self, bg=BG)
        button_frame.pack(side=BOTTOM, pady=(10, 80))

        round_button(button_frame, "Add Product", self.add_record, width=150).pack(side=LEFT, padx=6)
        round_button(button_frame, "Update Product", self.update_record, width=150).pack(side=LEFT, padx=6)
        round_button(button_frame, "Delete Product", self.delete_record, width=150).pack(side=LEFT, padx=6)
        round_button(button_frame, "Clear", self.clear_fields, width=150, secondary=True).pack(side=LEFT, padx=6)

        # Initial data fetch
        self.refresh_data()

    @staticmethod
    def _only_price(value: str) -> bool:
        return re.fullmatch(r"[0-9]{0,8}(\.[0-9]{0,2})?", value) is not None

    @staticmethod
    def _only_quantity(value: str) -> bool:
        return re.fullmatch(r"[0-9]{0,9}", value) is not None

    def browse_image(self) -> None:
        """Opens file dialog for product image."""
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Product Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
        )
        if path:
            self._image_path_entry.delete(0, END)
            self._image_path_entry.insert(0, path)

    def _extract_model_from_inputs(self, require_id: bool = False) -> Product:
        selected = self._treeview.selection()
        product_id = int(selected[0]) if selected and selected[0].isdigit() else None
        if require_id and not product_id:
            raise RecordNotFoundException("Please select a product from the table to update.")

        image_path = self._image_path_entry.get().strip()
        if image_path and not os.path.isfile(image_path):
            raise InvalidDataTypeException("The selected image file does not exist on disk.", field_name="image_path")

        return Product(
            product_id=product_id,
            name=self._name_entry.get(),
            category=self._category_entry.get(),
            price=self._price_entry.get(),
            quantity=self._qty_entry.get(),
            image_path=image_path
        )

    def add_record(self) -> None:
        """Functional Feature: Add Records."""
        if self._treeview.selection():
            messagebox.showwarning("Product Selected", "This product already exists. Click Clear to add a new one, or use Update.")
            return

        try:
            image_path = self._image_path_entry.get().strip()
            if not image_path:
                raise EmptyFieldException("Please select a product image before adding.")

            product = self._extract_model_from_inputs(require_id=False)
            new_id = self._repository.add(product)
            messagebox.showinfo("Success", f"Product '{product.name}' added successfully (ID: {new_id})!")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def update_record(self) -> None:
        """Functional Feature: Edit Records."""
        try:
            product = self._extract_model_from_inputs(require_id=True)
            self._repository.update(product)
            messagebox.showinfo("Success", f"Product '{product.name}' updated successfully!")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def delete_record(self) -> None:
        """Functional Feature: Delete Records."""
        selected = self._treeview.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a product to delete.")
            return

        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this product?")
        if not confirm:
            return

        try:
            self._repository.delete(int(selected[0]))
            messagebox.showinfo("Success", "Product deleted successfully!")
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def search_product(self) -> None:
        """Functional Feature: Search Records."""
        search_by = self._search_combobox.get()
        query = self._search_entry.get().strip()

        if not query:
            messagebox.showwarning("Search Error", "Please enter something to search.")
            return

        try:
            products = self._repository.search(search_by, query)
            self._display_records(products)
            if not products:
                messagebox.showinfo("Search Result", "No matching products found.")
        except Exception as err:
            self.handle_error(err)

    def refresh_data(self) -> None:
        """Functional Feature: Display Records."""
        try:
            products = self._repository.get_all()
            self._display_records(products)
            self._search_entry.delete(0, END)
            self._search_combobox.set("Name")
        except Exception as err:
            self.handle_error(err)

    def _display_records(self, products: list) -> None:
        self._treeview.delete(*self._treeview.get_children())
        self._product_images.clear()

        for prod in products:
            photo = safe_load_image(prod.image_path, size=self.IMAGE_SIZE)
            if photo:
                self._product_images[prod.product_id] = photo

            self._treeview.insert(
                "",
                "end",
                iid=str(prod.product_id),
                image=photo or "",
                values=prod.to_treeview_tuple()
            )

    def on_select_row(self, event=None) -> None:
        """Populates form when selecting a table row."""
        selected = self._treeview.selection()
        if not selected:
            return

        prod_id = selected[0]
        data = self._treeview.item(prod_id, "values")
        if not data:
            return

        self._name_entry.delete(0, END)
        self._name_entry.insert(0, data[1])

        self._category_entry.delete(0, END)
        self._category_entry.insert(0, data[2])

        self._price_entry.delete(0, END)
        self._price_entry.insert(0, data[3])

        self._qty_entry.delete(0, END)
        self._qty_entry.insert(0, data[4])

        # Fetch image path from repo
        try:
            prod = self._repository.get_by_id(int(prod_id))
            self._image_path_entry.delete(0, END)
            if prod and prod.image_path:
                self._image_path_entry.insert(0, prod.image_path)
        except Exception:
            pass

    def clear_fields(self) -> None:
        """Resets all form input fields."""
        self._name_entry.delete(0, END)
        self._category_entry.delete(0, END)
        self._price_entry.delete(0, END)
        self._qty_entry.delete(0, END)
        self._image_path_entry.delete(0, END)
        if self._treeview.selection():
            self._treeview.selection_remove(*self._treeview.selection())