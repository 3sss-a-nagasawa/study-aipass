"""生成AIパスポート模擬試験アプリ（Flask）。この端末だけで使う。"""

from flask import Flask, render_template

from config import Config


def create_app():
    """Flask アプリを生成して返す。"""
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.route("/")
    def index():
        """トップページ（試験開始画面）。"""
        return render_template(
            "index.html",
            question_count=app.config["QUIZ_QUESTION_COUNT"],
        )

    return app


if __name__ == "__main__":
    # ローカル専用のため 127.0.0.1 でのみ待ち受ける
    create_app().run(host="127.0.0.1", port=5000, debug=True)
