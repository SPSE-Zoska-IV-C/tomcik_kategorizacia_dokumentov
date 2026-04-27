Aplikácia na kategorizáciu dokumentov


Tento projekt je webová aplikácia na rozpoznávanie a organizáciu dokumentov. Používateľ nahraje súbory (PDF, DOCX, TXT) a aplikácia automaticky extrahuje text, použije model na určenie kategórie a súbory uloží do priečinkov podľa kategórií. Rozhranie poskytuje prehľad dokumentov, možnosť stiahnuť, otvoriť alebo zmazať súbory a spravovať vlastné kategórie.

Používané technológie:
- Backend: Flask (Python)  
- Textová extrakcia: PyMuPDF (fitz) pre PDF, python-docx pre DOCX
- Klasifikácia: Hugging Face Transformers (zero-shot) cez model MoritzLaurer/mDeBERTa-v3-base-xnli...
- Úložisko: súborový systém (adresár uploads) + SQLite databáza pre používateľov a kategórie


1. Vytvorte a aktivujte virtuálne prostredie:
python -m venv venv
venv\Scripts\activate
Nainštalujte závislosti: pip install -r [requirements.txt](http://_vscodecontentref_/0)


Inicializujte databázu (aplikácia to robí automaticky pri prvom spustení) a spustite server:python [main.py](http://_vscodecontentref_/1)



Otvorte v prehliadači: http://127.0.0.1:5000
Poznámky:

Základné súbory v projekte
Hlavná aplikácia a routy: main.app — main.py
Databázové funkcie: database.vytvor_databazu, database.pridaj_pouzivatela — database.py
Klasifikácia kategórií: ai.predict.predict_category — ai/predict.py
Zoznam závislostí: requirements.txt
Šablóny a statické súbory: templates/index.html, templates/documents.html, templates/login.html, templates/register.html, static/style.css
