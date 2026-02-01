document.addEventListener('DOMContentLoaded', () => {
    // ============= NAVIGATION ============= 
    const menuItems = document.querySelectorAll('.menu-item');
    
    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            menuItems.forEach(mi => mi.classList.remove('active'));
            item.classList.add('active');
            
            document.querySelectorAll('.section').forEach(sec => {
                sec.classList.remove('active');
            });
            
            const sectionName = item.dataset.section;
            const section = document.getElementById(`section-${sectionName}`);
            if (section) {
                section.classList.add('active');
            }
        });
    });

    // ============= ARRÊT D'URGENCE ============= 
    const emergencyBtn = document.getElementById('emergency-stop');
    if (emergencyBtn) {
        emergencyBtn.addEventListener('click', () => {
            const confirmed = confirm('Êtes-vous sûr de vouloir déclencher l\'arrêt d\'urgence ?\nToutes les opérations seront interrompues immédiatement.');
            if (confirmed) {
                // Arrêter tous les scripts
                fetch('/api/scripts/stop/test_app.py');
                fetch('/api/scripts/stop/test_hardware.py');
                fetch('/api/scripts/stop/run_auto.sh');
                fetch('/api/scripts/stop/run_manual.sh');
                alert('Arrêt d\'urgence activé !\n\nTous les systèmes sont maintenant à l\'arrêt.');
                console.log('Arrêt d\'urgence déclenché');
            }
        });
    }

    // ============= YOLO OVERLAY ============= 
    const yoloCheckbox = document.getElementById('yolo-overlay');
    if (yoloCheckbox) {
        yoloCheckbox.addEventListener('change', () => {
            console.log('YOLO GUI:', yoloCheckbox.checked ? 'Activé' : 'Désactivé');
            // TODO: Intégrer avec le code YOLO réel pour activer/désactiver le GUI
        });
    }

    // ============= CAMERA REFRESH ============= 
    const cameraRefreshBtn = document.getElementById('camera-refresh');
    if (cameraRefreshBtn) {
        cameraRefreshBtn.addEventListener('click', () => {
            console.log('Actualisation de la caméra');
            // TODO: Intégrer avec le streaming caméra réel
            alert('Caméra actualisée');
        });
    }

    // ============= SCRIPTS MANAGEMENT ============= 
    const scriptRunBtns = document.querySelectorAll('.btn-script-run');
    const scriptStopBtns = document.querySelectorAll('.btn-script-stop');
    const scriptLogBtns = document.querySelectorAll('.btn-script-log');
    const consoleOutput = document.getElementById('console-output');
    const consoleInput = document.getElementById('console-input');
    const consoleModal = document.getElementById('console-modal');
    const consoleModalClose = document.querySelector('.modal-close');

    // Stockage de l'état des scripts
    let scriptsState = {};

    // Fonction pour actualiser l'état des scripts
    function updateScriptsStatus() {
        fetch('/api/scripts/status')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    scriptsState = data.scripts;
                    
                    // Mettre à jour l'UI pour chaque script
                    Object.entries(data.scripts).forEach(([scriptName, info]) => {
                        const runBtn = document.querySelector(`[data-script="${scriptName}"].btn-script-run`);
                        const stopBtn = document.querySelector(`[data-script="${scriptName}"].btn-script-stop`);
                        const status = document.querySelector(`[data-script-status="${scriptName}"]`);
                        
                        if (runBtn) runBtn.disabled = info.running;
                        if (stopBtn) stopBtn.disabled = !info.running;
                        
                        if (status) {
                            if (info.running) {
                                status.innerHTML = '<span class="status-badge running">EN COURS (PID: ' + info.pid + ')</span>';
                                status.style.color = '#28a745';
                            } else {
                                status.innerHTML = '<span class="status-badge stopped">Arrêté</span>';
                                status.style.color = '#6c757d';
                            }
                        }
                    });
                }
            })
            .catch(err => console.error('Erreur statut scripts:', err));
    }

    // Initialiser le statut et l'actualiser toutes les 2 secondes
    updateScriptsStatus();
    setInterval(updateScriptsStatus, 2000);

    scriptRunBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const script = btn.dataset.script;
            
            // Vérifier si déjà en cours
            if (scriptsState[script]?.running) {
                addConsoleLog(`[WARN] ${script} est déjà en cours d'exécution`);
                return;
            }
            
            addConsoleLog(`[RUN] Lancement de ${script}...`);
            btn.disabled = true;
            
            fetch(`/api/scripts/run/${script}`)
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        addConsoleLog(`[INFO] ${script} lancé avec succès`);
                        updateScriptsStatus();
                    } else {
                        addConsoleLog(`[ERROR] Erreur: ${data.error}`);
                        btn.disabled = false;
                    }
                })
                .catch(err => {
                    addConsoleLog(`[ERROR] ${err.message}`);
                    btn.disabled = false;
                });
        });
    });

    scriptStopBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const script = btn.dataset.script;
            
            // Vérifier si en cours
            if (!scriptsState[script]?.running) {
                addConsoleLog(`[WARN] ${script} n'est pas en cours d'exécution`);
                return;
            }
            
            addConsoleLog(`[STOP] Arrêt de ${script}...`);
            btn.disabled = true;
            
            fetch(`/api/scripts/stop/${script}`)
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        addConsoleLog(`[INFO] ${script} arrêté`);
                        updateScriptsStatus();
                    } else {
                        addConsoleLog(`[WARN] ${data.error}`);
                        btn.disabled = false;
                    }
                })
                .catch(err => {
                    addConsoleLog(`[ERROR] ${err.message}`);
                    btn.disabled = false;
                });
        });
    });

    scriptLogBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const script = btn.dataset.script;
            document.getElementById('console-script-name').textContent = script;
            const modalOutput = document.getElementById('console-modal-output');
            modalOutput.innerHTML = '';
            
            // Copier les logs actuels dans la modal
            const logs = consoleOutput.querySelectorAll('.console-line');
            logs.forEach(log => {
                const p = document.createElement('p');
                p.textContent = log.textContent;
                p.style.color = '#0db40d';
                p.style.margin = '2px 0';
                modalOutput.appendChild(p);
            });
            
            consoleModal.style.display = 'flex';
        });
    });

    if (consoleModalClose) {
        consoleModalClose.addEventListener('click', () => {
            consoleModal.style.display = 'none';
        });
    }

    consoleModal.addEventListener('click', (e) => {
        if (e.target === consoleModal) {
            consoleModal.style.display = 'none';
        }
    });

    function addConsoleLog(message) {
        const p = document.createElement('p');
        p.className = 'console-line';
        p.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        consoleOutput.appendChild(p);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    // ============= CONSOLE INPUT ============= 
    if (consoleInput) {
        consoleInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const command = consoleInput.value.trim();
                if (command) {
                    addConsoleLog(`$ ${command}`);
                    consoleInput.value = '';
                    // TODO: Intégrer avec le shell réel si nécessaire
                }
            }
        });
    }

    // ============= ERROR CORRECTIONS ============= 
    const correctionBtns = document.querySelectorAll('.btn-correction');
    correctionBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const input = e.target.previousElementSibling;
            const correction = input.value.trim();
            
    // ============= ERROR CORRECTIONS ============= 
    const correctionBtns = document.querySelectorAll('.btn-correction');
    correctionBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const input = e.target.previousElementSibling;
            const correction = input.value.trim();
            
            if (correction) {
                alert(`Correction enregistrée: "${correction}"\n\nCes données seront utilisées pour l'entraînement futur.`);
                // TODO: Appeler l'API pour enregistrer la correction
                input.value = '';
            } else {
                alert('Veuillez entrer le nom correct de l\'objet.');
            }
        });
    });

    // ============= MAINTENANCE ============= 
    const toggleMaintenanceBtn = document.getElementById('toggle-maintenance');
    const maintenanceStatus = document.getElementById('maintenance-status');
    let maintenanceActive = false;

    if (toggleMaintenanceBtn) {
        toggleMaintenanceBtn.addEventListener('click', () => {
            maintenanceActive = !maintenanceActive;
            
            if (maintenanceActive) {
                toggleMaintenanceBtn.textContent = 'Désactiver Maintenance';
                toggleMaintenanceBtn.style.background = '#28a745';
                maintenanceStatus.innerHTML = '<span class="status-dot" style="background: #ffc107;"></span><span>Maintenance activée</span>';
                addConsoleLog('[MAINTENANCE] Mode maintenance activé');
                alert('Mode Maintenance ACTIVÉ\nLa poubelle est arrêtée.');
            } else {
                toggleMaintenanceBtn.textContent = 'Activer Maintenance';
                toggleMaintenanceBtn.style.background = '#6c757d';
                maintenanceStatus.innerHTML = '<span class="status-dot"></span><span>Actif</span>';
                addConsoleLog('[MAINTENANCE] Mode maintenance désactivé');
                alert('Mode Maintenance DÉSACTIVÉ\nLa poubelle reprend ses opérations.');
            }
        });
    }

    // ============= CONFIG EDITOR ============= 
    const editConfigBtn = document.getElementById('edit-config');
    const configEditor = document.getElementById('config-editor');
    const configContent = document.getElementById('config-content');
    const saveConfigBtn = document.getElementById('save-config');
    const cancelConfigBtn = document.getElementById('cancel-config');

    if (editConfigBtn) {
        editConfigBtn.addEventListener('click', () => {
            configEditor.style.display = 'block';
            configContent.value = 'Chargement...';
            
            // Récupérer le contenu du config.py depuis l'API
            fetch('/api/config/read')
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        configContent.value = data.content;
                    } else {
                        configContent.value = `# Erreur: ${data.error}\n\n# Configuration par défaut:\n# [À remplir]`;
                    }
                })
                .catch(err => {
                    configContent.value = `# Erreur de chargement: ${err.message}`;
                });
        });
    }

    if (saveConfigBtn) {
        saveConfigBtn.addEventListener('click', () => {
            const configText = configContent.value;
            
            fetch('/api/config/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: configText})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert('Configuration enregistrée avec succès !');
                    configEditor.style.display = 'none';
                } else {
                    alert(`Erreur: ${data.error}`);
                }
            })
            .catch(err => alert(`Erreur: ${err.message}`));
        });
    }

    if (cancelConfigBtn) {
        cancelConfigBtn.addEventListener('click', () => {
            configEditor.style.display = 'none';
            configContent.value = '';
        });
    }

    // ============= MISES À JOUR EN TEMPS RÉEL ============= 
    
    // Actualiser les infos système toutes les 5 secondes
    function updateSystemInfo() {
        fetch('/api/system/info')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Uptime
                    const uptimeEl = document.getElementById('system-uptime');
                    if (uptimeEl) uptimeEl.textContent = data.system.uptime;
                    
                    // CPU
                    const cpuEl = document.getElementById('cpu-percent');
                    if (cpuEl) cpuEl.textContent = data.cpu.percent + '%';
                    
                    // RAM
                    const ramUsedEl = document.getElementById('system-ram');
                    const ramPercent = document.querySelector('[data-field="ram-percent"]');
                    if (ramUsedEl) ramUsedEl.textContent = `${data.memory.used_gb}GB / ${data.memory.total_gb}GB`;
                    if (ramPercent) ramPercent.textContent = data.memory.percent + '%';
                    
                    // Disque
                    const diskEl = document.getElementById('system-disk');
                    const diskPercent = document.querySelector('[data-field="disk-percent"]');
                    if (diskEl) diskEl.textContent = `Libre: ${data.disk.free_gb}GB / ${data.disk.total_gb}GB`;
                    if (diskPercent) diskPercent.textContent = data.disk.percent + '%';
                    
                    // Système
                    const osEl = document.querySelector('[data-field="os"]');
                    if (osEl) osEl.textContent = `${data.system.os} ${data.system.os_version}`;
                    
                    const hostnameEl = document.querySelector('[data-field="hostname"]');
                    if (hostnameEl) hostnameEl.textContent = data.system.hostname;
                }
            })
            .catch(err => console.error('Erreur system info:', err));
    }
    
    // Actualiser les infos GPU toutes les 3 secondes
    function updateGPUInfo() {
        fetch('/api/gpu/info')
            .then(res => res.json())
            .then(data => {
                if (data.success && data.gpu_available && data.devices.length > 0) {
                    const gpu = data.devices[0];  // Premier GPU
                    
                    const gpuNameEl = document.getElementById('gpu-model');
                    const gpuTempEl = document.getElementById('gpu-temp');
                    const gpuVramEl = document.getElementById('gpu-vram');
                    const gpuUtilEl = document.querySelector('[data-field="gpu-util"]');
                    
                    if (gpuNameEl) gpuNameEl.textContent = gpu.name;
                    if (gpuTempEl) gpuTempEl.textContent = `${gpu.temperature}°C`;
                    if (gpuVramEl) gpuVramEl.textContent = `${gpu.memory_used_gb}GB / ${gpu.memory_total_gb}GB`;
                    if (gpuUtilEl) gpuUtilEl.textContent = `${gpu.utilization_percent}%`;
                } else if (!data.gpu_available) {
                    const gpuNameEl = document.getElementById('gpu-model');
                    if (gpuNameEl) gpuNameEl.textContent = 'Non disponible';
                }
            })
            .catch(err => console.error('Erreur GPU info:', err));
    }
    
    // Lancer les mises à jour
    updateSystemInfo();
    updateGPUInfo();
    updateBinsStatus();
    updateDetectionsHistory();
    setInterval(updateSystemInfo, 5000);
    setInterval(updateGPUInfo, 3000);
    setInterval(updateBinsStatus, 5000);
    setInterval(updateDetectionsHistory, 10000);

    // ============= GESTION DES BACS ============= 
    
    function updateBinsStatus() {
        fetch('/api/bins/status')
            .then(res => res.json())
            .then(data => {
                if (data.success && data.bins) {
                    data.bins.forEach(bin => {
                        // Progress bars
                        const progressBar = document.getElementById(`progress-${bin.color}`);
                        if (progressBar) progressBar.style.width = bin.fill_percent + '%';
                        
                        const percent = document.getElementById(`percent-${bin.color}`);
                        if (percent) percent.textContent = Math.round(bin.fill_percent) + '%';
                        
                        // Mise à jour des cartes de gestion
                        const section = document.getElementById('section-bins');
                        if (section) {
                            const cards = section.querySelectorAll('.card');
                            const colorNames = {
                                'yellow': 'Bac Jaune',
                                'green': 'Bac Vert',
                                'brown': 'Bac Marron'
                            };
                            
                            cards.forEach(card => {
                                if (card.textContent.includes(colorNames[bin.color])) {
                                    // Mettre à jour le contenu
                                    const items = card.querySelectorAll('.status-item');
                                    if (items[0]) items[0].querySelector('span:last-child').textContent = 
                                        Math.round(bin.fill_percent) + '%';
                                    if (items[2]) items[2].querySelector('span:last-child').textContent = 
                                        bin.item_count;
                                    
                                    // Ajouter alerte si presque plein
                                    if (bin.needs_emptying) {
                                        card.style.backgroundColor = '#fff3cd';
                                        const btn = card.querySelector('.btn-secondary');
                                        if (btn) btn.style.backgroundColor = '#ff6b6b';
                                    }
                                }
                            });
                        }
                    });
                }
            })
            .catch(err => console.error('Erreur bins status:', err));
    }
    
    function updateDetectionsHistory() {
        fetch('/api/bins/history?limit=20')
            .then(res => res.json())
            .then(data => {
                if (data.success && data.history) {
                    const tbody = document.querySelector('.detection-table tbody');
                    if (tbody) {
                        tbody.innerHTML = '';
                        
                        data.history.forEach(detection => {
                            const row = document.createElement('tr');
                            const timestamp = new Date(detection.timestamp);
                            const timeStr = timestamp.toLocaleString('fr-FR');
                            
                            const binLabels = {
                                'yellow': 'Jaune',
                                'green': 'Vert',
                                'brown': 'Marron'
                            };
                            
                            row.innerHTML = `
                                <td>${detection.item_name || 'Inconnu'}</td>
                                <td>${binLabels[detection.bin_color] || detection.bin_color}</td>
                                <td>${Math.round(detection.confidence * 100)}%</td>
                                <td>${timeStr}</td>
                            `;
                            tbody.appendChild(row);
                        });
                    }
                }
            })
            .catch(err => console.error('Erreur detections history:', err));
    }
    
    // Boutons "Vider" pour les bacs
    document.querySelectorAll('.section#section-bins .btn-secondary').forEach(btn => {
        btn.addEventListener('click', function() {
            const card = this.closest('.card');
            const title = card.querySelector('h3').textContent;
            const colorMap = {
                'Bac Jaune': 'yellow',
                'Bac Vert': 'green',
                'Bac Marron': 'brown'
            };
            const color = colorMap[title];
            
            if (confirm(`Êtes-vous sûr de vouloir vider le ${title} ?`)) {
                fetch(`/api/bins/empty/${color}`, {method: 'POST'})
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            addConsoleLog('LOG', `✓ ${title} vidé avec succès`);
                            updateBinsStatus();
                        } else {
                            addConsoleLog('ERROR', `✗ Erreur vidage: ${data.error}`);
                        }
                    })
                    .catch(err => addConsoleLog('ERROR', `Erreur: ${err}`));
            }
        });
    });

    console.log('Interface administrateur chargée avec succès - APIs intégrées');
});
