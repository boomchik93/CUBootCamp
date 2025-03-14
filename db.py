from sqlite3 import connect


# Подключение к базе данных
def get_db_connection():
    conn = connect('project.db')
    conn.row_factory = dict_factory  # Используем dict_factory для удобства
    return conn


def dict_factory(cursor, row):
    """Преобразует строку результата запроса в словарь."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Создание таблиц
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

    conn.commit()
    conn.close()


# Функции для работы с базой данных
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


def add_teacher_code(teacher_id, code):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO teacher_codes (teacher_id, code, used) VALUES (?, ?, ?)",
        (teacher_id, code, False)
    )
    conn.commit()
    conn.close()


def get_code_info(code):
    conn = get_db_connection()
    code_info = conn.execute(
        "SELECT * FROM teacher_codes WHERE code = ?",
        (code,)
    ).fetchone()
    conn.close()
    return code_info


def mark_code_as_used(code):
    conn = get_db_connection()
    conn.execute(
        "UPDATE teacher_codes SET used = ? WHERE code = ?",
        (True, code)
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


def get_teacher_code_info(code):
    conn = get_db_connection()
    code_info = conn.execute(
        "SELECT tc.*, t.subject FROM teacher_codes tc "
        "JOIN teachers t ON tc.teacher_id = t.id "
        "WHERE tc.code = ?",
        (code,)
    ).fetchone()
    conn.close()
    return code_info


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
