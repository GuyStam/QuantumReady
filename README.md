# QuantumReady

**Post-Quantum Migration Decision Support System**

מערכת תומכת החלטה למיפוי נכסי הצפנה, להערכת סיכונים ולתיעדוף המעבר להצפנה פוסט קוונטית.

---

## Project Purpose
### מטרת הפרויקט

QuantumReady is a Flask-based academic prototype for mapping cryptographic assets, assessing quantum-related risk and prioritizing migration toward post-quantum cryptography.

QuantumReady היא מערכת אב טיפוס אקדמית מבוססת Flask למיפוי נכסי הצפנה, הערכת סיכון קוונטי ותיעדוף המעבר להצפנה פוסט קוונטית.

The project uses synthetic demonstration data only.  
No private keys, passwords or customer content are stored.

הפרויקט משתמש בנתוני דמה בלבד.  
המערכת אינה שומרת מפתחות פרטיים, סיסמאות או תוכן של לקוחות.

---

## Windows - Run Instructions
### הוראות הפעלה ב Windows

1. Open PowerShell in the project folder.

2. Create a virtual environment:

```powershell
python -m venv .venv
```

3. Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Install the required dependencies:

```powershell
python -m pip install -r requirements.txt
```

5. Prepare the database:

```powershell
python prepare_inventory.py
```

6. Calculate the Risk Scores:

```powershell
python risk_engine.py
```

7. Start the application:

```powershell
python run.py
```

8. Open in the browser:

```text
http://127.0.0.1:5000
```

---

## Ubuntu - Run Instructions
### הוראות הפעלה ב Ubuntu

1. Clone the project from GitHub:

```bash
git clone https://github.com/GuyStam/QuantumReady.git
```

2. Enter the project folder:

```bash
cd QuantumReady
```

3. Create a virtual environment:

```bash
python3 -m venv .venv
```

4. Activate the virtual environment:

```bash
source .venv/bin/activate
```

5. Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

6. Prepare the database:

```bash
python prepare_inventory.py
```

7. Calculate the Risk Scores:

```bash
python risk_engine.py
```

8. Start the application:

```bash
python run.py
```

For server deployment, the host and port can be configured using the `QUANTUMREADY_HOST`, `QUANTUMREADY_PORT` and `QUANTUMREADY_DEBUG` environment variables.

---

## Main Application Pages
### עמודי המערכת המרכזיים

- `/` — Home
- `/dashboard` — Dashboard
- `/assets` — Cryptographic Assets
- `/alerts` — Alerts
- `/add-asset` — Add Asset
- `/edit-asset/<id>` — Edit Asset
- `/import` — Import Data
- `/sources` — Data Sources
- `/user/<name>` — Dynamic Jinja Route Demo
- `/export-report` — Export Risk Report

---

## Project Structure
### מבנה הפרויקט

```text
app/                    Flask application
data/                   Demo data and SQLite database
prepare_inventory.py    Database preparation
risk_engine.py          Risk calculation
run.py                  Application entry point
requirements.txt        Python dependencies
```

---

## Notes
### הערות

- The project uses synthetic demonstration data only.
- The `.venv` folder should not be uploaded to GitHub.
- Debug mode is disabled by default.
- The project is intended as an academic Proof of Concept.

- הפרויקט משתמש בנתוני דמה בלבד.
- אין להעלות את תיקיית `.venv` ל GitHub.
- מצב Debug כבוי כברירת מחדל.
- המערכת פותחה כאב טיפוס אקדמי.