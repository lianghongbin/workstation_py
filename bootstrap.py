import os
import platform

from flask import Flask, json
from backend import main, receiver, ship, ship_query, ship_processed, abnormal, sorting
from backend.monitor import start_all_monitors


CONFIG_FILE = "config.json"
system_name = platform.system().lower()  # windows / linux / darwin

WATCH_ROOT = "C:\\ECData"  # 默认
if os.path.exists(CONFIG_FILE):
    cfg = json.load(open(CONFIG_FILE, "r", encoding="utf-8"))
    for key, path in cfg.items():
        if key in system_name:
            WATCH_ROOT = path
            break

WATCH_ROOT = os.path.normpath(WATCH_ROOT)

def create_app():
    # 配置 web 目录作为模板目录和静态资源目录
    app = Flask(__name__, template_folder="web", static_folder="web/static")

    # 注册蓝图
    app.register_blueprint(main.bp)
    app.register_blueprint(receiver.bp)
    app.register_blueprint(ship.bp)
    app.register_blueprint(ship_query.bp)
    app.register_blueprint(ship_processed.bp)
    app.register_blueprint(abnormal.bp)
    app.register_blueprint(sorting.bp)

    return app


if __name__ == '__main__':
    app = create_app()

    # ✅ 仅在实际运行进程中启动后台任务，避免 Flask Debug 模式下双启动
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_all_monitors(WATCH_ROOT, 10)
    # 启动 Web 服务，默认首页走 main 蓝图 -> main.html
    app.run(host="0.0.0.0", port=80, debug=True)