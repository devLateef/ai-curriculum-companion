from flask import render_template
from markupsafe import escape
def home():
    return render_template("landing.html")

def hello(name):
    return f"Nice to meet you {escape(name)}"