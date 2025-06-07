import json
import sqlite3

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
        user_id INTEGER PRIMARY KEY,
        city_name TEXT,
        country TEXT,
        location_photo TEXT,
        latitude TEXT,
        longitude TEXT,
        dest_id TEXT,
        search_type TEXT,
        checkin TEXT,
        checkout TEXT,
        adults TEXT,
        children TEXT,
        room TEXT,
        hotel_descriptions TEXT,
        max_price TEXT,
        photo_urls TEXT,
        locations TEXT,
        hotels_dict TEXT,
        chosen_hotel_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def set_session(user_id, key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if isinstance(value, (dict, list)):
        value = json.dumps(value)

    cursor.execute("SELECT user_id FROM sessions WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        cursor.execute(f"UPDATE sessions SET {key} = ? WHERE user_id = ?", (value, user_id))
    else:
        cursor.execute(f"INSERT INTO sessions (user_id, {key}) VALUES (?, ?)", (user_id, value))
    conn.commit()
    conn.close()

def get_session(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    keys = [description[0] for description in cursor.description]
    conn.close()
    if row:
        data = dict(zip(keys, row))
        for k, v in data.items():
            if isinstance(v, str):
                try:
                    data[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    pass
        return data
    return {}

def clear_session(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()