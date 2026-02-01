#!/usr/bin/env python3
"""
Smart Bin SI - Simulateur de Détections
Simule des détections YOLO pour montrer le système en action
"""

import sys
import time
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*8 + "SMART BIN SI - SIMULATEUR DE DÉTECTIONS" + " "*11 + "║")
    print("╚" + "="*58 + "╝\n")
    
    try:
        import waste_classifier
        
        # Objets à détecter
        objects = [
            ("plastic_bottle", "yellow", 0.92),
            ("banana_peel", "green", 0.88),
            ("paper", "yellow", 0.85),
            ("food", "green", 0.90),
            ("cardboard", "yellow", 0.87),
            ("glass", "yellow", 0.95),
            ("organic", "green", 0.91),
            ("tissue", "brown", 0.89),
        ]
        
        # Initialiser DB
        waste_classifier.init_database()
        waste_classifier.init_serial_connection()
        
        print(f"[*] Base de données initialisée")
        print(f"[*] {len(objects)} types d'objets à détecter\n")
        
        # Simuler détections
        print(f"[*] Simulation de détections (5 secondes par détection)\n")
        print("-" * 60)
        
        for i in range(10):
            obj_name, expected_color, confidence = random.choice(objects)
            
            # Classification
            bin_color = waste_classifier.classify_and_sort(
                obj_name,
                ask_if_unknown=False,
                auto_mode=True,
                confidence=confidence
            )
            
            timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
            confidence_pct = int(confidence * 100)
            
            status = "✓" if bin_color else "✗"
            print(f"{status} [{timestamp}] Détection #{i+1}")
            print(f"    Objet: {obj_name}")
            print(f"    Bac: {bin_color}")
            print(f"    Confiance: {confidence_pct}%")
            print()
            
            time.sleep(5)
        
        print("-" * 60 + "\n")
        
        # Afficher état final des bacs
        print("[*] État final des bacs:\n")
        status = waste_classifier.get_bin_status()
        for color, fill, count, emptied, capacity in status:
            percent = (fill / capacity * 100) if capacity > 0 else 0
            bar_length = int(percent / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"  {color.upper():8} [{bar}] {percent:5.1f}% ({count} items, {fill:.1f}L)")
        
        print("\n[*] Historique des détections:\n")
        history = waste_classifier.get_detection_history(limit=10)
        for idx, (bin_color, item_name, timestamp, confidence) in enumerate(history[::-1], 1):
            confidence_pct = int(confidence * 100)
            print(f"  {idx:2}. {timestamp} → {item_name:20} → {bin_color:8} ({confidence_pct}%)")
        
        # Statistiques
        print("\n[*] Statistiques d'apprentissage:\n")
        stats = waste_classifier.get_stats()
        for item_name, bin_color, usage_count in stats:
            print(f"  {item_name:20} → {bin_color:8} ({usage_count} utilisations)")
        
        waste_classifier.cleanup()
        
        print("\n" + "="*60)
        print("✓ Simulation complétée avec succès!")
        print("="*60 + "\n")
        
        print("Vérifiez l'interface Web: http://localhost:5000")
        print("Onglet 'Détections' pour voir les données simulées\n")
        
    except KeyboardInterrupt:
        print("\n\n[*] Simulation arrêtée par l'utilisateur")
    except Exception as e:
        print(f"\n[✗] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
