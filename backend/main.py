from flask import Flask, request, render_template, abort
from markupsafe import escape
import os
from pathlib import Path
import logging
import sys

logging.basicConfig(level=logging.DEBUG, force=True)

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
app.logger.handlers.clear()
app.logger.addHandler(logging.StreamHandler())

@app.route('/')
def hello():
    return "<p>Hello, World!</p>"

@app.route("/hello/<string:name>")
def get_name(name):
    #name = request.args.get("name", "Flask")
    return f"Welcome to our platform {name}"

@app.route("/upload", methods = ['GET'])
def display_upload_form():
    print("hello tuetue")
    return render_template('index.html')

@app.route("/store", methods=["POST"])
def store_file():
    print(request.form.get("firstname"))
    return "Okay"
