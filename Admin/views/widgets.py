"""
Reusable UI Widgets and Helper Utilities for AIMS.
Demonstrates:
- Reusable Methods
- Consistent UI Theming (Fonts, Colors, Geometry)
"""
import os
import re  
from typing import Optional
from tkinter import *
from tkinter import ttk
import customtkinter as ctk
from PIL import Image, ImageTk

# Theme Colors
NAVY = "#012148"
ACTIVE = "#053e87"
BG = "#FDFCF8"
LIGHT = "#E9EEF5"
MUTED = "#6B7280"
CARD_COLORS = ["#053e87", "#1e8449", "#b9770e", "#7d3c98"]

# <project root>/photos  (three dirname calls up from this file)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICON_DIR = os.path.join(PROJECT_ROOT, "photos") + os.sep


# ---------------- Typing rules (keep ints as ints, text as text) ----------------

def letters_only(value: str) -> bool:
    """Text fields (names, categories): letters, spaces and common name punctuation only."""
    return re.fullmatch(r"[A-Za-z .,'&-]*", value) is not None


def digits_only(max_len: int = 9):
    """Whole-number fields (quantity, contact): digits 0-9 only, up to max_len."""
    return lambda value: re.fullmatch(r"[0-9]{0,%d}" % max_len, value) is not None


def contact_only(value: str) -> bool:
    """Contact numbers: digits only, must start with 9, up to 10 digits (e.g. 9171234567)."""
    return value == "" or re.fullmatch(r"9[0-9]{0,9}", value) is not None

def money_only(value: str) -> bool:
    """Money fields: digits with an optional decimal point and up to 2 decimals."""
    return re.fullmatch(r"[0-9]{0,9}(\.[0-9]{0,2})?", value) is not None


def apply_rule(entry, rule) -> None:
    """Block any keystroke or paste that would make the entry violate `rule`."""
    entry.configure(validate="key", validatecommand=(entry.register(rule), "%P"))

def _open_icon(name: str, size=None, scale=None):
    """Open photos/<name> as a PIL image (optionally resized). None if it cannot be read."""
    path = ICON_DIR + name
    if not os.path.isfile(path):
        return None
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        return None
    if size:
        img = img.resize(size)
    elif scale:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    return img


def load_icon(name: str, size=None, scale=None) -> Optional[ImageTk.PhotoImage]:
    """Icon for plain tkinter widgets (Label, Button, iconphoto). Keep a reference to it."""
    img = _open_icon(name, size, scale)
    return ImageTk.PhotoImage(img) if img else None


def load_ctk_icon(name: str, size=None) -> Optional[ctk.CTkImage]:
    """Icon for CustomTkinter widgets (CTkButton)."""
    img = _open_icon(name, size)
    return ctk.CTkImage(light_image=img, dark_image=img, size=img.size) if img else None


def round_button(
    parent,
    text: str,
    command=None,
    width: int = 120,
    secondary: bool = False,
    height: int = 35,
    font_size: int = 14,
    bg_color: str = BG
) -> ctk.CTkButton:
    """
    Reusable rounded button widget styled for AIMS.
    Navy = Primary action; Light = Secondary action.
    """
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        font=("Helvetica", font_size, "bold"),
        text_color=NAVY if secondary else "white",
        text_color_disabled="#8A94A6",
        fg_color=LIGHT if secondary else NAVY,
        hover_color="#DCE5F0" if secondary else ACTIVE,
        bg_color=bg_color,
        corner_radius=8,
        width=width,
        height=height,
        cursor="hand2"
    )


def safe_load_image(file_path: str, size=(80, 80)) -> Optional[ImageTk.PhotoImage]:
    """
    Safely loads and resizes an image file.
    Returns None if file is missing or invalid, preventing application crashes.
    """
    if file_path and os.path.isfile(file_path):
        try:
            with Image.open(file_path) as img:
                img = img.convert("RGBA")
                img.thumbnail(size)
                return ImageTk.PhotoImage(img)
        except Exception:
            return None
    return None