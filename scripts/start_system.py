#!/usr/bin/env python3
"""
Smart Bin SI - Démarrage Complet du Système
Initialise la DB, lance Flask, prépare tous les composants
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADMIN_INTERFACE = ROOT / "admin_interface"
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"


def run_command(cmd, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n[*] {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[✓] {description}: OK")
            return True
        else:
            print(f"[✗] {description}: ERREUR")
            if result.stderr:
                print(f"    {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[✗] {description}: {e}")
        return False


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "SMART BIN SI - DÉMARRAGE SYSTÈME" + " "*16 + "║")
    print("╚" + "="*58 + "╝")
    
    # 1. Créer répertoires
    print("\n[*] Création des répertoires...")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "logs").mkdir(exist_ok=True)
    (ROOT / "data" / "exports").mkdir(exist_ok=True)
    (ROOT / "data" / "training_images").mkdir(exist_ok=True)
    print("[✓] Répertoires créés")
    
    # 2. Initialiser base de données
    print("\n[*] Initialisation de la base de données...")
    try:
        sys.path.insert(0, str(SRC))
        import waste_classifier
        waste_classifier.init_database()
        waste_classifier.cleanup()
        print("[✓] Base de données initialisée")
    except Exception as e:
        print(f"[✗] Erreur DB: {e}")
    
    # 3. Installer/Vérifier dépendances
    print("\n[*] Vérification des dépendances...")
    deps_ok = True
    for pkg in ["flask", "psutil", "nvidia-ml-py3"]:
        result = subprocess.run(
            f"{sys.executable} -m pip show {pkg}",
            shell=True, capture_output=True
        )
        if result.returncode == 0:
            print(f"[✓] {pkg} installé")
        else:
            print(f"[⚠] {pkg} non trouvé")
            deps_ok = False
    
    if not deps_ok:
        print("\n[*] Installation des dépendances manquantes...")
        subprocess.run(
            f"{sys.executable} -m pip install flask psutil nvidia-ml-py3",
            shell=True
        )
    
    # 4. Lancer Flask
    print("\n" + "="*60)
    print("[*] Lancement du serveur Flask...")
    print("[*] Interface disponible à: http://localhost:5000")
    print("="*60 + "\n")
    
    try:
        subprocess.run(
            [sys.executable, str(ADMIN_INTERFACE / "app.py")],
            cwd=str(ADMIN_INTERFACE)
        )
    except KeyboardInterrupt:
        print("\n\n[*] Arrêt du système demandé")
    except Exception as e:
        print(f"[✗] Erreur: {e}")


if __name__ == "__main__":
    main()
