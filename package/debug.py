from flask_restful import Resource
from package.model import conn


class DebugDB(Resource):
    """Small helper endpoint to verify which MySQL server/database the app is using."""

    def get(self):
        db = conn.execute("SELECT DATABASE() AS db").fetchone()
        who = conn.execute("SELECT USER() AS user, CURRENT_USER() AS current_user").fetchone()
        host = conn.execute("SELECT @@hostname AS hostname, @@port AS port").fetchone()
        ver = conn.execute("SELECT VERSION() AS version").fetchone()

        out = {}
        for d in (db, who, host, ver):
            if isinstance(d, dict):
                out.update(d)
        return out
