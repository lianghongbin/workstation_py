from flask import Flask
from backend import main, receiver, ship, ship_query, ship_processed

def create_app():
    # 配置 web 目录作为模板目录和静态资源目录
    app = Flask(__name__, template_folder="web", static_folder="web/static")

    # 注册蓝图
    app.register_blueprint(main.bp)
    app.register_blueprint(receiver.bp)
    app.register_blueprint(ship.bp)
    app.register_blueprint(ship_query.bp)
    app.register_blueprint(ship_processed.bp)

    return app


if __name__ == '__main__':
    app = create_app()
    # 启动 Web 服务，默认首页走 main 蓝图 -> main.html
    app.run(host="0.0.0.0", port=80, debug=True)