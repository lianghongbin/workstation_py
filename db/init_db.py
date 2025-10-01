# db/init_db.py
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "tba_workstation.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ 收货表
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

    # ✅ 出货表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ship_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,         -- 产品条码
            processed INTEGER DEFAULT 0,   -- 出货申请处理完成
            cartons INTEGER NOT NULL,      -- 箱数
            qty INTEGER NOT NULL,          -- QTY 数量a
            weight REAL NOT NULL,          -- 重量
            spec TEXT,                     -- 箱规
            remark TEXT,                   -- 备注
            synced INTEGER DEFAULT 0,      -- 是否已同步到 Vika
            processed INTEGER DEFAULT 0,   -- 是否已经处理
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] 数据库初始化完成 -> {DB_PATH}")

if __name__ == "__main__":
    init_db()