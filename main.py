from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiar_esto_por_algo_seguro")

DB_PATH = "database.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        juego TEXT,
        score INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()

if not os.path.exists(DB_PATH):
    init_db()

@app.context_processor
def inject_user():
    return dict(logged_in = ("user_id" in session), user_name = session.get("user_name"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        email = request.form.get("email")
        password = request.form.get("password")
        if not (nombre and apellido and email and password):
            flash("Rellena todos los campos.", "warning")
            return redirect(url_for("register"))
        pw_hash = generate_password_hash(password)
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (nombre, apellido, email, password_hash) VALUES (?, ?, ?, ?)",
                        (nombre, apellido, email, pw_hash))
            conn.commit()
            flash("Registro exitoso. Por favor inicia sesión.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Ese correo ya está registrado.", "danger")
            return redirect(url_for("register"))
    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["nombre"]
            flash("Bienvenido, " + user["nombre"], "success")
            return redirect(url_for("menu_juego"))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for("login"))
    return render_template("iniciar_sesion.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("index"))

@app.route("/juego")
def menu_juego():
    if "user_id" not in session:
        flash("Inicia sesión para jugar.", "warning")
        return redirect(url_for("login"))
    return render_template("juego.html")

@app.route("/preguntas", methods=["GET", "POST"])
def preguntas():
    if "user_id" not in session:
        return redirect(url_for("login"))

    preguntas = [
        {"id": 1, "pregunta": "¿Qué va en la caneca blanca?", "opciones": ["Papel", "Vidrio", "Orgánico"], "respuesta": "Vidrio"},
        {"id": 2, "pregunta": "¿Qué va en la caneca verde?", "opciones": ["Orgánico", "Plástico", "Papel"], "respuesta": "Orgánico"},
        {"id": 3, "pregunta": "¿Qué va en la caneca negra?", "opciones": ["Restos no reciclables", "Plástico", "Metal"], "respuesta": "Restos no reciclables"}
    ]

    if request.method == "POST":
        puntaje = 0
        for p in preguntas:
            resp = request.form.get(f"q{p['id']}")
            if resp and resp == p["respuesta"]:
                puntaje += 1
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO resultados (user_id, juego, score) VALUES (?, ?, ?)",
                    (session["user_id"], "preguntas", puntaje))
        conn.commit()
        flash(f"Puntaje guardado: {puntaje}", "success")
        return redirect(url_for("menu_juego"))

    return render_template("preguntas.html", preguntas=preguntas)

@app.route("/historial")
def historial():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM resultados WHERE user_id = ? ORDER BY created_at DESC", (session["user_id"],))
    rows = cur.fetchall()
    return render_template("historial.html", resultados=rows)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
