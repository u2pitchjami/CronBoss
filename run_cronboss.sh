#!/bin/bash

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "❌ Le venv n'existe pas. Lancez d'abord : ./install_env.sh"
  exit 1
fi

source "$VENV_DIR/bin/activate"
python cronboss.py
