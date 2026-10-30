# Smart Document Expiry & Renewal Manager with Loan, EMI & Financial Management System

A full-stack web application designed for diploma-level Computer Engineering projects. The application tracks personal documents (Aadhaar, PAN, Driving Licence, Insurance, Vehicle RC/PUC, Passports), manages loan repayments, calculates reducing-balance EMIs, generates amortization schedules, captures photos using browser camera APIs, and runs OCR for automatic date detection.

---

## 🌟 Key Features

1. **Document Management & Expiry Tracking**:
   - Manage Aadhaar, PAN, Driving Licence, Vehicle Insurance, Health Insurance, Vehicle RC, PUC, Education certificates, and custom documents.
   - Dynamic validity status calculation: `Valid`, `Expiring Soon` (within 30 days), `Expiring Today`, `Expired`, `Renewed`, and `No Expiry` (Lifetime).
   - In-app reminder notifications at 30 days, 14 days, 7 days, and 1 day before expiry.

2. **Camera-Based Document Scanner with Multi-Device Support & OCR**:
   - **HTML5 MediaDevices API** with progressive multi-tier fallback (ideal rear camera `facingMode: { ideal: "environment" }`, falling back to `{ video: true }` for laptops).
   - **Mobile Direct Camera Integration**: Built-in `<input type="file" accept="image/*" capture="environment">` button ("Open Phone Camera") that triggers the phone's native camera immediately, even when accessing over plain LAN HTTP without HTTPS restrictions!
   - **Front / Rear Camera Switch**: Real-time switching between available devices on mobile and laptops.
   - **Lifecycle Management**: Stream stops cleanly on capture, user stop button click, or navigating away from the page.
   - **Detailed Diagnostic Alerts**: Informative in-page alerts for permission denied (`NotAllowedError`), camera in use (`NotReadableError`), hardware not found (`NotFoundError`), or insecure context (`SecurityError`).
   - **Interactive Canvas Controls**: 90° rotation, brightness slider (50%–200%), contrast slider (50%–200%), retake photo, and "Use Photo & Run OCR" buttons.
   - **OCR Extraction**: Tesseract OCR engine integration with English and Marathi language support, regex matching for identity numbers, holder names, issuing authorities, and expiry dates.

3. **Document Renewal Management**:
   - Track renewal applications: `Not Started`, `Applied`, `In Progress`, `Completed`, `Rejected`.
   - Update document expiry dates upon renewal completion while preserving past renewal audit history.

4. **Loan & EMI Management**:
   - Supports Personal, Home, Education, Vehicle, and Business loans with unique generated Loan IDs (`LN-YYYYMM-XXXX`).
   - Reducing-balance monthly EMI calculation using the standard financial formula:
     $$\text{EMI} = \frac{P \times R \times (1 + R)^N}{(1 + R)^N - 1}$$
   - Dedicated zero-interest loan calculation mode ($P / N$).
   - Full monthly amortization schedule generation with principal and interest breakdowns.
   - Track loan repayment progress percentages and estimated outstanding balances.

5. **Loan & EMI Payment Recording & Receipts**:
   - Dedicated "Pay EMI" workflow supporting full and partial payments.
   - Multiple partial payments combine safely to update remaining dues.
   - Overpayment protection.
   - Automatic generation of internal payment records with unique receipt numbers (`RCT-YYYYMM-XXXXX`).
   - Downloadable, print-ready PDF payment receipts with mandatory disclaimer:
     > **"APPLICATION-GENERATED PAYMENT RECORD — NOT A BANK-ISSUED RECEIPT"**

6. **Vibrant Modern UI Redesign (Strictly ZERO Green Theme)**:
   - Designed around a vibrant, accessible color palette without any green UI elements:
     - **Royal Purple (`#6C3BFF`)**: Primary brand identity, active states, key buttons
     - **Electric Blue (`#2878FF`)**: Action accents, financial totals, secondary charts
     - **Vibrant Pink (`#F044A7`)**: Primary action triggers, scanner guides, payment buttons
     - **Coral (`#FF6B6B`)**: Overdue alerts, delete actions, expired indicators
     - **Orange (`#FF9F43`)**: Expiring soon notices, interest indicators
     - **Yellow (`#FFD166`)**: Due today notices, pending indicators
     - **Cyan (`#22C7D6`)**: Valid status badges, OCR active badges
     - **Light Lavender (`#F5F3FF`)**: Soft, clean background canvas
     - **Dark Navy (`#20243A`)**: Readable, high-contrast typography
   - Bootstrap default green classes (`.btn-success`, `.text-success`, `.border-success`, `.bg-success`) are defensively overridden and eliminated across all HTML templates, CSS, and Chart.js scripts.

7. **Reports & Exports**:
   - Downloadable PDF reports: Loans Summary Report, Individual Loan Schedule PDF, Payment Receipts.
   - CSV data exports: Documents List, Loans Ledger, Payment History.
   - Global search across documents, reference numbers, loan names, and transaction IDs.

8. **Security & User Data Isolation**:
   - Werkzeug PBKDF2:SHA256 password hashing.
   - Flask-Login session management and Flask-WTF CSRF protection.
   - Strict server-side authorization: users can only view and modify their own records.
   - Complete audit logging of financial payments, corrections, cancellations, and renewals.

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Bootstrap Icons, Chart.js
- **Backend**: Python 3.9+, Flask 3.0+
- **Database**: SQLite (built-in, zero configuration) with SQLAlchemy ORM
- **OCR Engine**: Tesseract OCR via `pytesseract` with PIL (`Pillow`) and OpenCV preprocessing
- **PDF Engine**: ReportLab (for PDF reports and receipts) & PyPDF (for digital PDF text extraction)
- **Architecture**: Clean, modular structure without WAMP, Apache, or MySQL server requirements

---

## 📁 Project Structure

```
Document1/
├── app.py                     # Main Flask application and API routes
├── config.py                  # App configuration, security keys, and upload paths
├── models.py                  # SQLAlchemy ORM models (User, Document, Loan, EMI, etc.)
├── generate_cert.py           # Self-signed SSL certificate generator for LAN HTTPS
├── run_https.py               # Secure HTTPS dev runner for mobile Wi-Fi camera streaming
├── requirements.txt           # Python package dependencies
├── README.md                  # Complete documentation and user guide
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── seed_data.py               # Demo database seeder script (demo / demo123)
│
├── instance/
│   └── app.db                 # SQLite database file
│
├── uploads/
│   ├── documents/             # Uploaded and scanned user documents
│   └── receipts/              # Uploaded payment proof receipts
│
├── services/
│   ├── ocr_service.py         # Image preprocessing, OCR execution & pattern extraction
│   ├── document_service.py    # File validation, MIME checks, secure saving & deletion
│   ├── emi_service.py         # Reducing-balance EMI formula, schedules & transactions
│   ├── notification_service.py# In-app expiry reminders and duplicate suppression
│   └── report_service.py      # ReportLab PDF receipts, summary reports & CSV exports
│
├── templates/
│   ├── base.html              # Sidebar, topbar, global search, and layout shell
│   ├── login.html             # User login form
│   ├── register.html          # User registration form
│   ├── dashboard.html         # Live statistics, charts, and upcoming alerts
│   ├── documents.html         # Document catalog with filters, search, and sorting
│   ├── add_document.html      # Standard document upload form
│   ├── document_details.html  # Document metadata, inline preview, and renewal log
│   ├── scan_document.html     # Camera viewport, canvas adjustments & OCR review
│   ├── renewals.html          # Document renewal tracking and history
│   ├── loans.html             # Loans overview and registration form
│   ├── loan_details.html      # Repayment progress, schedule, and payment records
│   ├── emi_calculator.html    # Interactive loan EMI calculator with chart
│   ├── emi_schedule.html      # Complete monthly installment schedule
│   ├── loan_payments.html     # General loan payment recording form and ledger
│   ├── emi_payments.html      # Installment-wise payment page with partial payment support
│   ├── payment_history.html   # Payment ledger, receipt view modal, and cancellation
│   ├── reports.html           # Download center for PDF and CSV reports
│   ├── notifications.html     # In-app notification center
│   ├── settings.html          # Reminder days configuration and OCR diagnostic
│   ├── search.html            # Global search results page
│   └── errors/
│       ├── 404.html           # Page not found error page
│       └── 500.html           # Server error page
│
├── static/
│   ├── css/
│   │   └── style.css          # Vibrant custom styles, ZERO GREEN theme, badges, scanner UI
│   ├── js/
│   │   ├── main.js            # Sidebar toggle, auto-dismiss alerts, confirmation dialogs
│   │   ├── scanner.js         # MediaDevices camera capture, native mobile camera, canvas filters, OCR AJAX
│   │   └── charts.js          # Chart.js dashboard and EMI calculator visualizations (purple/cyan/pink)
│   └── images/
│       └── logo.png           # Brand logo
│
└── tests/
    ├── test_auth.py           # Authentication, registration, and session tests
    ├── test_documents.py      # Document validation, expiry status, and renewal tests
    ├── test_ocr.py            # OCR parsing, regex matching, and date normalization tests
    ├── test_loans.py          # Loan creation, balances, and data isolation tests
    ├── test_emi.py            # EMI formula, zero-interest, and schedule generation tests
    └── test_payments.py       # Full/partial payments, cancellation, and receipt tests
```

---

## 🚀 Running the Application

### Option A: Standard HTTP (Laptop & Localhost)
```powershell
python app.py
```
Open in browser:
👉 **[http://localhost:5000](http://localhost:5000)**

### Option B: Secure HTTPS (Recommended for Mobile Device Camera over Local Wi-Fi)
Modern mobile browsers (Chrome on Android, Safari on iOS) restrict live camera video streaming over raw HTTP LAN addresses. Running in HTTPS mode enables full live webcam streaming from your mobile device:
```powershell
python run_https.py
```
*or:*
```powershell
python app.py --https
```
The server will automatically generate a development SSL certificate and display your LAN address:
👉 **`https://<YOUR-IP>:5000`** (e.g. `https://10.63.158.208:5000`)
*(When opening on your phone for the first time, tap "Advanced" -> "Proceed to site" to accept the dev certificate).*

---

## 🔑 Demo Login Credentials

For testing and examination presentations:
- **Username:** `demo`
- **Password:** `demo123`

---

## 📷 Camera Scanner Options

1. **Live Camera Stream (Webcam / Laptop / Mobile HTTPS)**:
   - Click **Start Camera** to open the live viewfinder.
   - Use **Switch Camera** to toggle between front and rear cameras on mobile.
   - Click **Capture Photo**, adjust brightness and contrast if needed, and click **Use Photo & Run OCR**.
   - Click **Stop Camera** at any time to release the camera hardware.

2. **Direct Phone Camera (Works 100% on HTTP LAN without HTTPS)**:
   - Click **Open Phone Camera** to trigger your smartphone's native camera app directly.
   - Take the document photo; it loads instantly into the canvas for rotation, brightness adjustment, and OCR!

3. **Image / PDF File Upload**:
   - Use the **Upload Image File** option to select existing photos or scans from your hard drive.

---

## 🧪 Running Automated Tests

Run the complete 19-test automated test suite:
```powershell
python -m unittest discover tests
```
All 19 tests pass (`OK`).
#   s m a r t - d o c u m e n t - r e n e w a l - m a n a g e r  
 