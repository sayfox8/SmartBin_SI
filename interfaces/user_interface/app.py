"""
SmartBin SI - Interface Utilisateur
Interface web pour affecter les objets détectés aux bacs
"""

from flask import Flask, jsonify, request, render_template, send_file
import uuid
from datetime import datetime
from pathlib import Path
import os

app = Flask(__name__, static_folder='static', template_folder='static')

# Stockage des tâches
tasks = {}
confirmations = {}
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / 'src'

try:
    from src.config import USER_INTERFACE_PORT, VALID_BINS
except Exception:
    USER_INTERFACE_PORT = 5001
    VALID_BINS = ['yellow', 'green', 'brown', 'black']

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/api/ask', methods=['POST'])
def ask():
    """
    Recevoir une question de classification
    {
        "item_name": "plastic_bottle",
        "image_path": "path/to/image.jpg"  (optionnel)
    }
    """
    data = request.get_json() or {}
    item_name = data.get('item_name')
    image_path = data.get('image_path')
    
    if not item_name:
        return jsonify({'success': False, 'error': 'item_name requis'}), 400
    
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'item_name': item_name,
        'image_path': image_path,
        'created': datetime.now().isoformat(),
        'answered': False,
        'bin_color': None
    }
    
    return jsonify({'success': True, 'task_id': task_id}), 202

@app.route('/api/tasks')
def list_tasks():
    """Lister les tâches en attente"""
    pending = []
    for task_id, task in tasks.items():
        if not task['answered']:
            pending.append({
                'task_id': task_id,
                'item_name': task['item_name'],
                'image_path': task['image_path'],
                'created': task['created']
            })
    
    return jsonify({'success': True, 'pending': pending})


@app.route('/api/confirm_tasks')
def list_confirmations():
    """Lister les demandes de confirmation en attente"""
    pending = []
    for confirm_id, conf in confirmations.items():
        if not conf['answered']:
            pending.append({
                'confirmation_id': confirm_id,
                'item_name': conf['item_name'],
                'bin_color': conf['bin_color'],
                'created': conf['created']
            })
    
    return jsonify({'success': True, 'pending': pending})

@app.route('/api/answer/<task_id>', methods=['GET', 'POST'])
def answer(task_id):
    """
    Get/Set answer for a task
    POST avec {"bin_color": "yellow"} ou None
    """
    task = tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'answered': task['answered'],
            'bin_color': task['bin_color']
        })
    
    data = request.get_json() or {}
    bin_color = data.get('bin_color')
    
    if bin_color is None:
        # Rejet
        task['answered'] = True
        task['bin_color'] = None
        return jsonify({'success': True, 'task_id': task_id, 'bin_color': None})
    
    if bin_color not in VALID_BINS:
        return jsonify({'success': False, 'error': 'Invalid bin'}), 400
    
    # Enregistrer la réponse
    task['answered'] = True
    task['bin_color'] = bin_color
    
    return jsonify({'success': True, 'task_id': task_id, 'bin_color': bin_color})

@app.route('/api/confirm', methods=['POST'])
def confirm():
    """
    Créer une demande de confirmation après le tri
    {
        "item_name": "plastic_bottle",
        "bin_color": "yellow"
    }
    """
    data = request.get_json() or {}
    item_name = data.get('item_name')
    bin_color = data.get('bin_color')
    
    if not item_name or not bin_color:
        return jsonify({'success': False, 'error': 'item_name et bin_color requis'}), 400
    
    confirmation_id = str(uuid.uuid4())
    confirmations[confirmation_id] = {
        'item_name': item_name,
        'bin_color': bin_color,
        'created': datetime.now().isoformat(),
        'answered': False,
        'confirmed': False
    }
    
    return jsonify({'success': True, 'task_id': confirmation_id}), 202

@app.route('/api/confirm/<confirmation_id>', methods=['GET', 'POST'])
def confirm_answer(confirmation_id):
    """
    Get/Set confirmation for a task
    POST avec {"confirmed": true/false}
    """
    confirmation = confirmations.get(confirmation_id)
    if not confirmation:
        return jsonify({'success': False, 'error': 'Confirmation not found'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'answered': confirmation['answered'],
            'confirmed': confirmation['confirmed']
        })
    
    data = request.get_json() or {}
    confirmed = data.get('confirmed', False)
    
    # Enregistrer la réponse
    confirmation['answered'] = True
    confirmation['confirmed'] = confirmed
    
    return jsonify({'success': True, 'task_id': confirmation_id, 'confirmed': confirmed})

@app.route('/api/image/<path:image_path>')
def serve_image(image_path):
    """Servir une image de détection"""
    try:
        # Sécurité : s'assurer que le chemin est dans le répertoire autorisé
        full_path = SRC_DIR / 'data' / image_path
        
        # Vérifier que le chemin existe et qu'il ne sort pas du répertoire
        if not full_path.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        # Vérifier que le chemin résolu est bien dans data/
        if not str(full_path.resolve()).startswith(str((SRC_DIR / 'data').resolve())):
            return jsonify({'error': 'Access denied'}), 403
        
        return send_file(full_path, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/valid_bins')
def valid_bins():
    """Configuration des bacs valides"""
    return jsonify({'success': True, 'bins': VALID_BINS})

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=USER_INTERFACE_PORT, debug=False)
