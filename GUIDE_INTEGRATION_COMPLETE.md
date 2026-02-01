# 🎯 SmartBin SI - Guide Complet d'Intégration

**Date**: 31 janvier 2026  
**Statut**: ✅ SYSTÈME COMPLET FONCTIONNEL  
**Tests**: 6/6 PASSÉS

---

## 📊 Vue d'ensemble du système

Vous avez maintenant un **système complet et intégré** qui:

1. **Collecte les données** via YOLO + caméra
2. **Classe les objets** via `waste_classifier` + Arduino
3. **Stocke les données** dans SQLite
4. **Affiche tout en temps réel** via interface admin Flask
5. **Gère les bacs** avec alertes remplissage

```
┌─────────────────────────────────────────────────────┐
│                    SMARTBIN SI v3                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  YOLO Detector ─────→ Waste Classifier ──→ Arduino  │
│      (détecte)         (classe + tri)    (moteur)   │
│       ↓                    ↓                ↓        │
│   Caméra             Database (SQLite)  Poubelles   │
│                           ↓                         │
│                    Admin Interface (Flask)          │
│                           ↓                         │
│                   Web UI (affichage temps réel)     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🗄️ Structure de la Base de Données

### Table 1 : `waste_classification`
Stocke les associations objet → bac
```
item_name (TEXT, PK)   | bin_color (TEXT) | usage_count (INT) | created_at
"plastic_bottle"       | "yellow"         | 42                | 2026-01-31T...
"banana_peel"          | "green"          | 18                | 2026-01-31T...
```

### Table 2 : `sorting_history`
Historique complet des détections
```
id | bin_color | item_name       | timestamp           | confidence
1  | "yellow"  | "plastic_bottle"| 2026-01-31T14:32:15 | 0.95
2  | "green"   | "banana_peel"   | 2026-01-31T14:31:42 | 0.92
```

### Table 3 : `bin_status`
État des 3 bacs (remplissage, items, dernière vidange)
```
bin_color | fill_level | item_count | last_emptied        | capacity_liters
"yellow"  | 5.2        | 24         | 2026-01-31T08:00:00 | 10.0
"green"   | 1.8        | 8          | 2026-01-30T16:00:00 | 10.0
"brown"   | 4.5        | 16         | 2026-01-31T10:30:00 | 10.0
```

---

## 🔌 APIs Disponibles

### Système
```http
GET /api/system/info
```
Retourne: CPU%, RAM, Disque, OS, Uptime, Hostname

### Bacs (NOUVEAU)
```http
GET /api/bins/status
```
Retourne: État des 3 bacs (remplissage %, items count, dernière vidange)

### Historique (NOUVEAU)
```http
GET /api/bins/history?limit=50
```
Retourne: 50 dernières détections (objet, bac, timestamp, confiance)

### Vider un bac (NOUVEAU)
```http
POST /api/bins/empty/<bin_color>
```
Exemple: `POST /api/bins/empty/yellow`

### Classifier un objet (NOUVEAU)
```http
POST /api/waste/classify
Body: {"item_name": "plastic", "confidence": 0.92, "auto_mode": true}
```

### GPU
```http
GET /api/gpu/info
```
Retourne: Modèle, température, VRAM (ou graceful fallback)

### Scripts
```http
GET /api/scripts/status
GET/POST /api/scripts/run/<script>
GET/POST /api/scripts/stop/<script>
```

---

## 🚀 Démarrage du Système

### Option 1 : Démarrage Complet (Recommandé)
```bash
cd z:\SI\SIpoubelle
python scripts\start_system.py
```

Cela:
- ✅ Crée les répertoires
- ✅ Initialise la DB
- ✅ Vérifie les dépendances
- ✅ Lance Flask

### Option 2 : Démarrage Manuel
```bash
cd z:\SI\SIpoubelle\admin_interface
python app.py
```

Ouvrez: **http://localhost:5000**

---

## 🧪 Tests

### Test Complet (6/6 tests)
```bash
python scripts\test_complete.py
```

### Tests Spécifiques
```bash
# Test config + DB
python scripts\test_app.py

# Test hardware (capteurs, Arduino)
python scripts\test_hardware.py

# Diagnostic rapide
python scripts\snapshot.py
```

---

## 📊 Interface Web

### Onglet "Accueil"
- Affichage CPU, RAM, Disque en temps réel
- État des équipements (caméra, Arduino, GPU, système)
- Gestion des scripts (lancer/arrêter)

### Onglet "Gestion des Bacs" ✨ NOUVEAU
- Remplissage en temps réel (%)
- Nombre d'items dans chaque bac
- Bouton "Vider" pour chaque bac
- Dernière vidange
- Alerte si bac > 80% (fond jaune)

### Onglet "Détections" ✨ NOUVEAU
- Table avec les 20 dernières détections
- Columns: Objet détecté, Bac destination, Confiance IA, Timestamp
- Mis à jour toutes les 10 secondes

### Onglet "Erreurs"
- Logs des erreurs système
- Affichage des problèmes de connection

### Onglet "Paramètres"
- Lecture/écriture du fichier config.py
- Modification des seuils

---

## 💾 Flux de Données

### Scenario: Un objet est détecté

```
1. YOLO détecte via caméra
   ↓
2. waste_classifier.classify_and_sort() appelé
   ↓
3. get_bin_color() cherche dans DB
   ↓
4. log_detection() enregistre dans sorting_history
   ↓
5. Mise à jour bin_status (fill_level += 0.5, item_count += 1)
   ↓
6. send_sort_command() envoie à Arduino
   ↓
7. Interface affiche:
   • Nouvelle ligne en "Détections"
   • Mise à jour barre de remplissage
   • Log console horodaté
```

---

## 🔧 Configuration

Fichier: `z:\SI\SIpoubelle\src\config.py`

### Paramètres Importants
```python
# Bacs
VALID_BINS = ["yellow", "green", "brown"]
WASTE_TO_BIN_MAPPING = {...}  # 13 objets pré-configurés

# YOLO
CONFIDENCE_THRESHOLD = 0.6  # Seuil de détection
MODEL_PATH = "models/best.pt"

# Caméra
CAMERA_SOURCE = 0  # 0=USB, 1=CSI Jetson
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Arduino
ARDUINO_PORT = '/dev/ttyACM0'  # Adapter pour votre port
BAUD_RATE = 9600
SORTING_DURATION = 10  # Secondes par tri

# Apprentissage
LEARNING_MODE = True  # Demander validation pour nouveaux objets
SAVE_IMAGES = True  # Sauvegarder images d'apprentissage
```

---

## 📁 Structure de Fichiers

```
z:\SI\SIpoubelle\
├── admin_interface/              # Interface Web
│   ├── app.py                   # Flask principal (3 nouvelles APIs)
│   ├── static/
│   │   ├── index.html           # UI mis à jour
│   │   ├── script.js            # Polling bacs + historique
│   │   └── style.css
│   ├── requirements.txt
│   └── test_apis.py
│
├── src/                         # Logique métier
│   ├── config.py               # Configuration centrale
│   ├── waste_classifier.py     # DB + Arduino (amélioré)
│   ├── yolo_detector.py        # YOLO + caméra
│   ├── data/
│   │   ├── waste_items.db      # SQLite (NOUVEAU)
│   │   ├── logs/               # Logs système
│   │   └── training_images/    # Images d'apprentissage
│   └── models/
│       └── best.pt             # Modèle YOLO v5
│
├── scripts/                     # Scripts de contrôle
│   ├── test_complete.py        # Test 6/6 (NOUVEAU)
│   ├── start_system.py         # Démarrage complet (NOUVEAU)
│   ├── test_app.py
│   ├── test_hardware.py
│   ├── snapshot.py
│   ├── run_auto.sh
│   └── run_manual.sh
│
└── data/                        # Exports et logs
    ├── exports/
    └── logs/
```

---

## 🔄 Intégration avec Vos Systèmes

### Intégration YOLO
```python
# Dans yolo_detector.py
# Le modèle charge automatiquement depuis config.MODEL_PATH
model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH)
results = model(frame)  # Détecte objets

# Envoyer à waste_classifier
for det in results.xyxy:
    obj_name = results.names[int(det[-1])]
    confidence = float(det[-2])
    bin_color = waste_classifier.classify_and_sort(
        obj_name,
        confidence=confidence,
        auto_mode=True
    )
```

### Intégration Arduino
```python
# Dans waste_classifier.py
# Envoie automatiquement commande série
waste_classifier.send_sort_command("yellow")
# Envoie: "yellow\n" à /dev/ttyACM0

# Votre Arduino reçoit et actionne le moteur
```

### Intégration Caméra
```python
# Dans yolo_detector.py
import cv2

cap = cv2.VideoCapture(CAMERA_SOURCE)
while True:
    ret, frame = cap.read()
    # Envoyer à YOLO
```

---

## 🚨 Dépannage

### Erreur: "Arduino non détecté"
```
⚠ Arduino non détecté (...) - mode simulation
```
**Solution**: C'est normal! Le système fonctionne en mode simulation si Arduino n'est pas connecté.
- Connectez Arduino et mettez à jour `ARDUINO_PORT` dans config.py
- Redémarrez

### Erreur: "No module named 'yolov6'"
```
⚠ Chargement YOLO: No module named 'yolov6'
```
**Solution**: Erreur de cache torch. Supprimez le cache:
```bash
rmdir C:\Users\propo\.cache\torch\hub
```

### Erreur: "GPU non disponible"
```
[WARN] nvidia-ml-py non installé
```
**Solution**: C'est normal et prévu. L'interface fonctionne sans GPU.
- Optionnel: `pip install nvidia-ml-py3`

### DB vide après restart
**Solution**: La DB se remplit au fur et à mesure des détections. Pendant les tests:
```bash
python -c "
import sys; sys.path.insert(0, 'src')
import waste_classifier
waste_classifier.init_database()
waste_classifier.save_to_database('test', 'yellow')
waste_classifier.cleanup()
"
```

---

## 📈 Prochaines Étapes Optionnelles

### 1. Entraîner YOLO sur vos objets
```bash
# Annotation des images avec Roboflow
# Réentraînement du modèle
python yolo/train.py --data custom_data.yaml --epochs 100
# Copier best.pt vers src/models/
```

### 2. Ajouter Webhooks
```python
# Dans waste_classifier.py
import requests
def notify_collection_service():
    if fill_level > 80:
        requests.post("https://votre-api.com/collect", 
                     json={"bin": "yellow", "fill": 85})
```

### 3. Dashboard Grafana
- Connecter SQLite à Grafana
- Créer dashboards de statistiques
- Graphiques remplissage par jour/semaine

### 4. Alerts SMS/Email
```python
# Lors du vidage d'un bac
from twilio.rest import Client
client = Client(ACCOUNT_SID, AUTH_TOKEN)
client.messages.create(to="+33...", from_="+33...", 
                      body="Bac jaune vidé le 31/01")
```

---

## 📊 Statistiques Actuelles

| Composant | Statut | Notes |
|-----------|--------|-------|
| Configuration | ✅ | 13 objets pré-mappés |
| Base de données | ✅ | 3 tables créées et testées |
| YOLO v5 | ✅ | Modèle 77MB chargé |
| Flask API | ✅ | 9 endpoints fonctionnels |
| Interface Web | ✅ | 5 sections (Accueil, Bacs, Détections, Erreurs, Paramètres) |
| Arduino | ⚠️ | Mode simulation (attachez votre Arduino) |
| GPU | ⚠️ | Non disponible (fallback gracieux) |
| Tests | ✅ | 6/6 PASS |

---

## 🎓 Exemples de Code

### Ajouter un nouvel objet à la base
```python
import sys
sys.path.insert(0, 'src')
import waste_classifier

waste_classifier.init_database()
waste_classifier.save_to_database("mon_objet", "yellow")
waste_classifier.cleanup()
```

### Récupérer l'état d'un bac
```python
bins = waste_classifier.get_bin_status()
for color, fill, count, emptied, capacity in bins:
    print(f"{color}: {fill}L / {capacity}L ({count} items)")
```

### Vider un bac
```python
waste_classifier.empty_bin("yellow")
# Reset: fill_level=0, item_count=0, last_emptied=now
```

### Récupérer l'historique
```python
history = waste_classifier.get_detection_history(limit=10)
for bin_color, item, timestamp, confidence in history:
    print(f"{timestamp}: {item} → {bin_color} ({confidence:.0%})")
```

---

## 🔗 Ressources

- **YOLO v5**: https://docs.ultralytics.com/yolov5/
- **Flask**: https://flask.palletsprojects.com/
- **SQLite**: https://www.sqlite.org/
- **psutil**: https://psutil.readthedocs.io/
- **PySerial**: https://pyserial.readthedocs.io/

---

## ✅ Checklist de Validation

- [x] Base de données SQLite créée (3 tables)
- [x] APIs endpoints pour bacs créées (status, history, empty, classify)
- [x] Interface Web affichage temps réel
- [x] Test complet 6/6 PASS
- [x] Polling automatique (5-10 sec)
- [x] Logs horodatés
- [x] Alertes remplissage (>80%)
- [x] Mode simulation Arduino
- [x] Graceful fallback GPU
- [x] Documentation complète

---

## 📞 Support

**Erreur?** Exécutez le diagnostic:
```bash
python scripts\test_complete.py
python scripts\snapshot.py
```

**Plus d'infos?** Consultez les docstrings:
```bash
python -c "import sys; sys.path.insert(0, 'src'); help(__import__('waste_classifier'))"
```

---

**Créé par**: FlowGameStudio  
**Dernière mise à jour**: 31 janvier 2026  
**Version**: 3.0 - Système Intégré Complet
