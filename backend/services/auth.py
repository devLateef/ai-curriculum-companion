from flask import render_template
def home():
    return render_template("landing.html")

def hello(name):
    return f"Nice to meet you {name}"