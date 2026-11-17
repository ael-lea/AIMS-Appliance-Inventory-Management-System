"""Sidebar widgets: analog clock and date display."""
import math
import tkinter as tk
from datetime import datetime

from cashier.config import Theme


class AnalogClock(tk.Canvas):
    """A 160x160 analog clock that updates itself every second."""

    CENTER = 80

    def __init__(self, parent):
        super().__init__(parent, width=160, height=160, bg=Theme.NAVY, highlightthickness=0)
        self._after_id = None
        self._draw_face()
        self._tick()

    def _draw_face(self):
        c = self.CENTER
        self.create_oval(5, 5, 155, 155, outline="white", width=3)
        for i in range(1, 13):
            angle = i * (2 * math.pi / 12) - math.pi / 2
            self.create_line(c + 58 * math.cos(angle), c + 58 * math.sin(angle),
                             c + 68 * math.cos(angle), c + 68 * math.sin(angle),
                             fill="white", width=2)
            self.create_text(c + 45 * math.cos(angle), c + 45 * math.sin(angle),
                             text=str(i), fill="white", font=("Helvetica", 9, "bold"))

    def _tick(self):
        self.delete("hands")
        now, c = datetime.now(), self.CENTER
        sec_angle = (now.second / 60) * (2 * math.pi) - math.pi / 2
        min_angle = ((now.minute + now.second / 60) / 60) * (2 * math.pi) - math.pi / 2
        hr_angle = (((now.hour % 12) + now.minute / 60) / 12) * (2 * math.pi) - math.pi / 2
        for length, angle, color, width in ((55, sec_angle, "red", 2),
                                            (45, min_angle, "white", 4),
                                            (30, hr_angle, "white", 6)):
            self.create_line(c, c, c + length * math.cos(angle), c + length * math.sin(angle),
                             fill=color, width=width, tags="hands")
        self.create_oval(75, 75, 85, 85, fill="gray", tags="hands")
        self._after_id = self.after(1000, self._tick)

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        super().destroy()


class DateDisplay(tk.Frame):
    """Shows the date and weekday; refreshes every minute."""

    def __init__(self, parent):
        super().__init__(parent, bg=Theme.NAVY)
        self._date_label = tk.Label(self, font=("Helvetica", 15), bg=Theme.NAVY, fg="#FFFFFF")
        self._date_label.pack(fill=tk.X)
        self._day_label = tk.Label(self, font=("Helvetica", 15), bg=Theme.NAVY, fg="white")
        self._day_label.pack(fill=tk.X)
        self._after_id = None
        self._refresh()

    def _refresh(self):
        now = datetime.now()
        self._date_label.config(text=now.strftime("%B %d, %Y"))
        self._day_label.config(text=now.strftime("%A"))
        self._after_id = self.after(60000, self._refresh)

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        super().destroy()
