"""Entry point for the analysis API.

    ./venv/bin/python main.py                 # localhost:5000
    HOST=0.0.0.0 PORT=8000 python main.py     # bind elsewhere
    FLASK_DEBUG=1 python main.py              # autoreload while editing

Debug defaults to OFF. Werkzeug's reloader runs the module in two processes,
which means two model clients and two database handles on a machine with a tight
memory budget -- an accidental doubling of the footprint the design is built
around.
"""

import os

from src.app import app

__all__ = ["app"]

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
        threaded=True,  # sufficient for the single-user, localhost case
    )
