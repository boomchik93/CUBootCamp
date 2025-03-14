from sqlite3 import connect


def get_db_connection():
    conn = connect('project.db')
    conn.row_factory = dict_factory
    return conn


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def init_db():
    conn = get_db_connection()
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
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        first_name TEXT NOT NULL,
        last_name TEXT,
        phone_num TEXT NOT NULL,
        subject TEXT NOT NULL
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
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_username TEXT NOT NULL,
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        FOREIGN KEY (student_username) REFERENCES students(username)
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        cooteacher_username TEXT NOT NULL,
        FOREIGN KEY (request_id) REFERENCES requests(id),
        FOREIGN KEY (cooteacher_username) REFERENCES cooteachers(username)
    );
    ''')

    conn.commit()
    conn.close()


def add_student(username, first_name, second_name, phone_num, grade):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO students (username, first_name, second_name, phone_num, grade) VALUES (?, ?, ?, ?, ?)",
        (username, first_name, second_name, phone_num, grade)
    )
    conn.commit()
    conn.close()


def add_cooteacher(username, first_name, second_name, phone_num, grade, subject):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO cooteachers (username, first_name, second_name, phone_num, grade, subject) VALUES (?, ?, ?, ?, ?, ?)",
        (username, first_name, second_name, phone_num, grade, subject)
    )
    conn.commit()
    conn.close()


def add_teacher(username, first_name, last_name, phone_num, subject):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO teachers (username, first_name, last_name, phone_num, subject) VALUES (?, ?, ?, ?, ?)",
        (username, first_name, last_name, phone_num, subject)
    )
    conn.commit()
    conn.close()


def get_user_status(username):
    conn = get_db_connection()
    user_info = conn.execute(
        "SELECT * FROM students WHERE username = ? LIMIT 1", (username,)
    ).fetchone()
    if user_info:
        conn.close()
        return {'role': 'student', 'data': user_info}

    user_info = conn.execute(
        "SELECT * FROM cooteachers WHERE username = ? LIMIT 1", (username,)
    ).fetchone()
    if user_info:
        conn.close()
        return {'role': 'cooteacher', 'data': user_info}

    user_info = conn.execute(
        "SELECT * FROM teachers WHERE username = ? LIMIT 1", (username,)
    ).fetchone()
    if user_info:
        conn.close()
        return {'role': 'teacher', 'data': user_info}

    conn.close()
    return None


def user_exists(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM students WHERE username = ? UNION ALL "
        "SELECT 1 FROM cooteachers WHERE username = ? UNION ALL "
        "SELECT 1 FROM teachers WHERE username = ? LIMIT 1",
        (username, username, username)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def create_request(student_username, subject, description):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO requests (student_username, subject, description) VALUES (?, ?, ?)",
        (student_username, subject, description)
    )
    conn.commit()
    conn.close()


def get_open_requests():
    conn = get_db_connection()
    requests = conn.execute(
        "SELECT * FROM requests WHERE status = 'open'"
    ).fetchall()
    conn.close()
    return requests


def create_response(request_id, cooteacher_username):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO responses (request_id, cooteacher_username) VALUES (?, ?)",
        (request_id, cooteacher_username)
    )
    conn.commit()
    conn.close()


def close_request(request_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE requests SET status = 'closed' WHERE id = ?",
        (request_id,)
    )
    conn.commit()
    conn.close()


def get_student_username_by_request_id(request_id):
    conn = get_db_connection()
    request = conn.execute(
        "SELECT student_username FROM requests WHERE id = ?",
        (request_id,)
    ).fetchone()
    conn.close()
    return request['student_username'] if request else None


def get_student_info(username):
    conn = get_db_connection()
    student_info = conn.execute(
        "SELECT * FROM students WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    return student_info