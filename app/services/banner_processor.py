"""
Banner Processor Service.

Processes images into email banners with intelligent person detection.
Uses MediaPipe for full-body detection and OpenCV for face detection fallback.
"""

import io
import zipfile
from typing import List, Tuple, Any, Optional, Dict
from PIL import Image
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from app.models.schemas import BannerSettings, BannerResult


# Cache the detectors
_face_cascade = None
_pose_detector = None


def get_face_detector():
    """Get or create the face detector (cached)."""
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def get_pose_detector():
    """Get or create the MediaPipe pose detector (cached)."""
    global _pose_detector
    if _pose_detector is None:
        try:
            # Download and cache the model file in project directory or temp
            import os
            import urllib.request
            import tempfile
            
            # Try project directory first, fall back to temp
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                model_dir = os.path.join(project_root, '.mediapipe_models')
                os.makedirs(model_dir, exist_ok=True)
            except (OSError, PermissionError):
                # Use temp directory if project directory isn't writable
                model_dir = os.path.join(tempfile.gettempdir(), 'mediapipe_models')
                os.makedirs(model_dir, exist_ok=True)
            
            model_path = os.path.join(model_dir, 'pose_landmarker_lite.task')
            
            # Download model if not exists
            if not os.path.exists(model_path):
                print("Downloading MediaPipe pose detection model...")
                model_url = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task'
                urllib.request.urlretrieve(model_url, model_path)
                print(f"Model downloaded successfully to {model_path}")
            
            # Initialize detector with local model
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_poses=5,  # Detect up to 5 people
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            _pose_detector = vision.PoseLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Warning: Could not initialize MediaPipe pose detector: {e}")
            print("Falling back to face detection only")
            _pose_detector = None
    return _pose_detector


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


def detect_people(image_array: np.ndarray) -> List[Dict[str, Any]]:
    """
    Detect people using MediaPipe pose detection.
    Returns list of person bounding boxes with metadata.
    
    Returns:
        List of dicts with keys: 'bbox' (x, y, w, h), 'landmarks', 'confidence'
    """
    pose_detector = get_pose_detector()
    if pose_detector is None:
        return []
    
    try:
        # Convert numpy array to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_array)
        
        # Detect poses
        detection_result = pose_detector.detect(mp_image)
        
        if not detection_result.pose_landmarks:
            return []
        
        people = []
        img_height, img_width = image_array.shape[:2]
        
        for pose_landmarks in detection_result.pose_landmarks:
            # Calculate bounding box from all landmarks
            x_coords = [lm.x * img_width for lm in pose_landmarks]
            y_coords = [lm.y * img_height for lm in pose_landmarks]
            
            if not x_coords or not y_coords:
                continue
            
            min_x = max(0, int(min(x_coords)))
            max_x = min(img_width, int(max(x_coords)))
            min_y = max(0, int(min(y_coords)))
            max_y = min(img_height, int(max(y_coords)))
            
            # Calculate bounding box dimensions
            x = min_x
            y = min_y
            w = max_x - min_x
            h = max_y - min_y
            
            # Skip if bounding box is too small
            if w < 10 or h < 10:
                continue
            
            # Calculate average confidence (visibility score)
            avg_confidence = sum(lm.visibility for lm in pose_landmarks if hasattr(lm, 'visibility')) / len(pose_landmarks)
            
            people.append({
                'bbox': (x, y, w, h),
                'landmarks': pose_landmarks,
                'confidence': avg_confidence
            })
        
        return people
        
    except Exception as e:
        print(f"Error in pose detection: {e}")
        return []


def calculate_safe_crop_region(
    img_width: int,
    img_height: int,
    faces: List[Tuple[int, int, int, int]],
    target_aspect_ratio: float
) -> Tuple[int, int, int, int]:
    """Calculate optimal crop region that preserves faces (legacy function)."""
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


def calculate_smart_crop(
    img_width: int,
    img_height: int,
    people: List[Dict[str, Any]],
    faces: List[Tuple[int, int, int, int]],
    target_aspect_ratio: float,
    padding_percent: float = 0.15
) -> Tuple[int, int, int, int]:
    """
    Calculate optimal crop region using full-body person detection.
    Falls back to face detection, then center crop.
    
    Args:
        img_width: Image width
        img_height: Image height
        people: List of detected people with bounding boxes
        faces: List of detected faces (fallback)
        target_aspect_ratio: Target width/height ratio
        padding_percent: Padding around detected subjects (0.0-0.3)
    
    Returns:
        Tuple of (x1, y1, x2, y2) crop coordinates
    """
    target_height = int(img_width / target_aspect_ratio)
    
    # If image already fits, no crop needed
    if img_height <= target_height:
        return 0, 0, img_width, img_height
    
    # Priority 1: Use person detection
    if len(people) > 0:
        # Find bounding box that encompasses all detected people
        min_x = float('inf')
        max_x = 0
        min_y = float('inf')
        max_y = 0
        
        for person in people:
            x, y, w, h = person['bbox']
            min_x = min(min_x, x)
            max_x = max(max_x, x + w)
            min_y = min(min_y, y)
            max_y = max(max_y, y + h)
        
        # Add padding around people
        padding_x = int((max_x - min_x) * padding_percent)
        padding_y = int((max_y - min_y) * padding_percent)
        
        min_x = max(0, min_x - padding_x)
        max_x = min(img_width, max_x + padding_x)
        min_y = max(0, min_y - padding_y)
        max_y = min(img_height, max_y + padding_y)
        
        # Calculate vertical center of people region
        people_center_y = (min_y + max_y) // 2
        
        # Calculate crop top to center people vertically
        crop_top = people_center_y - target_height // 2
        
        # Ensure crop stays within image bounds
        if crop_top < 0:
            crop_top = 0
        elif crop_top + target_height > img_height:
            crop_top = img_height - target_height
        
        return 0, crop_top, img_width, crop_top + target_height
    
    # Priority 2: Fallback to face detection
    elif len(faces) > 0:
        return calculate_safe_crop_region(img_width, img_height, faces, target_aspect_ratio)
    
    # Priority 3: Center crop
    else:
        crop_top = (img_height - target_height) // 2
        return 0, crop_top, img_width, crop_top + target_height


def process_single_image(
    image_bytes: bytes,
    settings: BannerSettings,
    manual_crop: Optional[Dict[str, int]] = None
) -> Tuple[List[dict], int, int]:
    """
    Process a single image with the given settings.
    
    Args:
        image_bytes: Image data
        settings: Processing settings
        manual_crop: Optional manual crop coords {x1, y1, x2, y2}
    
    Returns:
        Tuple of (list of result dicts with bytes, people_detected count, faces_detected count)
    """
    # Load image
    pil_image = Image.open(io.BytesIO(image_bytes))
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    # Convert to numpy for detection
    img_array = np.array(pil_image)
    img_height, img_width = img_array.shape[:2]
    
    # Use manual crop if provided
    if manual_crop:
        x1 = manual_crop.get('x1', 0)
        y1 = manual_crop.get('y1', 0)
        x2 = manual_crop.get('x2', img_width)
        y2 = manual_crop.get('y2', img_height)
        people_count = 0
        faces_count = 0
    else:
        # Detect people (full body)
        people = detect_people(img_array)
        people_count = len(people)
        
        # Detect faces (fallback)
        faces = detect_faces(img_array)
        faces_count = len(faces)
        
        # Calculate smart crop region
        target_aspect_ratio = settings.width / settings.height
        padding = getattr(settings, 'crop_padding', 0.15)
        x1, y1, x2, y2 = calculate_smart_crop(
            img_width, img_height, people, faces, target_aspect_ratio, padding
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
    
    return results, people_count, faces_count


def generate_crop_preview(
    image_bytes: bytes,
    settings: BannerSettings
) -> Dict[str, Any]:
    """
    Generate a crop preview for a single image.
    
    Args:
        image_bytes: Image data
        settings: Banner settings
    
    Returns:
        Dict with image_base64, crop_box, people_detected, faces_detected, dimensions
    """
    import base64
    
    # Load image
    pil_image = Image.open(io.BytesIO(image_bytes))
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    # Convert to numpy for detection
    img_array = np.array(pil_image)
    img_height, img_width = img_array.shape[:2]
    
    # Detect people and faces
    people = detect_people(img_array)
    faces = detect_faces(img_array)
    
    # Calculate smart crop region
    target_aspect_ratio = settings.width / settings.height
    padding = getattr(settings, 'crop_padding', 0.15)
    x1, y1, x2, y2 = calculate_smart_crop(
        img_width, img_height, people, faces, target_aspect_ratio, padding
    )
    
    # Convert image to base64 for frontend
    buffer = io.BytesIO()
    pil_image.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return {
        'image_base64': f"data:image/jpeg;base64,{image_base64}",
        'crop_box': {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'width': x2 - x1,
            'height': y2 - y1
        },
        'people_detected': len(people),
        'faces_detected': len(faces),
        'dimensions': {
            'width': img_width,
            'height': img_height
        },
        'target_dimensions': {
            'width': settings.width,
            'height': settings.height
        }
    }


async def process_banners(
    files: List[Tuple[str, bytes]],
    settings: BannerSettings,
    manual_crops: Optional[Dict[str, Dict[str, int]]] = None
) -> Tuple[bytes, List[BannerResult]]:
    """
    Process multiple images into email banners.
    
    Args:
        files: List of (filename, content) tuples
        settings: Banner processing settings
        manual_crops: Optional dict mapping filename to crop coords
        
    Returns:
        Tuple of (zip_bytes, list of BannerResult)
    """
    import asyncio
    
    all_results = []
    processed_data = []
    
    # Process each file
    for filename, content in files:
        try:
            manual_crop = manual_crops.get(filename) if manual_crops else None
            results, people_detected, faces_detected = process_single_image(
                content, settings, manual_crop
            )
            
            processed_data.append({
                'filename': filename,
                'results': results,
                'people_detected': people_detected,
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
                    people_detected=people_detected,
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
