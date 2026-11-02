# Setup Guide: Smart Document Manager (Modern Modular Version)

## System Requirements

- **Python 3.12** (recommended) or Python 3.10+
- **Git** (for version control)
- **PostgreSQL** (optional, defaults to SQLite)
- **Tesseract OCR** (for document scanning)
- **Aadhaar/Sarkar Portal access** for government services integration

## Installation Steps

### Step 1: Clone / Locate the Project

Windows:
```cmd
cd "C:\Users\sarth\OneDrive\Desktop\document1"
```

Linux/Mac:
```bash
cd /path/to/document1
```

### Step 2: Set Up Python Environment

**Option A: Use System Python (Recommended if venv fails):**
```bash
# Check if pip is available
pip --version
```

**Option B: Create Virtual Environment:**
```bash
# Create venv
python -m venv .venv

# Activate venv
# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate

# If pip is missing in venv, install it:
python -m ensurepip --upgrade
```

### Step 3: Install Dependencies

Using system pip:
```bash
pip install --user Flask Flask-SQLAlchemy Flask-Login Flask-WTF WTForms
pip install --user Werkzeug python-dotenv Pillow pytesseract
pip install --user opencv-python-headless pypdf reportlab psycopg2-binary python-dateutil
```

Or use `pip3` if available:
```bash
pip3 install --user Flask Flask-SQLAlchemy Flask-Login Flask-WTF WTForms
pip3 install --user Werkzeug python-dotenv Pillow pytesseract
pip3 install --user opencv-python-headless pypdf reportlab psycopg2-binary python-dateutil
```

### Step 4: Configure Environment Variables

Create `.env` file in the project root:

```env
# Flask Configuration
SECRET_KEY=your-very-secret-key-here-change-me
FLASK_DEBUG=1
PORT=5000

# Database (optional - defaults to SQLite)
# DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/smartdoc_db

# Tesseract OCR (Windows path may vary - optional for OCR features)
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Step 5: Set Up the Database

For **SQLite** (development default):

```bash
# Database file will be created at instance/app.db
python -c "from app import create_app; from app.models import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database created!')"
```

For **PostgreSQL** (if installed):

```bash
# Create database and user
createdb smartdoc_db
psql -d smartdoc_db -c "CREATE USER smartdoc_user WITH PASSWORD 'your_password';"
psql -d smartdoc_db -c "GRANT ALL PRIVILEGES ON DATABASE smartdoc_db TO smartdoc_user;"
```

### Step 6: Seed Government Certificate Types

```bash
python services/government_seed.py
```

This seeds the database with 8 government certificate types and their required documents.

This will create all government certificates with their required documents:
- Domicile Certificate
- Income Certificate
- Caste Certificate
- Non-Creamy Layer Certificate
- Marriage Certificate
- Birth Certificate
- Death Certificate
- Property Documents

### Step 7: Create Admin User (Optional)

```bash
# Run the seeder for demo user
python seed_data.py
# Or register manually at /register
```

### Step 8: Run the Application

Development mode:

```bash
python run_modern.py
# or
python -c "from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000, debug=True)"
```

Open http://localhost:5000 in your browser.

---

## Project Structure

```
document1/
├── app/
│   ├── __init__.py          # Application factory (creates all blueprints)
│   ├── models.py            # SQLAlchemy models (all tables)
│   ├── forms.py             # Flask-WTF forms
│   ├── auth/                # Authentication blueprint
│   │   ├── routes.py
│   │   └── __init__.py
│   ├── dashboard/           # Dashboard blueprint
│   ├── documents/           # Documents blueprint
│   ├── loans/               # Loans blueprint
│   ├── emi/                 # EMI blueprint
│   ├── payments/            # Payments blueprint
│   ├── notifications/       # Notifications blueprint
│   ├── renewals/            # Renewals blueprint
│   ├── reminders/           # Reminders blueprint
│   ├── search/              # Search blueprint
│   ├── settings/            # Settings blueprint
│   ├── government/          # Government Documents module
│   │   ├── routes.py
│   │   ├── models.py
│   │   ├── forms.py
│   │   └── __init__.py
│   ├── reports/             # Reports blueprint
│   ├── utils/
│   │   └── helpers.py
│   └── services/
│       ├── document_service.py
│       ├── emi_service.py
│       ├── notification_service.py
│       ├── ocr_service.py
│       └── report_service.py
├── templates/
│   ├── base_modern.html     # Modern cinematic base template
│   ├── dashboard/
│   ├── documents/
│   ├── government/
│   ├── auth/
│   ├── settings/
│   └── ...
├── static/
│   ├── css/style.css        # Modern styling with animations
│   ├── js/main.js
│   └── images/
├── instance/
│   └── app.db               # SQLite database (if using)
├── services/
│   └── government_seed.py   # Seed government certificates
├── config.py
├── run_modern.py
├── requirements.txt
└── SETUP_GUIDE.md           # This file
```

## Available Routes (Blueprint Structure)

| Blueprint | URL Prefix | Endpoints |
|-----------|-----------|-----------|
| auth | / | register, login, logout, profile, change-password |
| dashboard | / | index (/) |
| documents | /documents | list, add, detail, edit, delete, download, preview |
| loans | /loans | list, add, detail, edit, delete, close |
| emi | /emi | list, calculator, edit, pay |
| payments | /payments | history, record, cancel, receipt |
| notifications | /notifications | index, read, mark-all, delete |
| renewals | /renewals | history, renew |
| search | /search | search, ajax |
| settings | /settings | settings, profile, security, notifications |
| government | /government | services, apply, view, edit, submit, cancel, upload-doc, status |
| reports | /reports | index, loans/pdf, documents/csv, loans/csv, payments/csv |

## Government Documents Usage Flow

1. **Browse Certificates**: Go to `/government/` to see available certificates
2. **Apply for Certificate**: Click "Apply Now" on a certificate card
3. **Fill Application**: Enter applicant name, district, dates, and reference number
4. **Upload Documents**: Use the document upload form for each required document
5. **Track Status**: View application at `/government/<id>`
6. **Print Acknowledgement**: Download PDF for your records

## Modern UI Features

- **Cinematic Transitions**: Fade-in animations for all elements
- **Gradient Borders**: Purple-to-blue accent colors
- **Interactive Cards**: Hover effects with shadow elevation
- **Step Indicators**: Multi-step form progress indicators
- **Responsive Design**: Mobile-friendly sidebar toggle
- **Status Badges**: Color-coded status indicators (NO GREEN - uses CYAN/PROGEN/INFO)

## Troubleshooting

### "module not found" errors
```bash
pip install -r requirements.txt
```

### Database errors
```bash
# Remove and recreate database
rm instance/app.db
python -c "from app import create_app; from app.models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Tesseract OCR not found
1. Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
2. Update `TESSERACT_CMD` in `.env`

### "No module named 'dateutil'"
```bash
pip install python-dateutil
```

## Production Deployment (Optional)

For production, use a WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run_modern:app
```

For HTTPS, use a reverse proxy (nginx/Apache) with SSL certificates.