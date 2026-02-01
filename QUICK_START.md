# ⚡ SmartBin SI - Quick Start (2 minutes)

## 1️⃣ Lancer le serveur (30 secondes)

```bash
cd z:\SI\SIpoubelle
python scripts\start_system.py
```

Vous verrez:
```
[*] Création des répertoires...
[✓] Répertoires créés
[*] Initialisation de la base de données...
[✓] Base de données initialisée
[*] Vérification des dépendances...
[*] Lancement du serveur Flask...
[*] Interface disponible à: http://localhost:5000
```

## 2️⃣ Ouvrir l'interface (10 secondes)

Ouvrez votre navigateur et allez à:
```
http://localhost:5000
```

## 3️⃣ Que voyez-vous?

### Onglet "Accueil"
- 📊 **Système**: CPU, RAM, Disque en temps réel
- 🖥️ **Équipements**: Caméra, Arduino, GPU, Système
- 🎮 **Scripts**: Lancer/arrêter les scripts

### Onglet "Gestion des Bacs" ✨ NOUVEAU
- 🟨 **Bac Jaune (Recyclage)**: Affiche remplissage %
- 🟩 **Bac Vert (Compost)**: Affiche remplissage %  
- 🟫 **Bac Marron (Général)**: Affiche remplissage %
- **Bouton "Vider"** pour chaque bac
- Alerte rouge si > 80%

### Onglet "Détections" ✨ NOUVEAU
- Table avec les **20 dernières détections**
- Colonnes: Objet, Bac destination, Confiance %, Timestamp
- Mise à jour toutes les 10 secondes

## 4️⃣ Tester avec des données simulées (1 minute)

Dans un **nouveau terminal**:
```bash
cd z:\SI\SIpoubelle
python scripts\simulate_detections.py
```

Vous verrez les bacs se remplir en temps réel dans l'interface! 

Chaque détection simulée:
- ✓ Ajoute 0.5L au bac
- ✓ Incrémente le compteur d'items
- ✓ Enregistre dans l'historique
- ✓ S'affiche dans "Détections"

## 5️⃣ Tester les APIs

### Récupérer l'état des bacs
```bash
curl http://localhost:5000/api/bins/status
```

Retourne:
```json
{
  "success": true,
  "bins": [
    {
      "color": "yellow",
      "fill_percent": 30.0,
      "item_count": 6,
      "needs_emptying": false
    }
  ]
}
```

### Récupérer l'historique
```bash
curl http://localhost:5000/api/bins/history
```

### Vider un bac
```bash
curl -X POST http://localhost:5000/api/bins/empty/yellow
```

### Classifier manuellement
```bash
curl -X POST http://localhost:5000/api/waste/classify \
  -H "Content-Type: application/json" \
  -d '{"item_name": "plastic_bottle", "confidence": 0.95}'
```

## ✨ C'est tout!

**Vous pouvez maintenant**:
- ✅ Voir l'état des bacs en temps réel
- ✅ Voir l'historique complet des détections
- ✅ Vider les bacs via l'interface
- ✅ Classifier manuellement des objets
- ✅ Accéder aux APIs directement

---

## 🔧 Commandes Utiles

| Commande | Description |
|----------|-------------|
| `python scripts\start_system.py` | Démarrer le serveur |
| `python scripts\test_complete.py` | Tests complets (6/6) |
| `python scripts\simulate_detections.py` | Simuler détections |
| `python scripts\snapshot.py` | Diagnostic système |
| `python scripts\test_app.py` | Test simple |

## 📋 Données Maintenant Stockées

- 🗄️ **Classification**: Quel bac pour quel objet
- 📊 **Historique**: Toutes les détections avec timestamp
- 🎯 **État bacs**: Remplissage, nombre items, dernière vidange
- 📈 **Statistiques**: Objets détectés, utilisation

## 🆘 Problème?

### Erreur: "Port 5000 déjà utilisé"
```bash
# Trouver et tuer le processus
taskkill /F /IM python.exe
```
Puis relancer `start_system.py`

### Erreur: "Arduino non détecté"
✅ Normal! Connectez votre Arduino et mettez à jour `config.py`

### Erreur: "Module not found"
```bash
pip install flask psutil nvidia-ml-py3
python scripts\start_system.py
```

### Vérifier que tout fonctionne
```bash
python scripts\test_complete.py  # Doit afficher: 6/6 PASS ✓
```

---

## 🎓 Exemples Pratiques

### Exemple 1: Vider le bac jaune via Web
1. Allez dans "Gestion des Bacs"
2. Cliquez "Vider maintenant" sur Bac Jaune
3. Confirmez
4. Remplissage revient à 0%

### Exemple 2: Voir les détections récentes
1. Allez dans "Détections"
2. Vous voyez les 20 dernières détections
3. Objet, Bac, Confiance %, Timestamp

### Exemple 3: Lancer un script
1. Allez dans "Accueil"
2. Cliquez "▶ Lancer" sur un script
3. Bouton devient gris (script en cours)
4. Cliquez "⊗ Stop" pour arrêter

---

## 📈 Ce qui s'est Passé

Avant:
- ❌ Interface affichait données statiques
- ❌ Pas de persistance
- ❌ Impossible voir remplissage bacs
- ❌ Aucun historique

Après:
- ✅ Données temps réel
- ✅ SQLite stocke tout
- ✅ Bacs affichent remplissage réel
- ✅ Historique 50 détections

---

## 🚀 Prochaines Étapes Optionnelles

1. **Connecter Arduino**: Tri automatique réel
2. **Connecter caméra**: YOLO détecte vrais objets
3. **Ajouter SMS**: Alerte quand bac plein
4. **Grafana**: Dashboard avancé

---

**C'est prêt!** Lancez `start_system.py` et profitez 🎉
