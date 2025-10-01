import webview
from flask import Flask, render_template
from backend import main, receiver, ship, ship_query, ship_processed

app = Flask(__name__, template_folder="web", static_folder="web/static")

# 注册蓝图（模块化管理路由）
app.register_blueprint(main.bp)
app.register_blueprint(receiver.bp)
app.register_blueprint(ship.bp)

app.register_blueprint(ship_query.bp)

app.register_blueprint(ship_processed.bp)


if __name__ == '__main__':
    window = webview.create_window("TBA Workstation", app)
    webview.start(debug=False)