#!/bin/bash
# DataEraser - Lanceur Mac/Linux
# Double-cliquer ou exécuter dans le terminal

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        DataEraser  🛡️               ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Vérifier Python
PY=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    VER=$("$cmd" -c "import sys; print(sys.version_info.major)")
    if [ "$VER" -ge 3 ]; then PY="$cmd"; break; fi
  fi
done

if [ -z "$PY" ]; then
  echo "❌ Python 3 non trouvé."
  echo ""
  echo "Installez-le depuis : https://www.python.org/downloads/"
  echo ""
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Sur Mac, vous pouvez aussi lancer :"
    echo "  brew install python"
  fi
  echo ""
  read -p "Appuyez sur Entrée pour fermer..."
  exit 1
fi

echo "✅ Python trouvé : $($PY --version)"
echo ""
echo "📦 Vérification de Flask..."

# Installer Flask si absent
if ! $PY -c "import flask" 2>/dev/null; then
  echo "   Installation de Flask..."
  $PY -m pip install flask --quiet --break-system-packages 2>/dev/null \
    || $PY -m pip install flask --quiet --user 2>/dev/null \
    || $PY -m pip install flask --quiet
fi

echo "✅ Flask OK"
echo ""
echo "🚀 Démarrage - le navigateur va s'ouvrir automatiquement"
echo "   Ctrl+C pour arrêter l'outil"
echo ""

$PY app.py
