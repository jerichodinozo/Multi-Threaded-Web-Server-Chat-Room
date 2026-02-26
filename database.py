# database.py
import socket, select, json, sqlite3, time

HOST = "127.0.0.1"
PORT = 50042

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            msg TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()

def recv_exact(sock: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return b""
        data += chunk
    return data

def handle_request(db: sqlite3.Connection, req: dict) -> dict:
    method = req.get("method")

    if method == "GetUser":
        user = req.get("user", "")
        cur = db.cursor()
        cur.execute("SELECT username, password FROM users WHERE username=?", (user,))
        row = cur.fetchone()
        if not row:
            return {"status": 4} 
        return {"status": 0, "user": {"name": row[0], "pass": row[1]}}

    if method == "AddUser":
        user = req.get("user", "")
        pw = req.get("pass", "")
        try:
            cur = db.cursor()
            cur.execute("INSERT INTO users(username, password) VALUES(?, ?)", (user, pw))
            db.commit()
            return {"status": 0}
        except sqlite3.IntegrityError:
            return {"status": 1, "error": "user exists"}

    if method == "GetMessages":
        cur = db.cursor()
        cur.execute("SELECT author, msg, id FROM messages ORDER BY id ASC")
        rows = cur.fetchall()
        msgs = [{"author": a, "msg": m, "id": i} for (a, m, i) in rows]
        return {"status": 0, "msgs": msgs}

    if method == "NewMessage":
        author = req.get("author", "")
        msg = req.get("msg", "")
        cur = db.cursor()
        cur.execute(
            "INSERT INTO messages(author, msg, created_at) VALUES(?, ?, ?)",
            (author, msg, time.time())
        )
        db.commit()
        return {"status": 0, "id": cur.lastrowid}

    return {"status": 2, "error": "unknown method"}

def main():
    db = sqlite3.connect("local.db", check_same_thread=False)
    init_db(db)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(50)
    print(f"Local DB listening on {HOST}:{PORT}")

    while True:
        client, addr = server.accept()
        with client:
            # read 4-byte length prefix
            hdr = recv_exact(client, 4)
            if not hdr:
                continue
            length = int.from_bytes(hdr, "big")
            body = recv_exact(client, length)
            if not body:
                continue

            try:
                req = json.loads(body.decode("utf-8"))
                resp = handle_request(db, req)
            except Exception as e:
                resp = {"status": 3, "error": str(e)}

            resp_bytes = json.dumps(resp).encode("utf-8")
            client.sendall(len(resp_bytes).to_bytes(4, "big") + resp_bytes)

if __name__ == "__main__":
    main()
