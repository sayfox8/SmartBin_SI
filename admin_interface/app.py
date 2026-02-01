from flask import Flask, render_template, jsonify, request
import os
import psutil
import json
import subprocess
import platform
from datetime import datetime, timedelta

# Tentative d'import nvidia-ml-py
try:
    from pynvml import nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex, nvmlDeviceGetName, nvmlDeviceGetTemperature, nvmlDeviceGetMemoryInfo, nvmlDeviceGetUtilizationRates, NVML_TEMP_GPU
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("[WARN] nvidia-ml-py non installé. Les infos GPU ne seront pas disponibles.")

# Obtenir le répertoire courant
base_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            static_folder=os.path.join(base_dir, 'static'),
            static_url_path='/static',
            template_folder=os.path.join(base_dir, 'static'))

# Initialiser nvidia-ml-py si disponible
if GPU_AVAILABLE:
    try:
        nvmlInit()
    except Exception as e:
        GPU_AVAILABLE = False
        print(f"[WARN] Erreur lors de l'initialisation nvidia-ml-py: {e}")

# ============= ROUTES ============= 

@app.route('/')
def index():
    return render_template('index.html')

# ============= API SYSTÈME ============= 

@app.route('/api/system/info')
def system_info():
    """Récupère les infos générales du système"""
    try:
        boot_time = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(boot_time)
        uptime_str = f"{int(uptime.total_seconds() // 3600)}h {int((uptime.total_seconds() % 3600) // 60)}m"
        
        # RAM
        ram = psutil.virtual_memory()
        ram_gb = ram.used / (1024**3)
        ram_total_gb = ram.total / (1024**3)
        
        # Disque
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024**3)
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        return jsonify({
            'success': True,
            'system': {
                'hostname': platform.node(),
                'os': platform.system(),
                'os_version': platform.release(),
                'python_version': platform.python_version(),
                'uptime': uptime_str,
                'uptime_seconds': int(uptime.total_seconds())
            },
            'cpu': {
                'count': cpu_count,
                'percent': cpu_percent,
                'freq_mhz': int(cpu_freq.current) if cpu_freq else 0
            },
            'memory': {
                'used_gb': round(ram_gb, 2),
                'total_gb': round(ram_total_gb, 2),
                'percent': ram.percent
            },
            'disk': {
                'free_gb': round(disk_free_gb, 2),
                'total_gb': round(disk.total / (1024**3), 2),
                'percent': disk.percent
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============= API GPU ============= 

@app.route('/api/gpu/info')
def gpu_info():
    """Récupère les infos du GPU Nvidia"""
    if not GPU_AVAILABLE:
        return jsonify({'success': False, 'error': 'GPU Nvidia non disponible', 'gpu_available': False})
    
    try:
        gpu_devices = []
        device_count = nvmlDeviceGetCount()
        
        for i in range(device_count):
            handle = nvmlDeviceGetHandleByIndex(i)
            
            # Nom du GPU
            gpu_name = nvmlDeviceGetName(handle).decode('utf-8') if isinstance(nvmlDeviceGetName(handle), bytes) else nvmlDeviceGetName(handle)
            
            # Température
            temp = nvmlDeviceGetTemperature(handle, NVML_TEMP_GPU)
            
            # Mémoire
            mem_info = nvmlDeviceGetMemoryInfo(handle)
            mem_used_gb = mem_info.used / (1024**3)
            mem_total_gb = mem_info.total / (1024**3)
            
            # Utilisation
            util = nvmlDeviceGetUtilizationRates(handle)
            
            gpu_devices.append({
                'id': i,
                'name': gpu_name,
                'temperature': int(temp),
                'memory_used_gb': round(mem_used_gb, 2),
                'memory_total_gb': round(mem_total_gb, 2),
                'memory_percent': round((mem_info.used / mem_info.total) * 100, 1),
                'utilization_percent': int(util.gpu),
                'memory_utilization_percent': int(util.memory)
            })
        
        return jsonify({
            'success': True,
            'gpu_available': True,
            'devices': gpu_devices
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'gpu_available': False})

# ============= API PROCESSUS ============= 

@app.route('/api/processes')
def processes():
    """Récupère la liste des processus Python/Scripts en cours"""
    try:
        processes_list = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
            try:
                if 'python' in proc.info['name'].lower() or proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Chercher les scripts connus
                    if any(script in cmdline for script in ['test_app.py', 'test_hardware.py', 'run_auto.sh', 'run_manual.sh']):
                        processes_list.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline[:100],  # Limiter la taille
                            'memory_percent': round(proc.info['memory_percent'], 2),
                            'cpu_percent': round(proc.info['cpu_percent'], 2)
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return jsonify({
            'success': True,
            'processes': processes_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============= API SCRIPTS ============= 

@app.route('/api/scripts/status')
def scripts_status():
    """Vérifie l'état réel de tous les scripts"""
    try:
        scripts_list = ['test_app.py', 'test_hardware.py', 'run_auto.sh', 'run_manual.sh']
        status = {}
        
        for script in scripts_list:
            is_running = False
            pid = None
            
            # Chercher le processus
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Gérer le cas où cmdline est None ou vide
                    cmdline_list = proc.info['cmdline']
                    if cmdline_list is None:
                        cmdline = ''
                    else:
                        cmdline = ' '.join(cmdline_list)
                    
                    if script in cmdline:
                        is_running = True
                        pid = proc.info['pid']
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                    pass
            
            status[script] = {
                'running': is_running,
                'pid': pid
            }
        
        return jsonify({
            'success': True,
            'scripts': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scripts/run/<script_name>')
def run_script(script_name):
    """Lance un script"""
    try:
        scripts_dir = os.path.join(os.path.dirname(base_dir), 'scripts')
        script_path = os.path.join(scripts_dir, script_name)
        
        # Vérifier que le script existe
        if not os.path.exists(script_path):
            return jsonify({'success': False, 'error': f'Script {script_name} non trouvé'})
        
        # Vérifier que le script n'est pas déjà en cours
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline) if proc.cmdline else ''
                if script_name in cmdline:
                    return jsonify({'success': False, 'error': f'{script_name} est déjà en cours d\'exécution'})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Lancer le script
        if script_name.endswith('.py'):
            subprocess.Popen(['python', script_path])
        else:
            subprocess.Popen(['bash', script_path])
        
        return jsonify({
            'success': True,
            'message': f'Script {script_name} lancé'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scripts/stop/<script_name>')
def stop_script(script_name):
    """Arrête un script"""
    try:
        # Trouver et tuer le processus
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline) if proc.cmdline else ''
                if script_name in cmdline:
                    proc.terminate()
                    proc.wait(timeout=5)
                    return jsonify({
                        'success': True,
                        'message': f'Script {script_name} arrêté'
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        
        return jsonify({'success': False, 'error': f'Script {script_name} non trouvé en cours d\'exécution'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============= API CONFIG ============= 

@app.route('/api/config/read')
def read_config():
    """Lit le fichier config.py"""
    try:
        config_path = os.path.join(os.path.dirname(base_dir), 'src', 'config.py')
        
        if not os.path.exists(config_path):
            return jsonify({'success': False, 'error': f'Fichier config.py non trouvé à {config_path}'})
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'path': config_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/save', methods=['POST'])
def save_config():
    """Enregistre le fichier config.py"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        config_path = os.path.join(os.path.dirname(base_dir), 'src', 'config.py')
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'message': 'Configuration enregistrée',
            'path': config_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============= API BACS (WASTE MANAGEMENT) ============= 

@app.route('/api/bins/status')
def bins_status():
    """Récupère l'état des bacs (remplissage, items, dernière vidange)"""
    try:
        import sys
        from pathlib import Path
        src_dir = Path(__file__).resolve().parent.parent / 'src'
        sys.path.insert(0, str(src_dir))
        
        import waste_classifier
        waste_classifier.init_database()
        
        bins = waste_classifier.get_bin_status()
        
        # Formater les données
        data = []
        for bin_color, fill_level, item_count, last_emptied, capacity in bins:
            fill_percent = min(100, (fill_level / capacity) * 100) if capacity > 0 else 0
            data.append({
                'color': bin_color,
                'fill_level': float(fill_level),
                'fill_percent': float(fill_percent),
                'item_count': int(item_count),
                'capacity_liters': float(capacity),
                'last_emptied': last_emptied,
                'needs_emptying': fill_percent > 80
            })
        
        waste_classifier.cleanup()
        
        return jsonify({
            'success': True,
            'bins': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/bins/history')
def bins_history():
    """Récupère l'historique des détections"""
    try:
        import sys
        from pathlib import Path
        src_dir = Path(__file__).resolve().parent.parent / 'src'
        sys.path.insert(0, str(src_dir))
        
        limit = request.args.get('limit', 50, type=int)
        
        import waste_classifier
        waste_classifier.init_database()
        
        history = waste_classifier.get_detection_history(limit)
        
        # Formater les données
        data = []
        for bin_color, item_name, timestamp, confidence in history:
            data.append({
                'bin_color': bin_color,
                'item_name': item_name,
                'timestamp': timestamp,
                'confidence': float(confidence)
            })
        
        waste_classifier.cleanup()
        
        return jsonify({
            'success': True,
            'history': data,
            'count': len(data)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/bins/empty/<bin_color>', methods=['POST'])
def empty_bin(bin_color):
    """Vide un bac"""
    try:
        import sys
        from pathlib import Path
        src_dir = Path(__file__).resolve().parent.parent / 'src'
        sys.path.insert(0, str(src_dir))
        
        import waste_classifier
        waste_classifier.init_database()
        
        result = waste_classifier.empty_bin(bin_color)
        
        waste_classifier.cleanup()
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Bac {bin_color} vidé avec succès',
                'bin_color': bin_color,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'error': f'Impossible de vider le bac {bin_color}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/waste/classify', methods=['POST'])
def waste_classify():
    """Classifie un objet et l'ajoute au bac approprié"""
    try:
        import sys
        from pathlib import Path
        src_dir = Path(__file__).resolve().parent.parent / 'src'
        sys.path.insert(0, str(src_dir))
        
        data = request.get_json()
        item_name = data.get('item_name', '').strip()
        confidence = data.get('confidence', 1.0)
        auto_mode = data.get('auto_mode', False)
        
        if not item_name:
            return jsonify({'success': False, 'error': 'item_name requis'})
        
        import waste_classifier
        waste_classifier.init_database()
        
        bin_color = waste_classifier.classify_and_sort(
            item_name, 
            ask_if_unknown=False, 
            auto_mode=auto_mode,
            confidence=confidence
        )
        
        waste_classifier.cleanup()
        
        if bin_color:
            return jsonify({
                'success': True,
                'item_name': item_name,
                'bin_color': bin_color,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Objet inconnu: {item_name}'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============= API CAMÉRA ============= 

@app.route('/api/camera/status')
def camera_status():
    """Récupère le statut de la caméra"""
    try:
        # TODO: Intégrer avec le code caméra réel
        return jsonify({
            'success': True,
            'connected': True,
            'resolution': '1920x1080',
            'fps': 30,
            'device': '/dev/video0',
            'last_frame': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'connected': False})

# ============= API ARDUINO ============= 

@app.route('/api/arduino/status')
def arduino_status():
    """Récupère le statut d'Arduino"""
    try:
        # TODO: Intégrer avec le code Arduino réel
        return jsonify({
            'success': True,
            'connected': True,
            'port': 'COM3',
            'baudrate': 9600,
            'motor_status': 'Fonctionnel',
            'last_communication': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'connected': False})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
