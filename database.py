import os
import psycopg2
from psycopg2 import pool
from werkzeug.security import generate_password_hash
import threading

def get_db():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    conn = get_db()
    cur = conn.cursor()
    try:
        # Create users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """)
        
        # Create documents table with embeddings column
        cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            drive_file_id TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT FALSE,
            embeddings BYTEA,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Add test user if none exists
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            hashed_pw = generate_password_hash('test123')
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                ('testuser', 'test@example.com', hashed_pw)
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_user_documents(user_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, filename, upload_date FROM documents WHERE user_id = %s ORDER BY upload_date DESC",
            (user_id,)
        )
        columns = [desc[0] for desc in cur.description]
        # Convert each row to a dictionary
        results = []
        for row in cur.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    finally:
        cur.close()
        conn.close()

def add_document(user_id, filename, filepath, drive_file_id=None):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO documents (user_id, filename, filepath, drive_file_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, filename, filepath, drive_file_id)
        )
        doc_id = cur.fetchone()[0]
        conn.commit()
        return doc_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_document_path(user_id, doc_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT filepath FROM documents WHERE id = %s AND user_id = %s",
            (doc_id, user_id)
        )
        doc = cur.fetchone()
        return doc[0] if doc else None
    finally:
        cur.close()
        conn.close()

def get_drive_file_id(user_id, doc_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT drive_file_id FROM documents WHERE id = %s AND user_id = %s",
            (doc_id, user_id)
        )
        doc = cur.fetchone()
        return doc[0] if doc else None
    finally:
        cur.close()
        conn.close()

def delete_document(user_id, doc_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT filepath FROM documents WHERE id = %s AND user_id = %s",
            (doc_id, user_id)
        )
        doc = cur.fetchone()
        
        if not doc:
            return None
            
        cur.execute(
            "DELETE FROM documents WHERE id = %s AND user_id = %s",
            (doc_id, user_id)
        )
        conn.commit()
        return doc[0]
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def update_document_with_drive_id(doc_id, drive_file_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE documents SET drive_file_id = %s WHERE id = %s",
            (drive_file_id, doc_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def save_embeddings(user_id, doc_id, chunks, embeddings, index):
    """Store all embedding data in PostgreSQL"""
    import pickle
    from io import BytesIO
    
    conn = get_db()
    cur = conn.cursor()
    try:
        combined = pickle.dumps({
            'chunks': chunks,
            'embeddings': embeddings,
            'index': index
        })
        
        cur.execute(
            "UPDATE documents SET embeddings = %s, processed = TRUE WHERE id = %s AND user_id = %s",
            (combined, doc_id, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def load_embeddings(user_id, doc_id):
    """Load embedding data from PostgreSQL"""
    import pickle
    import numpy as np
    import faiss
    
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT embeddings FROM documents WHERE id = %s AND user_id = %s",
            (doc_id, user_id)
        )
        data = cur.fetchone()
        
        if not data or not data[0]:
            return None
            
        return pickle.loads(data[0])
    finally:
        cur.close()
        conn.close()