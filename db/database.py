# db/database.py
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "tba_workstation.db")

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def connect(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    # ================= 收货表操作 =================
    def add_receive(self, entryDate, customerId, packageNo, packageQty, remark=""):
        """新增收货记录"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO receive_data (entryDate, customerId, packageNo, packageQty, remark, synced)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (entryDate, customerId, packageNo, packageQty, remark),
            )
            conn.commit()

    def get_all_receive(self):
        """获取所有收货记录"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM receive_data ORDER BY createdAt DESC")
            return cursor.fetchall()

    def mark_receive_synced(self, record_id):
        """标记收货数据已同步"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE receive_data SET synced = 1 WHERE id = ?", (record_id,))
            conn.commit()

    # ================= 出货表操作 =================
    def add_ship(self, barcode, cartons, qty, weight, spec="", remark=""):
        """新增出货记录"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ship_data (barcode, cartons, qty, weight, spec, remark, synced)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (barcode, cartons, qty, weight, spec, remark),
            )
            conn.commit()

    def get_all_ship(self):
        """获取所有出货记录"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ship_data ORDER BY createdAt DESC")
            return cursor.fetchall()

    def mark_ship_synced(self, record_id):
        """标记出货数据已同步"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE ship_data SET synced = 1 WHERE id = ?", (record_id,))
            conn.commit()

    def mark_ship_processed(self, record_id: int):
        """
        把 ship_data 表里的 processed 字段置为 1
        """
        """标记出货申请已处理完成"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ship_data SET processed = 1 WHERE id = ?",
                (record_id,)
            )
            conn.commit()