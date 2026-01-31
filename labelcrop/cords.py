#!/usr/bin/env python3
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog

class PDFLabelSelector:
    def __init__(self):
        # Prompt for a PDF file
        self.pdf_path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF Files", "*.pdf")])
        if not self.pdf_path:
            print("No file selected. Exiting.")
            exit(0)
        self.doc = fitz.open(self.pdf_path)
        self.page = self.doc[0]  # Use first page
        self.page_height = self.page.rect.height
        self.scale = 0.5  # Scale factor for display
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.init_gui()

    def init_gui(self):
        self.root = tk.Tk()
        self.root.title("PDF Label Selector")
        self.canvas = tk.Canvas(self.root, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.render_page()
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.mainloop()

    def render_page(self):
        # Render the first page at the specified scale
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
        # Normalize coordinates (canvas origin is top-left)
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        # Convert canvas coordinates to PDF coordinates.
        # PDF x = canvas_x/scale.
        # PDF y = page_height - (canvas_y/scale)  (since PDF origin is bottom-left).
        pdf_x1 = x1 / self.scale
        pdf_y1 = self.page_height - (y2 / self.scale)  # bottom (use larger canvas y)
        pdf_x2 = x2 / self.scale
        pdf_y2 = self.page_height - (y1 / self.scale)  # top (use smaller canvas y)
        print("Selected rectangle coordinates in PDF points:")
        print(f"Bottom-left: ({pdf_x1:.2f}, {pdf_y1:.2f})")
        print(f"Top-right:   ({pdf_x2:.2f}, {pdf_y2:.2f})")
        print(f"Width: {pdf_x2 - pdf_x1:.2f}, Height: {pdf_y2 - pdf_y1:.2f}")

if __name__ == "__main__":
    PDFLabelSelector()
