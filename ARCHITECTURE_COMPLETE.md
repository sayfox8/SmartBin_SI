# 🏗️ Architecture Complète - SmartBin SI v3

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                     🎯 SMARTBIN SI v3                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  COUCHE CAPTEURS                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Caméra (USB/CSI) → YOLO v5 → Détection Objets       │  │
│  │ Arduino → État Moteur/Capteurs                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                    ↓                                         │
│  COUCHE MÉTIER                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ waste_classifier.py                                 │  │
│  │  • get_bin_color(objet) → détermine bac            │  │
│  │  • classify_and_sort(objet) → classe + log         │  │
│  │  • send_sort_command(bac) → envoie à Arduino       │  │
│  │  • log_detection() → enregistre détection          │  │
│  └──────────────────────────────────────────────────────┘  │
│                    ↓                                         │
│  COUCHE PERSISTANCE                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SQLite Database (waste_items.db)                    │  │
│  │  • Table: waste_classification (objet → bac)       │  │
│  │  • Table: sorting_history (détections + log)       │  │
│  │  • Table: bin_status (état 3 bacs)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                    ↓                                         │
│  COUCHE API                                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Flask REST APIs (app.py)                            │  │
│  │  • /api/bins/status → état bacs                    │  │
│  │  • /api/bins/history → détections                  │  │
│  │  • /api/bins/empty/<color> → vider                 │  │
│  │  • /api/waste/classify → classifier manuellement   │  │
│  │  • /api/system/info → infos système                │  │
│  │  • /api/gpu/info → infos GPU                       │  │
│  │  • /api/scripts/* → gestion scripts               │  │
│  └──────────────────────────────────────────────────────┘  │
│                    ↓                                         │
│  COUCHE PRÉSENTATION                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Web Interface (HTML/CSS/JavaScript)                 │  │
│  │  • Onglet Accueil: Système + Équipements          │  │
│  │  • Onglet Bacs: État remplissage + vidage         │  │
│  │  • Onglet Détections: Historique 50 items         │  │
│  │  • Onglet Scripts: Gestion lancement/arrêt        │  │
│  │  • Polling: 5-10 sec pour mise à jour             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flux de Données Complet

### Scenario: Un objet est détecté

```
1. CAMÉRA
   └─ Capture image
       └─ Envoie à YOLO

2. YOLO DETECTOR
   └─ Analyse image
       └─ Détecte "plastic_bottle"
           └─ Confiance: 0.92
               └─ Envoie à waste_classifier

3. WASTE CLASSIFIER (src/waste_classifier.py)
   └─ get_bin_color("plastic_bottle")
       ├─ Cherche en DB (√ trouvé)
       └─ Retourne "yellow"
           └─ classify_and_sort()
               ├─ log_detection("yellow", "plastic_bottle", 0.92)
               │   └─ Enregistre dans sorting_history
               │       └─ Incrémente bin_status (fill_level, item_count)
               └─ send_sort_command("yellow")
                   └─ Envoie à Arduino
                       └─ Moteur trie vers bac jaune

4. BASE DE DONNÉES (SQLite)
   ├─ sorting_history: +1 ligne
   │   └─ id=42, bin_color='yellow', item='plastic_bottle',
   │       timestamp='2026-01-31T14:32:15', confidence=0.92
   └─ bin_status: update
       └─ yellow: fill_level += 0.5, item_count += 1
           └─ De: 4.5L, 20 items
               └─ À: 5.0L, 21 items

5. FLASK API (admin_interface/app.py)
   └─ GET /api/bins/status
       └─ Lit bin_status
           └─ Retourne état actuel
               └─ yellow: fill_percent=50%, item_count=21

6. WEB INTERFACE (JavaScript)
   └─ updateBinsStatus() poll toutes 5 sec
       └─ Fetch /api/bins/status
           └─ Met à jour barre progress
               └─ 50% rouge si alert
           └─ updateDetectionsHistory()
               └─ Affiche new row dans table "Détections"

7. UTILISATEUR
   └─ Voit bac jaune à 50% en temps réel
       └─ Voit "plastic_bottle → yellow (92%)" dans historique
           └─ Peut cliquer "Vider" si besoin
```

---

## 🗄️ Schéma Base de Données

### Table 1: `waste_classification`
Mapping objet → bac (apprentissage)

```sql
CREATE TABLE waste_classification (
    item_name TEXT PRIMARY KEY,           -- 'plastic_bottle'
    bin_color TEXT NOT NULL,              -- 'yellow'
    created_at TEXT,                      -- '2026-01-31T14:32:15'
    usage_count INTEGER DEFAULT 1         -- 42
);
```

Exemple:
```
plastic_bottle   | yellow | 2026-01-31T... | 42
glass            | yellow | 2026-01-31T... | 18
banana_peel      | green  | 2026-01-31T... | 35
```

### Table 2: `sorting_history`
Historique complet des détections

```sql
CREATE TABLE sorting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 1, 2, 3, ...
    bin_color TEXT NOT NULL,               -- 'yellow'
    item_name TEXT,                        -- 'plastic_bottle'
    timestamp TEXT NOT NULL,               -- '2026-01-31T14:32:15.123456'
    confidence REAL DEFAULT 1.0            -- 0.92
);
```

Exemple:
```
1 | yellow | plastic_bottle | 2026-01-31T14:32:15 | 0.92
2 | green  | banana_peel    | 2026-01-31T14:31:42 | 0.88
3 | yellow | paper          | 2026-01-31T14:30:18 | 0.85
```

### Table 3: `bin_status`
État actuel des 3 bacs

```sql
CREATE TABLE bin_status (
    bin_color TEXT PRIMARY KEY,            -- 'yellow'
    fill_level REAL DEFAULT 0.0,           -- 5.2 (litres)
    item_count INTEGER DEFAULT 0,          -- 21 (nombre items)
    last_emptied TEXT,                     -- '2026-01-31T08:00:00'
    capacity_liters REAL DEFAULT 10.0      -- 10.0
);
```

Exemple:
```
yellow | 5.2  | 21 | 2026-01-31T08:00:00 | 10.0
green  | 1.8  | 8  | 2026-01-30T16:00:00 | 10.0
brown  | 4.5  | 16 | 2026-01-31T10:30:00 | 10.0
```

---

## 📡 APIs Détaillées

### 1. GET /api/bins/status

**Retourne**: État des 3 bacs

```json
{
  "success": true,
  "bins": [
    {
      "color": "yellow",
      "fill_level": 5.2,
      "fill_percent": 52.0,
      "item_count": 21,
      "capacity_liters": 10.0,
      "last_emptied": "2026-01-31T08:00:00",
      "needs_emptying": false
    },
    {
      "color": "green",
      "fill_level": 1.8,
      "fill_percent": 18.0,
      "item_count": 8,
      "capacity_liters": 10.0,
      "last_emptied": "2026-01-30T16:00:00",
      "needs_emptying": false
    },
    {
      "color": "brown",
      "fill_level": 4.5,
      "fill_percent": 45.0,
      "item_count": 16,
      "capacity_liters": 10.0,
      "last_emptied": "2026-01-31T10:30:00",
      "needs_emptying": false
    }
  ],
  "timestamp": "2026-01-31T14:35:00.123456"
}
```

**Polling**: Toutes les 5 secondes

### 2. GET /api/bins/history?limit=50

**Retourne**: 50 dernières détections

```json
{
  "success": true,
  "history": [
    {
      "bin_color": "yellow",
      "item_name": "plastic_bottle",
      "timestamp": "2026-01-31T14:32:15.123456",
      "confidence": 0.92
    },
    {
      "bin_color": "green",
      "item_name": "banana_peel",
      "timestamp": "2026-01-31T14:31:42.654321",
      "confidence": 0.88
    }
  ],
  "count": 2
}
```

**Polling**: Toutes les 10 secondes

### 3. POST /api/bins/empty/<bin_color>

**Exemple**: `POST /api/bins/empty/yellow`

**Retourne**:
```json
{
  "success": true,
  "message": "Bac yellow vidé avec succès",
  "bin_color": "yellow",
  "timestamp": "2026-01-31T14:35:15.123456"
}
```

**Effet**: 
- fill_level = 0
- item_count = 0
- last_emptied = now()

### 4. POST /api/waste/classify

**Body**:
```json
{
  "item_name": "plastic_bottle",
  "confidence": 0.95,
  "auto_mode": true
}
```

**Retourne**:
```json
{
  "success": true,
  "item_name": "plastic_bottle",
  "bin_color": "yellow",
  "timestamp": "2026-01-31T14:35:20.123456"
}
```

---

## 🔌 Modules et Dépendances

### `src/waste_classifier.py` (270 lignes)
**Responsabilité**: Gestion DB + Classification + Arduino

**Fonctions clés**:
```python
init_database()                  # Crée 3 tables
init_serial_connection()         # Ouvre Arduino (ou simulation)
get_bin_color(item)              # Détermine le bac
classify_and_sort(item, ...)     # Classe + log + Arduino
log_detection(color, item, ...)  # Enregistre détection
get_bin_status()                 # État des 3 bacs
empty_bin(color)                 # Vide un bac
get_detection_history(limit)     # Historique
get_stats()                       # Stats apprentissage
```

### `src/yolo_detector.py` (538 lignes)
**Responsabilité**: Détection YOLO + caméra

**Utilise**: 
- `torch.hub.load()` pour charger modèle
- `cv2.VideoCapture()` pour caméra
- `waste_classifier.classify_and_sort()` pour tri

### `admin_interface/app.py` (450+ lignes)
**Responsabilité**: APIs REST Flask

**Routes**:
- `GET /api/system/info` → psutil
- `GET /api/gpu/info` → nvidia-ml-py
- `GET /api/bins/status` → waste_classifier
- `GET /api/bins/history` → waste_classifier
- `POST /api/bins/empty/<color>` → waste_classifier
- `POST /api/waste/classify` → waste_classifier
- `GET /api/scripts/status` → subprocess
- `GET/POST /api/scripts/run/<script>` → subprocess
- `GET/POST /api/scripts/stop/<script>` → subprocess

### `admin_interface/static/script.js` (450+ lignes)
**Responsabilité**: UI interactif + Polling

**Polling**:
- System info: 5 sec
- GPU info: 3 sec
- **Bins status: 5 sec** ✨ NOUVEAU
- **Detections history: 10 sec** ✨ NOUVEAU
- Scripts status: 2 sec

---

## 🔄 Cycles de Mise à Jour

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│ BOUCLE PRINCIPALE (S'exécute en continu)          │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ T=0s     : Caméra capture + YOLO détecte          │
│           └─ Si objet détecté → waste_classifier   │
│                └─ DB mise à jour                    │
│                                                     │
│ T=2s     : Polling scripts status                 │
│                                                     │
│ T=3s     : Polling GPU info                       │
│                                                     │
│ T=5s     : Polling system info                    │
│           Polling bins status                      │
│           └─ UI affiche barre remplissage          │
│                                                     │
│ T=10s    : Polling detections history             │
│           └─ UI affiche nouvelle ligne tableau     │
│                                                     │
│ T=15s    : (répète de T=0s)                       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Améliorations Apportées (Avant → Après)

### Avant
- ❌ Données système uniquement (pas de bacs)
- ❌ Aucune persistance
- ❌ Aucun historique
- ❌ Pas de DB
- ❌ Interface purement statique

### Après
- ✅ **Système COMPLET**
- ✅ **SQLite 3 tables** (classification, historique, status)
- ✅ **50 détections** en historique
- ✅ **État bacs** en temps réel
- ✅ **Vidage** avec reset
- ✅ **Classification** manuelle via API
- ✅ **Polling** automatique
- ✅ **Alerts** si bac > 80%
- ✅ **Logs** horodatés

---

## 📊 Performance

| Opération | Temps | Notes |
|-----------|-------|-------|
| Init DB | < 100ms | Une seule fois au démarrage |
| get_bin_color() | < 5ms | Accès DB rapide |
| log_detection() | < 10ms | Insert + update rapide |
| Fetch /api/bins/status | < 50ms | Lecture DB simple |
| UI update | < 100ms | DOM manipulation rapide |
| Flask startup | < 1s | Avec debug=True |

---

## 🔐 Limitations Connues

1. **Pas de WiFi**: SQLite sur disque local (vérifier accès réseau NAS)
2. **Pas d'authentification**: Interface accessible à tous (ajouter Flask-Login si besoin)
3. **Pas de HTTPS**: Développement local (ajouter SSL en production)
4. **Pas de backup auto**: Ajouter cronjob pour backup DB
5. **Arduino simulation**: Sans Arduino, tri = simulation

---

## 🚀 Roadmap

- [ ] Webhooks pour alertes externes
- [ ] GraphQL API alternative
- [ ] Grafana dashboard
- [ ] SMS/Email notifications
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Tests unitaires
- [ ] Authentification JWT

---

**Architecture finalisée le**: 31 janvier 2026  
**Créée par**: FlowGameStudio  
**Version**: 3.0 - Système Complet
