# LabelCrop

A CLI for defining crop regions on PDFs and batch cropping/rotating them. Useful for shipping labels or other PDF documents that need consistent formatting.


> **Acknowledgement:** Credit to the [original project](https://github.com/abdulhtc24/label_corrector) and [tutorial](https://www.youtube.com/watch?v=buwDcc9j00o) by abdulhtc24. This fork simplifies installation and adds a few extra features.

![Screenshot of the LabelCrop GUI](LabelCrop-GUI.webp)

## Features

- **Interactive GUI**: visually select the crop area on the first page of your PDF.
- **Batch Processing**: applies the crop selection to all pages in the PDF.
- **Rotation**: optionally rotate the cropped pages (e.g., 90 or 180 degrees).
- **Cross-Platform**: Works on macOS, Linux, and Windows.

## Installation

### Prerequisites:
- Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) to be installed.

### Install:
```bash
uv tool install https://github.com/proulxdev/LabelCrop/archive/refs/heads/main.zip
```
### Update:
```bash
uv tool upgrade labelcrop
```
### Remove:
```bash
uv tool uninstall labelcrop
```

## Usage

### Select Crop Area:
```bash
labelcrop input.pdf
```
Use the toolbar to choose Freeform, Force Aspect Ratio, or Force Dimensions. Enter any aspect ratio or dimension constraints. Adjust the crop area by dragging the rectangle, its edges, or its corners. Click Done to save the selection and close.

### Crop:
```bash
labelcrop input.pdf output.pdf
```
Applies the saved crop selection to every page.

### Crop & Rotate:
```bash
labelcrop input.pdf output.pdf 90
```
Applies the saved crop selection to every page then rotates in degrees clockwise.


> **Note:** Crop settings are saved to `crop_data.cfg` in your current directory. Cropping requires this file to be present in your current directory.

> **Note:** You should have `labelcrop` as a global command. Alternatively, you can run `lbl.py` using `uv run` or `python3`.