QuantumReady
Post-Quantum Migration Decision Support System
מערכת תומכת החלטה לתיעדוף המעבר להצפנה פוסט קוונטית


PROJECT PURPOSE
QuantumReady is a Flask-based decision-support prototype for mapping
cryptographic assets, assessing quantum-related risk and prioritizing
migration toward post-quantum cryptography.
מטרת הפרויקט
QuantumReady היא מערכת אב טיפוס מבוססת Flask למיפוי נכסי הצפנה,
הערכת סיכון קוונטי ותיעדוף המעבר להצפנה פוסט קוונטית.

The prototype uses synthetic demonstration data only.
It stores cryptographic metadata and does not store private keys,
passwords or customer content.
האב טיפוס משתמש בנתוני דמה בלבד.
המערכת שומרת Metadata קריפטוגרפי בלבד ואינה שומרת מפתחות פרטיים,
סיסמאות או תוכן של לקוחות.


WINDOWS - RUN INSTRUCTIONS
הוראות הפעלה ב Windows

1. Open PowerShell
פתח PowerShell.

2. Go to the project folder:
cd Desktop\QuantumReady
עבור לתיקיית הפרויקט.

3. Activate the virtual environment:
.\.venv\Scripts\Activate.ps1
הפעל את סביבת ה Python הווירטואלית של הפרויקט.

4. Install dependencies if needed:
python -m pip install -r requirements.txt
התקן את הספריות הנדרשות במידת הצורך.

5. Prepare the database if needed:
python prepare_inventory.py
צור או בנה מחדש את מסד הנתונים מתוך קבצי המקור.

6. Calculate Risk Scores:
python risk_engine.py
חשב את Risk Score, רמת הדחיפות וההמלצות.

7. Start the Flask application:
python run.py
הפעל את אפליקציית Flask.

8. Open:
http://127.0.0.1:5000
פתח את הכתובת בדפדפן.


UBUNTU - RUN INSTRUCTIONS
הוראות הפעלה ב Ubuntu

Important:
Do not copy the Windows .venv folder to Ubuntu.
Create a new virtual environment on the Ubuntu server.
חשוב:
אין להעתיק את תיקיית .venv של Windows ל Ubuntu.
יש ליצור סביבת Python חדשה בשרת Ubuntu.

1. Go to the project folder:
cd QuantumReady
עבור לתיקיית הפרויקט.

2. Create a new virtual environment:
python3 -m venv .venv
צור סביבת Python חדשה לשרת Ubuntu.

3. Activate it:
source .venv/bin/activate
הפעל את סביבת ה Python.

4. Install dependencies:
python3 -m pip install -r requirements.txt
התקן את הספריות הנדרשות.

5. Prepare the database:
python3 prepare_inventory.py
צור את מסד הנתונים מתוך קבצי המקור.

6. Calculate Risk Scores:
python3 risk_engine.py
חשב את ציוני הסיכון, רמת הדחיפות וההמלצות.

7. Start the application:
python3 run.py
הפעל את אפליקציית Flask.

8. Open:
http://127.0.0.1:5000
פתח את הכתובת בדפדפן.


MAIN APPLICATION PAGES
עמודי המערכת המרכזיים

/               Home
דף הבית

/dashboard      Dashboard
לוח המחוונים המרכזי

/assets         Cryptographic Assets
רשימת נכסי ההצפנה

/alerts         Alerts
התראות וסיכונים דחופים

/import         Import Data
ייבוא שלושת מקורות המידע

/add-asset      Add Asset
הוספת נכס ידנית

/sources        Data Sources
הסבר על מקורות המידע

/user/<name>    Dynamic Jinja Route Demo
הדגמה ל Dynamic Route ו Jinja


FILE ENCODING
קידוד הקובץ

Save this README file using UTF-8 encoding to ensure that the Hebrew
text is displayed correctly on both Windows and Ubuntu.
יש לשמור את קובץ ה README בקידוד UTF-8 כדי שהעברית תוצג בצורה תקינה
גם ב Windows וגם ב Ubuntu.