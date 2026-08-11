# AI Curriculum Companion

AI Curriculum Companion is a Flask-based Python project that serves as a crucial evaluator for learning materials for DRC curriculum.

## Features

- Flask API
- Simple hello route
- Query parameter support

## Getting started

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install flask
```

### Run the app

On Windows:

```bash
set FLASK_APP=backend.main
flask run
```

On macOS/Linux:

```bash
export FLASK_APP=backend.main
flask run
```

Then open:

```text
http://127.0.0.1:5000/
```

## Example routes

- `/` returns a simple welcome page
- `/hello?name=YourName` returns a personalized greeting

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
