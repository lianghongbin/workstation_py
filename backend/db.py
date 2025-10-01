import sqlite3
import os

DB_PATH = "db/receive.db"

def init_db():
    os.makedirs("db", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receive_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entryDate TEXT NOT NULL,
            customerId TEXT NOT NULL,
            packageNo TEXT NOT NULL UNIQUE,
            packageQty INTEGER NOT NULL,
            remark TEXT,
            synced INTEGER DEFAULT 0,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_receive_data(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO receive_data (entryDate, customerId, packageNo, packageQty, remark)
        VALUES (?, ?, ?, ?, ?)
    """, (data["entryDate"], data["customerId"], data["packageNo"], data["packageQty"], data.get("remark", "")))
    conn.commit()
    conn.close()

def get_receive_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receive_data ORDER BY createdAt DESC")
    rows = cursor.fetchall()
    conn.close()

    # 转换成 JSON 格式
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "entryDate": row[1],
            "customerId": row[2],
            "packageNo": row[3],
            "packageQty": row[4],
            "remark": row[5],
            "synced": row[6],
            "createdAt": row[7],
        })
    return result