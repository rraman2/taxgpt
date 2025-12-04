#!/usr/bin/env python3
"""
Convert PDF to JPEG images (one per page)

Usage:
    python convert_pdf_to_jpeg.py input.pdf [output_prefix]

Example:
    python convert_pdf_to_jpeg.py 1040.pdf 1040
    # Creates: 1040_page_1.jpeg, 1040_page_2.jpeg, etc.
"""

import sys
from pathlib import Path

try:
    from pdf2image import convert_from_path
    from PIL import Image
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install with: pip3 install pdf2image pillow")
    print("\nAlso install poppler:")
    print("  macOS: brew install poppler")
    sys.exit(1)


def convert_pdf_to_jpeg(pdf_path: str, output_prefix: str = None, dpi: int = 300):
    """
    Convert PDF to JPEG images, one per page.
    
    Args:
        pdf_path: Path to input PDF file
        output_prefix: Prefix for output files (default: PDF filename without extension)
        dpi: Resolution for output images (default: 300)
    """
    pdf_path_obj = Path(pdf_path)
    
    if not pdf_path_obj.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    if output_prefix is None:
        output_prefix = pdf_path_obj.stem
    
    print(f"Converting {pdf_path} to JPEG images...")
    print(f"Output prefix: {output_prefix}")
    print(f"DPI: {dpi}")
    print()
    
    try:
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=dpi)
        
        print(f"Converted {len(images)} pages")
        
        # Save each page as JPEG
        output_files = []
        for i, image in enumerate(images, start=1):
            output_filename = f"{output_prefix}_page_{i}.jpeg"
            image.save(output_filename, "JPEG", quality=95)
            output_files.append(output_filename)
            print(f"  Page {i} → {output_filename}")
        
        print()
        print(f"✓ Successfully converted {len(output_files)} pages")
        print(f"Output files:")
        for f in output_files:
            print(f"  - {f}")
        
        return output_files
    
    except Exception as e:
        print(f"Error converting PDF: {e}")
        print("\nIf you see 'poppler' errors, install poppler:")
        print("  macOS: brew install poppler")
        print("  Ubuntu: sudo apt-get install poppler-utils")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_pdf_to_jpeg(pdf_path, output_prefix)

