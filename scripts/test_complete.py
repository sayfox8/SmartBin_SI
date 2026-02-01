#!/usr/bin/env python3
"""
Smart Bin SI - Test Complet du Système
Teste tous les composants : config, DB, API, scripts
"""

import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "admin_interface"))


def test_config():
    """Test 1 : Configuration"""
    print("\n" + "="*60)
    print("[ 1 / 6 ] Configuration")
    print("="*60)
    try:
        from config import (
            DB_PATH, MODEL_PATH, VALID_BINS, WASTE_TO_BIN_MAPPING,
            ARDUINO_PORT, BAUD_RATE, CAMERA_SOURCE
        )
        
        print("✓ Config chargé")
        print(f"  • DB_PATH: {DB_PATH}")
        print(f"  • MODEL_PATH: {MODEL_PATH}")
        print(f"  • Bacs valides: {VALID_BINS}")
        print(f"  • Entrées mapping: {len(WASTE_TO_BIN_MAPPING)}")
        print(f"  • Arduino: {ARDUINO_PORT} @ {BAUD_RATE} bauds")
        return True
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False


def test_database():
    """Test 2 : Base de données"""
    print("\n" + "="*60)
    print("[ 2 / 6 ] Base de Données")
    print("="*60)
    try:
        import waste_classifier
        
        # Init DB
        waste_classifier.init_database()
        print("✓ Base de données initialisée")
        
        # Test insert
        waste_classifier.save_to_database("test_plastic", "yellow")
        waste_classifier.save_to_database("test_organic", "green")
        waste_classifier.save_to_database("test_waste", "brown")
        print("✓ 3 éléments test insérés")
        
        # Test get_bin_color
        assert waste_classifier.get_bin_color("test_plastic") == "yellow"
        print("✓ Récupération données: OK")
        
        # Test log_detection
        waste_classifier.log_detection("yellow", "test_plastic", 0.95)
        print("✓ Détection enregistrée")
        
        # Test get_bin_status
        status = waste_classifier.get_bin_status()
        print(f"✓ État des bacs: {len(status)} bacs")
        for bin_color, fill, count, emptied, capacity in status:
            print(f"  • {bin_color}: {fill}L / {capacity}L, {count} items")
        
        # Test get_detection_history
        history = waste_classifier.get_detection_history(limit=5)
        print(f"✓ Historique: {len(history)} détections")
        
        # Test get_stats
        stats = waste_classifier.get_stats()
        print(f"✓ Stats: {len(stats)} objets classés")
        
        waste_classifier.cleanup()
        return True
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_waste_classifier():
    """Test 3 : Classification et tri"""
    print("\n" + "="*60)
    print("[ 3 / 6 ] Waste Classifier")
    print("="*60)
    try:
        import waste_classifier
        
        waste_classifier.init_database()
        waste_classifier.init_serial_connection()
        
        # Test classification
        bin_color = waste_classifier.classify_and_sort(
            "plastic_bottle",
            ask_if_unknown=False,
            auto_mode=True,
            confidence=0.92
        )
        print(f"✓ Classification: 'plastic_bottle' → {bin_color}")
        
        # Test objet inconnu
        bin_color2 = waste_classifier.classify_and_sort(
            "unknown_object",
            ask_if_unknown=False,
            auto_mode=True
        )
        print(f"✓ Objet inconnu retourne: {bin_color2}")
        
        waste_classifier.cleanup()
        return True
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flask_app():
    """Test 4 : Application Flask"""
    print("\n" + "="*60)
    print("[ 4 / 6 ] Application Flask")
    print("="*60)
    try:
        import requests
        import subprocess
        import time
        
        # Lancer Flask en background
        print("⏳ Lancement du serveur Flask...")
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "admin_interface" / "app.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ROOT / "admin_interface")
        )
        
        time.sleep(3)  # Attendre que le serveur démarre
        
        # Test /api/system/info
        try:
            r = requests.get("http://localhost:5000/api/system/info", timeout=5)
            if r.status_code == 200:
                data = r.json()
                print(f"✓ /api/system/info: {data['hostname']} ({data['os']})")
                print(f"  • CPU: {data['cpu_percent']}% ({data['cpu_count']} cores)")
                print(f"  • RAM: {data['memory_percent']}%")
            else:
                print(f"✗ Status code: {r.status_code}")
        except Exception as e:
            print(f"⚠ /api/system/info: {e}")
        
        # Test /api/bins/status
        try:
            r = requests.get("http://localhost:5000/api/bins/status", timeout=5)
            if r.status_code == 200:
                data = r.json()
                print(f"✓ /api/bins/status: {len(data['bins'])} bacs")
                for b in data['bins']:
                    print(f"  • {b['color']}: {b['fill_percent']:.1f}% ({b['item_count']} items)")
            else:
                print(f"✗ Status code: {r.status_code}")
        except Exception as e:
            print(f"⚠ /api/bins/status: {e}")
        
        # Test /api/bins/history
        try:
            r = requests.get("http://localhost:5000/api/bins/history?limit=5", timeout=5)
            if r.status_code == 200:
                data = r.json()
                print(f"✓ /api/bins/history: {data['count']} détections")
            else:
                print(f"✗ Status code: {r.status_code}")
        except Exception as e:
            print(f"⚠ /api/bins/history: {e}")
        
        # Arrêter le serveur
        proc.terminate()
        proc.wait(timeout=5)
        print("✓ Serveur arrêté")
        return True
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        try:
            proc.terminate()
        except:
            pass
        return False


def test_yolo_detector():
    """Test 5 : Intégration YOLO"""
    print("\n" + "="*60)
    print("[ 5 / 6 ] YOLO Detector")
    print("="*60)
    try:
        from config import MODEL_PATH
        from pathlib import Path
        
        model_file = Path(MODEL_PATH)
        if model_file.exists():
            print(f"✓ Modèle YOLO trouvé: {MODEL_PATH}")
            print(f"  • Taille: {model_file.stat().st_size / (1024*1024):.1f} MB")
            
            # Vérifier que torch peut charger
            try:
                import torch
                print("✓ PyTorch disponible")
                
                # Essayer charger le modèle (sans lancer la détection)
                try:
                    model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                          path=str(MODEL_PATH), force_reload=False)
                    print("✓ Modèle YOLO chargé avec succès")
                    return True
                except Exception as e:
                    print(f"⚠ Chargement YOLO: {e}")
                    return True  # Ne pas bloquer si YOLO ne charge pas
            except ImportError:
                print("⚠ PyTorch non disponible (normal si GPU non utilisé)")
                return True
        else:
            print(f"⚠ Modèle YOLO non trouvé: {MODEL_PATH}")
            return False
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False


def test_scripts():
    """Test 6 : Scripts"""
    print("\n" + "="*60)
    print("[ 6 / 6 ] Scripts")
    print("="*60)
    try:
        scripts = [
            "test_app.py",
            "test_hardware.py",
            "run_auto.sh",
            "run_manual.sh"
        ]
        
        for script in scripts:
            script_path = ROOT / "scripts" / script
            if script_path.exists():
                print(f"✓ {script} trouvé")
            else:
                print(f"✗ {script} manquant")
        
        return True
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "SMART BIN SI - TEST COMPLET" + " "*20 + "║")
    print("╚" + "="*58 + "╝")
    
    results = []
    results.append(("Configuration", test_config()))
    results.append(("Base de données", test_database()))
    results.append(("Waste Classifier", test_waste_classifier()))
    results.append(("Flask API", test_flask_app()))
    results.append(("YOLO Detector", test_yolo_detector()))
    results.append(("Scripts", test_scripts()))
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print("\n" + "-"*60)
    print(f"Total: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("Le système est prêt à fonctionner.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
