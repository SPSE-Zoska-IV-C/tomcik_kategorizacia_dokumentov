import sqlite3


def vytvor_databazu():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # používateľské účty
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pouzivatelia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meno TEXT NOT NULL UNIQUE,
            heslo TEXT NOT NULL
        )
    """
    )

    # kategórie dokumentov priradené ku konkrétnemu používateľovi
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS kategorie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meno TEXT NOT NULL,
            nazov TEXT NOT NULL,
            UNIQUE(meno, nazov)
        )
    """
    )

    conn.commit()
    conn.close()

def pouzivatel_existuje(meno):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM pouzivatelia WHERE meno = ?", (meno,))
    user = c.fetchone()
    conn.close()
    return user is not None


def pridaj_pouzivatela(meno, heslo):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO pouzivatelia (meno, heslo) VALUES (?, ?)", (meno, heslo)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Používateľ už existuje")
    finally:
        conn.close()


def over_pouzivatela(meno, heslo):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "SELECT * FROM pouzivatelia WHERE meno=? AND heslo=?", (meno, heslo)
    )
    user = c.fetchone()
    conn.close()
    return user


def ziskaj_kategorie_pre_pouzivatela(meno):
    """Vráti zoznam názvov kategórií pre daného používateľa."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT nazov FROM kategorie WHERE meno = ? ORDER BY nazov", (meno,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def pridaj_kategorium(meno, nazov):
    """Pridá novú kategóriu používateľovi (ak ešte neexistuje)."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO kategorie (meno, nazov) VALUES (?, ?)",
            (meno, nazov),
        )
        conn.commit()
    finally:
        conn.close()


def odstran_kategorium(meno, nazov):
    """Odstráni kategóriu používateľa z databázy."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    try:
        c.execute(
            "DELETE FROM kategorie WHERE meno = ? AND nazov = ?", (meno, nazov)
        )
        conn.commit()
    finally:
        conn.close()

