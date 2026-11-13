"""生成AIパスポート模擬試験アプリ（Flask）。この端末だけで使う。"""

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for

import feedback
import history
import quiz
from config import Config


def create_app(config_object=Config):
    """Flask アプリを生成して返す。"""
    app = Flask(__name__)
    app.config.from_object(config_object)
    store = quiz.ExamStore()
    app.extensions["exam_store"] = store
    app.extensions["questions"] = None

    def get_questions():
        """問題データを初回だけ読み込んで返す。"""
        if app.extensions["questions"] is None:
            app.extensions["questions"] = quiz.load_questions(app.config["QUIZ_DATA_PATH"])
        return app.extensions["questions"]

    def get_current_exam():
        """セッションに紐づく試験を返す（無ければトップへ戻す）。"""
        exam = store.get(session.get("exam_id"))
        if exam is None:
            abort(redirect(url_for("index")))
        return exam

    @app.route("/", methods=["GET", "POST"])
    def index():
        """トップページ。POST で新しい試験を開始する。"""
        if request.method == "POST":
            try:
                questions = get_questions()
            except FileNotFoundError as error:
                flash(str(error))
                return redirect(url_for("index"))
            exam = quiz.create_exam(questions, app.config["QUIZ_QUESTION_COUNT"])
            store.add(exam)
            session["exam_id"] = exam.exam_id
            return redirect(url_for("question"))
        exam = store.get(session.get("exam_id"))
        return render_template(
            "index.html",
            question_count=app.config["QUIZ_QUESTION_COUNT"],
            exam_in_progress=exam is not None and not exam.is_finished,
        )

    @app.route("/question")
    def question():
        """次に回答すべき問題を表示する。"""
        exam = get_current_exam()
        index = exam.current_index
        if index is None:
            return redirect(url_for("result"))
        item = exam.items[index]
        question_data = get_questions()[item.question_id]
        return render_template(
            "question.html",
            exam=exam,
            index=index,
            question=question_data,
            choices=quiz.display_choices(question_data, item),
        )

    @app.route("/question/<int:index>", methods=["POST"])
    def answer(index):
        """回答を受け付けて採点し、判定画面へ移る。"""
        exam = get_current_exam()
        try:
            selected = [int(value) for value in request.form.getlist("choice")]
            quiz.submit_answer(exam, get_questions(), index, selected)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("question"))
        return redirect(url_for("judged", index=index))

    @app.route("/question/<int:index>/judged")
    def judged(index):
        """回答済みの問題の判定結果を表示する（再回答はできない）。"""
        exam = get_current_exam()
        if index >= len(exam.items) or exam.items[index].selected is None:
            return redirect(url_for("question"))
        item = exam.items[index]
        question_data = get_questions()[item.question_id]
        return render_template(
            "judged.html",
            exam=exam,
            index=index,
            item=item,
            question=question_data,
            choices=quiz.display_choices(question_data, item),
        )

    @app.route("/result")
    def result():
        """結果ページ。スコア・分野別正答率・60問の正誤一覧を表示する。"""
        exam = get_current_exam()
        if not exam.is_finished:
            return redirect(url_for("question"))
        questions = get_questions()
        summary = quiz.summarize(exam, questions)
        # 試験単位のスコアを履歴に保存（初回表示時のみ新規作成）
        history.save_record(app.config["HISTORY_DIR"], exam, summary)
        return render_template(
            "result.html",
            exam=exam,
            summary=summary,
            review=quiz.build_review(exam, questions),
        )

    @app.route("/result/feedback", methods=["POST"])
    def result_feedback():
        """AIによる総評を生成して JSON で返す（生成済みなら再利用する）。"""
        exam = get_current_exam()
        if not exam.is_finished:
            return jsonify({"error": "試験が終了していません"}), 400
        if exam.feedback is None:
            questions = get_questions()
            summary = quiz.summarize(exam, questions)
            payload = feedback.build_payload(exam, questions, summary)
            try:
                exam.feedback = feedback.generate_feedback(
                    app.config["GEMINI_API_KEY"], app.config["GEMINI_MODEL"], payload
                )
            except feedback.FeedbackError as error:
                return jsonify({"error": str(error)}), 502
            history.save_record(
                app.config["HISTORY_DIR"], exam, summary, exam.feedback, app.config["GEMINI_MODEL"]
            )
        return jsonify({"feedback": exam.feedback})

    @app.route("/history")
    def history_list():
        """過去の試験のスコア一覧。"""
        return render_template("history.html", records=history.list_records(app.config["HISTORY_DIR"]))

    @app.route("/history/<exam_id>")
    def history_detail(exam_id):
        """過去の試験1件のスコアとAI総評。"""
        try:
            record = history.load_record(app.config["HISTORY_DIR"], exam_id)
        except ValueError:
            record = None
        if record is None:
            abort(404)
        return render_template("history_detail.html", record=record)

    return app


if __name__ == "__main__":
    # ローカル専用のため 127.0.0.1 でのみ待ち受ける
    create_app().run(host="127.0.0.1", port=5000, debug=True)
