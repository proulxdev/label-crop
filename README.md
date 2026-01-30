# LabelCrop

A CLI for defining crop regions on PDFs and batch cropping/rotating them. Useful for shipping labels or other PDF documents that need consistent formatting.

> **Acknowledgement:** Credit to the [original project](https://github.com/abdulhtc24/label_corrector) and [tutorial](https://www.youtube.com/watch?v=buwDcc9j00o) by abdulhtc24. This fork turns it into a `uv` tool, making installation and usage easier.

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
uv tool install https://github.com/proulxdev/label-crop/archive/refs/heads/main.zip
```
### Update:
```bash
uv tool upgrade label-crop
```
### Remove:
```bash
uv tool uninstall label-crop
```

## Usage
You should have `label-crop` as a global command. Alternatively, you can run `lbl.py` using `python3` or `uv run`.

### Crop Selection:
```bash
label-crop input.pdf
```
Select the rectangular crop region.

### Crop:
```bash
label-crop input.pdf output.pdf
```
Applies the saved crop selection to every page.

### Crop & Rotate:
```bash
label-crop input.pdf output.pdf 90
```
Applies the saved crop selection to every page then rotates in degrees clockwise.


> **Note:** Crop settings are saved to `crop_data.cfg` in your current directory. Cropping requires this file to be present in your current directory.
