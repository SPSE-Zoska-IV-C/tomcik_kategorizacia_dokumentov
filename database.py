import sqlite3

def vytvor_databazu():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pouzivatelia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meno TEXT NOT NULL UNIQUE,
            heslo TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def pouzivatel_existuje(meno):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM pouzivatelia WHERE meno = ?', (meno,))
    user = c.fetchone()
    conn.close()
    return user is not None

def pridaj_pouzivatela(meno, heslo):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO pouzivatelia (meno, heslo) VALUES (?, ?)', (meno, heslo))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Používateľ už existuje")
    finally:
        conn.close()

def over_pouzivatela(meno, heslo):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM pouzivatelia WHERE meno=? AND heslo=?', (meno, heslo))
    user = c.fetchone()
    conn.close()
    return user
