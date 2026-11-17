"""
Sales and Analytics View.
Demonstrates:
- Inheritance (SalesView inherits from BaseFormView)
- Encapsulation (Encapsulates SalesRepository, ProductRepository, Matplotlib charts)
- Polymorphism (Overrides build_ui, refresh_data, clear_fields)
- Functional Features: Record Sale, Display Records, Analytics
"""
import os
import html
import tempfile
import webbrowser
from datetime import datetime, timedelta
from tkinter import *
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Tuple
import customtkinter as ctk
from tkcalendar import DateEntry

# Matplotlib configuration for Tkinter
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

from .base_view import BaseFormView
from .widgets import round_button, NAVY, ACTIVE, BG, LIGHT, CARD_COLORS, apply_rule, digits_only
from ..models.sale import Sale
from ..repositories.sales_repo import SalesRepository
from ..repositories.product_repo import ProductRepository
from ..core.exceptions import (
    ValidationError,
    EmptyFieldException,
    InvalidDataTypeException
)

class SalesView(BaseFormView):
    """
    Form view managing sales transactions, analytics charts, inventory deduction, and receipts.
    """

    CHART_COLORS = ["#053e87", "#2e86c1", "#1e8449", "#b9770e", "#7d3c98", "#7f8c8d"]

    def __init__(self, parent_window: Tk):
        self._sales_repo = SalesRepository()
        self._product_repo = ProductRepository()
        self._product_lookup: Dict[str, Any] = {}
        self._card_labels: Dict[str, Label] = {}
        super().__init__(parent_window, title="Sales & Analytics")

    def build_ui(self) -> None:
        """Constructs Sales form components."""
        # Filter & Export Toolbar
        toolbar = Frame(self, bg=BG)
        toolbar.pack(fill=X, padx=40, pady=(55, 5))

        Label(toolbar, text="Period:", font=("Helvetica", 11, "bold"), bg=BG, fg=NAVY).pack(side=LEFT, padx=5)

        self._period_combobox = ttk.Combobox(
            toolbar,
            values=["Today", "Last 7 Days", "Last 30 Days", "This Year", "All Time"],
            state="readonly",
            width=15,
            font=("Helvetica", 10)
        )
        self._period_combobox.set("Last 30 Days")
        self._period_combobox.pack(side=LEFT, padx=5)
        self._period_combobox.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        round_button(toolbar, "Refresh", self.refresh_data, width=90, secondary=True).pack(side=LEFT, padx=10)
        round_button(toolbar, "Print Sales Report", self.open_report_dialog, width=170).pack(side=LEFT, padx=5)

        # Metric Cards Frame
        cards_frame = Frame(self, bg=BG)
        cards_frame.pack(fill=X, padx=40, pady=(8, 5))

        card_titles = ["Total Revenue", "Total Orders", "Items Sold", "Avg Order Value"]
        for i, title in enumerate(card_titles):
            card = Frame(cards_frame, bg=CARD_COLORS[i], width=280, height=65)
            card.pack(side=LEFT, padx=8, expand=True, fill=X)
            card.pack_propagate(False)

            Label(card, text=title, font=("Helvetica", 10), bg=CARD_COLORS[i], fg="white").pack(pady=(6, 0))
            val_lbl = Label(card, text="0", font=("Helvetica", 16, "bold"), bg=CARD_COLORS[i], fg="white")
            val_lbl.pack()
            self._card_labels[title] = val_lbl

        # Charts Frame
        charts_frame = Frame(self, bg=BG)
        charts_frame.pack(pady=(8, 5))

        self._trend_fig, self._trend_canvas = self._make_chart(charts_frame)
        self._top_fig, self._top_canvas = self._make_chart(charts_frame)
        self._cat_fig, self._cat_canvas = self._make_chart(charts_frame)

        # Recent Sales Table Frame
        table_frame = Frame(self, bg=BG)
        table_frame.pack(fill=BOTH, expand=True, padx=40, pady=(8, 5))

        scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL)
        style = ttk.Style()
        style.configure("Sales.Treeview", rowheight=20)

        self._treeview = ttk.Treeview(
            table_frame,
            style="Sales.Treeview",
            columns=("id", "date", "product", "category", "qty", "price", "total"),
            show="headings",
            height=3,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self._treeview.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self._treeview.pack(fill=BOTH, expand=True)

        headings = {
            "id": ("Sale ID", 70),
            "date": ("Date", 160),
            "product": ("Product", 240),
            "category": ("Category", 150),
            "qty": ("Qty", 70),
            "price": ("Unit Price", 120),
            "total": ("Total", 130)
        }
        for col, (text, width) in headings.items():
            self._treeview.heading(col, text=text)
            self._treeview.column(col, width=width, anchor=CENTER)

        # Record Sale Input Bar Frame
        record_frame = Frame(self, bg=BG)
        record_frame.pack(pady=(8, 20))

        Label(record_frame, text="Product:", font=("Helvetica", 11, "bold"), bg=BG).pack(side=LEFT, padx=5)
        self._product_combobox = ttk.Combobox(record_frame, state="readonly", width=38, font=("Helvetica", 10))
        self._product_combobox.pack(side=LEFT, padx=5)

        Label(record_frame, text="Qty:", font=("Helvetica", 11, "bold"), bg=BG).pack(side=LEFT, padx=5)
        self._qty_entry = Entry(record_frame, font=("Helvetica", 11), width=6)
        self._qty_entry.insert(0, "1")
        self._qty_entry.pack(side=LEFT, padx=5)
        apply_rule(self._qty_entry, digits_only(9))

        round_button(record_frame, "Record Sale", self.add_record, width=130).pack(side=LEFT, padx=10)

        # Initial data load
        self.load_products()
        self.refresh_data()

    def _make_chart(self, parent) -> Tuple[Figure, FigureCanvasTkAgg]:
        fig = Figure(figsize=(3.6, 1.8), dpi=100)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(side=LEFT, padx=4)
        return fig, canvas

    def load_products(self) -> None:
        """Populates product selection dropdown with currently in-stock inventory items."""
        self._product_lookup.clear()
        try:
            products = self._product_repo.get_in_stock()
            values = []
            for p in products:
                label = f"{p.name}  (₱{p.price:,.2f}, stock: {p.quantity})"
                self._product_lookup[label] = p
                values.append(label)
            self._product_combobox["values"] = values
            self._product_combobox.set("")
        except Exception:
            pass

    def add_record(self) -> None:
        """Functional Feature: Add Records (Record Sale)."""
        selected_label = self._product_combobox.get().strip()
        product = self._product_lookup.get(selected_label)
        if not product:
            messagebox.showwarning("Product Required", "Please select a product from the list.")
            return

        qty_str = self._qty_entry.get().strip()
        if not qty_str or not qty_str.isdigit():
            messagebox.showwarning("Invalid Quantity", "Please enter a valid whole number for quantity.")
            return

        qty = int(qty_str)
        if qty <= 0:
            messagebox.showwarning("Invalid Quantity", "Quantity must be greater than zero.")
            return

        if qty > product.quantity:
            messagebox.showwarning("Out of Stock", f"Only {product.quantity} units available.")
            return

        try:
            sale = Sale(
                product_id=product.product_id,
                product_name=product.name,
                category=product.category,
                quantity=qty,
                unit_price=product.price
            )
            new_id = self._sales_repo.add(sale)
            messagebox.showinfo("Success", f"Sale #{new_id} recorded successfully (Total: ₱{sale.total:,.2f})!")

            # Reload and clear
            self.load_products()
            self.refresh_data()
            self.clear_fields()
        except Exception as err:
            self.handle_error(err)

    def refresh_data(self) -> None:
        """Functional Feature: Display Records and Update Visual Analytics."""
        period = self._period_combobox.get()
        try:
            # 1. Update Metrics Cards
            metrics = self._sales_repo.get_summary_metrics(period)
            self._card_labels["Total Revenue"].config(text=f"₱{metrics['revenue']:,.2f}")
            self._card_labels["Total Orders"].config(text=f"{metrics['orders']:,}")
            self._card_labels["Items Sold"].config(text=f"{metrics['items_sold']:,}")
            self._card_labels["Avg Order Value"].config(text=f"₱{metrics['avg_order']:,.2f}")

            # 2. Update Charts
            trend_rows = self._sales_repo.get_trend_chart_data(period)
            self._draw_trend(trend_rows)

            top_rows = self._sales_repo.get_top_products_data(period)
            self._draw_top_products(top_rows)

            cat_rows = self._sales_repo.get_category_chart_data(period)
            self._draw_categories(cat_rows)

            # 3. Update Table
            sales = self._sales_repo.get_filtered_sales(period)
            self._treeview.delete(*self._treeview.get_children())
            for s in sales:
                self._treeview.insert("", "end", values=s.to_treeview_tuple())

        except Exception as err:
            self.handle_error(err)

    def _draw_trend(self, rows: list) -> None:
        self._trend_fig.clear()
        ax = self._trend_fig.add_subplot(111)
        if not rows:
            self._no_data(ax, "Revenue Over Time")
        else:
            dates = [r[0] for r in rows]
            totals = [float(r[1]) for r in rows]
            ax.plot(dates, totals, marker="o", color=self.CHART_COLORS[0], linewidth=2)
            ax.fill_between(dates, totals, alpha=0.15, color=self.CHART_COLORS[0])
            ax.set_title("Revenue Over Time", fontsize=9, fontweight="bold")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            ax.tick_params(labelsize=7)
            self._trend_fig.autofmt_xdate(rotation=30)
            ax.grid(alpha=0.3)
        self._trend_fig.tight_layout()
        self._trend_canvas.draw()

    def _draw_top_products(self, rows: list) -> None:
        self._top_fig.clear()
        ax = self._top_fig.add_subplot(111)
        if not rows:
            self._no_data(ax, "Top Selling Products")
        else:
            names = [str(r[0])[:14] for r in rows]
            qty = [int(r[1]) for r in rows]
            ax.barh(names, qty, color=self.CHART_COLORS[1])
            ax.invert_yaxis()
            ax.set_title("Top Selling Products (Qty)", fontsize=9, fontweight="bold")
            ax.tick_params(labelsize=7)
            ax.grid(axis="x", alpha=0.3)
        self._top_fig.tight_layout()
        self._top_canvas.draw()

    def _draw_categories(self, rows: list) -> None:
        self._cat_fig.clear()
        ax = self._cat_fig.add_subplot(111)
        if not rows:
            self._no_data(ax, "Sales by Category")
        else:
            labels = [str(r[0]) for r in rows[:5]]
            values = [float(r[1]) for r in rows[:5]]
            if len(rows) > 5:
                labels.append("Others")
                values.append(sum(float(r[1]) for r in rows[5:]))
            ax.pie(values, labels=labels, autopct="%1.0f%%", colors=self.CHART_COLORS[:len(values)], textprops={"fontsize": 7}, startangle=90)
            ax.set_title("Sales by Category", fontsize=9, fontweight="bold")
        self._cat_fig.tight_layout()
        self._cat_canvas.draw()

    @staticmethod
    def _no_data(ax, title: str) -> None:
        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes, color="gray")
        ax.set_xticks([])
        ax.set_yticks([])

    # ---------------- PRINT SALES REPORT ----------------

    @staticmethod
    def _peso(value) -> str:
        return f"₱{float(value):,.2f}"

    def open_report_dialog(self) -> None:
        """Dialog to choose the date range of the report."""
        dialog = Toplevel(self)
        dialog.title("Print Sales Report")

        w, h = 340, 190
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.resizable(False, False)
        dialog.config(bg=BG)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        Label(dialog, text="Choose the dates to print",
              font=("Helvetica", 12, "bold"), bg=BG, fg=NAVY).pack(pady=(15, 10))

        date_frame = Frame(dialog, bg=BG)
        date_frame.pack()

        Label(date_frame, text="From:", font=("Helvetica", 11), bg=BG).grid(
            row=0, column=0, padx=8, pady=6, sticky="w")
        from_entry = DateEntry(date_frame, width=14, font=("Helvetica", 11), date_pattern="yyyy-mm-dd")
        from_entry.set_date(datetime.now() - timedelta(days=6))
        from_entry.grid(row=0, column=1, pady=6)

        Label(date_frame, text="To:", font=("Helvetica", 11), bg=BG).grid(
            row=1, column=0, padx=8, pady=6, sticky="w")
        to_entry = DateEntry(date_frame, width=14, font=("Helvetica", 11), date_pattern="yyyy-mm-dd")
        to_entry.grid(row=1, column=1, pady=6)

        def print_now():
            start, end = from_entry.get_date(), to_entry.get_date()
            if start > end:
                messagebox.showwarning(
                    "Date Error", "The 'From' date cannot be after the 'To' date.", parent=dialog)
                return
            dialog.destroy()
            self.print_sales_report(start, end)

        button_row = Frame(dialog, bg=BG)
        button_row.pack(pady=12)
        round_button(button_row, "Print", print_now, width=100).pack(side=LEFT, padx=8)
        round_button(button_row, "Cancel", dialog.destroy, width=100, secondary=True).pack(side=LEFT, padx=8)

    def print_sales_report(self, start_date, end_date) -> None:
        """Builds an HTML report, opens it in the browser and shows the print dialog."""
        try:
            data = self._sales_repo.get_report_data(start_date, end_date)
        except Exception as err:
            self.handle_error(err)
            return

        if not data["details"]:
            messagebox.showinfo("Sales Report", "There are no sales between those dates.")
            return

        peso = self._peso
        printed_at = datetime.now()

        daily_rows = "".join(
            f"<tr><td>{d.strftime('%a, %b %d')}</td><td>{c}</td><td>{q}</td>"
            f"<td class='r'>{peso(t)}</td></tr>"
            for d, c, q, t in data["daily"]
        )
        top_rows = "".join(
            f"<tr><td>{html.escape(str(n))}</td><td>{q}</td><td class='r'>{peso(t)}</td></tr>"
            for n, q, t in data["top"]
        )
        detail_rows = "".join(
            f"<tr><td>{sid}</td><td>{d.strftime('%Y-%m-%d %H:%M')}</td>"
            f"<td>{html.escape(str(n))}</td><td>{html.escape(str(c or ''))}</td>"
            f"<td>{q}</td><td class='r'>{peso(u)}</td><td class='r'>{peso(t)}</td></tr>"
            for sid, d, n, c, q, u, t in data["details"]
        )

        report = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Sales Report</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 30px; color: #222; }}
  h1 {{ color: #012148; margin-bottom: 0; }}
  h2 {{ color: #012148; margin-top: 28px; border-bottom: 2px solid #012148; padding-bottom: 4px; }}
  .sub {{ color: #666; margin-top: 4px; }}
  .cards {{ display: flex; gap: 12px; margin-top: 18px; }}
  .card {{ flex: 1; background: #012148; color: white; padding: 12px; border-radius: 6px; text-align: center; }}
  .card b {{ display: block; font-size: 20px; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #012148; color: white; padding: 6px; text-align: left; }}
  td {{ padding: 5px 6px; border-bottom: 1px solid #ddd; }}
  .r {{ text-align: right; }}
  @media print {{ .card {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                  th {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
</style></head><body>
<h1>Sales Report</h1>
<div class="sub">{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}
 &nbsp;|&nbsp; Printed {printed_at.strftime('%B %d, %Y %I:%M %p')}</div>

<div class="cards">
  <div class="card">Total Revenue<b>{peso(data['revenue'])}</b></div>
  <div class="card">Total Orders<b>{data['orders']}</b></div>
  <div class="card">Items Sold<b>{data['items_sold']}</b></div>
  <div class="card">Average Order<b>{peso(data['avg_order'])}</b></div>
</div>

<h2>Daily Summary</h2>
<table><tr><th>Date</th><th>Orders</th><th>Items</th><th class="r">Revenue</th></tr>{daily_rows}</table>

<h2>Top Selling Products</h2>
<table><tr><th>Product</th><th>Qty Sold</th><th class="r">Revenue</th></tr>{top_rows}</table>

<h2>All Sales</h2>
<table><tr><th>ID</th><th>Date</th><th>Product</th><th>Category</th><th>Qty</th>
<th class="r">Unit Price</th><th class="r">Total</th></tr>{detail_rows}</table>

<script>window.onload = function() {{ window.print(); }};</script>
</body></html>"""

        path = os.path.join(tempfile.gettempdir(), "sales_report.html")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(report)
        except OSError as err:
            messagebox.showerror("File Error", f"Could not create the report:\n{err}")
            return

        # opens in the browser and shows the print dialog
        # (choose "Save as PDF" there if you want a PDF copy)
        webbrowser.open("file:///" + path.replace("\\", "/"))

    def clear_fields(self) -> None:
        self._product_combobox.set("")
        self._qty_entry.delete(0, END)
        self._qty_entry.insert(0, "1")