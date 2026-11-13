"""アプリの設定。値は .env（Git 追跡対象外）から読み込む。"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Flask と問題集の設定をまとめたクラス。"""

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32).hex()
    QUIZ_DATA_PATH = BASE_DIR / os.environ.get("QUIZ_DATA_PATH", "data/all.json")
    QUIZ_QUESTION_COUNT = int(os.environ.get("QUIZ_QUESTION_COUNT", "60"))
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
