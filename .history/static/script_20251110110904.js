//script.js

const login_button = document.getElementById('login-button');
const register_button = document.getElementById("register-button")
const status_text = document.getElementById("status");
const logout_button = document.getElementById("logout-button")
const message_field = document.getElementById("msg-field")
const message_button = document.getElementById('message-button');

const message_section = document.getElementById("message-section");
message_section.style.display = "none";

const credentials_inputs = document.getElementById("credentials-input");
const credentials_buttons = document.getElementById("credentials-buttons");

function showMessages() {
    //document.getElementById("username").style.display = "none";
    document.getElementById("password").style.display = "none";
    //document.getElementById("message-section").style.display = "block";
    login_button.style.display = "none";
    register_button.style.display = "none";
}

function showLogin() {
    document.getElementById("username").style.display = "block";
    document.getElementById("password").style.display = "block";
    login_button.style.display = "block";
    register_button.style.display = "block";
    document.getElementById("message-section").style.display = "none";
}

//Login and Register Logic ----------------------------

//login button listener
login_button.addEventListener('click', function() {
    const username = document.getElementById("username").value
    const password = document.getElementById("password").value
    body = {
        username: username,
        password: password

    };
    response = send_response("POST", "/api/login", {username, password})
    status_text.textContent = response.responseText;
    if(response.status == 200) {
        showMessages();
    }
   
});

//register button listener
register_button.addEventListener('click', function() {
    const username = document.getElementById("username").value
    const password = document.getElementById("password").value
    body = {
        username: username,
        password: password

    };
    response = send_response("CREATE", "/api/login", {username, password})
    status_text.textContent = response.responseText;
})

//----------------------------------

logout_button.addEventListener('click', function() {
    const xhr = new XMLHttpRequest();
    xhr.open("DELETE", "/api/login", true);
    xhr.withCredentials = true;
    xhr.onload = function() {
        status_text.textContent = xhr.responseText;
        if (xhr.status === 200) {
            // Optionally reset the UI
            document.getElementById("username").value = "";
            document.getElementById("password").value = "";
            showLogin();
        }
    };
    xhr.send();
});

window.addEventListener("load", function () {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/session", true);
    xhr.withCredentials = true;  // important so cookies are sent
    xhr.onload = function() {
        if (xhr.status === 200) {
            status_text.textContent = xhr.responseText;
        } else {
            status_text.textContent = "Please log in.";
        }
    };
    xhr.send();
});

//message logic
message_button.addEventListener("click", function() {
    const msg_text = message_field.value;
    if (!msg_text) return;
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/messages", true)
    xhr.withCredentials = true;
    xhr.setRequestHeader("Content-Type", "application/json")
    xhr.onload = function() {
        if(xhr.status === 200) {
            message_field.value = "";
            
        } else {
            alert("Must be logged in")
        }
    };
    xhr.send(JSON.stringify({message: msg_text}))
});

//get messages
function getMessages() {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/messages", true);
    xhr.withCredentials = true;
    xhr.onload = function() {
        if(xhr.status === 200) {
            const data = JSON.parse(xhr.responseText)
            displayMessages(data)
        }
    }
    xhr.send();
}

setInterval(getMessages, 3000);

//display messages
function displayMessages(messages) {
    const msg_div = document.getElementById("messages")
    msg_div.innerHTML = "";
    for(let i = 0; i < messages.length; i++) {
        const msg = messages[i]
        const div = document.createElement("div");
        div.textContent = `${msg.author}: ${msg.message}`;
        msg_div.appendChild(div)
    }
}

/*
    Function: send_response()
    params: method, path, body

    description:
        This function sends a response using XHR to the server.
        This function has parameters:
            method - method of the request
            path - path of the request
            body - body of the request
        All of these parameters are used to form an HTTP response to the server.
*/
function send_response(method, path, body) {
    const xmlhttp = new XMLHttpRequest();
    xmlhttp.open(method, path, false)
    xmlhttp.withCredentials = true;
    xmlhttp.setRequestHeader('Content-Type', 'application/json');
    xmlhttp.send(JSON.stringify(body))
    //return xmlhttp.responseText;
    return xmlhttp;
}