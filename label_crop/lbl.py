#!/usr/bin/env python3
"""
PDF Label Tool

Modes of operation:
  1. Interactive Crop Box Definition:
       label-crop input.pdf
     • Opens a GUI showing the first page.
     • Click & drag to draw a rectangle. The script computes the bottom‑left and top‑right 
       coordinates (in PDF points) from your drag (converting from the canvas’ top‑left origin).
     • These coordinates are saved to a configuration file (crop_data.cfg) exactly as selected.
  
  2. Cropping Mode:
       label-crop input.pdf output.pdf
     • Reads the saved crop rectangle from crop_data.cfg and crops every page of the input PDF to that exact rectangle.
  
  3. Cropping + Rotation Mode:
       label-crop input.pdf output.pdf rotation_angle
     • Crops as above, then rotates each page by the given angle (in degrees, clockwise).

All coordinates are in PDF points.
"""

import sys
import os
import json
import tkinter as tk
from tkinter import filedialog
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter

CONFIG_FILE = "crop_data.cfg"

### Interactive Crop Definition (GUI)
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
            self.start_x = None
            self.start_y = None
            self.rect_id = None
            self.init_gui()
        
        def init_gui(self):
            self.root = tk.Tk()
            self.root.title("Define Crop Box: Drag a rectangle over the label area")
            self.canvas = tk.Canvas(self.root, cursor="cross")
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self.render_page()
            self.canvas.bind("<ButtonPress-1>", self.on_button_press)
            self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
            self.root.mainloop()
        
        def render_page(self):
            matrix = fitz.Matrix(self.scale, self.scale)
            pix = self.page.get_pixmap(matrix=matrix)
            self.tk_img = tk.PhotoImage(data=pix.tobytes("ppm"))
            self.canvas.config(width=pix.width, height=pix.height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        def on_button_press(self, event):
            self.start_x = event.x
            self.start_y = event.y
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                self.rect_id = None
        
        def on_mouse_drag(self, event):
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red", width=2)
        
        def on_button_release(self, event):
            end_x = event.x
            end_y = event.y
            # Normalize coordinates on the canvas (origin at top-left)
            x1 = min(self.start_x, end_x)
            y1 = min(self.start_y, end_y)
            x2 = max(self.start_x, end_x)
            y2 = max(self.start_y, end_y)
            # Convert canvas coordinates to PDF coordinates.
            # Canvas x is same direction as PDF x: pdf_x = canvas_x/scale.
            # Canvas y is top-down; PDF y is bottom-up:
            #    pdf_y = page_height - (canvas_y/scale)
            pdf_x1 = x1 / self.scale
            pdf_y1 = self.page_height - (y2 / self.scale)  # bottom (y2 is lower on canvas)
            pdf_x2 = x2 / self.scale
            pdf_y2 = self.page_height - (y1 / self.scale)  # top (y1 is higher on canvas)
            print("Selected rectangle in PDF points:")
            print(f"  Bottom-left: ({pdf_x1:.2f}, {pdf_y1:.2f})")
            print(f"  Top-right:   ({pdf_x2:.2f}, {pdf_y2:.2f})")
            print(f"  Width: {pdf_x2 - pdf_x1:.2f}, Height: {pdf_y2 - pdf_y1:.2f}")
            # Save the data exactly as selected.
            crop_data = {
                "bottom_left": {"x": pdf_x1, "y": pdf_y1},
                "top_right": {"x": pdf_x2, "y": pdf_y2}
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(crop_data, f)
            print(f"Crop data saved to {CONFIG_FILE}")
            self.root.destroy()
    
    PDFLabelSelector(input_pdf_path)

### Cropping Function
def crop_pdf(input_pdf, output_pdf, crop_data):
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
    print(f"Cropped PDF saved to {output_pdf}")

### Rotation Function
def rotate_pdf(pdf_path, angle):
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
    print(f"Rotated PDF saved to {pdf_path}")

### Main Routine
def main():
    # Modes:
    # 1 argument: input.pdf → interactive crop box definition.
    # 2 arguments: input.pdf output.pdf → crop using saved crop data.
    # 3 arguments: input.pdf output.pdf rotation_angle → crop then rotate.
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
        crop_pdf(input_pdf, output_pdf, crop_data)
        if len(sys.argv) == 4:
            try:
                angle = int(sys.argv[3])
            except ValueError:
                print("Rotation angle must be an integer (e.g., 90).")
                sys.exit(1)
            rotate_pdf(output_pdf, angle)
    else:
        print("Usage:")
        print("  To define crop box interactively:")
        print("      label-crop input.pdf")
        print("  To crop using saved crop box:")
        print("      label-crop input.pdf output.pdf")
        print("  To crop and rotate:")
        print("      label-crop input.pdf output.pdf rotation_angle")
        sys.exit(1)

if __name__ == '__main__':
    main()
