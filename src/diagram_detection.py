import cv2
import os
import numpy as np
import fitz

def pdf_to_images_for_diagrams(pdf_path, output_dir, dpi=200):
    os.makedirs(output_dir, exist_ok=True)
    pdf = fitz.open(pdf_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    paths = []
    for i in range(pdf.page_count):
        page = pdf.load_page(i)
        pix = page.get_pixmap(matrix=matrix)
        img_path = os.path.join(output_dir, f"page_{i+1}.png")
        pix.save(img_path)
        paths.append(img_path)
    pdf.close()
    return paths

def detect_diagrams(pdf_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    images = pdf_to_images_for_diagrams(pdf_path, output_dir)
    total_diagrams = 0
    for img_path in images:
        img = cv2.imread(img_path)
        if img is None:
            continue  # Skip if image failed to load
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if 10000 < area < 500000:
                total_diagrams += 1
    return total_diagrams
