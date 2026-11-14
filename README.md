# CampusConnect – Smart Campus Lost & Found Portal

**CampusConnect** is a comprehensive, production-style, database-driven web application engineered for university campuses. It enables students, faculty members, and administrative staff to report lost or found belongings, discover matching items through an intelligent multi-attribute similarity engine, submit secure ownership claims, communicate in real time, and coordinate in-person item recovery.

---

## 🌟 Key System Capabilities

1. **Multi-Role Access Control**:
   - **Student / Faculty / Staff**: Report items, search catalog, view AI matches, submit ownership claims, engage in claim-specific messaging, confirm handovers.
   - **Campus Administrator**: Moderate reports (approve/reject with mandatory justification), evaluate private claim evidence, schedule handovers, verify in-person photo IDs, mark items returned, manage campus locations and categories.
   - **Super Administrator**: System-wide control, institutional email domain allowlist management, and user role promotion.

2. **Intelligent Item Matching Engine (scikit-learn)**:
   - Evaluates Lost and Found reports using weighted multi-attribute analysis:
     - **Category Match**: 25%
     - **Name Similarity**: 20% (TF-IDF vectorizer + Cosine similarity)
     - **Color Similarity**: 15% (Primary and secondary color cross-matching)
     - **Brand Compatibility**: 10%
     - **Description Text Similarity**: 10%
     - **Location Proximity**: 10% (Campus building mapping & coordinate calculations)
     - **Date Compatibility**: 10% (Logical lost vs. found timeframe analysis)
   - Dynamic classifications: **Strong Match (≥85%)**, **Possible Match (65–84%)**, **Weak Match (40–64%)**. Below 40% filtered out.
   - Human-readable explanation generation for every match.

3. **Anti-Fraud Ownership Verification & Physical Handover**:
   - **Privacy Protection**: Identifying characteristics (serial numbers, wallet contents, lockscreens) are masked from public cards.
   - **Claim Review**: Claimants provide private answers and proof of ownership attachments (receipts, serial certificates).
   - **In-Person Verification**: Administrator verifies claimant's institutional photo ID in person.
   - **Automated QR Code & PDF Recovery Receipt**: Official receipt generated with ReportLab and unique QR code pointing to an authenticated verification portal.

4. **Real-Time WebSockets & Notifications**:
   - Powered by **Flask-SocketIO** with rooms segregated by user ID and `admin_room`.
   - Toast notifications and bell badge increments delivered live without page refreshes.
   - Graceful polling fallback (`/api/notifications/poll`) ensuring continuous operation across all network environments.

5. **Interactive Campus Mapping**:
   - **Leaflet.js** and OpenStreetMap integration plotting campus buildings, incident counts, and location-based coordinates.

---

## 🛠 Technology Stack

- **Backend**: Python 3.11+, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-SocketIO, Flask-Mail, Werkzeug.
- **Database**: PostgreSQL (production) with SQLite fallback (zero-configuration development).
- **Machine Learning & Cheminformatics**: scikit-learn (TF-IDF vectorization, Cosine similarity).
- **Media & Document Processing**: Pillow (image compression & formatting), qrcode (QR code generation), ReportLab (PDF recovery receipt creation), Pandas (analytics exports).
- **Frontend**: HTML5, CSS3, JavaScript ES6+, Bootstrap 5, Bootstrap Icons, Leaflet.js, Chart.js.

---

## 📂 Project Architecture

```
CLFP/
├── app/
│   ├── __init__.py                 # Application factory & SocketIO events
│   ├── extensions.py               # SQLAlchemy, Migrate, Login, Mail, CSRF, SocketIO
│   ├── models/                     # Database ORM models
│   │   ├── __init__.py
│   │   ├── user.py                 # User, Department
│   │   ├── report.py               # LostReport, FoundReport, CampusLocation, ItemCategory
│   │   ├── match.py                # ItemMatch (computed similarity records)
│   │   ├── claim.py                # Claim (ownership verification workflows)
│   │   ├── handover.py             # Handover (recovery records & QR tokens)
│   │   ├── message.py              # Conversation, Message
│   │   └── notification.py         # Notification, Announcement, AuditLog, SystemSetting
│   ├── routes/                     # Blueprint controllers
│   │   ├── __init__.py
│   │   ├── auth.py                 # Registration, email verify, login, password reset
│   │   ├── main.py                 # Landing page, How It Works, About, Contact
│   │   ├── reports.py              # Catalog discovery, report lost/found forms
│   │   ├── claims.py               # Ownership claims submission & tracking
│   │   ├── messages.py             # Real-time claim messaging
│   │   ├── handovers.py            # Handover confirmation & PDF receipt download
│   │   ├── user.py                 # User dashboard & profile settings
│   │   ├── notifications.py        # Notification management
│   │   ├── admin.py                # Administrator dashboard, approvals, user management
│   │   ├── analytics.py            # Hotspot analytics, CSV & PDF exports
│   │   └── api.py                  # Structured REST API endpoints
│   ├── services/                   # Business logic layer
│   │   ├── __init__.py
│   │   ├── matching_service.py     # Weighted TF-IDF item matching algorithm
│   │   ├── notification_service.py # Database persistence & real-time socket delivery
│   │   ├── email_service.py        # Token generation & mail handler (console fallback)
│   │   ├── image_service.py        # Secure image validation & Pillow compression
│   │   ├── claim_service.py        # Claim state transitions & lifecycle logic
│   │   └── handover_service.py     # Handover scheduling, QR code & PDF receipt generation
│   ├── templates/                  # Jinja2 responsive templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── auth/
│   │   ├── user/
│   │   ├── reports/
│   │   ├── claims/
│   │   ├── messages/
│   │   ├── handover/
│   │   └── admin/
│   └── static/
│       ├── css/style.css
│       ├── js/ (main.js, socket.js, map.js)
│       └── uploads/ (reports, evidence, qrcodes)
├── tests/                          # Automated pytest suite
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_reports.py
│   ├── test_matching.py
│   ├── test_claims.py
│   └── test_security.py
├── config.py                       # Configuration classes (Dev, Test, Prod)
├── run.py                          # Application entry point
├── seed.py                         # Complete realistic database seeder
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
└── .gitignore
```

---

## 🚀 Local Installation & Execution Guide

### 1. Prerequisites
- Python 3.11 or higher installed on your system.

### 2. Virtual Environment Setup
Open a terminal in the project directory:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate virtual environment (macOS/Linux)
# source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
*(SQLite is used by default if `DATABASE_URL` is omitted. If using PostgreSQL, provide your connection string e.g., `DATABASE_URL=postgresql://postgres:password@localhost:5432/campusconnect_db`)*.

### 4. Seed Database with Realistic Demo Data
Run the seeding script to initialize all tables, 25 users, 12 campus locations, 15 item categories, 30 reports, intelligent matches, sample claims, handovers with QR codes, announcements, and audit logs:
```bash
python seed.py
```

### 5. Start the Application
```bash
python run.py
```
Open your web browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Demonstration Credentials

| Role | Email Address | Password |
|---|---|---|
| **Super Administrator** | `superadmin@campusconnect.edu` | `CampusPass2026!` |
| **Campus Administrator 1** | `admin1@campusconnect.edu` | `CampusPass2026!` |
| **Campus Administrator 2** | `admin2@campusconnect.edu` | `CampusPass2026!` |
| **Student (Alex Rivers)** | `alex.rivers@student.campusconnect.edu` | `CampusPass2026!` |
| **Student (David Kim)** | `david.kim@student.campusconnect.edu` | `CampusPass2026!` |
| **Faculty Member (Prof. Lang)** | `robert.lang@faculty.campusconnect.edu` | `CampusPass2026!` |

---

## 🧪 Running Automated Tests

Run the full pytest automated test suite:
```bash
python -m pytest tests -v
```

---

## 🛡 Security Highlights

- **Werkzeug PBKDF2:SHA256 password hashing**.
- **CSRF Protection** on all forms and state-changing actions.
- **Strict Role-Based Access Control (RBAC)** preventing unauthorized route execution and privilege escalation.
- **Anti-IDOR protection** ensuring claimants cannot access other claimants' confidential files.
- **Pillow image processing** generating sanitized UUID filenames and re-encoding uploaded files to prevent malicious uploads.
- **Full Audit Logging** recording every administrative action, review status change, and handover confirmation.
