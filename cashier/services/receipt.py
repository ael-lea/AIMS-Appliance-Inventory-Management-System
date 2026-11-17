"""Receipt creation. ReceiptRenderer is abstract so other formats can be added."""
import html
import os
import tempfile
import webbrowser
from abc import ABC, abstractmethod

from cashier.config import Settings, Theme
from cashier.utils import peso


class ReceiptRenderer(ABC):
    """Turns an Order into printable text."""

    @abstractmethod
    def render(self, order):
        """Return the receipt content for `order`."""


class HtmlReceiptRenderer(ReceiptRenderer):
    """Renders a 300px-wide thermal-style receipt as an HTML page."""

    def render(self, order):
        vat_percent = int(Settings.VAT_RATE * 100)
        return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
    <title>Receipt {html.escape(str(order.order_id))}</title>
    <style>
      body {{ font-family: 'Courier New', monospace; width: 300px; margin: 20px auto; color: #000; font-size: 13px; }}
      h2 {{ text-align: center; margin: 0; color: {Theme.NAVY}; }}
      .center {{ text-align: center; }} table {{ width: 100%; border-collapse: collapse; }}
      td {{ padding: 3px 0; }} .right {{ text-align: right; white-space: nowrap; }}
      hr {{ border: 0; border-top: 1px dashed #000; margin: 8px 0; }}
      .row {{ display: flex; justify-content: space-between; margin: 4px 0; }}
    </style></head><body>
    <h2>AIMS</h2><div class='center'>Official Receipt</div><hr>
    <div>Order: {html.escape(str(order.order_id))}</div>
    <div>Date: {order.order_date.strftime('%Y-%m-%d %I:%M %p')}</div><hr>
    <table>{self._item_rows(order)}</table><hr>
    <div class='row'><span>Subtotal</span><span>{peso(order.subtotal)}</span></div>
    <div class='row'><span>VAT ({vat_percent}%)</span><span>{peso(order.vat)}</span></div>
    <div class='row'><b>TOTAL</b><b>{peso(order.total)}</b></div>
    {self._payment_section(order)}<hr><div class='center'>Thank you!</div>
    <script>window.onload = function() {{ window.print(); }};</script>
    </body></html>"""

    @staticmethod
    def _item_rows(order):
        return "".join(
            f"<tr><td>{int(line.quantity)} × {html.escape(str(line.product_name))}</td>"
            f"<td class='right'>{peso(line.line_total)}</td></tr>"
            for line in order.lines
        )

    @staticmethod
    def _payment_section(order):
        if order.is_pending:
            return "<hr><div class='row'><span>Status</span><span>Pending payment</span></div>"
        section = (f"<hr><div class='row'><span>Payment</span>"
                   f"<span>{html.escape(str(order.payment_method or ''))}</span></div>")
        if order.payment_method == "Cash":
            section += (f"<div class='row'><span>Received</span><span>{peso(order.amount_paid)}</span></div>"
                        f"<div class='row'><span>Change</span><span>{peso(order.change_amount)}</span></div>")
        return section


class ReceiptPrinter:
    """Writes the rendered receipt to a temp file and opens it in the browser."""

    def __init__(self, renderer=None):
        self._renderer = renderer or HtmlReceiptRenderer()

    def print_receipt(self, order):
        path = os.path.join(tempfile.gettempdir(), "aims_receipt.html")
        with open(path, "w", encoding="utf-8") as file:
            file.write(self._renderer.render(order))
        webbrowser.open("file:///" + path.replace("\\", "/"))
