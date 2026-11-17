"""Reusable widget helpers (buttons, tables, icons, error dialogs)."""
import os
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = ImageDraw = ImageTk = None

from cashier.config import Settings, Theme


BACK_IMAGE_PATH = os.path.join(Settings.ICON_DIR, "back.png")

def show_db_error(error, title="Database Error"):
    messagebox.showerror(title, str(error))


def load_icon(file_name):
    """Load a picture from the icons folder. Returns None when the file is missing."""
    if not file_name:
        return None
    path = os.path.join(Settings.ICON_DIR, file_name)
    try:
        return tk.PhotoImage(file=path) if os.path.exists(path) else None
    except tk.TclError:
        return None


def make_nav_icon(kind, size=26):
    """A simple white line icon drawn with Pillow (home, cart, history, chart, truck)."""
    if Image is None or ImageDraw is None:
        return None
    s = 4                                   # draw 4x bigger, then shrink, for smooth lines
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    white, w = (255, 255, 255, 255), 2 * s

    def pts(*points):
        return [(x * s, y * s) for x, y in points]

    if kind == "home":
        d.line(pts((3, 13), (13, 4), (23, 13)), fill=white, width=w, joint="curve")
        d.line(pts((6, 12), (6, 22), (20, 22), (20, 12)), fill=white, width=w, joint="curve")
        d.line(pts((11, 22), (11, 16), (15, 16), (15, 22)), fill=white, width=w, joint="curve")
    elif kind == "cart":
        d.line(pts((2, 4), (6, 4), (9, 17), (21, 17), (23, 8), (7, 8)), fill=white, width=w, joint="curve")
        d.ellipse((9 * s, 20 * s, 12 * s, 23 * s), fill=white)
        d.ellipse((18 * s, 20 * s, 21 * s, 23 * s), fill=white)
    elif kind == "history":
        d.ellipse((3 * s, 3 * s, 23 * s, 23 * s), outline=white, width=w)
        d.line(pts((13, 7), (13, 13), (17, 16)), fill=white, width=w, joint="curve")
    elif kind == "chart":
        for x, height in ((4, 8), (11, 14), (18, 19)):
            d.rectangle((x * s, (23 - height) * s, (x + 4) * s, 23 * s), fill=white)
    elif kind == "truck":
        d.rectangle((2 * s, 7 * s, 15 * s, 18 * s), outline=white, width=w)
        d.rectangle((15 * s, 11 * s, 22 * s, 18 * s), outline=white, width=w)
        d.line(pts((17, 11), (20, 11), (22, 14)), fill=white, width=w)
        d.ellipse((5 * s, 17 * s, 10 * s, 22 * s), outline=white, width=w)
        d.ellipse((17 * s, 17 * s, 22 * s, 22 * s), outline=white, width=w)
    return ImageTk.PhotoImage(big.resize((size, size), Image.LANCZOS))


def styled_button(parent, text, command, primary=False, width=14, height=36,
                  danger=False, px=None):
    """A rounded button that changes colour on hover.
    `width` is in characters; `px` sets an exact width in pixels instead."""
    return ctk.CTkButton(
        parent, text=text, command=command, width=px or width * 8 + 24, height=height,
        corner_radius=10, cursor="hand2",
        font=ctk.CTkFont("Helvetica", 13, "bold" if primary else "normal"),
        fg_color=Theme.NAVY if primary else Theme.LIGHT_BTN,
        hover_color=Theme.ACTIVE if primary else Theme.LIGHT_ACTIVE,
        text_color="white" if primary else (Theme.DANGER if danger else Theme.TEXT),
        text_color_disabled="#E5E7EB",
    )


def make_tree(parent, columns, headings, widths, height=12):
    """A Treeview with a scrollbar. Returns (wrapper_frame, tree)."""
    wrapper = tk.Frame(parent, bg=Theme.BG)
    tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=height,
                        selectmode="browse")
    scroll = ttk.Scrollbar(wrapper, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    for column, heading, width in zip(columns, headings, widths):
        tree.heading(column, text=heading)
        tree.column(column, width=width, anchor=tk.CENTER)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    return wrapper, tree


def make_back_icon(size=32):
    """A navy back arrow drawn with Pillow. Used when back.png is not in the icons folder."""
    if Image is None or ImageDraw is None:
        return None
    k = 4
    big = Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    navy, w = (1, 33, 72, 255), 3 * k
    u = size / 32
    d.line([(26 * u * k, 16 * u * k), (7 * u * k, 16 * u * k)], fill=navy, width=w)
    d.line([(15 * u * k, 8 * u * k), (7 * u * k, 16 * u * k), (15 * u * k, 24 * u * k)],
           fill=navy, width=w, joint="curve")
    return ImageTk.PhotoImage(big.resize((size, size), Image.LANCZOS))

def make_back_button(frame, navigate):
    """The 'back to Dashboard' image button used on every page except the dashboard."""
    frame.back_image = tk.PhotoImage(file=BACK_IMAGE_PATH, master=frame)

    button = tk.Button(
        frame,
        image=frame.back_image,
        bd=0,
        cursor="hand2",
        bg=Theme.BG,
        activebackground=Theme.BG,
        command=lambda: navigate("Dashboard"),
    )
    button.place(x=10, y=12)
    return button