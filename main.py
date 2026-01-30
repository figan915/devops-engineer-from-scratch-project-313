from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Введите localhost:8080/ping и получи ответ"

@app.get("/ping")
def get_ping():
    return "pong"