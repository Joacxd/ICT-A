import os
import subprocess
import sys

port = os.environ.get("PORT", "8000")

# Inicializar BD
subprocess.run([sys.executable, "scripts/init_db.py"], check=True)

# Iniciar gunicorn
subprocess.run([
    sys.executable, "-m", "gunicorn",
    "api.app:app",
    "--bind", f"0.0.0.0:{port}",
    "--workers", "2"
], check=True)