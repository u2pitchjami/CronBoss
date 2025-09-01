#!/bin/bash

set -e

VENV_DIR=".venv"

echo "🔧 Installation de l’environnement Python..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python3 est requis mais non installé."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "📁 Création du venv dans $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "📦 Activation du venv et installation des dépendances..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Environnement prêt. Utilisez ./run_cron_hub.sh pour lancer l’application."
