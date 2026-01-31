#!/usr/bin/env python3
"""
LabelCrop: CLI PDF Crop Tool

Modes of operation:
  1. Interactive Crop Area Selection:
       labelcrop input.pdf
     • Opens a GUI showing the first page.
         • Shows a default rectangle that you can move by dragging its center and resize by dragging its edges.
         • Choose freeform, forced aspect ratio, or forced dimensions from the toolbar.
         • Click the Done button to save the selection and close the window.
     • These coordinates are saved to a configuration file (crop_data.cfg) exactly as selected.
  
  2. Cropping Mode:
       labelcrop input.pdf output.pdf
     • Reads the saved crop rectangle from crop_data.cfg and crops every page of the input PDF to that exact rectangle.
  
  3. Cropping + Rotation Mode:
       labelcrop input.pdf output.pdf angle_clockwise
     • Crops as above, then rotates each page by the given angle (in degrees, clockwise).

All coordinates are in PDF points.
"""

import sys
import os
import json
import tkinter as tk
import tkinter.font as tkfont
import math
from tkinter import filedialog
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter

CONFIG_FILE = "crop_data.cfg"

POINTS_PER_INCH = 72.0
POINTS_PER_CM = POINTS_PER_INCH / 2.54

def parse_aspect_ratio(text):
    if not text:
        return None
    value = text.strip().lower()
    if not value:
        return None
    for sep in ("x", ":", "/"):
        if sep in value:
            parts = value.split(sep, 1)
            try:
                w = float(parts[0])
                h = float(parts[1])
            except (ValueError, IndexError):
                return None
            return (w / h) if w > 0 and h > 0 else None
    try:
        ratio = float(value)
    except ValueError:
        return None
    return ratio if ratio > 0 else None

def parse_float(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None

def unit_to_points(value, unit):
    if value is None:
        return None
    unit_norm = (unit or "").strip().lower()
    if unit_norm in ("in", "inch", "inches"):
        return value * POINTS_PER_INCH
    if unit_norm in ("cm", "centimeter", "centimeters"):
        return value * POINTS_PER_CM
    if unit_norm in ("pt", "pts", "point", "points"):
        return value
    if unit_norm in ("px", "pixel", "pixels"):
        return value
    return None

def points_to_unit(value, unit):
    if value is None:
        return None
    unit_norm = (unit or "").strip().lower()
    if unit_norm in ("in", "inch", "inches"):
        return value / POINTS_PER_INCH
    if unit_norm in ("cm", "centimeter", "centimeters"):
        return value / POINTS_PER_CM
    if unit_norm in ("pt", "pts", "point", "points"):
        return value
    if unit_norm in ("px", "pixel", "pixels"):
        return value
    return None

### Interactive Crop Area Selector (GUI)
def interactive_crop_selector(input_pdf_path):
    """
    Opens a GUI on the first page of the input PDF.
    Lets you draw a rectangle.
    Computes bottom‑left and top‑right coordinates (in PDF points) and saves them.
    """
    class PDFLabelSelector:
        def __init__(self, pdf_path):
            self.pdf_path = pdf_path
            self.doc = fitz.open(pdf_path)
            self.page = self.doc[0]  # use first page
            self.page_height = self.page.rect.height
            self.scale = 0.5  # scale factor for display
            self.rect_id = None
            self.rect = None
            self.drag_mode = None
            self.resize_edges = None
            self.drag_start = None
            self.handle_size = 6
            self.min_size = 10
            self.aspect_ratio = None
            self.forced_dimensions = None  # (width_pts, height_pts)
            self.canvas_width = None
            self.canvas_height = None
            self.image_x0 = 0
            self.image_y0 = 0
            self.image_width = 0
            self.image_height = 0
            self.suppress_field_update = False
            self.resize_job = None
            self.init_gui()
        
        def init_gui(self):
            self.root = tk.Tk()
            self.root.title("Select Crop Area")
            self.toolbar = tk.Frame(self.root)
            self.toolbar.pack(fill=tk.X)

            self.mode_var = tk.StringVar(value="Freeform")
            tk.Label(self.toolbar, text="Mode:").pack(side=tk.LEFT, padx=(6, 2))
            self.mode_menu = tk.OptionMenu(self.toolbar, self.mode_var, "Freeform", "Force Aspect Ratio", "Force Dimensions", command=self.on_mode_change)
            self.mode_menu.pack(side=tk.LEFT)
            self.set_menu_width(self.mode_menu, ["Freeform", "Force Aspect Ratio", "Force Dimensions"])

            self.ratio_label = tk.Label(self.toolbar, text="Ratio:")
            self.ratio_var = tk.StringVar()
            self.ratio_entry = tk.Entry(self.toolbar, textvariable=self.ratio_var, width=10)
            self.ratio_entry.bind("<Return>", self.on_entry_commit)
            self.ratio_entry.bind("<FocusOut>", self.on_entry_commit)

            self.dim_w_label = tk.Label(self.toolbar, text="W:")
            self.dim_w_var = tk.StringVar()
            self.dim_w_entry = tk.Entry(self.toolbar, textvariable=self.dim_w_var, width=8)
            self.dim_w_entry.bind("<Return>", self.on_entry_commit)
            self.dim_w_entry.bind("<FocusOut>", self.on_entry_commit)
            self.dim_w_unit = tk.StringVar(value="in")
            self.dim_w_unit_menu = tk.OptionMenu(self.toolbar, self.dim_w_unit, "in", "cm", "pt", "px", command=self.on_unit_change)
            self.set_menu_width(self.dim_w_unit_menu, ["in", "cm", "pt", "px"])

            self.dim_h_label = tk.Label(self.toolbar, text="H:")
            self.dim_h_var = tk.StringVar()
            self.dim_h_entry = tk.Entry(self.toolbar, textvariable=self.dim_h_var, width=8)
            self.dim_h_entry.bind("<Return>", self.on_entry_commit)
            self.dim_h_entry.bind("<FocusOut>", self.on_entry_commit)
            self.dim_h_unit = tk.StringVar(value="in")
            self.dim_h_unit_menu = tk.OptionMenu(self.toolbar, self.dim_h_unit, "in", "cm", "pt", "px", command=self.on_unit_change)
            self.set_menu_width(self.dim_h_unit_menu, ["in", "cm", "pt", "px"])

            self.crop_button = tk.Button(self.toolbar, text="Done", command=self.save_and_close)
            self.ratio_label.pack(side=tk.LEFT, padx=(12, 2))
            self.ratio_entry.pack(side=tk.LEFT)
            self.dim_w_label.pack(side=tk.LEFT, padx=(12, 2))
            self.dim_w_entry.pack(side=tk.LEFT)
            self.dim_w_unit_menu.pack(side=tk.LEFT)
            self.dim_h_label.pack(side=tk.LEFT, padx=(6, 2))
            self.dim_h_entry.pack(side=tk.LEFT)
            self.dim_h_unit_menu.pack(side=tk.LEFT)
            self.crop_button.pack(side=tk.LEFT, padx=(8, 6))

            self.canvas = tk.Canvas(self.root, cursor="cross", takefocus=1, highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self.root.update_idletasks()
            toolbar_width = self.toolbar.winfo_reqwidth()
            toolbar_height = self.toolbar.winfo_reqheight()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            desired_width = min(toolbar_width, screen_width - 80)
            desired_height = min(720, screen_height - 80)
            self.root.geometry(f"{desired_width}x{desired_height}")
            self.render_page()
            self.create_default_rect()
            self.update_fields_from_rect()
            self.canvas.bind("<ButtonPress-1>", self.on_button_press)
            self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
            self.canvas.bind("<Motion>", self.on_mouse_move)
            self.canvas.bind("<Leave>", self.on_mouse_leave)
            self.root.bind("<Configure>", self.on_window_resize)
            self.root.mainloop()
        
        def render_page(self):
            canvas_width = max(self.canvas.winfo_width(), 1)
            canvas_height = max(self.canvas.winfo_height(), 1)
            page_width = self.page.rect.width
            page_height = self.page.rect.height
            scale_x = canvas_width / page_width
            scale_y = canvas_height / page_height
            self.scale = min(scale_x, scale_y)
            matrix = fitz.Matrix(self.scale, self.scale)
            pix = self.page.get_pixmap(matrix=matrix)
            self.tk_img = tk.PhotoImage(data=pix.tobytes("ppm"))
            self.canvas_width = canvas_width
            self.canvas_height = canvas_height
            self.image_width = page_width * self.scale
            self.image_height = page_height * self.scale
            self.image_x0 = (self.canvas_width - self.image_width) / 2
            self.image_y0 = (self.canvas_height - self.image_height) / 2
            self.canvas.delete("page")
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                anchor=tk.CENTER,
                image=self.tk_img,
                tags="page",
            )
            self.canvas.tag_lower("page")
            if self.rect_id:
                self.canvas.tag_raise(self.rect_id)

        def on_window_resize(self, event):
            if self.resize_job:
                self.root.after_cancel(self.resize_job)
            self.resize_job = self.root.after(150, self.on_resize_commit)

        def on_resize_commit(self):
            self.resize_job = None
            previous_scale = self.scale
            if not previous_scale:
                previous_scale = 1.0
            prev_image_x0 = self.image_x0
            prev_image_y0 = self.image_y0
            self.render_page()
            if not self.rect:
                return
            x1, y1, x2, y2 = self.rect
            x1p = (x1 - prev_image_x0) / previous_scale
            x2p = (x2 - prev_image_x0) / previous_scale
            y1p = (y1 - prev_image_y0) / previous_scale
            y2p = (y2 - prev_image_y0) / previous_scale
            x1 = self.image_x0 + (x1p * self.scale)
            x2 = self.image_x0 + (x2p * self.scale)
            y1 = self.image_y0 + (y1p * self.scale)
            y2 = self.image_y0 + (y2p * self.scale)
            x1, y1, x2, y2 = self.clamp_rect(x1, y1, x2, y2, keep_size=True)
            self.update_rect(x1, y1, x2, y2)

        def create_default_rect(self):
            default_w = 4 * POINTS_PER_INCH * self.scale
            default_h = 6 * POINTS_PER_INCH * self.scale
            if default_w > 0 and default_h > 0:
                fit_ratio = min(self.image_width / default_w, self.image_height / default_h, 1.0)
                default_w *= fit_ratio
                default_h *= fit_ratio
            center_x = self.image_x0 + self.image_width / 2
            center_y = self.image_y0 + self.image_height / 2
            x1 = center_x - default_w / 2
            y1 = center_y - default_h / 2
            x2 = center_x + default_w / 2
            y2 = center_y + default_h / 2
            self.rect = (x1, y1, x2, y2)
            self.rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)
            self.canvas.tag_raise(self.rect_id)

        def on_mode_change(self, *_):
            self.apply_constraints()

        def set_menu_width(self, menu_widget, items):
            if not items:
                return
            font = tkfont.Font(font=menu_widget.cget("font"))
            max_px = max(font.measure(str(item)) for item in items)
            avg_char_px = max(font.measure("0"), 1)
            width_chars = max(1, math.ceil(max_px / avg_char_px))
            menu_widget.config(width=width_chars)

        def on_entry_commit(self, *_):
            if self.suppress_field_update:
                return
            self.apply_constraints()

        def on_unit_change(self, *_):
            self.update_fields_from_rect()

        def set_status(self, text):
            return

        def apply_constraints(self):
            mode = self.mode_var.get()
            if mode == "Freeform":
                self.aspect_ratio = None
                self.forced_dimensions = None
                self.set_status("")
                return

            if mode == "Force Aspect Ratio":
                ratio = parse_aspect_ratio(self.ratio_var.get())
                if not ratio:
                    self.aspect_ratio = None
                    self.forced_dimensions = None
                    self.set_status("")
                    return
                self.aspect_ratio = ratio
                self.forced_dimensions = None
                self.apply_aspect_ratio_to_rect()
                self.set_status("")
                return

            if mode == "Force Dimensions":
                width = unit_to_points(parse_float(self.dim_w_var.get()), self.dim_w_unit.get())
                height = unit_to_points(parse_float(self.dim_h_var.get()), self.dim_h_unit.get())
                if not width or not height:
                    self.aspect_ratio = None
                    self.forced_dimensions = None
                    self.set_status("")
                    return
                self.aspect_ratio = None
                self.forced_dimensions = (width, height)
                self.apply_forced_dimensions_to_rect()
                self.set_status("")

        def apply_aspect_ratio_to_rect(self):
            if not self.rect or not self.aspect_ratio:
                return
            x1, y1, x2, y2 = self.rect
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            ratio = self.aspect_ratio
            if height == 0:
                height = 1
            if (width / height) > ratio:
                width = height * ratio
            else:
                height = width / ratio
            x1 = center_x - width / 2
            x2 = center_x + width / 2
            y1 = center_y - height / 2
            y2 = center_y + height / 2
            x1, y1, x2, y2 = self.clamp_rect(x1, y1, x2, y2, keep_size=True)
            self.update_rect(x1, y1, x2, y2)

        def apply_forced_dimensions_to_rect(self):
            if not self.rect or not self.forced_dimensions:
                return
            width_pts, height_pts = self.forced_dimensions
            width = width_pts * self.scale
            height = height_pts * self.scale
            width = min(width, self.canvas_width)
            height = min(height, self.canvas_height)
            x1, y1, x2, y2 = self.rect
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            x1 = center_x - width / 2
            x2 = center_x + width / 2
            y1 = center_y - height / 2
            y2 = center_y + height / 2
            x1, y1, x2, y2 = self.clamp_rect(x1, y1, x2, y2, keep_size=True)
            self.update_rect(x1, y1, x2, y2)

        def update_rect(self, x1, y1, x2, y2):
            self.rect = (x1, y1, x2, y2)
            if self.rect_id:
                self.canvas.coords(self.rect_id, x1, y1, x2, y2)
            self.update_fields_from_rect()

        def update_fields_from_rect(self):
            if not self.rect or self.suppress_field_update:
                return
            x1, y1, x2, y2 = self.rect
            width_pts = abs(x2 - x1) / self.scale
            height_pts = abs(y2 - y1) / self.scale
            ratio = width_pts / height_pts if height_pts else 0
            self.suppress_field_update = True
            try:
                if ratio:
                    self.ratio_var.set(f"{ratio:.6g}")
                else:
                    self.ratio_var.set("")
                width_value = points_to_unit(width_pts, self.dim_w_unit.get())
                height_value = points_to_unit(height_pts, self.dim_h_unit.get())
                if width_value is not None:
                    self.dim_w_var.set(f"{width_value:.6g}")
                if height_value is not None:
                    self.dim_h_var.set(f"{height_value:.6g}")
            finally:
                self.suppress_field_update = False

        def clamp_rect(self, x1, y1, x2, y2, keep_size=False):
            left_bound = self.image_x0
            right_bound = self.image_x0 + self.image_width
            top_bound = self.image_y0
            bottom_bound = self.image_y0 + self.image_height
            if keep_size:
                w = x2 - x1
                h = y2 - y1
                x1 = min(max(x1, left_bound), right_bound - w)
                y1 = min(max(y1, top_bound), bottom_bound - h)
                x2 = x1 + w
                y2 = y1 + h
                return x1, y1, x2, y2
            x1 = max(left_bound, min(x1, right_bound))
            x2 = max(left_bound, min(x2, right_bound))
            y1 = max(top_bound, min(y1, bottom_bound))
            y2 = max(top_bound, min(y2, bottom_bound))
            return x1, y1, x2, y2

        def is_inside_rect(self, x, y):
            if not self.rect:
                return False
            x1, y1, x2, y2 = self.rect
            return x1 <= x <= x2 and y1 <= y <= y2

        def get_resize_edges(self, x, y):
            if not self.rect:
                return None
            x1, y1, x2, y2 = self.rect
            near_left = abs(x - x1) <= self.handle_size
            near_right = abs(x - x2) <= self.handle_size
            near_top = abs(y - y1) <= self.handle_size
            near_bottom = abs(y - y2) <= self.handle_size
            if not (near_left or near_right or near_top or near_bottom):
                return None
            return {
                "left": near_left,
                "right": near_right,
                "top": near_top,
                "bottom": near_bottom,
            }

        def on_button_press(self, event):
            if self.canvas:
                self.canvas.focus_set()
            if not self.rect:
                return
            if not self.is_inside_rect(event.x, event.y):
                return
            edges = self.get_resize_edges(event.x, event.y)
            if edges:
                self.drag_mode = "resize"
                self.resize_edges = edges
            else:
                self.drag_mode = "move"
                self.resize_edges = None
            self.drag_start = (event.x, event.y)

        def on_mouse_drag(self, event):
            if not self.rect or not self.drag_mode or not self.drag_start:
                return
            x1, y1, x2, y2 = self.rect
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]

            if self.drag_mode == "move":
                x1 += dx
                x2 += dx
                y1 += dy
                y2 += dy
                x1, y1, x2, y2 = self.clamp_rect(x1, y1, x2, y2, keep_size=True)
                self.update_rect(x1, y1, x2, y2)
                self.drag_start = (event.x, event.y)
                return

            if self.drag_mode == "resize":
                x1, y1, x2, y2 = self.resize_rect(x1, y1, x2, y2, event.x, event.y)
                self.update_rect(x1, y1, x2, y2)
                self.drag_start = (event.x, event.y)

        def on_button_release(self, event):
            self.drag_mode = None
            self.resize_edges = None
            self.drag_start = None
            self.update_cursor(event.x, event.y)

        def on_mouse_move(self, event):
            self.update_cursor(event.x, event.y)

        def on_mouse_leave(self, event):
            self.set_cursor("arrow")

        def update_cursor(self, x, y):
            if not self.rect:
                self.set_cursor("arrow")
                return
            if self.drag_mode == "move":
                self.set_cursor("hand2", fallbacks=["fleur", "arrow", "cross"])
                return
            if self.drag_mode == "resize" and self.resize_edges:
                cursor_name, fallbacks = self.cursor_for_edges(self.resize_edges)
                self.set_cursor(cursor_name, fallbacks=fallbacks)
                return
            if not self.is_inside_rect(x, y):
                self.set_cursor("arrow")
                return
            edges = self.get_resize_edges(x, y)
            if edges:
                cursor_name, fallbacks = self.cursor_for_edges(edges)
                self.set_cursor(cursor_name, fallbacks=fallbacks)
            else:
                self.set_cursor("hand2", fallbacks=["fleur", "arrow", "cross"])

        def cursor_for_edges(self, edges):
            left = edges.get("left")
            right = edges.get("right")
            top = edges.get("top")
            bottom = edges.get("bottom")
            if (left or right) and (top or bottom):
                if (left and top) or (right and bottom):
                    return "fleur", ["size_nw_se", "top_left_corner", "bottom_right_corner", "cross"]
                return "fleur", ["size_ne_sw", "top_right_corner", "bottom_left_corner", "cross"]
            if left or right:
                return "sb_h_double_arrow", ["size_we", "cross"]
            if top or bottom:
                return "sb_v_double_arrow", ["size_ns", "cross"]
            return "cross", []

        def set_cursor(self, cursor_name, fallbacks=None):
            choices = [cursor_name]
            if fallbacks:
                choices.extend(fallbacks)
            for name in choices:
                try:
                    self.canvas.config(cursor=name)
                    return
                except tk.TclError:
                    continue
            self.canvas.config(cursor="arrow")

        def resize_rect(self, x1, y1, x2, y2, cursor_x, cursor_y):
            edges = self.resize_edges or {}
            if self.forced_dimensions:
                width_pts, height_pts = self.forced_dimensions
                width = width_pts * self.scale
                height = height_pts * self.scale
                width = min(width, self.canvas_width)
                height = min(height, self.canvas_height)
                if edges.get("left"):
                    x1 = cursor_x
                    x2 = x1 + width
                if edges.get("right"):
                    x2 = cursor_x
                    x1 = x2 - width
                if edges.get("top"):
                    y1 = cursor_y
                    y2 = y1 + height
                if edges.get("bottom"):
                    y2 = cursor_y
                    y1 = y2 - height
                x1, y1, x2, y2 = self.clamp_rect(x1, y1, x2, y2, keep_size=True)
                return x1, y1, x2, y2

            if edges.get("left"):
                x1 = min(cursor_x, x2 - self.min_size)
            if edges.get("right"):
                x2 = max(cursor_x, x1 + self.min_size)
            if edges.get("top"):
                y1 = min(cursor_y, y2 - self.min_size)
            if edges.get("bottom"):
                y2 = max(cursor_y, y1 + self.min_size)

            if self.aspect_ratio:
                ratio = self.aspect_ratio
                corner_drag = (edges.get("left") or edges.get("right")) and (edges.get("top") or edges.get("bottom"))
                if corner_drag:
                    anchor_x = x2 if edges.get("left") else x1
                    anchor_y = y2 if edges.get("top") else y1
                    dx = cursor_x - anchor_x
                    dy = cursor_y - anchor_y
                    width = max(self.min_size, abs(dx))
                    height = max(self.min_size, abs(dy))
                    if (width / height) > ratio:
                        height = width / ratio
                    else:
                        width = height * ratio
                    if edges.get("left"):
                        x1 = anchor_x - width
                        x2 = anchor_x
                    else:
                        x1 = anchor_x
                        x2 = anchor_x + width
                    if edges.get("top"):
                        y1 = anchor_y - height
                        y2 = anchor_y
                    else:
                        y1 = anchor_y
                        y2 = anchor_y + height
                else:
                    if edges.get("left") or edges.get("right"):
                        width = max(self.min_size, abs(x2 - x1))
                        height = width / ratio
                        center_y = (y1 + y2) / 2
                        y1 = center_y - height / 2
                        y2 = center_y + height / 2
                    if edges.get("top") or edges.get("bottom"):
                        height = max(self.min_size, abs(y2 - y1))
                        width = height * ratio
                        center_x = (x1 + x2) / 2
                        x1 = center_x - width / 2
                        x2 = center_x + width / 2

            x1, y1, x2, y2 = self.clamp_rect(x1, y1, x2, y2, keep_size=False)
            return x1, y1, x2, y2

        def save_and_close(self):
            if not self.rect:
                return
            x1, y1, x2, y2 = self.rect
            # Convert canvas coordinates to PDF coordinates.
            # Canvas x is same direction as PDF x: pdf_x = canvas_x/scale.
            # Canvas y is top-down; PDF y is bottom-up:
            #    pdf_y = page_height - (canvas_y/scale)
            pdf_x1 = (x1 - self.image_x0) / self.scale
            pdf_y1 = self.page_height - ((y2 - self.image_y0) / self.scale)  # bottom
            pdf_x2 = (x2 - self.image_x0) / self.scale
            pdf_y2 = self.page_height - ((y1 - self.image_y0) / self.scale)  # top
            crop_data = {
                "bottom_left": {"x": pdf_x1, "y": pdf_y1},
                "top_right": {"x": pdf_x2, "y": pdf_y2}
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(crop_data, f)
            print("Selected rectangle in PDF points:")
            print(f"  Bottom-left: ({pdf_x1:.2f}, {pdf_y1:.2f})")
            print(f"  Top-right:   ({pdf_x2:.2f}, {pdf_y2:.2f})")
            print(f"  Width: {pdf_x2 - pdf_x1:.2f}, Height: {pdf_y2 - pdf_y1:.2f}")
            print(f"Crop data saved to {CONFIG_FILE}")
            self.root.destroy()
    
    PDFLabelSelector(input_pdf_path)

### Cropping Function
def crop_pdf(input_pdf, output_pdf, crop_data, quiet=False):
    """
    Crops each page of input_pdf to the rectangle defined in crop_data
    and saves the result to output_pdf.
    crop_data is a dict with keys:
       bottom_left: {x, y}
       top_right: {x, y}
    """
    crop_x = crop_data["bottom_left"]["x"]
    crop_y = crop_data["bottom_left"]["y"]
    crop_width = crop_data["top_right"]["x"] - crop_x
    crop_height = crop_data["top_right"]["y"] - crop_y
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        # Set MediaBox and CropBox exactly as in the saved data.
        page.mediabox.lower_left = (crop_x, crop_y)
        page.mediabox.upper_right = (crop_x + crop_width, crop_y + crop_height)
        page.cropbox.lower_left = (crop_x, crop_y)
        page.cropbox.upper_right = (crop_x + crop_width, crop_y + crop_height)
        writer.add_page(page)
    with open(output_pdf, "wb") as f:
        writer.write(f)
    if not quiet:
        print(f"Cropped PDF saved to {output_pdf}")

### Rotation Function
def rotate_pdf(pdf_path, angle, quiet=False):
    """
    Reopens the PDF at pdf_path, rotates each page by 'angle' (clockwise),
    and overwrites the file.
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for page in reader.pages:
        rotated_page = page.rotate(angle)
        writer.add_page(rotated_page)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    if not quiet:
        print(f"Rotated PDF saved to {pdf_path}")

### Main Routine
def main():
    # Modes:
    # 1 argument: input.pdf → interactive crop box definition.
    # 2 arguments: input.pdf output.pdf → crop using saved crop data.
    # 3 arguments: input.pdf output.pdf angle_clockwise → crop then rotate.
    if len(sys.argv) == 2:
        input_pdf = sys.argv[1]
        interactive_crop_selector(input_pdf)
    elif len(sys.argv) == 3 or len(sys.argv) == 4:
        input_pdf = sys.argv[1]
        output_pdf = sys.argv[2]
        # Load crop data from config file.
        if not os.path.exists(CONFIG_FILE):
            print("Crop data not found. Run the script with only the input PDF to define the crop box.")
            sys.exit(1)
        with open(CONFIG_FILE, "r") as f:
            crop_data = json.load(f)
        if len(sys.argv) == 4:
            try:
                angle = int(sys.argv[3])
            except ValueError:
                print("Rotation angle must be an integer (e.g., 90).")
                sys.exit(1)
            crop_pdf(input_pdf, output_pdf, crop_data, quiet=True)
            rotate_pdf(output_pdf, angle, quiet=True)
            print(f"Cropped and rotated PDF saved to {output_pdf}")
        else:
            crop_pdf(input_pdf, output_pdf, crop_data)
    else:
        print("Usage:")
        print("  To define crop box interactively:")
        print("      labelcrop input.pdf")
        print("  To crop using saved crop box:")
        print("      labelcrop input.pdf output.pdf")
        print("  To crop and rotate:")
        print("      labelcrop input.pdf output.pdf angle_clockwise")
        sys.exit(1)

if __name__ == '__main__':
    main()
