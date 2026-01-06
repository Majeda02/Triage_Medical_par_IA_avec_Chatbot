# Hospital Management System - MySQL backend
# Updated to use MySQL (localhost) instead of SQLite.
#
# Works with Python 3.x
#
# Configure credentials in config.json:
# {
#   "mysql": {"host":"127.0.0.1","port":3306,"user":"root","password":"","database":"hospital_db"}
# }

import json
import mysql.connector
from mysql.connector import Error
from datetime import date, datetime
from decimal import Decimal

with open('config.json', 'r', encoding='utf-8') as data_file:
    config = json.load(data_file)

mysql_cfg = config.get('mysql', {})


class _CursorWrapper:
    """Wrap a mysql-connector cursor to look a bit like sqlite's cursor."""
    def __init__(self, cur):
        self._cur = cur

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

    def fetchall(self):
        rows = self._cur.fetchall()
        return _sanitize_mysql(rows)

    def fetchone(self):
        row = self._cur.fetchone()
        return _sanitize_mysql(row)

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


def _sanitize_mysql(obj):
    """Make mysql-connector returned values JSON-serializable.

    Flask/Flask-RESTful JSON encoder can't serialize datetime/date/Decimal by default.
    The UI uses jQuery DataTables, so the GET endpoints must always return valid JSON.
    """

    def sanitize_value(v):
        if isinstance(v, (datetime, date)):
            return v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat()
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (bytes, bytearray)):
            try:
                return v.decode("utf-8")
            except Exception:
                return v.hex()
        return v

    if obj is None:
        return None

    # list of rows
    if isinstance(obj, list):
        return [_sanitize_mysql(x) for x in obj]

    # single row dict
    if isinstance(obj, dict):
        return {k: sanitize_value(v) for k, v in obj.items()}

    # tuple row (should not happen with dictionary=True, but handle anyway)
    if isinstance(obj, tuple):
        return tuple(sanitize_value(v) for v in obj)

    return sanitize_value(obj)


class MySQLConn:
    def __init__(self, cfg):
        self.cfg = cfg
        self._cnx = None
        self._connect()
        self._init_schema()

    def _connect(self):
        """Connect to MySQL.

        Important: some local MySQL setups fail if you try to connect to a DB
        that doesn't exist yet. To make the project robust, we first connect
        *without* selecting a database, create it if needed, then reconnect
        selecting the database.
        """

        host = self.cfg.get("host", "127.0.0.1")
        port = int(self.cfg.get("port", 3306))
        user = self.cfg.get("user", "root")
        password = self.cfg.get("password", "")
        db = self.cfg.get("database", "hospital_db")

        # 1) Connect without DB
        base_cnx = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            autocommit=True,
        )

        # 2) Ensure DB exists
        try:
            cur = base_cnx.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}`")
            cur.close()
        finally:
            try:
                base_cnx.close()
            except Exception:
                pass

        # 3) Reconnect selecting DB
        self._cnx = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db,
            autocommit=True,
        )

    def _ensure(self):
        try:
            if self._cnx is None or not self._cnx.is_connected():
                self._connect()
        except Exception:
            self._connect()

    def execute(self, query, params=None):
        """
        Execute SQL and return a cursor wrapper.
        Use %s placeholders (mysql-connector style).
        """
        self._ensure()
        cur = self._cnx.cursor(dictionary=True)
        cur.execute(query, params or ())
        return _CursorWrapper(cur)

    def commit(self):
        # With autocommit=True this is mostly a no-op, but we keep it
        # so the original code structure remains unchanged.
        self._ensure()
        try:
            self._cnx.commit()
        except Exception:
            pass

    def _init_schema(self):
        """Create tables if they don't exist."""
        self._ensure()
        cur = self._cnx.cursor()
        # Ensure database exists (best-effort; may require privileges)
        try:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.cfg.get('database','hospital_db')}`")
        except Exception:
            pass

        # Reconnect to ensure correct DB selected
        try:
            self._cnx.database = self.cfg.get("database", "hospital_db")
        except Exception:
            pass

        cur.execute("""
        CREATE TABLE IF NOT EXISTS patient (
            pat_id INT AUTO_INCREMENT PRIMARY KEY,
            pat_first_name VARCHAR(100) NOT NULL,
            pat_last_name VARCHAR(100) NOT NULL,
            pat_insurance_no VARCHAR(100) NOT NULL,
            pat_ph_no VARCHAR(30) NOT NULL,
            pat_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            pat_address VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS doctor (
            doc_id INT AUTO_INCREMENT PRIMARY KEY,
            doc_first_name VARCHAR(100) NOT NULL,
            doc_last_name VARCHAR(100) NOT NULL,
            doc_ph_no VARCHAR(30) NOT NULL,
            doc_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            doc_address VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS appointment (
            app_id INT AUTO_INCREMENT PRIMARY KEY,
            pat_id INT NOT NULL,
            doc_id INT NOT NULL,
            appointment_date DATE NOT NULL,
            CONSTRAINT fk_appointment_patient
                FOREIGN KEY (pat_id) REFERENCES patient(pat_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_appointment_doctor
                FOREIGN KEY (doc_id) REFERENCES doctor(doc_id)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB;
        """)

        self._cnx.commit()
        cur.close()


# Exported connection object used by the REST resources
conn = MySQLConn(mysql_cfg)
