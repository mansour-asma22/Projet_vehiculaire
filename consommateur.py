import paho.mqtt.client as mqtt
import json
import os
import time
import pyshark
import random
from scapy.all import Ether, wrpcap
from scapy.layers.dot11 import RadioTap, Dot11
import folium
from folium.plugins import MarkerCluster, TimestampedGeoJson
from flask import Flask, render_template_string, render_template, jsonify
import threading


# Configuration
BROKER = "localhost"
TOPIC = "cam/packets"
PCAP_FILE = "mqtt_capture.pcap"
MAP_FILE = "car_tracking.html"

# Dictionnaire pour stocker les positions des véhicules
vehicules = {}

# Génération dynamique de 100 couleurs distinctes
couleurs_vehicules = [
    'red', 'green', 'blue', 'purple', 'orange', 'black', 'pink', 'cyan', 
    'yellow', 'brown', 'gray', 'lime', 'magenta', 'navy', 'teal', 'gold', 
    'silver', 'maroon', 'olive', 'coral', 'indigo', 'turquoise', 'violet', 
    'chocolate', 'deepskyblue'
]

def get_vehicle_color(station_id):
    """Assigne une couleur en fonction du station_id"""
    return couleurs_vehicules[station_id % len(couleurs_vehicules)]


# Centre de la carte (évite le rechargement visible)
CARTE_CENTRE = [45.0531764, 7.6578783]
ZOOM_LEVEL = 20  # Fixation du niveau de zoom

# Initialisation de l'application Flask
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def get_vehicle_data():
    return jsonify(vehicules)
    

# Fonction pour créer la carte
def create_map():
    print("📌 Update de la carte...")

    if not vehicules:
        print("⚠️ Aucun véhicule détecté. Affichage d'une carte vide.")
        return folium.Map(location=CARTE_CENTRE, zoom_start=ZOOM_LEVEL)._repr_html_()

    # Initialisation de la carte centrée
    m = folium.Map(location=CARTE_CENTRE, zoom_start=ZOOM_LEVEL)
    features = []

    for station_id, data in vehicules.items():
        couleur = get_vehicle_color(station_id)  # Récupérer la couleur associée
        trajets = data.get("positions", [])   # Récupérer la liste des positions

        # 🔹 Vérifier si le véhicule a des positions valides
        trajets_valides = [p for p in trajets if isinstance(p.get("coordinates"), list) and len(p["coordinates"]) == 2]
        if not trajets_valides:
            print(f"⚠️ Véhicule {station_id} n'a pas de positions valides.")
            continue

        # 🔹 Correction des coordonnées (latitude, longitude)
        coords = [(p["coordinates"][1], p["coordinates"][0]) for p in trajets_valides]

        # 🔹 Tracé de la trajectoire du véhicule
        folium.PolyLine(
            locations=coords, color=couleur, weight=3, opacity=0.7
        ).add_to(m)

        # 🔹 Ajouter un marqueur pour la dernière position du véhicule
        last_pos = trajets_valides[-1]  # Dernière position connue
        folium.CircleMarker(
            location=(last_pos["coordinates"][1], last_pos["coordinates"][0]),
            radius=4,
            color=couleur,
            fill=True,
            fill_color=couleur,
            fill_opacity=0.9,
            popup=folium.Popup(
                f"🚗 <b>Véhicule {station_id}</b><br>📍 Position: {last_pos['coordinates'][1]}, {last_pos['coordinates'][0]}<br>🔥 Vitesse: {last_pos['speed']} km/h",
                max_width=250
            )
        ).add_to(m)

        # 🔹 Ajout des points animés pour suivre le déplacement en temps réel
        for point in trajets_valides:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": point["coordinates"]},
                "properties": {
                    "time": point["time"] * 1000,  # Conversion en millisecondes
                    "popup": f"🚗 Véhicule {station_id} - Vitesse: {point['speed']} km/h",
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": couleur,
                        "fillOpacity": 0.8,
                        "stroke": "true",
                        "radius": 5
                    }
                }
            })

    # 🔹 Ajouter les points animés (historique des positions)
    if features:
        TimestampedGeoJson({
            "type": "FeatureCollection",
            "features": features
        }, period="PT1S", add_last_point=True, auto_play=True, loop=True).add_to(m)

    print("✅ Carte mise à jour avec succès.")
    return m._repr_html_()



@app.route("/map")
def map_view():
    return create_map()

# Fonction pour mettre à jour la position des véhicules
def update_position(data):
    station_id = data["stationId"]
    latitude = data["latitude"]
    longitude = data["longitude"]
    vitesse = data["speed"]
    timestamp = int(time.time())

    if station_id not in vehicules:
        vehicules[station_id] = {
            "color": get_vehicle_color(station_id),  # Associer une couleur unique
            "positions": []
        }

    vehicules[station_id]["positions"].append({
        "time": timestamp,
        "coordinates": [longitude, latitude],
        "speed": vitesse
    })

    # Limiter l'historique des positions à 100 points pour éviter la surcharge
    #if len(positions_vehicules[station_id]["positions"]) > 100:
     #   positions_vehicules[station_id]["positions"].pop(0)

    
# Liste pour stocker les paquets
def on_message(client, userdata, msg):
    
    # Conversion du message JSON
    packet_json = json.loads(msg.payload)
    raw_bytes = bytes.fromhex(packet_json["raw"])  # Reconstruire le paquet
    #packet = Ether(raw_bytes)  # Convertir en objet Scapy
    packet = RadioTap()/Dot11(raw_bytes)
    
    print(f"Nouveau paquet reçu et ajouté au PCAP: {packet.summary()}")

    # Supprimer l'ancien fichier PCAP et recréer un nouveau
    if os.path.exists(PCAP_FILE):
        os.remove(PCAP_FILE)  # Supprimer le fichier précédent

    #print(f" Contenu du paquet avant écriture: {packet.show(dump=True)}")
    # Sauvegarder uniquement le dernier paquet reçu
    wrpcap(PCAP_FILE, [packet])

    # Attendre la mise à jour complète du fichier PCAP
    time.sleep(0.2)

    # Vérifier que le fichier PCAP contient bien des données avant d'ouvrir PyShark
    file_size = os.path.getsize(PCAP_FILE)
    if file_size == 0:
        print("Le fichier PCAP est vide, impossible d'extraire des données.")
        return

    # Lire uniquement le dernier paquet avec PyShark
    cap = pyshark.FileCapture(PCAP_FILE, display_filter="its")

    found_packet = False  # Vérifier si PyShark a trouvé un paquet

    for pkt in cap:
        found_packet = True
        #print(pkt)
        try:
            # Extraction des informations du paquet ITS
            station_id = int(pkt.its.stationid) if hasattr(pkt.its, 'stationid') else "N/A"
            latitude = int(pkt.its.latitude) / 10**7 if hasattr(pkt.its, 'latitude') else "N/A"
            longitude = int(pkt.its.longitude) / 10**7 if hasattr(pkt.its, 'longitude') else "N/A"
            speed = int(pkt.its.speedValue) / 100 if hasattr(pkt.its, 'speedValue') else "N/A"

            print(f"🚗 Véhicule {station_id} - Latitude: {latitude}, Longitude: {longitude}, Vitesse: {speed} m/s")
            
            # Mise à jour de la position du véhicule
            if station_id != "N/A" and latitude != "N/A" and longitude != "N/A":
                update_position({
                    "stationId": station_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "speed": speed
                })
                
        except Exception as e:
            print(f"  ❌ Erreur lors de l'extraction : {e}")

    if not found_packet:
        print("❌ Aucun paquet ITS trouvé par PyShark.")

    cap.close()



# Configuration MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(BROKER)
client.subscribe(TOPIC, qos=2)

# Démarrer Flask dans un thread séparé
import threading
flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False))
flask_thread.start()

print("📡 En attente des paquets CAM...")
client.loop_forever()

