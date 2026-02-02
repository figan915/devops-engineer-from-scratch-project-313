from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Введите localhost:8080/ping и получи ответ"

@app.get("/ping")
def get_ping():
    return "pong"

@app.errorhandler(404)
def not_found(error):
    return "Page Not Found", 404
