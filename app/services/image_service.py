import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_DOC_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def is_allowed_file(filename, allowed_extensions=ALLOWED_IMAGE_EXTENSIONS):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions

def process_and_save_image(file_storage, subfolder='reports', max_width=1200, quality=85):
    """
    Validates, renames with UUID, resizes/compresses with Pillow, and saves image.
    Never trusts original filename. Returns the relative web path.
    """
    if not file_storage or not file_storage.filename:
        return None
        
    original_ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else 'jpg'
    if original_ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None
        
    unique_name = f"{uuid.uuid4().hex}.{original_ext if original_ext != 'jpeg' else 'jpg'}"
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(target_dir, exist_ok=True)
    destination_path = os.path.join(target_dir, unique_name)
    
    try:
        # Open with Pillow for format verification & compression
        image = Image.open(file_storage)
        
        # Convert RGBA/P to RGB if saving as JPEG
        if image.mode in ('RGBA', 'P') and original_ext in ['jpg', 'jpeg']:
            image = image.convert('RGB')
            
        # Resize if oversized while keeping aspect ratio
        w, h = image.size
        if w > max_width:
            ratio = max_width / float(w)
            new_h = int(float(h) * float(ratio))
            image = image.resize((max_width, new_h), Image.Resampling.LANCZOS)
            
        # Save compressed
        if original_ext in ['jpg', 'jpeg']:
            image.save(destination_path, 'JPEG', quality=quality, optimize=True)
        elif original_ext == 'webp':
            image.save(destination_path, 'WEBP', quality=quality)
        elif original_ext == 'png':
            image.save(destination_path, 'PNG', optimize=True)
        else:
            image.save(destination_path)
            
        # Return web-accessible path
        return f"uploads/{subfolder}/{unique_name}"
    except Exception as e:
        print(f"[ImageService Error] Failed processing image: {e}")
        return None

def save_evidence_document(file_storage):
    """
    Saves an ownership proof document (image or PDF) with a unique filename.
    """
    if not file_storage or not file_storage.filename:
        return None
        
    if not is_allowed_file(file_storage.filename, ALLOWED_DOC_EXTENSIONS):
        return None
        
    original_ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    unique_name = f"evidence_{uuid.uuid4().hex}.{original_ext}"
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'evidence')
    os.makedirs(target_dir, exist_ok=True)
    destination_path = os.path.join(target_dir, unique_name)
    
    # If image, compress and verify
    if original_ext in ALLOWED_IMAGE_EXTENSIONS:
        return process_and_save_image(file_storage, subfolder='evidence')
    else:
        # PDF document
        file_storage.save(destination_path)
        return f"uploads/evidence/{unique_name}"

