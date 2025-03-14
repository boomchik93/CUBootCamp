from sqlite3 import connect

conn = connect('project.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    second_name TEXT,
    phone_num TEXT,
    grade INTEGER
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS cooteachers (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    second_name TEXT,
    phone_num TEXT,
    grade INTEGER,
    subject TEXT,
    approved INTEGER DEFAULT 0
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    second_name TEXT,
    phone_num TEXT,
    subject TEXT,
    codes TEXT
);
''')

conn.commit()


def user_exists(username):
    cursor.execute("SELECT 1 FROM students WHERE username = ? UNION ALL "
                   "SELECT 1 FROM cooteachers WHERE username = ? UNION ALL "
                   "SELECT 1 FROM teachers WHERE username = ? LIMIT 1",
                   (username, username, username))
    return cursor.fetchone() is not None


def get_user_status(username):
    cursor.execute("SELECT * FROM students WHERE username = ? LIMIT 1", (username,))
    result = cursor.fetchone()
    if result:
        return {'role': 'student', 'data': result}
    cursor.execute("SELECT * FROM cooteachers WHERE username = ? LIMIT 1", (username,))
    result = cursor.fetchone()
    if result:
        return {'role': 'cooteacher', 'data': result}

    cursor.execute("SELECT * FROM teachers WHERE username = ? LIMIT 1", (username,))
    result = cursor.fetchone()
    if result:
        return {'role': 'teacher', 'data': result}

    return None
