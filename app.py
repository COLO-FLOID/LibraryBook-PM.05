from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from datetime import datetime

app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)

db = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="library_db",
    cursorclass=pymysql.cursors.DictCursor
)

def format_dates(rows):
    for row in rows:
        if "created_at" in row and row["created_at"]:
            row["created_at"] = row["created_at"].strftime("%d.%m.%Y %H:%M")
    return rows


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/books")
def books_page():
    return render_template("books.html")


@app.route("/applications")
def applications_page():
    return render_template("applications.html")


@app.route("/reviews")
def reviews_page():
    return render_template("reviews.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.json

    login = data["login"]
    password = data["password"]
    full_name = data["full_name"]
    phone = data["phone"]
    email = data["email"]

    password_hash = generate_password_hash(password)

    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users(login, password_hash, full_name, phone, email, role_id)
            VALUES(%s, %s, %s, %s, %s, 2)
            """,
            (login, password_hash, full_name, phone, email)
        )

        db.commit()

    return jsonify({"message": "Пользователь зарегистрирован"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    login = data["login"]
    password = data["password"]

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM users WHERE login=%s",
            (login,)
        )

        user = cursor.fetchone()

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Неверный пароль"}), 401

    return jsonify({
        "message": "Успешный вход",
        "user_id": user["id"],
        "role_id": user["role_id"]
    })


@app.route("/api/books", methods=["GET"])
def get_books():
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()

    return jsonify(books)


@app.route("/api/applications", methods=["POST"])
def create_application():
    data = request.json

    user_id = data["user_id"]
    book_id = data["book_id"]

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT in_stock FROM books WHERE id=%s",
            (book_id,)
        )

        book = cursor.fetchone()

        if not book:
            return jsonify({"error": "Книга не найдена"}), 404

        if book["in_stock"] <= 0:
            return jsonify({"error": "Книги нет в наличии"}), 400

        cursor.execute(
            """
            INSERT INTO applications(user_id, book_id, status_id)
            VALUES(%s, %s, 1)
            """,
            (user_id, book_id)
        )

        cursor.execute(
            """
            UPDATE books
            SET in_stock = in_stock - 1
            WHERE id=%s
            """,
            (book_id,)
        )

        db.commit()

    return jsonify({"message": "Заявка на бронирование создана"})


@app.route("/api/applications/my/<int:user_id>", methods=["GET"])
def my_applications(user_id):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                applications.id,
                books.title,
                books.author,
                application_statuses.name AS status,
                applications.created_at
            FROM applications
            JOIN books ON applications.book_id = books.id
            JOIN application_statuses ON applications.status_id = application_statuses.id
            WHERE applications.user_id=%s
            ORDER BY applications.id DESC
            """,
            (user_id,)
        )

        applications = cursor.fetchall()
        
        applications = format_dates(applications)

    return jsonify(applications)


@app.route("/api/admin/applications", methods=["GET"])
def admin_applications():
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                applications.id,
                users.full_name,
                books.title,
                books.author,
                application_statuses.name AS status,
                applications.created_at
            FROM applications
            JOIN users ON applications.user_id = users.id
            JOIN books ON applications.book_id = books.id
            JOIN application_statuses ON applications.status_id = application_statuses.id
            ORDER BY applications.id DESC
            """
        )

        applications = cursor.fetchall()
        
        applications = format_dates(applications)

    return jsonify(applications)


@app.route("/api/admin/applications/<int:id>/status", methods=["PATCH"])
def update_status(id):
    data = request.json
    status_id = data["status_id"]

    with db.cursor() as cursor:
        cursor.execute(
            """
            UPDATE applications
            SET status_id=%s
            WHERE id=%s
            """,
            (status_id, id)
        )

        db.commit()

    return jsonify({"message": "Статус заявки изменён"})


@app.route("/api/reviews", methods=["POST"])
def add_review():
    data = request.json

    user_id = data["user_id"]
    text = data["text"]

    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO reviews(user_id, text)
            VALUES(%s, %s)
            """,
            (user_id, text)
        )

        db.commit()

    return jsonify({"message": "Отзыв добавлен"})


@app.route("/api/reviews", methods=["GET"])
def get_reviews():

    with db.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                reviews.id,
                users.login,
                reviews.text,
                reviews.created_at
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            ORDER BY reviews.id DESC
            """
        )

        reviews = cursor.fetchall()
        
        reviews = format_dates(reviews)

    return jsonify(reviews)

@app.route("/api/admin/applications/<int:id>", methods=["DELETE"])
def delete_application(id):

    with db.cursor() as cursor:

        cursor.execute(
            "DELETE FROM applications WHERE id=%s",
            (id,)
        )

        db.commit()

    return jsonify({"message": "Заявка удалена"})


if __name__ == "__main__":
    app.run(debug=True)