# Contributing to AI Curriculum Companion

Thanks for your interest in contributing to this project. This guide explains how to set up the repository locally, make changes safely, and submit a pull request (PR).

## Code of conduct

Please be respectful, constructive, and professional in all interactions. Keep discussions focused on improving the project.

## Getting started

### Prerequisites

- Python 3.10+
- pip
- Git

### Clone the repository

```bash
git clone https://github.com/devLateef/ai-curriculum-companion.git
cd ai-curriculum-companion
```

### Create and activate a virtual environment

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install flask
```

## Running the app locally

From the project root, run:

```bash
set FLASK_APP=backend.main
flask run
```

If you are using PowerShell on Windows, use:

```powershell
$env:FLASK_APP = "backend.main"
flask run
```

## Contribution workflow

1. Fork the repository (if you do not have write access).
2. Create a new branch for your work:

    ```bash
    git checkout -b feature/your-change-name
    ```

3. Make your changes.
4. Test your changes locally.
5. Commit your work with a clear message:

    ```bash
    git add .
    git commit -m "Add your meaningful change"
    ```

6. Push to your branch:

    ```bash
    git push origin feature/your-change-name
    ```

7. Open a pull request on GitHub.

## Pull request guidelines

Please make sure your PR:

- has a clear title
- explains what changed and why
- includes relevant tests or validation steps
- keeps changes focused on a single purpose
- does not include unrelated files or debug code

## Suggested PR format

### Title

Use a short, descriptive title such as:

- Add Flask route for hello endpoint
- Improve contribution instructions
- Fix local setup issue

### Description

Include:

- summary of the change
- why the change is needed
- any testing you performed

## Coding style

- Write clear and readable Python code
- Follow standard Python naming conventions
- Keep functions and routes simple and easy to understand
- Avoid committing secrets or local environment files

## Before submitting

Please confirm that:

- your code runs locally
- your changes do not break existing behavior
- you have reviewed your diff carefully

Thank you for contributing to this project.
