"""
Banner Processor Service.

Processes images into email banners with face detection.
Migrated from the original Streamlit implementation.
"""

import io
import zipfile
from typing import List, Tuple, Any
from PIL import Image
import cv2
import numpy as np

from app.models.schemas import BannerSettings, BannerResult


# Cache the face detector
_face_cascade = None


def get_face_detector():
    """Get or create the face detector (cached)."""
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def detect_faces(image_array: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect faces in the image and return bounding boxes."""
    face_cascade = get_face_detector()
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    return faces


def calculate_safe_crop_region(
    img_width: int,
    img_height: int,
    faces: List[Tuple[int, int, int, int]],
    target_aspect_ratio: float
) -> Tuple[int, int, int, int]:
    """Calculate optimal crop region that preserves faces."""
    target_height = int(img_width / target_aspect_ratio)
    
    if img_height <= target_height:
        return 0, 0, img_width, img_height
    
    if len(faces) > 0:
        head_padding = 0.5
        min_face_y = float('inf')
        max_face_bottom = 0
        
        for (x, y, w, h) in faces:
            face_top = max(0, y - int(h * head_padding))
            min_face_y = min(min_face_y, face_top)
            face_bottom = y + h
            max_face_bottom = max(max_face_bottom, face_bottom)
        
        face_region_height = max_face_bottom - min_face_y
        
        if face_region_height <= target_height:
            face_center_y = min_face_y + face_region_height // 2
            crop_top = face_center_y - target_height // 2
            
            if crop_top < 0:
                crop_top = 0
            elif crop_top + target_height > img_height:
                crop_top = img_height - target_height
        else:
            crop_top = min_face_y
            if crop_top + target_height > img_height:
                crop_top = img_height - target_height
    else:
        crop_top = (img_height - target_height) // 2
    
    return 0, crop_top, img_width, crop_top + target_height


def process_single_image(
    image_bytes: bytes,
    settings: BannerSettings
) -> Tuple[List[dict], int]:
    """
    Process a single image with the given settings.
    
    Returns:
        Tuple of (list of result dicts with bytes, faces_detected count)
    """
    # Load image
    pil_image = Image.open(io.BytesIO(image_bytes))
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    # Convert to numpy for face detection
    img_array = np.array(pil_image)
    img_height, img_width = img_array.shape[:2]
    
    # Detect faces
    faces = detect_faces(img_array)
    
    # Calculate crop region
    target_aspect_ratio = settings.width / settings.height
    x1, y1, x2, y2 = calculate_safe_crop_region(
        img_width, img_height, faces, target_aspect_ratio
    )
    
    # Crop
    cropped = pil_image.crop((x1, y1, x2, y2))
    
    results = []
    
    # Process standard size
    resized = cropped.resize(
        (settings.width, settings.height),
        Image.LANCZOS
    )
    if resized.mode in ('RGBA', 'P'):
        resized = resized.convert('RGB')
    
    # Save to bytes
    buffer = io.BytesIO()
    resized.save(buffer, format='JPEG', quality=settings.quality, optimize=True)
    buffer.seek(0)
    
    results.append({
        'bytes': buffer.getvalue(),
        'width': settings.width,
        'height': settings.height,
        'size_kb': len(buffer.getvalue()) / 1024,
        'suffix': f"_{settings.width}"
    })
    
    # Process retina size if enabled
    if settings.include_retina:
        retina_width = settings.width * 2
        retina_height = settings.height * 2
        resized_retina = cropped.resize(
            (retina_width, retina_height),
            Image.LANCZOS
        )
        if resized_retina.mode in ('RGBA', 'P'):
            resized_retina = resized_retina.convert('RGB')
        
        buffer_retina = io.BytesIO()
        resized_retina.save(buffer_retina, format='JPEG', quality=settings.quality, optimize=True)
        buffer_retina.seek(0)
        
        results.append({
            'bytes': buffer_retina.getvalue(),
            'width': retina_width,
            'height': retina_height,
            'size_kb': len(buffer_retina.getvalue()) / 1024,
            'suffix': f"_{retina_width}"
        })
    
    return results, len(faces)


async def process_banners(
    files: List[Tuple[str, bytes]],
    settings: BannerSettings
) -> Tuple[bytes, List[BannerResult]]:
    """
    Process multiple images into email banners.
    
    Args:
        files: List of (filename, content) tuples
        settings: Banner processing settings
        
    Returns:
        Tuple of (zip_bytes, list of BannerResult)
    """
    import asyncio
    
    all_results = []
    processed_data = []
    
    # Process each file
    for filename, content in files:
        try:
            results, faces_detected = process_single_image(content, settings)
            
            processed_data.append({
                'filename': filename,
                'results': results,
                'faces_detected': faces_detected,
            })
            
            # Add to results
            for result in results:
                all_results.append(BannerResult(
                    filename=filename,
                    width=result['width'],
                    height=result['height'],
                    size_kb=result['size_kb'],
                    faces_detected=faces_detected,
                ))
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Create ZIP file
    zip_buffer = io.BytesIO()
    prefix = settings.filename_prefix
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, data in enumerate(processed_data):
            for result in data['results']:
                # Build filename
                if len(processed_data) > 1:
                    base = f"email_banner{i+1}"
                else:
                    base = "email_banner"
                
                if prefix:
                    filename = f"{prefix}_{base}{result['suffix']}.jpg"
                else:
                    filename = f"{base}{result['suffix']}.jpg"
                
                zip_file.writestr(filename, result['bytes'])
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue(), all_results
