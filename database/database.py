import psycopg2
from psycopg2 import pool
from config.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


# 🔥 CONNECTION POOL
connection_pool = pool.SimpleConnectionPool(
    1, 20,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)


def get_connection():
    return connection_pool.getconn()


def put_connection(conn):
    connection_pool.putconn(conn)


# 🚀 INIT DATABASE
def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:

            # USERS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    referrer_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # CHATS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id BIGINT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # INVITES
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invites (
                    inviter_id BIGINT,
                    invited_id BIGINT,
                    chat_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    PRIMARY KEY (inviter_id, invited_id, chat_id),

                    FOREIGN KEY (inviter_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (invited_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                )
            """)

            # CONTESTS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contests (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,

                    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                )
            """)

            # CONTEST RESULTS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contest_results (
                    contest_id INT,
                    user_id BIGINT,
                    invite_count INT,

                    PRIMARY KEY (contest_id, user_id),

                    FOREIGN KEY (contest_id) REFERENCES contests(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # WITHDRAWALS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    amount TEXT,
                    details TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # INDEXES (tezlik uchun)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inviter ON invites(inviter_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat ON invites(chat_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON invites(created_at)")

        conn.commit()
    finally:
        put_connection(conn)


# 👤 USER
def add_user(user_id, username, first_name, referrer_id=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, referrer_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET username = EXCLUDED.username, 
                    first_name = EXCLUDED.first_name
            """, (user_id, username, first_name, referrer_id))
        conn.commit()
    finally:
        put_connection(conn)


# 👥 CHAT
def add_chat(chat_id, title):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chats (chat_id, title)
                VALUES (%s, %s)
                ON CONFLICT (chat_id) DO NOTHING
            """, (chat_id, title))
        conn.commit()
    finally:
        put_connection(conn)


# 📩 INVITE
def add_invite(inviter_id, invited_id, chat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO invites (inviter_id, invited_id, chat_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (inviter_id, invited_id, chat_id) DO NOTHING
            """, (inviter_id, invited_id, chat_id))
        conn.commit()
    finally:
        put_connection(conn)


# 🔍 CHECK DUPLICATE
def invite_exists(inviter_id, invited_id, chat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM invites
                WHERE inviter_id=%s AND invited_id=%s AND chat_id=%s
            """, (inviter_id, invited_id, chat_id))
            return cursor.fetchone() is not None
    finally:
        put_connection(conn)


# 📊 STAT
def get_user_stat(user_id, chat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM invites
                WHERE inviter_id=%s AND chat_id=%s
            """, (user_id, chat_id))
            result = cursor.fetchone()
            return result[0] if result else 0
    finally:
        put_connection(conn)


# 🏆 TOP
def get_top_inviters(chat_id, limit=10):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.first_name, u.username, COUNT(i.invited_id) as count
                FROM invites i
                JOIN users u ON i.inviter_id = u.user_id
                WHERE i.chat_id = %s
                GROUP BY i.inviter_id, u.first_name, u.username
                ORDER BY count DESC
                LIMIT %s
            """, (chat_id, limit))
            return cursor.fetchall()
    finally:
        put_connection(conn)


# 💸 WITHDRAWAL
def add_withdrawal_request(user_id, amount, details):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO withdrawals (user_id, amount, details)
                VALUES (%s, %s, %s)
            """, (user_id, amount, details))
        conn.commit()
    finally:
        put_connection(conn)


# 🔥 WEEKLY TOP
def get_weekly_top(chat_id, limit=10):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.first_name, COUNT(i.invited_id)
                FROM invites i
                JOIN users u ON i.inviter_id = u.user_id
                WHERE i.chat_id = %s
                AND i.created_at >= NOW() - INTERVAL '7 days'
                GROUP BY i.inviter_id, u.first_name
                ORDER BY COUNT(i.invited_id) DESC
                LIMIT %s
            """, (chat_id, limit))
            return cursor.fetchall()
    finally:
        put_connection(conn)