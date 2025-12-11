#!/usr/bin/env python3
"""
DFMC Email Banner Image Processor

This script processes marathon photos for email templates:
- Detects faces to avoid cropping heads
- Intelligently crops for email banner aspect ratios
- Resizes to 600px width (with optional 1200px for retina)
- Optimizes file size while maintaining quality
"""

import os
import cv2
import numpy as np
from PIL import Image
import glob

# Configuration
INPUT_DIR = "originals"
OUTPUT_DIR = "resized"
TARGET_WIDTH = 600
TARGET_HEIGHT = 340  # Taller banner for better cropping
RETINA_WIDTH = 1200  # For high-DPI displays
RETINA_HEIGHT = 680  # Matching height for retina
TARGET_ASPECT_RATIO = TARGET_WIDTH / TARGET_HEIGHT  # ~1.76:1 ratio
JPEG_QUALITY = 82  # Balance between quality and file size
MAX_FILE_SIZE_KB = 100  # Target max file size for fast email loading

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_face_detector():
    """Load OpenCV's pre-trained face detector."""
    # Use OpenCV's built-in Haar cascade for face detection
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    return face_cascade

def detect_faces(image, face_cascade):
    """Detect faces in the image and return bounding boxes."""
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect faces with various parameters for better detection
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    
    return faces

def calculate_safe_crop_region(img_width, img_height, faces, target_aspect_ratio):
    """
    Calculate the optimal crop region that:
    1. Maintains the target aspect ratio
    2. Avoids cropping any detected faces/heads
    3. Centers on the most interesting part of the image
    """
    # Calculate target height based on aspect ratio
    target_height = int(img_width / target_aspect_ratio)
    
    # If the image is already shorter than target height, don't crop vertically
    if img_height <= target_height:
        return 0, 0, img_width, img_height
    
    # Find the vertical bounds that include all faces (with padding for heads)
    if len(faces) > 0:
        # Add 50% extra space above faces for heads
        head_padding = 0.5
        
        min_face_y = float('inf')
        max_face_bottom = 0
        
        for (x, y, w, h) in faces:
            # Top of face with head padding
            face_top = max(0, y - int(h * head_padding))
            min_face_y = min(min_face_y, face_top)
            
            # Bottom of face
            face_bottom = y + h
            max_face_bottom = max(max_face_bottom, face_bottom)
        
        # Calculate face region height
        face_region_height = max_face_bottom - min_face_y
        
        # If faces fit within target height, center crop around faces
        if face_region_height <= target_height:
            # Center the crop around the face region
            face_center_y = min_face_y + face_region_height // 2
            crop_top = face_center_y - target_height // 2
            
            # Ensure crop stays within image bounds
            if crop_top < 0:
                crop_top = 0
            elif crop_top + target_height > img_height:
                crop_top = img_height - target_height
        else:
            # Faces span more than target height, crop from top of topmost face
            crop_top = min_face_y
            if crop_top + target_height > img_height:
                crop_top = img_height - target_height
    else:
        # No faces detected - center crop (typical for group/landscape shots)
        crop_top = (img_height - target_height) // 2
    
    return 0, crop_top, img_width, crop_top + target_height

def process_image(input_path, output_base, face_cascade):
    """Process a single image: detect faces, crop, resize, and save."""
    print(f"\nProcessing: {os.path.basename(input_path)}")
    
    # Load image with OpenCV for face detection
    cv_image = cv2.imread(input_path)
    if cv_image is None:
        print(f"  ERROR: Could not load image")
        return None
    
    img_height, img_width = cv_image.shape[:2]
    print(f"  Original size: {img_width}x{img_height}")
    
    # Detect faces
    faces = detect_faces(cv_image, face_cascade)
    print(f"  Faces detected: {len(faces)}")
    
    # Calculate crop region
    x1, y1, x2, y2 = calculate_safe_crop_region(
        img_width, img_height, faces, TARGET_ASPECT_RATIO
    )
    crop_height = y2 - y1
    print(f"  Crop region: y={y1} to y={y2} (height={crop_height})")
    
    # Load with PIL for high-quality resizing
    pil_image = Image.open(input_path)
    
    # Crop the image
    cropped = pil_image.crop((x1, y1, x2, y2))
    cropped_width, cropped_height = cropped.size
    print(f"  Cropped size: {cropped_width}x{cropped_height}")
    
    results = []
    
    # Process for both standard (600px) and retina (1200px) widths
    for target_width in [TARGET_WIDTH, RETINA_WIDTH]:
        # Calculate new height maintaining aspect ratio
        scale = target_width / cropped_width
        new_height = int(cropped_height * scale)
        
        # High-quality resize using LANCZOS resampling
        resized = cropped.resize((target_width, new_height), Image.LANCZOS)
        
        # Convert to RGB if necessary (for JPEG)
        if resized.mode in ('RGBA', 'P'):
            resized = resized.convert('RGB')
        
        # Save with optimized quality
        output_path = f"{output_base}_{target_width}.jpg"
        
        # Start with target quality and adjust if file too large
        quality = JPEG_QUALITY
        resized.save(output_path, 'JPEG', quality=quality, optimize=True)
        
        file_size_kb = os.path.getsize(output_path) / 1024
        
        # If file is too large for 600px version, reduce quality
        if target_width == TARGET_WIDTH and file_size_kb > MAX_FILE_SIZE_KB:
            for q in range(JPEG_QUALITY - 5, 50, -5):
                resized.save(output_path, 'JPEG', quality=q, optimize=True)
                file_size_kb = os.path.getsize(output_path) / 1024
                if file_size_kb <= MAX_FILE_SIZE_KB:
                    quality = q
                    break
        
        print(f"  Saved: {output_path} ({target_width}x{new_height}, {file_size_kb:.1f}KB, q={quality})")
        results.append({
            'path': output_path,
            'width': target_width,
            'height': new_height,
            'size_kb': file_size_kb,
            'quality': quality
        })
    
    return results

def main():
    print("=" * 70)
    print("DFMC EMAIL BANNER IMAGE PROCESSOR")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Target widths: {TARGET_WIDTH}px (standard), {RETINA_WIDTH}px (retina)")
    print(f"  Target aspect ratio: {TARGET_ASPECT_RATIO}:1")
    print(f"  JPEG quality: {JPEG_QUALITY}")
    print(f"  Max file size (600px): {MAX_FILE_SIZE_KB}KB")
    
    # Load face detector
    print("\nLoading face detector...")
    face_cascade = load_face_detector()
    
    # Find all input images
    input_pattern = os.path.join(INPUT_DIR, "dfmc_email_banner*.jpg")
    input_files = sorted(glob.glob(input_pattern))
    
    if not input_files:
        print(f"\nERROR: No images found matching {input_pattern}")
        return
    
    print(f"\nFound {len(input_files)} images to process")
    
    # Process each image
    all_results = []
    for input_path in input_files:
        # Extract banner number from filename
        basename = os.path.basename(input_path)
        # e.g., "dfmc_email_banner1.jpg" -> "1"
        banner_num = basename.replace("dfmc_email_banner", "").replace(".jpg", "")
        
        output_base = os.path.join(OUTPUT_DIR, f"dfmc_banner{banner_num}")
        results = process_image(input_path, output_base, face_cascade)
        
        if results:
            all_results.append({
                'input': input_path,
                'banner_num': banner_num,
                'outputs': results
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nSuccessfully processed: {len(all_results)} images")
    
    print(f"\nOutput files in '{OUTPUT_DIR}/':")
    total_600_size = 0
    total_1200_size = 0
    
    for result in all_results:
        for output in result['outputs']:
            if output['width'] == 600:
                total_600_size += output['size_kb']
            else:
                total_1200_size += output['size_kb']
            print(f"  {os.path.basename(output['path'])} - {output['width']}x{output['height']}, {output['size_kb']:.1f}KB")
    
    print(f"\nTotal file sizes:")
    print(f"  600px versions: {total_600_size:.1f}KB ({total_600_size/len(all_results):.1f}KB avg)")
    print(f"  1200px versions: {total_1200_size:.1f}KB ({total_1200_size/len(all_results):.1f}KB avg)")

if __name__ == "__main__":
    main()

