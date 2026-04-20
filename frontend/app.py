"""
Lightweight Flask frontend that serves the single-page annotation UI.
All data is fetched from the backend API via JavaScript.
"""
import os
from flask import Flask, render_template, send_from_directory

app = Flask(__name__)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")


@app.route("/")
@app.route("/<path:path>")
def index(path=""):
    return render_template("index.html", api_base_url=API_BASE_URL)


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
