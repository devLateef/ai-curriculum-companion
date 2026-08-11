from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)

@app.route('/')
def hello():
    return "<p>Hello, World!</p>"

@app.route("/hello")
def get_name():
    name = request.args.get("name", "Flask")
    return f"Welcome {escape(name)}"