from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

class User(UserMixin):
    def __init__(self, id_, username, email):
        self.id = id_
        self.username = username
        self.email = email

    @staticmethod
    def get(user_id):
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT * FROM users WHERE id = %s", (user_id,)
            )
            user = cur.fetchone()
            if not user:
                return None
            return User(id_=user[0], username=user[1], email=user[2])
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def create(username, email, password):
        conn = get_db()
        cur = conn.cursor()
        try:
            hashed_password = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                (username, email, hashed_password),
            )
            conn.commit()
            return cur.fetchone()[0]
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()