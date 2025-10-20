from flask import Flask, render_template, request, redirect, session, url_for
import os, uuid, shutil
from database import vytvor_databazu, pridaj_pouzivatela, over_pouzivatela, pouzivatel_existuje
from ai.predict import init, analyze_text
import fitz  # PyMuPDF
from docx import Document

app = Flask(__name__)
app.secret_key = "tajny_klic_zmen"  # pouzi nieco bezpeicnejsie v produkcii

BASE = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

kategorie = ["financne", "pravne", "spravy", "clanky", "osobne"]

# vytvor DB a inicializuj AI
vytvor_databazu()
try:
    init()
except Exception as e:
    # ak model nie je lokalne, nech to nepadne pri startupe - len upozornime
    print("Upozornenie: model nie je dostupný (ai/model). Ak chceš používať AI, natrénuj a ulož model. Chyba:", e)

def extract_text_from_pdf(path):
    text = ""
    doc = fitz.open(path)
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(path):
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs])

def extrahuj_text(subor_cesta):
    if subor_cesta.lower().endswith(".pdf"):
        return extract_text_from_pdf(subor_cesta)
    elif subor_cesta.lower().endswith(".docx"):
        return extract_text_from_docx(subor_cesta)
    else:
        # ak iné, vráti len prázdny alebo názov
        return ""

@app.route("/register", methods=["GET", "POST"])
def registracia():
    if request.method == "POST":
        meno = request.form["meno"].strip()
        heslo = request.form["heslo"].strip()
        if pouzivatel_existuje(meno):
            return "Používateľ už existuje, zvoľ iné meno."
        pridaj_pouzivatela(meno, heslo)
        # vytvor priecinky
        user_folder = os.path.join(UPLOAD_FOLDER, meno)
        os.makedirs(user_folder, exist_ok=True)
        for k in kategorie:
            os.makedirs(os.path.join(user_folder, k), exist_ok=True)
        return redirect(url_for("prihlasenie"))
    return render_template("register.html")

@app.route("/", methods=["GET","POST"])
def prihlasenie():
    if request.method == "POST":
        meno = request.form["meno"].strip()
        heslo = request.form["heslo"].strip()
        if over_pouzivatela(meno, heslo):
            session["meno"] = meno
            return redirect(url_for("nahrat_subor"))
        else:
            return "Nesprávne meno alebo heslo"
    return render_template("login.html")


# --- New Upload Page with Category Selection ---
@app.route("/upload_new", methods=["GET", "POST"])
def upload_new():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))
    if request.method == "POST":
        f = request.files["subor"]
        category = request.form.get("kategoria")
        if f and category in kategorie:
            user = session["meno"]
            user_folder = os.path.join(UPLOAD_FOLDER, user)
            dest_folder = os.path.join(user_folder, category)
            os.makedirs(dest_folder, exist_ok=True)
            dest_name = f"{uuid.uuid4().hex}_{f.filename}"
            dest_path = os.path.join(dest_folder, dest_name)
            f.save(dest_path)
            # Optionally, store upload date in a log/db for listing (not in current DB, so use file info)
            return redirect(url_for("documents_category", category=category))
    return render_template("upload_new.html")

# --- Category Document Listing Pages ---
from datetime import datetime
from flask import send_from_directory

def get_all_documents(category=None):
    docs = []
    for user in os.listdir(UPLOAD_FOLDER):
        user_folder = os.path.join(UPLOAD_FOLDER, user)
        if not os.path.isdir(user_folder):
            continue
        cats = [category] if category else kategorie
        for cat in cats:
            cat_folder = os.path.join(user_folder, cat)
            if not os.path.isdir(cat_folder):
                continue
            for fname in os.listdir(cat_folder):
                fpath = os.path.join(cat_folder, fname)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    docs.append({
                        "filename": fname,
                        "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "uploader": user,
                        "download_url": url_for("download_file", user=user, category=cat, filename=fname)
                    })
    # Sort by date desc
    docs.sort(key=lambda d: d["date"], reverse=True)
    return docs

@app.route("/documents/total")
def documents_total():
    docs = get_all_documents()
    return render_template("documents_base.html", title="Všetky dokumenty", documents=docs)

@app.route("/documents/<category>")
def documents_category(category):
    if category not in kategorie:
        return "Neznáma kategória", 404
    docs = get_all_documents(category)
    title_map = {
        "financne": "Finančné dokumenty",
        "pravne": "Právne dokumenty",
        "spravy": "Správy",
        "clanky": "Články",
        "osobne": "Osobné dokumenty"
    }
    return render_template("documents_base.html", title=title_map.get(category, category), documents=docs)

@app.route("/download/<user>/<category>/<filename>")
def download_file(user, category, filename):
    folder = os.path.join(UPLOAD_FOLDER, user, category)
    return send_from_directory(folder, filename, as_attachment=True)

# --- Keep original /upload for AI/auto-classification uploads ---
@app.route("/upload", methods=["GET","POST"])
def nahrat_subor():
    if "meno" not in session:
        return redirect(url_for("prihlasenie"))
    if request.method == "POST":
        f = request.files["subor"]
        if f:
            user = session["meno"]
            user_folder = os.path.join(UPLOAD_FOLDER, user)
            tmp_path = os.path.join(user_folder, f"tmp_{uuid.uuid4().hex}_{f.filename}")
            f.save(tmp_path)
            # extrahuj text
            text = extrahuj_text(tmp_path)
            # ak AI je dostupná, klasifikuj, inak default 'osobne'
            try:
                category = analyze_text(text)
            except Exception as e:
                print("AI classify failed:", e)
                category = "osobne"
            # zabezpec nazov suboru unikátny
            dest_folder = os.path.join(user_folder, category)
            os.makedirs(dest_folder, exist_ok=True)
            dest_name = f"{uuid.uuid4().hex}_{f.filename}"
            dest_path = os.path.join(dest_folder, dest_name)
            shutil.move(tmp_path, dest_path)
            return render_template("result.html", subor=dest_name, category=category)
    return render_template("upload.html")

@app.route("/logout")
def odhlasenie():
    session.pop("meno", None)
    return redirect(url_for("prihlasenie"))

if __name__ == "__main__":
    app.run(debug=True)
