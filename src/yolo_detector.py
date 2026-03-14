"""
Smart Bin SI - Détecteur YOLO avec apprentissage au fur et à mesure
- Détecte les objets via caméra
- Demande ta validation : si tu dis "oui c'est correct", l'image est sauvegardée pour réentraîner le modèle
- Utilise waste_classifier pour le tri (DB + Arduino)
"""

import cv2
import torch
import time
import numpy as np
from pathlib import Path
from datetime import datetime

import waste_classifier
from config import (
    MODEL_PATH, CONFIDENCE_THRESHOLD, IOU_THRESHOLD,
    CAMERA_SOURCE, USE_CSI_CAMERA, FRAME_WIDTH, FRAME_HEIGHT, SHOW_DISPLAY,
    AUTO_SORT_DELAY, MIN_DETECTIONS, LEARNING_MODE, SAVE_IMAGES,
    TRAINING_DIR, BIN_COLORS,
    ENABLE_POST_SORT_CONFIRMATION, ENABLE_SORT_PAUSE, SORT_PAUSE_SECONDS,
)
from config import ADMIN_AUTOSTART, ADMIN_INTERFACE_PORT, USER_INTERFACE_PORT
import socket
import subprocess
import sys
import os
# Essayer de forcer la sortie en UTF-8 (évite UnicodeEncodeError sur Windows)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass


# ============================================
# SUPPORT CAMÉRA CSI JETSON
# ============================================

def get_csi_pipeline(camera_id=0, width=640, height=480, fps=30):
    """
    Créer un pipeline GStreamer pour caméra CSI Jetson
    
    Args:
        camera_id: ID du capteur caméra (0 ou 1)
        width: Largeur de l'image
        height: Hauteur de l'image
        fps: Fréquence d'images
    
    Retourne:
        str: Chaîne de pipeline GStreamer
    """
    return (
        f"nvarguscamerasrc sensor-id={camera_id} ! "
        f"video/x-raw(memory:NVMM), width={width}, height={height}, "
        f"format=NV12, framerate={fps}/1 ! "
        f"nvvidconv flip-method=0 ! "
        f"video/x-raw, width={width}, height={height}, format=BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=BGR ! appsink"
    )


# ============================================
# CLASSE DÉTECTEUR DE DÉCHETS
# ============================================

class WasteDetector:
    """
    Système de détection de déchets basé sur YOLO
    Utilise waste_classifier pour la logique de tri
    """
    
    def __init__(self, model_path=MODEL_PATH):
        """
        Initialiser le détecteur YOLO
        
        Args:
            model_path: Chemin vers les poids YOLO entraînés (fichier .pt)
        """
        print("\n" + "="*50)
        print("🤖 SMART BIN SI - DÉTECTEUR YOLO")
        print("="*50)
        
        # Charger le modèle YOLO
        self.model = self.load_model(model_path)
        
        # Suivi des détections
        self.last_detection = None
        self.detection_count = 0
        self.last_sort_time = 0
        self.last_frame = None  # Pour sauvegarder l'image lors de corrections
        
        # Initialiser les connexions via waste_classifier
        waste_classifier.init_serial_connection()
        waste_classifier.init_database()
        
        # Dossier pour les images d'apprentissage (quand tu confirmes "correct")
        if SAVE_IMAGES:
            TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        
        print("✓ Détecteur initialisé\n")
    
    def load_model(self, model_path):
        """
        Charger le modèle YOLO depuis un fichier
        Supporte YOLOv5 et YOLOv8 via torch.hub ou ultralytics
        """
        print(f"📦 Chargement du modèle depuis : {model_path}")
        # Première tentative : utiliser l'API ultralytics (si installée)
        try:
            from ultralytics import YOLO
            # Si le modèle custom existe, on l'utilise, sinon on prend le yolov5s fourni au repo
            if Path(model_path).exists():
                model_file = str(model_path)
            else:
                model_file = str(Path(__file__).resolve().parent.parent / 'yolov5s.pt')

            try:
                model = YOLO(model_file)
                self._use_ultralytics = True
                print(f"✓ Modèle chargé via ultralytics ({model_file})")
            except Exception as e_load:
                # Cas fréquent : checkpoint YOLOv5 incompatible avec ultralytics (module manquant)
                print(f"[WARN] impossible de charger '{model_file}' via ultralytics: {e_load}")
                print("→ Retraitement: utilisation d'un modèle ultralytics officiel léger (yolov8n.pt)")
                model = YOLO('yolov8n.pt')
                self._use_ultralytics = True
                print("✓ Modèle yolov8n chargé via ultralytics (fallback)")
        except Exception as e_ultra:
            print(f"[WARN] ultralytics non disponible ou erreur: {e_ultra}")
            # Fallback : essayer torch.hub (ancienne méthode)
            try:
                if Path(model_path).exists():
                    model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
                else:
                    model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                self._use_ultralytics = False
                print("✓ Modèle chargé via torch.hub (ultralytics/yolov5)")
            except Exception as e_hub:
                print(f"✗ Erreur lors du chargement du modèle : {e_hub}")
                raise

        # Note : pour ultralytics on passera conf/iou au moment de l'appel d'inférence.
        # Pour torch.hub (yolov5), on laisse les attributs si disponibles.
        try:
            if hasattr(model, 'conf'):
                model.conf = CONFIDENCE_THRESHOLD
            if hasattr(model, 'iou'):
                model.iou = IOU_THRESHOLD
        except Exception:
            pass

        # Si CUDA disponible, on essayera d'activer (uniquement si l'objet le supporte)
        try:
            if torch.cuda.is_available():
                if hasattr(model, 'to'):
                    model = model.to('cuda')
                print("✓ Accélération GPU activée")
            else:
                print("⚠ Exécution sur CPU (plus lent)")
        except Exception:
            pass

        return model
    
    def detect_waste(self, frame):
        """
        Exécuter la détection YOLO sur une image
        
        Args:
            frame: Image OpenCV (format BGR)
        
        Retourne:
            results: Résultats de détection YOLO
        """
        # Exécuter l'inférence
        # Si on utilise ultralytics, passer conf/iou en paramètres
        try:
            if getattr(self, '_use_ultralytics', False):
                results = self.model(frame, conf=CONFIDENCE_THRESHOLD, iou=IOU_THRESHOLD)
            else:
                results = self.model(frame)
        except TypeError:
            # Cas où le modèle n'accepte pas ces kwargs
            results = self.model(frame)
        return results
    
    def process_detections(self, results):
        """
        Traiter les résultats YOLO et extraire les déchets
        
        Args:
            results: Résultats de détection YOLO
        
        Retourne:
            list: Déchets détectés avec [nom_classe, confiance, bbox]
        """
        detections = []
        # Extraire les résultats selon le backend utilisé
        try:
            if getattr(self, '_use_ultralytics', False):
                # ultralytics retourne souvent une liste de Results ou un Results
                res = results[0] if isinstance(results, list) else results
                boxes = getattr(res, 'boxes', None)
                if boxes is not None:
                    # boxes.xyxy, boxes.conf, boxes.cls
                    try:
                        xyxy = boxes.xyxy.cpu().numpy()
                    except Exception:
                        xyxy = boxes.xyxy.numpy() if hasattr(boxes.xyxy, 'numpy') else []
                    try:
                        confs = boxes.conf.cpu().numpy()
                    except Exception:
                        confs = boxes.conf.numpy() if hasattr(boxes.conf, 'numpy') else []
                    try:
                        cls_idx = boxes.cls.cpu().numpy().astype(int)
                    except Exception:
                        cls_idx = boxes.cls.numpy().astype(int) if hasattr(boxes.cls, 'numpy') else []

                    for i, bbox in enumerate(xyxy):
                        x1, y1, x2, y2 = [float(v) for v in bbox]
                        confidence = float(confs[i]) if i < len(confs) else 0.0
                        cls = int(cls_idx[i]) if i < len(cls_idx) else 0
                        class_name = None
                        if hasattr(self.model, 'names'):
                            try:
                                class_name = self.model.names[cls]
                            except Exception:
                                class_name = str(cls)
                        else:
                            class_name = str(cls)

                        detections.append({
                            'class': class_name,
                            'confidence': confidence,
                            'bbox': [x1, y1, x2, y2]
                        })
                else:
                    # Pas de boxes → pas de détections
                    return []
            else:
                # Ancien format (torch.hub / yolov5)
                try:
                    predictions = results.pandas().xyxy[0]
                    for idx, row in predictions.iterrows():
                        class_name = row['name']
                        confidence = row['confidence']
                        bbox = [row['xmin'], row['ymin'], row['xmax'], row['ymax']]
                        detections.append({
                            'class': class_name,
                            'confidence': confidence,
                            'bbox': bbox
                        })
                except Exception:
                    pred = results.xyxy[0].cpu().numpy()
                    for detection in pred:
                        x1, y1, x2, y2, conf, cls = detection
                        class_name = self.model.names[int(cls)] if hasattr(self.model, 'names') else str(int(cls))
                        detections.append({
                            'class': class_name,
                            'confidence': float(conf),
                            'bbox': [float(x1), float(y1), float(x2), float(y2)]
                        })
        except Exception as e:
            print(f"⚠ Erreur extraction détections: {e}")
            return []
        
        return detections
    
    def should_trigger_sort(self, detection):
        """
        Décider si on doit déclencher l'action de tri
        Utilise un filtrage temporel pour éviter les faux positifs
        
        Args:
            detection: Dictionnaire de détection actuel
        
        Retourne:
            bool: True si on doit trier maintenant
        """
        current_time = time.time()
        
        # Vérifier si assez de temps s'est écoulé depuis le dernier tri
        if current_time - self.last_sort_time < AUTO_SORT_DELAY:
            return False
        
        # Vérifier si le même objet est détecté plusieurs fois
        if detection and self.last_detection:
            if detection['class'] == self.last_detection['class']:
                self.detection_count += 1
            else:
                self.detection_count = 1
                self.last_detection = detection
        else:
            self.detection_count = 1
            self.last_detection = detection
        
        # Déclencher si le minimum de détections consécutives est atteint
        if self.detection_count >= MIN_DETECTIONS:
            self.detection_count = 0
            self.last_sort_time = current_time
            return True
        
        return False
    
    def get_bin_color_for_display(self, waste_class):
        """
        Obtenir la couleur du bac pour l'affichage (sans trier)
        
        Args:
            waste_class: Nom de la classe de déchet
        
        Retourne:
            str: Couleur du bac ou None
        """
        # Chercher en base de données sans sauvegarder
        bin_color = waste_classifier.get_bin_color(waste_class)
        return bin_color
    
    def draw_detections(self, frame, detections):
        """
        Dessiner les boîtes de détection et labels sur l'image
        
        Args:
            frame: Image OpenCV
            detections: Liste des dictionnaires de détection
        
        Retourne:
            frame: Image annotée
        """
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det['bbox']]
            class_name = det['class']
            confidence = det['confidence']
            
            # Obtenir la couleur du bac pour ce déchet (juste pour affichage)
            bin_color = self.get_bin_color_for_display(class_name)
            
            color = BIN_COLORS.get(bin_color, BIN_COLORS["unknown"])
            
            # Dessiner la boîte
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Dessiner le label
            label = f"{class_name} ({confidence:.2f})"
            if bin_color:
                label += f" -> {bin_color}"
            else:
                label += " -> ?"
            
            # Fond pour le texte
            (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, y1-text_height-10), (x1+text_width, y1), color, -1)
            
            # Texte
            cv2.putText(frame, label, (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return frame
    
    def save_image_for_training(self, frame, class_name, bbox=None, class_id=None, correct=True):
        """
        Sauvegarde une image pour le réentraînement YOLO.
        Quand tu confirmes que la détection est correcte, l'image est stockée
        dans data/training_images/<class_name>/ (+ fichier .txt YOLO si bbox fourni).
        
        Args:
            frame: Image à sauvegarder
            class_name: Nom de la classe (ex: plastic_bottle)
            bbox: [x1, y1, x2, y2] optionnel → génère un .txt au format YOLO
            class_id: index de la classe (pour le .txt YOLO)
            correct: True = bonne détection, False = erreur (sauvegardé dans _errors/)
        """
        if not SAVE_IMAGES:
            return
        class_name = class_name.strip().lower().replace(" ", "_")
        if correct:
            folder = TRAINING_DIR / class_name
        else:
            folder = TRAINING_DIR / "_errors" / class_name
        folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "ok" if correct else "err"
        base = f"{prefix}_{timestamp}"
        filename = folder / f"{base}.jpg"
        cv2.imwrite(str(filename), frame)
        # Fichier label YOLO (une ligne : class_id x_center y_center width height, normalisé 0-1)
        if bbox is not None and class_id is not None and len(bbox) == 4:
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = [float(x) for x in bbox]
            x_center = ((x1 + x2) / 2) / w
            y_center = ((y1 + y2) / 2) / h
            width = (x2 - x1) / w
            height = (y2 - y1) / h
            label_path = folder / f"{base}.txt"
            with open(label_path, "w") as f:
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
        print(f"💾 Image sauvegardée pour apprentissage : {filename.name} ({class_name})")
    
    def _class_name_to_id(self, class_name):
        """Retourne l'index de la classe dans le modèle (pour le label YOLO)."""
        if not hasattr(self.model, "names"):
            return None
        names = self.model.names  # dict int -> str
        for idx, name in names.items():
            if name == class_name:
                return idx
        return None

    def handle_correction(self, frame, best_detection):
        """
        Demande si la détection est correcte ; si oui, sauvegarde l'image (+ label YOLO) pour réentraînement.
        
        Args:
            frame: Image actuelle
            best_detection: dict avec 'class', 'confidence', 'bbox'
        """
        detected_class = best_detection["class"]
        bbox = best_detection.get("bbox")
        class_id = self._class_name_to_id(detected_class)
        
        print(f"\n⚠ YOLO a détecté : '{detected_class}'")
        print("Est-ce correct ?")
        print("  y - Oui, c'est correct → image sauvegardée pour améliorer le modèle")
        print("  n - Non, corriger le nom")
        print("  skip - Ignorer")
        
        choice = input("Votre choix : ").strip().lower()
        
        if choice == 'y':
            print("✓ Détection confirmée → image sauvegardée pour réentraînement")
            self.save_image_for_training(
                frame, detected_class, bbox=bbox, class_id=class_id, correct=True
            )
            return detected_class
        
        elif choice == 'n':
            print("\nQuel est le vrai nom de cet objet ?")
            correct_name = input("Nom correct : ").strip()
            
            if correct_name:
                correct_name = correct_name.strip().lower().replace(" ", "_")
                self.save_image_for_training(frame, correct_name, correct=True)
                self.save_image_for_training(frame, detected_class, correct=False)
                print(f"✓ Correction enregistrée : {detected_class} → {correct_name}")
                return correct_name
        
        print("⊘ Détection ignorée")
        return None
    
    def run_camera_detection(self):
        """
        Boucle principale : capturer images, détecter déchets, déclencher tri
        """
        # Initialiser la caméra
        if USE_CSI_CAMERA:
            print("📷 Ouverture caméra CSI...")
            pipeline = get_csi_pipeline(width=FRAME_WIDTH, height=FRAME_HEIGHT)
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        else:
            print(f"📷 Ouverture caméra : {CAMERA_SOURCE}")
            cap = cv2.VideoCapture(CAMERA_SOURCE)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        if not cap.isOpened():
            print("✗ Échec d'ouverture de la caméra")
            return
        
        print("✓ Caméra prête")
        print("\n" + "="*50)
        print("CONTRÔLES :")
        print("  'q' - Quitter")
        print("  's' - Forcer le tri de la détection actuelle")
        print("  'r' - Réinitialiser le compteur de détections")
        if LEARNING_MODE:
            print("  'c' - Corriger la dernière détection")
        print("  'stats' - Voir les statistiques")
        print("="*50 + "\n")
        
        fps_time = time.time()
        fps_counter = 0
        fps_display = 0
        
        try:
            while True:
                # Capturer l'image
                ret, frame = cap.read()
                if not ret:
                    print("✗ Échec de lecture de l'image")
                    break
                
                # Sauvegarder la dernière frame pour corrections
                self.last_frame = frame.copy()
                
                # Exécuter la détection YOLO
                results = self.detect_waste(frame)
                detections = self.process_detections(results)
                
                # Dessiner les détections
                if SHOW_DISPLAY:
                    frame = self.draw_detections(frame, detections)
                
                # Vérifier si on doit déclencher le tri
                if detections:
                    best_detection = max(detections, key=lambda x: x['confidence'])
                    
                    if self.should_trigger_sort(best_detection):
                        waste_class = best_detection['class']
                        
                        # En mode apprentissage, demander confirmation AVANT le tri
                        if LEARNING_MODE:
                            corrected_class = self.handle_correction(self.last_frame, best_detection)
                            if corrected_class is None:
                                continue  # Ignoré par l'utilisateur
                            waste_class = corrected_class
                        
                        print(f"\n🎯 OBJET DÉTECTÉ : {waste_class}")
                        
                        # Déterminer le bac (demande via UI si inconnu), sans effectuer le tri immédiatement
                        bin_color = waste_classifier.classify_and_sort(
                            waste_class,
                            ask_if_unknown=True,
                            auto_mode=False,
                            perform_sort=False
                        )

                        if not bin_color:
                            continue

                        # Si mode apprentissage, demander confirmation AVANT le tri
                        if LEARNING_MODE:
                            confirmed = waste_classifier.ask_confirmation(waste_class, bin_color)
                            if not confirmed:
                                print("❌ Tri annulé par l'utilisateur (mode apprentissage)")
                                continue

                        # Envoi du tri à l'Arduino / simulation
                        waste_classifier.send_sort_command(bin_color)

                        # Confirmation après tri (toujours possible depuis l'UI) - lancée immédiatement
                        if ENABLE_POST_SORT_CONFIRMATION:
                            is_correct = waste_classifier.ask_confirmation(waste_class, bin_color)
                            if is_correct:
                                print("✅ Tri confirmé")
                            else:
                                print("❌ Tri non confirmé")

                        # Pause pour laisser le temps à l'objet d'être trié physiquement
                        if ENABLE_SORT_PAUSE and SORT_PAUSE_SECONDS > 0:
                            print(f"⏸️  Attente {SORT_PAUSE_SECONDS} secondes pour le tri...")
                            time.sleep(SORT_PAUSE_SECONDS)

                
                # Calculer les FPS
                fps_counter += 1
                if time.time() - fps_time > 1.0:
                    fps_display = fps_counter
                    fps_counter = 0
                    fps_time = time.time()
                
                # Afficher les infos sur l'image
                if SHOW_DISPLAY:
                    # Info FPS et détections
                    info_text = f"FPS: {fps_display} | Detections: {len(detections)}"
                    cv2.putText(frame, info_text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Suivi de détection
                    if self.last_detection:
                        status_text = f"Suivi: {self.last_detection['class']} ({self.detection_count}/{MIN_DETECTIONS})"
                        cv2.putText(frame, status_text, (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    # Mode
                    mode_text = "Mode: Apprentissage" if LEARNING_MODE else "Mode: Auto"
                    cv2.putText(frame, mode_text, (10, FRAME_HEIGHT - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                    
                    cv2.imshow('Smart Bin - Detection', frame)
                
                # Gérer les entrées clavier
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\n👋 Arrêt de la détection...")
                    break
                
                elif key == ord('s'):
                    # Tri manuel forcé
                    if detections:
                        best = max(detections, key=lambda x: x['confidence'])
                        waste_class = best['class']
                        print(f"\n⚡ TRI MANUEL FORCÉ : {waste_class}")
                        waste_classifier.classify_and_sort(
                            waste_class,
                            ask_if_unknown=True,
                            auto_mode=False
                        )
                
                elif key == ord('r'):
                    # Réinitialiser le compteur
                    self.detection_count = 0
                    self.last_detection = None
                    print("\n↻ Compteur de détections réinitialisé")
                
                elif key == ord('c') and LEARNING_MODE:
                    # Corriger la dernière détection
                    if self.last_detection:
                        corrected = self.handle_correction(
                            self.last_frame,
                            self.last_detection
                        )
                        if corrected:
                            bin_color = waste_classifier.ask_user_for_bin(corrected)
                            if bin_color:
                                waste_classifier.save_to_database(corrected, bin_color)
                
                # Commande textuelle pour stats
                # (Note: ne fonctionne que si on redirige stdin, sinon utiliser 's' dans le menu)
        
        except KeyboardInterrupt:
            print("\n\n⚠ Interrompu par l'utilisateur")
        
        finally:
            # Nettoyage
            cap.release()
            if SHOW_DISPLAY:
                cv2.destroyAllWindows()
            
            waste_classifier.cleanup()
            
            print("\n✓ Système de détection arrêté\n")


# ============================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================

def main():
    """Exécuter la détection YOLO"""
    from config import ADMIN_AUTOSTART
    
    # Menu de choix des interfaces si ADMIN_AUTOSTART est désactivé
    admin_interface_required = False
    user_interface_required = False
    
    if not ADMIN_AUTOSTART:
        print("\n" + "="*60)
        print("DÉCLARATION DU SYSTÈME DE SMART BIN SI")
        print("="*60)
        print("\nQuelle interface voulez-vous lancer ?")
        print("1. 🔹 Admin uniquement (supervision complète)")
        print("2. 👤 User uniquement (affectation des objets)")
        print("3. 🔹👤 Admin + User (complète)")
        print("4. ⚙️  Aucune interface (détection caméra uniquement)")
        print("="*60)
        
        choice = input("\nVotre choix (1-4) : ").strip()
        
        if choice == "1":
            admin_interface_required = True
            print("\n→ Lancement de l'interface Admin uniquement\n")
        elif choice == "2":
            user_interface_required = True
            print("\n→ Lancement de l'interface User uniquement\n")
        elif choice == "3":
            admin_interface_required = True
            user_interface_required = True
            print("\n→ Lancement de l'interface Admin + User\n")
        elif choice == "4":
            print("\n→ Mode sans interface (détection caméra uniquement)\n")
        else:
            print("\n⚠ Choix invalide ! Démarrage avec Admin + User par défaut\n")
            admin_interface_required = True
            user_interface_required = True
    else:
        # Si ADMIN_AUTOSTART est activé, lancer automatiquement admin et user
        admin_interface_required = True
        user_interface_required = True
    
    # Lancer les interfaces selon le choix
    if admin_interface_required or user_interface_required:
        print("🚀 Démarrage des interfaces...")
        
        # Admin interface
        if admin_interface_required:
            try:
                s = socket.socket()
                s.settimeout(0.5)
                try:
                    s.connect(("127.0.0.1", ADMIN_INTERFACE_PORT))
                    s.close()
                    print(f"→ Interface admin déjà en écoute sur le port {ADMIN_INTERFACE_PORT}")
                except Exception:
                    admin_path = Path(__file__).resolve().parent.parent / 'interfaces' / 'admin_interface' / 'app.py'
                    if admin_path.exists():
                        print(f"→ Démarrage interface admin ({ADMIN_INTERFACE_PORT})")
                        try:
                            subprocess.Popen([sys.executable, str(admin_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            time.sleep(1)
                            print(f"   ✓ Admin disponible à http://127.0.0.1:{ADMIN_INTERFACE_PORT}")
                        except Exception as e:
                            print(f"   ⚠ Impossible de lancer l'interface admin: {e}")
            except Exception as e:
                print(f"   ⚠ Erreur au démarrage de l'interface admin: {e}")
        
        # User interface
        if user_interface_required:
            try:
                s2 = socket.socket()
                s2.settimeout(0.5)
                s2.connect(("127.0.0.1", USER_INTERFACE_PORT))
                s2.close()
                print(f"→ Interface utilisateur déjà en écoute sur le port {USER_INTERFACE_PORT}")
            except Exception:
                user_path = Path(__file__).resolve().parent.parent / 'interfaces' / 'user_interface' / 'app.py'
                if user_path.exists():
                    print(f"→ Démarrage interface user ({USER_INTERFACE_PORT})")
                    try:
                        subprocess.Popen([sys.executable, str(user_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(1)
                        print(f"   ✓ User disponible à http://127.0.0.1:{USER_INTERFACE_PORT}")
                    except Exception as e:
                        print(f"   ⚠ Impossible de lancer l'interface utilisateur: {e}")
            except Exception as e:
                print(f"   ⚠ Erreur au démarrage de l'interface user: {e}")
        
        print()
    
    # Lancer la détection YOLO
    detector = WasteDetector()
    detector.run_camera_detection()


if __name__ == "__main__":
    main()