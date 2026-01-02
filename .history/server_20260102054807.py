#server.py
"""
Author: Jericho Dinozo
Student #: 007875358

This program serves as a webpage that retrieves messages from a database
to display to the fronend HTML page to the user.

"""
import socket
import threading
import os
import uuid
import json
import select
import time
import argparse
import re


HOST = ''
PORT = 8080
database_host = ''
database_port = 0

sessions = {}

#Function db_call()
#This function takes parameters string, int, and JSON data
#This function is responsible for interacting with the database
def db_call(database_host, database_port, data):
    message = json.dumps(data).encode("utf-8")
    message_length = len(message).to_bytes(4, 'big')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as database_socket:
        database_socket.connect((database_host, database_port))
        database_socket.sendall(message_length + message)
        readable, _, _ = select.select([database_socket], [], [], 5)
        if not readable:
            print("DB timeout")
            return None
        
        length_bytes = database_socket.recv(4) #length of body
        if not length_bytes:
            return None
        response_length = int.from_bytes(length_bytes, 'big')
        response_data = b""
        while len(response_data) < response_length:
            readable, _, _ = select.select([database_socket], [], [], 5)
            if not readable:
                break
            more = database_socket.recv(4096)
            if not more:
                break
            response_data += more
        
        return json.loads(response_data.decode())

#function getMessages()
#This function fetches messages from the database
def getMessages():
    response = db_call(database_host, database_port, {"method": "GetMessages"})
    msgs = []
    if response and response["status"] == 0:
        messages = response["msgs"]
        for msg in messages:
            msgs.append({
                "author": msg["author"],
                "message": msg["msg"]
            })
    return msgs

#function user_fromCookie
#This function returns the user based on cookie
def user_fromCookie(headers):
    pattern = re.compile(r"^cookie\s*", re.IGNORECASE) #ignore uppercase or lowercase
    for line in headers.split("\r\n"): 
        if pattern.search(line): #if cookie header is found
            cookie_data = line.split(":", 1)[1].strip()
            for cookie in cookie_data.split(";"):
                key, _, value = cookie.strip().partition("=")
                if key == "session":
                    return sessions.get(value)
    return None

#This function creates an HTTP response
def create_response(status, content_type, content_length, body, extra_hdrs):
    return (
        f"HTTP/1.1 {status}\r\n"
        f"Content-type: {content_type}\r\n"
        f"Content-Length: {content_length}\r\n"
        f"{extra_hdrs}"
        "\r\n"
        f"{body}"
    )

#This function is responsible for api calls
#for path /api/
def api_call(method, path, body, hdrs):
    response_body = ''
    status = ''
    content_type = ''
    extra_hdrs = ''
    if path == "/api/login":
        json_params = {}
        username = ""
        password = ""
        content_type = "text/plain"
        extra_hdrs = ''

        if method in ["POST", "CREATE"]:
            json_response = body
            json_params = json.loads(json_response or "{}")
            username = json_params["username"]
            password = json_params["password"]
        

        if method == "POST":

            if not username or not password:
                response_body = "username and password cannot be empty"
                status="400 Bad Request"
                return create_response(status, "text/plain", len(response_body), response_body, "")
            
            response = db_call(database_host, database_port, {"method": "GetUser",
                                                               "user": username}) #check if user already exists
            if response.get("status") == 4: #if user does not exist
                response_body = "user does not exist"
                status = "403 Forbidden"
            elif response.get("status") == 0 and password == response.get("user").get("pass"): #if user exists and password matches
                response_body = "welcome " + username
                status = "200 OK"
                session_id = str(uuid.uuid4())
                sessions[session_id] = username
                extra_hdrs = f"Set-Cookie: session={session_id}; HttpOnly\r\n"
            elif response.get("status") == 0 and password != response.get("user").get("pass"): #if user exists but wrong password
                response_body = "invalid username or password"
                status = "403 Forbidden"
        elif method == "CREATE":
            response = db_call(database_host, database_port, {"method": "GetUser",
                                                               "user": username}) #check if user exists
            
            if response.get("status") == 4: #if user does not exist yet, create new user
                db_response = db_call(database_host, database_port, {"method": "AddUser",
                                                                        "user": username,
                                                                        "pass": password})
                if db_response.get("status") == 0:
                    response_body = "registration success!"
                    status = "200 OK"
                else:
                    print(db_response)
            elif response.get("status") == 0: #if user already exists
                response_body = "username already taken!"
                status = "403 Forbidden"
        elif method == "DELETE": #logout
            user = user_fromCookie(hdrs)
            if user:
                for sessionID in sessions:
                    if sessions[sessionID] == user:
                        del sessions[sessionID]
                        break
                response_body = "Logged out"
                status = "200 OK"
            else:
                response_body = "No active session"
                status = "403 Forbidden"
            extra_hdrs = "Set-Cookie: session=deleted; Max-Age=0; HttpOnly\r\n"

    elif path == "/api/session":
        user = user_fromCookie(hdrs)
        if user:
            response_body = f"Hello, {user}"
            status = "200 OK"
        else:
            response_body = "Please login/register"
            status = "403 Forbidden"
    

    elif path == "/api/messages": #path messages
        user = user_fromCookie(hdrs)
        content_type = "application/json"

        if not user:
            response_body = json.dumps({"error": "not logged in"})
            status = "403 Forbidden"

        elif method == "POST": #sending new messages
            message = json.loads(body)
            text = message.get("message").strip()
            if not text: #if message is empty
                response_body = json.dumps({"error": "message cannot be empty"})
                status = "400 Bad Request"
            else:
                db_response = db_call(database_host, database_port, {
                    "method": "NewMessage",
                    "author": user,
                    "msg": text
                })
                if db_response.get("status") == 0: #successful message
                    response_body = json.dumps({"success": True, "id": db_response["id"]})
                    status = "200 OK"
                else:
                    response_body = json.dumps({
                        "error"
                    })
                    status = "500 Internal Server Error"
        elif method == "GET":
            status = "200 OK"
            response_body = json.dumps(getMessages())
    content_length = len(response_body)
    return (
        create_response(status, content_type, content_length, response_body, extra_hdrs)
    )


#this function handles client interaction
def handle_client(connection, address):
    try:
        request_data = connection.recv(4096).decode('utf-8')

        
        headers, body = request_data.split('\r\n\r\n')
        request_line = headers.splitlines()[0]
        method, path, _ = request_line.split()
        
        content_length = 0
        for line in headers.split('\r\n'):
            if "Content-Length" in line:
                content_length = (int)(line.split(":")[1])

        while len(body) < content_length:
            more = connection.recv(4096).decode('utf-8')
            if not more:
                break
            body += more

        if path == '/':
            path = '/index.html'

        if path.startswith('/api/'):
            response = api_call(method, path, body, headers)
            connection.sendall(response.encode())
            return  
        
        pagepath = os.path.join('static', path.lstrip('/'))

        if not os.path.isfile(pagepath):
            http_response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 13\r\n"
                "\r\n"
                "404 Not Found"
            )
            connection.sendall(http_response.encode())
            return
        with open(pagepath, 'rb') as f:
            content = f.read()

        http_response = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Length: {len(content)}\r\n"
            "Content-Type: text/html\r\n"
            "\r\n"
        ).encode() + content
        connection.sendall(http_response)
        
    except Exception as e:
        http_response = (
            "HTTP/1.1 500 Internal Server Error\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 21\r\n"
            "\r\n"
            "Internal Server Error"
        )
        connection.sendall(http_response.encode())

    finally:
        connection.close()



def main():
    global database_host, database_port
    """parser = argparse.ArgumentParser()
    parser.add_argument("database_host", type=str, help="Enter hostname of database")
    args = parser.parse_args()
    database_host = args.database_host
    database_port = 50042"""
    parser = argparse.ArgumentParser()
parser.add_argument("--database_host", default="127.0.0.1", help="DB hostname (default: localhost)")
parser.add_argument("--database_port", type=int, default=50042, help="DB port (default: 50042)")
args = parser.parse_args()
database_host = args.database_host
database_port = args.database_port
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Server active on port {PORT}...")
    while True:
        client_connection, client_address = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_connection, client_address))
        thread.start()
if __name__ == "__main__":
    main()