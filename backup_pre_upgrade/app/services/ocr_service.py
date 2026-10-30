"""OCR Service for extracting text and data from documents."""
import re
from datetime import datetime


def extract_text_from_file(filepath):
    """Extract text from a PDF or image file.
    Returns extracted text or empty string if OCR is unavailable.
    """
    text = ''
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''

    try:
        if ext == 'pdf':
            text = _extract_from_pdf(filepath)
        elif ext in ('jpg', 'jpeg', 'png'):
            text = _extract_from_image(filepath)
    except Exception as e:
        print(f"OCR extraction error: {e}")

    return text


def _extract_from_pdf(filepath):
    """Extract text from PDF using PyMuPDF, fall back to OCR."""
    text = ''
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        for page in doc:
            page_text = page.get_text()
            if page_text.strip():
                text += page_text + '\n'
        doc.close()
    except ImportError:
        pass
    except Exception as e:
        print(f"PyMuPDF error: {e}")

    # If no text extracted (scanned PDF), try OCR on images
    if not text.strip():
        try:
            import fitz
            doc = fitz.open(filepath)
            for page_num in range(min(len(doc), 3)):  # First 3 pages
                page = doc[page_num]
                pix = page.get_pixmap(dpi=200)
                img_data = pix.tobytes("png")

                import io
                from PIL import Image
                img = Image.open(io.BytesIO(img_data))
                page_text = _ocr_image(img)
                if page_text:
                    text += page_text + '\n'
            doc.close()
        except ImportError:
            pass
        except Exception as e:
            print(f"PDF OCR fallback error: {e}")

    return text


def _extract_from_image(filepath):
    """Extract text from an image file using OCR."""
    try:
        from PIL import Image
        img = Image.open(filepath)
        return _ocr_image(img)
    except Exception as e:
        print(f"Image extraction error: {e}")
        return ''


def _ocr_image(pil_image):
    """Run OCR on a PIL Image, with optional OpenCV preprocessing."""
    try:
        import pytesseract
        import numpy as np
        from config import Config

        # Set tesseract path
        pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

        # Try preprocessing with OpenCV
        try:
            import cv2
            img_array = np.array(pil_image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            # Denoise
            gray = cv2.medianBlur(gray, 3)
            # Threshold
            gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 11, 2)
            from PIL import Image
            pil_image = Image.fromarray(gray)
        except ImportError:
            pass  # OpenCV not available, use raw image

        text = pytesseract.image_to_string(pil_image)
        return text
    except ImportError:
        print("Tesseract not available")
        return ''
    except Exception as e:
        print(f"OCR error: {e}")
        return ''


def extract_document_info(text):
    """Parse extracted text to find document number, issue date, and expiry date candidates."""
    info = {
        'document_numbers': [],
        'issue_dates': [],
        'expiry_dates': [],
        'raw_text': text,
    }

    if not text:
        return info

    # Date patterns (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD MMM YYYY, etc.)
    date_patterns = [
        r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b',
        r'\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b',
        r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b',
    ]

    # Expiry keywords
    expiry_keywords = [
        r'expir[yation]\s*(?:date)?',
        r'valid\s*(?:until|upto|till|thru|through)',
        r'date\s*of\s*expir[yation]',
        r'exp(?:iry)?\s*date',
        r'expires?\s*(?:on)?',
        r'best\s*before',
        r'validity',
    ]

    # Issue keywords
    issue_keywords = [
        r'issue\s*date',
        r'date\s*of\s*issue',
        r'issued?\s*(?:on)?',
        r'start\s*date',
        r'date\s*of\s*commencement',
        r'effective\s*(?:date|from)',
    ]

    lines = text.split('\n')
    for line in lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue

        # Find dates in this line
        found_dates = _find_dates_in_line(line, date_patterns)

        # Check if line contains expiry keywords
        is_expiry_line = any(re.search(kw, line_lower) for kw in expiry_keywords)
        is_issue_line = any(re.search(kw, line_lower) for kw in issue_keywords)

        for d in found_dates:
            if is_expiry_line:
                info['expiry_dates'].append(d)
            elif is_issue_line:
                info['issue_dates'].append(d)

        # Look for document numbers (alphanumeric patterns)
        doc_num_patterns = [
            r'(?:no|number|#|id|ref)[\s.:]*([A-Z0-9][A-Z0-9\-/]{3,20})',
            r'\b([A-Z]{2,5}\d{5,15})\b',  # e.g., DL0520190001234
        ]
        for pattern in doc_num_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for m in matches:
                if len(m) >= 4 and not m.replace('/', '').replace('-', '').replace('.', '').isspace():
                    info['document_numbers'].append(m.strip())

    # Deduplicate
    info['document_numbers'] = list(dict.fromkeys(info['document_numbers']))[:5]
    info['issue_dates'] = list(dict.fromkeys(info['issue_dates']))[:5]
    info['expiry_dates'] = list(dict.fromkeys(info['expiry_dates']))[:5]

    return info


def _find_dates_in_line(line, patterns):
    """Find and parse dates from a line of text."""
    dates = []
    months_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    # DD/MM/YYYY or DD-MM-YYYY
    for m in re.finditer(patterns[0], line):
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= d <= 31 and 1 <= mo <= 12 and 1900 <= y <= 2100:
                dt = datetime(y, mo, d).date()
                dates.append(dt.strftime('%Y-%m-%d'))
            elif 1 <= mo <= 31 and 1 <= d <= 12 and 1900 <= y <= 2100:
                dt = datetime(y, d, mo).date()
                dates.append(dt.strftime('%Y-%m-%d'))
        except (ValueError, OverflowError):
            pass

    # YYYY-MM-DD
    for m in re.finditer(patterns[1], line):
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1900 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                dt = datetime(y, mo, d).date()
                dates.append(dt.strftime('%Y-%m-%d'))
        except (ValueError, OverflowError):
            pass

    # DD MMM YYYY
    for m in re.finditer(patterns[2], line, re.IGNORECASE):
        try:
            d = int(m.group(1))
            mo = months_map.get(m.group(2).lower()[:3])
            y = int(m.group(3))
            if mo and 1 <= d <= 31 and 1900 <= y <= 2100:
                dt = datetime(y, mo, d).date()
                dates.append(dt.strftime('%Y-%m-%d'))
        except (ValueError, OverflowError):
            pass

    return dates
