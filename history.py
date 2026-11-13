"""試験ごとのスコアとAI総評をローカルの JSON ファイルに保存する。

保存先（既定: history/）は Git 追跡対象外。試験途中の状態は保存しない。
"""

import json
import re
from datetime import datetime
from pathlib import Path

_EXAM_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _record_path(history_dir, exam_id):
    """試験IDから保存ファイルのパスを返す（不正なIDは拒否する）。"""
    if not _EXAM_ID_PATTERN.match(exam_id or ""):
        raise ValueError("不正な試験IDです")
    return Path(history_dir) / f"{exam_id}.json"


def save_record(history_dir, exam, summary, feedback_text=None, model=None):
    """試験結果を保存する。既存の記録があれば総評などを上書き更新する。"""
    path = _record_path(history_dir, exam.exam_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = load_record(history_dir, exam.exam_id) or {
        "exam_id": exam.exam_id,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "total": summary["total"],
        "correct": summary["correct"],
        "by_chapter": summary["by_chapter"],
        "by_section": summary["by_section"],
        "by_type": summary["by_type"],
        "feedback": None,
        "model": None,
    }
    if feedback_text is not None:
        record["feedback"] = feedback_text
        record["model"] = model
    with path.open("w", encoding="utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent=2)
    return record


def load_record(history_dir, exam_id):
    """1件の記録を読み込む（無ければ None）。"""
    path = _record_path(history_dir, exam_id)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def list_records(history_dir):
    """全記録を新しい順に返す。"""
    directory = Path(history_dir)
    if not directory.exists():
        return []
    records = []
    for path in directory.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as file:
                records.append(json.load(file))
        except (OSError, json.JSONDecodeError):
            continue  # 壊れたファイルは一覧から除外する
    return sorted(records, key=lambda record: record.get("finished_at", ""), reverse=True)
