from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
    send_from_directory,
)
import os
import shutil
import string
from werkzeug.utils import secure_filename
from database import (
    vytvor_databazu,
    pridaj_pouzivatela,
    over_pouzivatela,
    ziskaj_kategorie_pre_pouzivatela,
    pridaj_kategorium,
    odstran_kategorium,
)
from docx import Document
import fitz
from ai.predict import predict_category

app = Flask(__name__)
# v produkcii nastav FLASK_SECRET_KEY v prostredí
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEFAULT_KATEGORIE = ["pravne", "financne", "clanky", "spravy"]

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


def _heslo_je_platne(heslo: str) -> bool:
    """Min. 8 znakov a aspoň jeden špeciálny znak."""
    if len(heslo) < 8:
        return False
    special_chars = set("!@#$%^&*()-_=+[]{};:,./?\\|`~\"'")
    return any(ch in special_chars for ch in heslo)


def get_user_categories(user):
    """
    Načíta kategórie daného používateľa z DB.
    Ak ešte nemá žiadne, založí predvolené.
    Zároveň zabezpečí existenciu adresárov.
    """
    cats = ziskaj_kategorie_pre_pouzivatela(user)
    if not cats:
        for kat in DEFAULT_KATEGORIE:
            pridaj_kategorium(user, kat)
        cats = list(DEFAULT_KATEGORIE)

    user_folder = os.path.join(UPLOAD_FOLDER, user)
    os.makedirs(user_folder, exist_ok=True)
    for kat in cats:
        os.makedirs(os.path.join(user_folder, kat), exist_ok=True)

    return cats


@app.route("/")
def index():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    user_folder = os.path.join(UPLOAD_FOLDER, user)
    os.makedirs(user_folder, exist_ok=True)

    categories = get_user_categories(user)

    counts = {}
    for kat in categories:
        folder = os.path.join(user_folder, kat)
        counts[kat] = len(os.listdir(folder)) if os.path.exists(folder) else 0

    total = sum(counts.values())

    return render_template(
        "index.html", meno=user, counts=counts, total=total, categories=categories
    )


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

    # dynamické kategórie pre daného používateľa (vrátane vlastných)
    user_categories = get_user_categories(user)

    for f in files:
        safe_name = secure_filename(f.filename)
        if not safe_name:
            continue

        temp_path = os.path.join(user_folder, safe_name)
        f.save(temp_path)

        text = extract_text(temp_path)

        try:
            category, confidence = predict_category(text, user_categories)
        except Exception:
            category = "pravne"

        # ak model vráti niečo prázdne, padni na default
        if not category:
            category = "pravne"

        # keď používateľ medzičasom pridal novú kategóriu, znovu načítaj zoznam
        if category not in user_categories:
            user_categories.append(category)

        # uložíme kategóriu do DB (ak ešte neexistuje) a vytvoríme priečinok
        pridaj_kategorium(user, category)
        target = os.path.join(user_folder, category)
        os.makedirs(target, exist_ok=True)

        os.replace(temp_path, os.path.join(target, safe_name))

    flash("Dokumenty boli nahrané.")
    return redirect(url_for("index"))


@app.route("/documents/<category>")
def documents_category(category):
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    folder = os.path.join(UPLOAD_FOLDER, user, category)

    raw_files = os.listdir(folder) if os.path.exists(folder) else []

    # Normalizujeme dáta pre šablónu tak, aby mali rovnaký formát
    files = [{"filename": f, "category": category} for f in raw_files]

    return render_template("documents.html", meno=user, category=category, files=files)


@app.route("/documents/total")
def documents_total():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    docs = []

    categories = get_user_categories(user)
    for kat in categories:
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

        flash("Zlé meno alebo heslo.")
        return redirect(url_for("prihlasenie"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def registracia():
    if request.method == "POST":
        meno = request.form["meno"]
        heslo = request.form["heslo"]

        # základná validácia hesla: dĺžka a špeciálny znak
        if not _heslo_je_platne(heslo):
            flash(
                "Heslo musí mať aspoň 8 znakov a obsahovať aspoň jeden špeciálny znak."
            )
            return redirect(url_for("registracia"))

        try:
            pridaj_pouzivatela(meno, heslo)
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("registracia"))

        # po registrácii založíme predvolené kategórie pre používateľa
        user_folder = os.path.join(UPLOAD_FOLDER, meno)
        os.makedirs(user_folder, exist_ok=True)
        for kat in DEFAULT_KATEGORIE:
            pridaj_kategorium(meno, kat)
            os.makedirs(os.path.join(user_folder, kat), exist_ok=True)

        return redirect(url_for("prihlasenie"))

    return render_template("register.html")


@app.route("/logout")
def odhlasenie():
    session.pop("meno", None)
    return redirect(url_for("prihlasenie"))


@app.route("/categories", methods=["POST"])
def add_category():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]
    raw_name = request.form.get("nova_kategoria", "").strip()

    if not raw_name:
        flash("Názov kategórie nesmie byť prázdny.")
        return redirect(url_for("index"))

    # jednoduchá normalizácia názvu
    name = raw_name.lower()

    pridaj_kategorium(user, name)

    user_folder = os.path.join(UPLOAD_FOLDER, user)
    os.makedirs(os.path.join(user_folder, name), exist_ok=True)

    flash(f"Kategória '{name}' bola pridaná.")
    return redirect(url_for("index"))


@app.route("/categories/delete/<category>", methods=["POST"])
def delete_category(category):
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))

    user = session["meno"]

    # odstránenie z DB
    odstran_kategorium(user, category)

    # zmazanie adresára s dokumentmi tejto kategórie
    folder = os.path.join(UPLOAD_FOLDER, user, category)
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)

    flash(f"Kategória '{category}' bola odstránená.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
