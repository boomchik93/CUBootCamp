from sqlite3 import connect


def get_db_connection():
    conn = connect('project.db')
    conn.row_factory = dict_factory
    return conn


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


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
    CREATE TABLE IF NOT EXISTS teacher_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    code TEXT NOT NULL UNIQUE,
    used BOOLEAN DEFAULT FALSE,
    subject TEXT NOT NULL,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id)
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
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY,
        username TEXT,
        subject TEXT,
        status TEXT
    );
    ''')

    conn.commit()
    conn.close()


def add_ticket(username, subject):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO tickets (username, subject, status) VALUES (?, ?, ?)",
        (username, subject, "waiting")
    )
    conn.commit()
    conn.close()


def get_tickets():
    conn = get_db_connection()
    tickets = conn.execute(
        "SELECT username FROM tickets"
    ).fetchall()
    ids = []
    for x in tickets:
        ids.append(int(x["username"]))
    conn.close()
    return ids


def close_ticket(username):
    conn = get_db_connection()
    conn.execute("DELETE FROM tickets WHERE username=?", (str(username)))
    conn.close()
    return


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
        """INSERT INTO cooteachers 
        (username, first_name, second_name, phone_num, grade, subject) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        (username, first_name, second_name, phone_num, grade, subject)
    )
    conn.commit()
    conn.close()


def add_teacher(username, first_name, last_name, phone_num, subject):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO teachers (username, first_name, last_name, phone_num, subject) VALUES (?, ?, ?, ?, ?)",
        (username, first_name, last_name or '', phone_num, subject)
    )
    conn.commit()
    conn.close()


def add_teacher_code(teacher_id, code, subject):
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO teacher_codes 
        (teacher_id, code, used, subject) 
        VALUES (?, ?, ?, ?)""",
        (teacher_id, code.upper(), 0, subject)
    )
    conn.commit()
    conn.close()


def mark_code_as_used(code):
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE teacher_codes SET used = 1 WHERE code = ?",
            (code.upper(),)
        )
        conn.commit()
    finally:
        conn.close()


def get_teacher_code_info(code):
    conn = get_db_connection()
    try:
        code_info = conn.execute(
            """SELECT tc.*, t.subject as teacher_subject 
               FROM teacher_codes tc
               JOIN teachers t ON tc.teacher_id = t.id
               WHERE code = ?""",
            (code.upper(),)
        ).fetchone()

        if code_info:
            return {
                'id': code_info['id'],
                'code': code_info['code'],
                'used': bool(code_info['used']),
                'subject': code_info['subject'],
                'teacher_id': code_info['teacher_id'],
                'teacher_subject': code_info['teacher_subject']
            }
        return None
    finally:
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


def delete_student(username):
    with connect('project.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE username = ?", (username,))
        conn.commit()


def delete_cooteacher(username):
    with connect('project.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cooteachers WHERE username = ?", (username,))
        conn.commit()


def delete_teacher(username):
    with connect('project.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM teachers WHERE username = ?", (username,))
        conn.commit()
