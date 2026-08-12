from flask import Flask, request, render_template, abort
from markupsafe import escape
import logging
from backend.services.auth import home, hello

logging.basicConfig(level=logging.DEBUG, force=True)

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
app.logger.handlers.clear()
app.logger.addHandler(logging.StreamHandler())

@app.route('/')
def landing():
    return home()

@app.route("/hello/<string:name>")
def get_name(name):
    return hello(name)

