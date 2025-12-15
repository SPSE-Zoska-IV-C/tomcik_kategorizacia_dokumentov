from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
import os
from database import vytvor_databazu, pridaj_pouzivatela, over_pouzivatela
from docx import Document
import fitz
from ai.predict import predict_category

app = Flask(__name__)
app.secret_key = "tajny_klic"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

KATEGORIE = ["pravne", "financne", "clanky", "spravy"]

vytvor_databazu()


def extract_text(path):
    if path.endswith(".pdf"):
        text = ""
        with fitz.open(path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text

    if path.endswith(".docx"):
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    if path.endswith(".txt"):
        return open(path, "r", encoding="utf-8", errors="ignore").read()

    return ""


@app.route("/")
def index():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    user_folder = os.path.join(UPLOAD_FOLDER, user)

    os.makedirs(user_folder, exist_ok=True)

    counts = {}
    for kat in KATEGORIE:
        folder = os.path.join(user_folder, kat)
        os.makedirs(folder, exist_ok=True)
        counts[kat] = len(os.listdir(folder))

    total = sum(counts.values())

    return render_template("index.html", meno=user, counts=counts, total=total)


@app.route("/upload", methods=["POST"])
def upload():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    files = request.files.getlist("subor")

    if not files or files[0].filename == "":
        flash("Nevybral si žiadne súbory.")
        return redirect(url_for("index"))

    user = session["meno"]
    user_folder = os.path.join(UPLOAD_FOLDER, user)

    for f in files:
        temp_path = os.path.join(user_folder, f.filename)
        f.save(temp_path)

        text = extract_text(temp_path)

        try:
            category, confidence = predict_category(text)
        except:
            category = "pravne"

        if category not in KATEGORIE:
            category = "pravne"

        target = os.path.join(user_folder, category)
        os.makedirs(target, exist_ok=True)

        os.replace(temp_path, os.path.join(target, f.filename))

    flash("Dokumenty boli nahrané.")
    return redirect(url_for("index"))


@app.route("/documents/<category>")
def documents_category(category):
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    folder = os.path.join(UPLOAD_FOLDER, user, category)

    files = os.listdir(folder) if os.path.exists(folder) else []

    return render_template("documents.html", meno=user, category=category, files=files)


@app.route("/documents/total")
def documents_total():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    docs = []

    for kat in KATEGORIE:
        folder = os.path.join(UPLOAD_FOLDER, user, kat)
        if os.path.exists(folder):
            for file in os.listdir(folder):
                docs.append({"filename": file, "category": kat})

    return render_template("documents.html", meno=user, category="vsetky", files=docs)


@app.route("/uploads/<username>/<category>/<filename>")
def serve_file(username, category, filename):
    folder = os.path.join(UPLOAD_FOLDER, username, category)
    return send_from_directory(folder, filename)


@app.route("/delete/<category>/<filename>", methods=["POST"])
def delete_file(category, filename):
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    file_path = os.path.join(UPLOAD_FOLDER, user, category, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        flash("Dokument bol odstránený.")
    else:
        flash("Súbor neexistuje.")

    return redirect(request.referrer or url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def prihlasenie():
    if request.method == "POST":
        meno = request.form["meno"]
        heslo = request.form["heslo"]

        if over_pouzivatela(meno, heslo):
            session["meno"] = meno
            return redirect(url_for("index"))

        return "Zlé meno alebo heslo"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def registracia():
    if request.method == "POST":
        meno = request.form["meno"]
        heslo = request.form["heslo"]

        pridaj_pouzivatela(meno, heslo)

        user_folder = os.path.join(UPLOAD_FOLDER, meno)
        for kat in KATEGORIE:
            os.makedirs(os.path.join(user_folder, kat), exist_ok=True)

        return redirect(url_for("prihlasenie"))

    return render_template("register.html")


@app.route("/logout")
def odhlasenie():
    session.pop("meno", None)
    return redirect(url_for("prihlasenie"))


if __name__ == "__main__":
    app.run(debug=True)
