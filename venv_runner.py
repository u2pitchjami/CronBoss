#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

# 📂 1. Script cible à exécuter
target_script = Path(sys.argv[1])
args = sys.argv[2:]

# 📂 2. Racine du projet = dossier parent jusqu'à "bin/brain_ops"
# (à adapter si l'organisation change)
for parent in target_script.parents:
    if parent.name == "bin":
        project_root = parent
        break
else:
    print("❌ Impossible de détecter automatiquement le projet (pas de 'bin')")
    sys.exit(1)


# 🐍 3. Environnement virtuel fixe
venv_path = Path("/home/pipo/bin/.venv-run")

# 🌐 4. Préparation de l'environnement
env = os.environ.copy()
env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"

# 📦 5. Construction de la commande
cmd = [str(venv_path / "bin" / "python"), str(target_script)] + args

# 🏁 6. Lancement dans le bon dossier
subprocess.run(cmd, env=env, cwd=target_script.parent)
