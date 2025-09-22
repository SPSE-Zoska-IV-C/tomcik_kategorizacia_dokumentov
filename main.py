from flask import Flask, request, render_template
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    # Demo kategória – AI logika pridáme neskôr
    category = "To be analyzed by AI later"
    
    return render_template("result.html", filename=file.filename, category=category)

if __name__ == "__main__":
    app.run(debug=True)

    
