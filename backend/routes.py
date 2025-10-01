from flask import Flask, render_template, request, jsonify
from backend.db import init_db, save_receive_data, get_receive_data

def create_app():
    app = Flask(__name__, template_folder="../web/templates", static_folder="../web/static")

    # 初始化数据库
    init_db()

    # 首页（加载 ship-query.html）
    @app.route("/")
    def index():
        return render_template("ship-query.html")

    # 保存收货数据
    @app.route("/api/receive", methods=["POST"])
    def receive():
        data = request.json
        save_receive_data(data)
        return jsonify({"status": "ok"})

    # 查询收货数据
    @app.route("/api/receive", methods=["GET"])
    def list_receive():
        return jsonify(get_receive_data())

    return app