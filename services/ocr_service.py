import os
import re
import shutil
from datetime import datetime
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from config import Config


def is_tesseract_available():
    """Check if Tesseract binary is available on system or configured path."""
    configured_cmd = Config.TESSERACT_CMD
    if configured_cmd and os.path.isfile(configured_cmd):
        return True
    if shutil.which('tesseract'):
        return True
    return False


def get_tesseract_cmd():
    """Return configured or system-found Tesseract command."""
    if Config.TESSERACT_CMD and os.path.isfile(Config.TESSERACT_CMD):
        return Config.TESSERACT_CMD
    which_cmd = shutil.which('tesseract')
    if which_cmd:
        return which_cmd
    return None


def preprocess_image(image_path):
    """Preprocess image with OpenCV or PIL for optimal OCR accuracy."""
    try:
        if cv2 is not None and np is not None:
            # OpenCV pipeline
            img = cv2.imread(image_path)
            if img is None:
                return Image.open(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Median blur to reduce noise
            blurred = cv2.medianBlur(gray, 3)
            
            # Adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Convert back to PIL Image
            return Image.fromarray(thresh)
        else:
            # Fallback to PIL grayscale & contrast enhancement
            pil_img = Image.open(image_path).convert('L')
            return pil_img
    except Exception as e:
        print(f"Preprocess warning: {e}")
        return Image.open(image_path)


def extract_text_from_pdf(pdf_path):
    """Extract digital text from PDF using pypdf."""
    text = ""
    if not PdfReader:
        return text
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        print(f"PDF extraction error: {e}")
    return text.strip()


def extract_text_from_file(file_path):
    """Extract text from PDF or image file.
    Returns a dictionary with status, extracted text, and helpful messages.
    """
    res = {
        'success': False,
        'tesseract_available': is_tesseract_available(),
        'text': '',
        'message': ''
    }

    if not os.path.isfile(file_path):
        res['message'] = "File not found on server."
        return res

    ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''

    # Handle PDF
    if ext == 'pdf':
        digital_text = extract_text_from_pdf(file_path)
        if digital_text:
            res['success'] = True
            res['text'] = digital_text
            res['message'] = "Extracted digital text from PDF successfully."
            return res
        else:
            # Scanned PDF without text layer
            res['message'] = "PDF does not contain digital text layer. For scanned PDFs, please upload an image or install Tesseract OCR."
            return res

    # Handle Image files (PNG, JPG, JPEG)
    if ext in ('jpg', 'jpeg', 'png'):
        if not is_tesseract_available():
            res['message'] = (
                "Tesseract OCR is not installed or not configured in PATH. "
                "You can still preview the captured image and enter the document details manually below."
            )
            return res

        try:
            t_cmd = get_tesseract_cmd()
            if t_cmd:
                pytesseract.pytesseract.tesseract_cmd = t_cmd

            preprocessed = preprocess_image(file_path)
            
            # Try running English and Marathi (if available in tessdata)
            try:
                extracted = pytesseract.image_to_string(preprocessed, lang='eng+mar')
            except Exception:
                # Fallback to English only
                extracted = pytesseract.image_to_string(preprocessed, lang='eng')

            res['success'] = True
            res['text'] = extracted.strip()
            res['message'] = "OCR completed successfully."
            return res
        except Exception as e:
            res['message'] = f"OCR engine error during scan: {str(e)}"
            return res

    res['message'] = f"Unsupported file extension: .{ext}"
    return res


def parse_document_text(text):
    """Parse text and extract key metadata using rule-based and regex patterns.
    Never invents data!
    """
    info = {
        'category': 'other',
        'document_number': '',
        'holder_name': '',
        'issue_date': '',
        'expiry_date': '',
        'issuing_authority': '',
        'confidence_notes': []
    }

    if not text:
        return info

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # ── 1. Document Category & Number Detection ──
    # Aadhaar Card: 12 digits (often 4 4 4)
    aadhaar_match = re.search(r'\b(\d{4}\s\d{4}\s\d{4})\b', text)
    if not aadhaar_match:
        aadhaar_match = re.search(r'\b(\d{12})\b', text)

    # PAN Card: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
    pan_match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)

    # Driving Licence: e.g., MH14 20180012345 or DL-0420110012345
    dl_match = re.search(r'\b([A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{4,11})\b', text)

    # Passport: 1 letter followed by 7 digits
    passport_match = re.search(r'\b([A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9])\b', text)

    # Vehicle RC (Vehicle Registration: e.g., MH 12 AB 1234)
    vehicle_reg_match = re.search(r'\b([A-Z]{2}[-\s]?[0-9]{1,2}[-\s]?[A-Z]{1,3}[-\s]?[0-9]{4})\b', text)

    text_lower = text.lower()

    if 'income tax' in text_lower or 'permanent account' in text_lower or pan_match:
        info['category'] = 'pan'
        info['issuing_authority'] = 'Income Tax Department, Govt of India'
        if pan_match:
            info['document_number'] = pan_match.group(1).upper()
            info['confidence_notes'].append("Detected PAN format.")
    elif 'aadhaar' in text_lower or 'uidai' in text_lower or 'unique identification' in text_lower or aadhaar_match:
        info['category'] = 'aadhaar'
        info['issuing_authority'] = 'Unique Identification Authority of India (UIDAI)'
        if aadhaar_match:
            info['document_number'] = aadhaar_match.group(1).strip()
            info['confidence_notes'].append("Detected Aadhaar 12-digit format.")
    elif 'driving licence' in text_lower or 'motor vehicles act' in text_lower or 'driving license' in text_lower:
        info['category'] = 'driving_licence'
        info['issuing_authority'] = 'Regional Transport Office (RTO)'
        if dl_match:
            info['document_number'] = dl_match.group(1).strip()
            info['confidence_notes'].append("Detected Driving Licence format.")
    elif 'passport' in text_lower or 'republic of india' in text_lower:
        info['category'] = 'passport'
        info['issuing_authority'] = 'Ministry of External Affairs, India'
        if passport_match:
            info['document_number'] = passport_match.group(1).replace(' ', '').upper()
            info['confidence_notes'].append("Detected Indian Passport number.")
    elif 'pollution under control' in text_lower or 'puc certificate' in text_lower:
        info['category'] = 'vehicle_puc'
        info['issuing_authority'] = 'Transport Department'
    elif 'policy' in text_lower and ('insurance' in text_lower or 'sum insured' in text_lower):
        if 'health' in text_lower or 'mediclaim' in text_lower:
            info['category'] = 'health_insurance'
        elif 'life' in text_lower or 'lic' in text_lower:
            info['category'] = 'life_insurance'
        else:
            info['category'] = 'vehicle_insurance'
    elif 'certificate of registration' in text_lower or 'chassis' in text_lower or 'engine no' in text_lower:
        info['category'] = 'vehicle_rc'
        info['issuing_authority'] = 'Regional Transport Office (RTO)'
        if vehicle_reg_match:
            info['document_number'] = vehicle_reg_match.group(1).strip()

    # ── 2. Dates Extraction (Issue & Expiry) ──
    date_regex = r'\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b'

    expiry_keywords = ['expiry', 'expires', 'valid till', 'valid upto', 'validity', 'valid through', 'valid until', 'end date', 'best before']
    issue_keywords = ['issue date', 'date of issue', 'issued on', 'start date', 'effective from', 'commencement', 'reg date']

    for line in lines:
        l_lower = line.lower()
        dates_in_line = re.findall(date_regex, line, re.IGNORECASE)
        if dates_in_line:
            # Check context
            if any(k in l_lower for k in expiry_keywords) and not info['expiry_date']:
                parsed = normalize_date(dates_in_line[0])
                if parsed:
                    info['expiry_date'] = parsed
                    info['confidence_notes'].append(f"Identified expiry date from context: '{line[:40]}'")
            elif any(k in l_lower for k in issue_keywords) and not info['issue_date']:
                parsed = normalize_date(dates_in_line[0])
                if parsed:
                    info['issue_date'] = parsed
                    info['confidence_notes'].append(f"Identified issue date from context: '{line[:40]}'")

    # Fallback date assignment if two dates found and none assigned
    all_dates = []
    for match in re.finditer(date_regex, text, re.IGNORECASE):
        norm = normalize_date(match.group(1))
        if norm and norm not in all_dates:
            all_dates.append(norm)

    if not info['issue_date'] and not info['expiry_date'] and len(all_dates) >= 2:
        # Earliest date is likely issue, latest is likely expiry
        sorted_dates = sorted(all_dates)
        info['issue_date'] = sorted_dates[0]
        info['expiry_date'] = sorted_dates[-1]
        info['confidence_notes'].append("Assigned chronological dates (earlier as issue, later as expiry). Please verify.")

    # ── 3. Holder Name Detection ──
    for line in lines:
        name_match = re.search(r'\b(?:Name|Holder|Member)\s*[:\-]\s*([A-Za-z\s]{3,35})\b', line, re.IGNORECASE)
        if name_match:
            candidate = name_match.group(1).strip()
            if candidate and not any(kw in candidate.lower() for kw in ['card', 'republic', 'india', 'department']):
                info['holder_name'] = candidate.title()
                break

    return info


def normalize_date(date_str):
    """Parse various date string formats and convert to YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip().replace('.', '/').replace('-', '/')
    
    formats = [
        '%d/%m/%Y', '%d/%m/%y',
        '%Y/%m/%d',
        '%m/%d/%Y', '%m/%d/%y',
        '%d %b %Y', '%d %B %Y',
        '%d %b %y'
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if 1950 <= dt.year <= 2100:
                return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

