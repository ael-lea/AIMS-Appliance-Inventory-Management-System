"""Sales Overview page: totals, completed transactions and payment breakdown."""
import csv
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from cashier.config import Theme
from cashier.database.connection import DatabaseError
from cashier.database.sales_repository import SalesPeriod
from cashier.ui.base_page import BasePage
from cashier.ui.widgets import make_tree, show_db_error, styled_button
from cashier.utils import peso

UP_COLOR = "#1E8449"
DOWN_COLOR = "#C0392B"
METHOD_COLORS = ("#2E86C1", "#28B463", "#F5B041", "#AF7AC5", "#EC7063", "#5DADE2")
LIST_LIMIT = 300          # most recent completed orders shown in the table
AUTO_REFRESH_MS = 60_000  # re-query every minute


def _hour_label(hour):
    return f"{hour % 12 or 12}{'a' if hour < 12 else 'p'}"


class SalesOverviewPage(BasePage):
    HEADING = "Sales Overview"

    STAT_CARDS = (("Total Sales", "sales"), ("Transactions", "transactions"),
                  ("Items Sold", "items"), ("Average Order", "average"))

    def __init__(self, window, navigate, context):
        super().__init__(window, navigate, context)
        self._stat_labels = {}
        self._delta_labels = {}
        self._after_id = None
        self._report = None          # last loaded data, used by Export

    def _build(self):
        self._build_filter_bar()
        self._build_stat_cards()
        self._build_transactions_table()
        self._build_breakdown_canvas()
        self._build_hourly_canvas()
        self._build_best_sellers()
        self.refresh()

    # ---- layout ----------------------------------------------------------------
    def _build_filter_bar(self):
        bar = tk.Frame(self._frame, bg=Theme.BG)
        bar.place(x=25, y=55)
        tk.Label(bar, text="Sales Period:", bg=Theme.BG, font=("Helvetica", 10)).pack(
            side=tk.LEFT, padx=5)
        self._period_var = tk.StringVar(value="Today")
        period_box = ttk.Combobox(bar, textvariable=self._period_var, state="readonly",
                                  width=15, values=SalesPeriod.LABELS)
        period_box.pack(side=tk.LEFT, padx=5)
        period_box.bind("<<ComboboxSelected>>", self.refresh)
        styled_button(bar, "Refresh", self.refresh, True, 10).pack(side=tk.LEFT, padx=8)
        styled_button(bar, "Export", self._export, True, 10).pack(side=tk.LEFT, padx=4)

        self._updated_label = tk.Label(bar, text="", bg=Theme.BG, fg=Theme.MUTED,
                                       font=("Helvetica", 9))
        self._updated_label.pack(side=tk.LEFT, padx=(12, 4))
        self._auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text="Auto-refresh", variable=self._auto_var, bg=Theme.BG,
                       activebackground=Theme.BG, font=("Helvetica", 9),
                       command=self._schedule_auto_refresh).pack(side=tk.LEFT)

    def _build_stat_cards(self):
        stats = tk.Frame(self._frame, bg=Theme.BG)
        stats.place(x=25, y=105, width=1260, height=110)
        for i, (title, key) in enumerate(self.STAT_CARDS):
            box = tk.Frame(stats, bg=Theme.CARD, highlightbackground=Theme.BORDER,
                           highlightthickness=1, width=295, height=95)
            box.place(x=i * 315, y=0)
            tk.Label(box, text=title, bg=Theme.CARD, fg=Theme.MUTED,
                     font=("Helvetica", 10, "bold")).place(x=15, y=10)
            self._stat_labels[key] = tk.Label(box, text="...", bg=Theme.CARD, fg=Theme.NAVY,
                                              font=("Helvetica", 19, "bold"))
            self._stat_labels[key].place(x=15, y=32)
            self._delta_labels[key] = tk.Label(box, text="", bg=Theme.CARD, fg=Theme.MUTED,
                                               font=("Helvetica", 9))
            self._delta_labels[key].place(x=15, y=68)

    def _build_transactions_table(self):
        tk.Label(self._frame, text="Completed Transactions", bg=Theme.BG, fg=Theme.NAVY,
                 font=("Helvetica", 13, "bold")).place(x=25, y=245)
        tk.Label(self._frame, text="Double-click a row to open its receipt", bg=Theme.BG,
                 fg=Theme.MUTED, font=("Helvetica", 9)).place(x=240, y=251)
        # Column widths add up to less than the 800px wrapper so no header is clipped.
        wrap, self._tree = make_tree(
            self._frame, ("id", "date", "items", "total", "method", "ship"),
            ("Order ID", "Date", "Items", "Total", "Payment Method", "Shipment"),
            (105, 190, 60, 130, 150, 135), height=5)
        for column in ("items", "total"):
            self._tree.column(column, anchor=tk.E)          # values right-aligned
            self._tree.heading(column, anchor=tk.CENTER)    # titles centered
        wrap.place(x=25, y=280, width=800, height=160)
        self._tree.bind("<Double-1>", self._open_receipt)

        # Footer: totals of the rows currently listed
        footer = tk.Frame(self._frame, bg=Theme.CARD, highlightbackground=Theme.BORDER,
                          highlightthickness=1)
        footer.place(x=25, y=443, width=800, height=26)
        self._footer_label = tk.Label(footer, text="", bg=Theme.CARD, fg=Theme.NAVY,
                                      font=("Helvetica", 10, "bold"), anchor="w", padx=10)
        self._footer_label.pack(fill=tk.BOTH, expand=True)

    def _build_breakdown_canvas(self):
        tk.Label(self._frame, text="Payment Breakdown", bg=Theme.BG, fg=Theme.NAVY,
                 font=("Helvetica", 13, "bold")).place(x=865, y=245)
        self._canvas = tk.Canvas(self._frame, bg=Theme.CARD, highlightbackground=Theme.BORDER,
                                 highlightthickness=1, width=390, height=185)
        self._canvas.place(x=865, y=280)

    def _build_hourly_canvas(self):
        tk.Label(self._frame, text="Sales by Hour", bg=Theme.BG, fg=Theme.NAVY,
                 font=("Helvetica", 13, "bold")).place(x=25, y=475)
        self._hourly_canvas = tk.Canvas(self._frame, bg=Theme.CARD,
                                        highlightbackground=Theme.BORDER,
                                        highlightthickness=1, width=800, height=145)
        self._hourly_canvas.place(x=25, y=500)

    def _build_best_sellers(self):
        tk.Label(self._frame, text="Best Sellers", bg=Theme.BG, fg=Theme.NAVY,
                 font=("Helvetica", 13, "bold")).place(x=865, y=475)
        wrap, self._best_tree = make_tree(
            self._frame, ("product", "qty", "revenue"),
            ("Product", "Qty", "Revenue"), (180, 60, 120), height=5)
        for column in ("qty", "revenue"):
            self._best_tree.column(column, anchor=tk.E)          # values right-aligned
            self._best_tree.heading(column, anchor=tk.CENTER)    # titles centered
        wrap.place(x=865, y=500, width=390, height=145)

    # ---- data ---------------------------------------------------------------------
    def refresh(self, event=None, silent=False):
        period = SalesPeriod(self._period_var.get())
        try:
            sales = self._context.sales
            summary = sales.summary(period)
            previous = sales.previous_summary(period)
            orders = sales.completed_orders(period, LIST_LIMIT)
            shipments = sales.shipment_statuses(period)
            methods = sales.payment_breakdown(period)
            top_products = sales.top_products(period)
            by_hour = sales.sales_by_hour(period)
        except DatabaseError as error:
            if silent:
                self._updated_label.config(text="Update failed - will retry")
            else:
                show_db_error(error)
            self._schedule_auto_refresh()
            return

        # Keep what was loaded so Export writes exactly what is on screen.
        self._report = {"period": self._period_var.get(), "summary": summary,
                        "orders": orders, "shipments": shipments,
                        "methods": methods, "top": top_products}

        self._stat_labels["sales"].config(text=peso(summary.total_sales))
        self._stat_labels["transactions"].config(text=str(summary.transactions))
        self._stat_labels["items"].config(text=str(summary.items_sold))
        self._stat_labels["average"].config(text=peso(summary.average_order))
        self._show_deltas(summary, previous, period.compare_label)

        self._tree.delete(*self._tree.get_children())
        for row in orders:
            self._tree.insert("", tk.END, values=(
                row.order_id,
                row.order_date.strftime("%b %d, %Y %I:%M %p"),
                row.item_count,
                peso(row.total),
                row.payment_method,
                shipments.get(str(row.order_id), "Not shipped")
            ))
        self._update_footer(orders)

        self._best_tree.delete(*self._best_tree.get_children())
        for name, qty, revenue in top_products:
            self._best_tree.insert("", tk.END, values=(name, qty, peso(revenue)))

        self._draw_breakdown(methods)
        self._draw_hourly(by_hour)

        self._updated_label.config(
            text=f"Last updated {datetime.now().strftime('%I:%M %p').lstrip('0')}")
        self._schedule_auto_refresh()

    # ---- auto refresh -------------------------------------------------------------
    def _schedule_auto_refresh(self):
        """(Re)start the one-minute timer, or stop it if auto-refresh is off."""
        if self._after_id is not None:
            self._frame.after_cancel(self._after_id)
            self._after_id = None
        if self._auto_var.get():
            self._after_id = self._frame.after(AUTO_REFRESH_MS, self._auto_refresh)

    def _auto_refresh(self):
        self._after_id = None
        if not self._frame.winfo_exists():
            return
        if not self._frame.winfo_viewable():      # page not on screen: skip the query
            self._schedule_auto_refresh()
            return
        self.refresh(silent=True)

    # ---- export -------------------------------------------------------------------
    def _export(self):
        """Save the currently loaded report as CSV or PDF (chosen by file extension)."""
        if not self._report:
            messagebox.showinfo("Export", "Nothing to export yet.")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        period = self._report["period"].replace(" ", "_")
        path = filedialog.asksaveasfilename(
            title="Export sales report", defaultextension=".csv",
            initialfile=f"sales_{period}_{stamp}",
            filetypes=[("CSV file", "*.csv"), ("PDF file", "*.pdf")])
        if not path:
            return
        try:
            if path.lower().endswith(".pdf"):
                self._export_pdf(path)
            else:
                self._export_csv(path)
        except ImportError:
            messagebox.showerror("Export", "PDF export needs reportlab.\n\n"
                                           "Install it with:  pip install reportlab")
            return
        except OSError as error:
            messagebox.showerror("Export", f"Could not write the file:\n{error}")
            return
        messagebox.showinfo("Export", f"Report saved to:\n{path}")

    def _export_csv(self, path):
        r = self._report
        s = r["summary"]
        # utf-8-sig so Excel opens it cleanly; plain numbers so totals can be summed
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            out = csv.writer(handle)
            out.writerow(["Sales Report", r["period"],
                          "Generated " + datetime.now().strftime("%b %d, %Y %I:%M %p")])
            out.writerow([])
            out.writerow(["Total Sales", "Transactions", "Items Sold", "Average Order"])
            out.writerow([f"{s.total_sales:.2f}", s.transactions, s.items_sold,
                          f"{s.average_order:.2f}"])
            out.writerow([])
            out.writerow(["Order ID", "Date", "Items", "Total", "Payment Method", "Shipment"])
            for o in r["orders"]:
                out.writerow([o.order_id, o.order_date.strftime("%Y-%m-%d %H:%M"),
                              o.item_count, f"{float(o.total):.2f}", o.payment_method,
                              r["shipments"].get(str(o.order_id), "Not shipped")])
            out.writerow([])
            out.writerow(["Payment Method", "Orders", "Amount"])
            for method, count, amount in r["methods"]:
                out.writerow([method, count, f"{float(amount):.2f}"])
            out.writerow([])
            out.writerow(["Best Seller", "Qty", "Revenue"])
            for name, qty, revenue in r["top"]:
                out.writerow([name, qty, f"{float(revenue):.2f}"])

    def _export_pdf(self, path):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                        TableStyle)

        r = self._report
        s = r["summary"]
        money = lambda v: f"PHP {float(v):,.2f}"    # built-in PDF fonts have no peso glyph
        styles = getSampleStyleSheet()

        def table(rows, widths, right_cols=()):
            t = Table(rows, colWidths=widths, repeatRows=1)
            style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
                     ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                     ("FONTSIZE", (0, 0), (-1, -1), 8),
                     ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                     ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                      [colors.white, colors.HexColor("#F4F6F8")])]
            style += [("ALIGN", (c, 0), (c, -1), "RIGHT") for c in right_cols]
            t.setStyle(TableStyle(style))
            return t

        story = [Paragraph(f"Sales Report - {r['period']}", styles["Title"]),
                 Paragraph("Generated " + datetime.now().strftime("%b %d, %Y %I:%M %p"),
                           styles["Normal"]),
                 Spacer(1, 10),
                 table([["Total Sales", "Transactions", "Items Sold", "Average Order"],
                        [money(s.total_sales), s.transactions, s.items_sold,
                         money(s.average_order)]], [120] * 4),
                 Spacer(1, 12), Paragraph("Completed Transactions", styles["Heading2"])]

        rows = [["Order ID", "Date", "Items", "Total", "Payment", "Shipment"]]
        for o in r["orders"]:
            rows.append([o.order_id, o.order_date.strftime("%b %d, %Y %I:%M %p"),
                         o.item_count, money(o.total), o.payment_method,
                         r["shipments"].get(str(o.order_id), "Not shipped")])
        story.append(table(rows, [55, 110, 40, 85, 85, 80], right_cols=(2, 3)))

        story += [Spacer(1, 12), Paragraph("Payment Breakdown", styles["Heading2"]),
                  table([["Method", "Orders", "Amount"]] +
                        [[m, c, money(a)] for m, c, a in r["methods"]],
                        [150, 60, 100], right_cols=(1, 2)),
                  Spacer(1, 12), Paragraph("Best Sellers", styles["Heading2"]),
                  table([["Product", "Qty", "Revenue"]] +
                        [[n, q, money(v)] for n, q, v in r["top"]],
                        [200, 60, 100], right_cols=(1, 2))]
        SimpleDocTemplate(path, pagesize=A4, title="Sales Report").build(story)

    # ---- table / chart helpers ------------------------------------------------------
    def _update_footer(self, orders):
        if not orders:
            self._footer_label.config(text="No orders listed")
            return
        items = sum(row.item_count for row in orders)
        total = sum(float(row.total) for row in orders)
        text = f"{len(orders)} order(s) listed   ·   {items} item(s)   ·   Total {peso(total)}"
        if len(orders) >= LIST_LIMIT:
            text += f"   ·   latest {LIST_LIMIT} only"
        self._footer_label.config(text=text)

    def _open_receipt(self, event):
        """Double-click a transaction to open (and print) its receipt."""
        row_id = self._tree.identify_row(event.y)
        if not row_id:
            return
        order_id = str(self._tree.item(row_id, "values")[0])
        try:
            order = self._context.orders.get(order_id)
        except DatabaseError as error:
            show_db_error(error)
            return
        if order is None:
            messagebox.showwarning("Receipt", f"Order {order_id} could not be found.")
            return
        self._context.receipts.print_receipt(order)

    def _show_deltas(self, summary, previous, compare_label):
        current_values = {"sales": summary.total_sales, "transactions": summary.transactions,
                          "items": summary.items_sold, "average": summary.average_order}
        for key, label in self._delta_labels.items():
            if previous is None:
                label.config(text="", fg=Theme.MUTED)
                continue
            before = {"sales": previous.total_sales, "transactions": previous.transactions,
                      "items": previous.items_sold, "average": previous.average_order}[key]
            now = current_values[key]
            if not before:
                label.config(text=f"No sales {compare_label}" if not now else f"New vs {compare_label}",
                             fg=Theme.MUTED)
                continue
            change = (now - before) / before * 100
            if round(change) == 0:
                label.config(text=f"No change vs {compare_label}", fg=Theme.MUTED)
            else:
                arrow, color = ("▲", UP_COLOR) if change > 0 else ("▼", DOWN_COLOR)
                label.config(text=f"{arrow} {abs(change):.0f}% vs {compare_label}", fg=color)

    def _draw_breakdown(self, methods):
        canvas = self._canvas
        canvas.delete("all")
        canvas.create_text(18, 12, anchor="nw", text="Sales by payment method",
                           fill=Theme.MUTED, font=("Helvetica", 9))
        if not methods:
            canvas.create_text(195, 100, text="No completed transactions yet.", fill=Theme.MUTED)
            return
        grand_total = sum(float(row[2]) for row in methods) or 1
        max_value = max(float(row[2]) for row in methods) or 1
        y = 38
        for index, (method, count, amount) in enumerate(methods[:4]):
            share = float(amount) / grand_total * 100
            canvas.create_text(20, y, anchor="nw", text=f"{method} ({count}) · {share:.0f}%",
                               fill=Theme.TEXT, font=("Helvetica", 10, "bold"))
            # Amount sits on the label line, right-aligned, so it never touches the edge.
            canvas.create_text(370, y, anchor="ne", text=peso(amount), fill=Theme.TEXT,
                               font=("Helvetica", 9))
            bar_width = max(2, 350 * float(amount) / max_value)
            canvas.create_rectangle(20, y + 20, 20 + bar_width, y + 32,
                                    fill=METHOD_COLORS[index % len(METHOD_COLORS)], outline="")
            y += 36

    def _draw_hourly(self, by_hour):
        canvas = self._hourly_canvas
        canvas.delete("all")
        if not by_hour or not any(by_hour.values()):
            canvas.create_text(400, 72, text="No completed transactions yet.", fill=Theme.MUTED)
            return
        peak = max(by_hour, key=by_hour.get)
        canvas.create_text(18, 10, anchor="nw", fill=Theme.MUTED, font=("Helvetica", 9),
                           text=f"Peak hour: {_hour_label(peak)} ({peso(by_hour[peak])})")
        hours = range(min(8, min(by_hour)), max(20, max(by_hour)) + 1)
        left, right, top, bottom = 20, 780, 38, 118
        slot = (right - left) / len(hours)
        max_value = max(by_hour.values()) or 1
        for i, hour in enumerate(hours):
            x0, x1 = left + i * slot + 4, left + (i + 1) * slot - 4
            value = by_hour.get(hour, 0)
            if value > 0:
                bar_height = max(2, (bottom - top) * value / max_value)
                canvas.create_rectangle(x0, bottom - bar_height, x1, bottom, outline="",
                                        fill=Theme.NAVY if hour == peak else Theme.ACTIVE)
            canvas.create_text((x0 + x1) / 2, bottom + 4, anchor="n", text=_hour_label(hour),
                               fill=Theme.MUTED, font=("Helvetica", 8))