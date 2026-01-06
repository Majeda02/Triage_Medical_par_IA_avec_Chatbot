# Hospital Management System (Dynamic - MySQL)

This project is a **Flask + REST API + HTML/JS UI** hospital management system (Patients / Doctors / Appointments),
now updated to work with a **MySQL database (localhost)** instead of SQLite.

## 1) Prerequisites
- Python 3.9+ (recommended)
- MySQL Server running on your machine (localhost)

## 2) Create the database (MySQL)
Open MySQL and run:

```sql
CREATE DATABASE IF NOT EXISTS hospital_db;
```

> The app also tries to create the DB/tables automatically, but the manual step above avoids permission issues.

## 3) Configure MySQL connection
Edit `config.json`:

```json
{
  "host": "127.0.0.1",
  "port": 5000,
  "mysql": {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "hospital_db"
  }
}
```

## 4) Install dependencies
```bash
pip install -r requirements.txt
```

## 5) Run the project
```bash
python app.py
```

Then open:
- http://127.0.0.1:5000/

## API Endpoints
- `/patient` and `/patient/<id>`
- `/doctor` and `/doctor/<id>`
- `/appointment` and `/appointment/<id>`
- `/common`

"# Triage_Medical_par_IA_avec_Chatbot" 
