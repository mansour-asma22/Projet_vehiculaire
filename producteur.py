from scapy.all import rdpcap, Raw
import paho.mqtt.client as mqtt
import json
import time

# Configuration
BROKER = "localhost"  # Adresse du broker MQTT
TOPIC = "cam/packets"  # Nom du topic MQTT
PCAP_FILE = "v2v-EVA-2-0.pcap"

# Connexion au broker
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER)

# Lecture des paquets du fichier PCAPNG
packets = rdpcap(PCAP_FILE)

print(f"Nombre total de paquets lus : {len(packets)}")

# Fonction pour filtrer uniquement les messages CAM
def is_cam_packet(packet):
    """ Vérifie si un paquet est un message CAM valide (taille 121 octets) """
    if packet.haslayer(Raw):
        raw_data = bytes(packet[Raw].load)
        
        # Vérifier que la longueur est exactement 121 octets
        if len(raw_data) == 89:
            # Vérifier que le paquet contient un identifiant CAM
            return True

    return False

sent_packets = set()  # Stocker les paquets déjà envoyés

for index, packet in enumerate(packets):
    if is_cam_packet(packet):
        packet_hex = bytes(packet).hex()  # Convertir en hex
        if packet_hex not in sent_packets:  # Vérifier si déjà envoyé
            sent_packets.add(packet_hex)  # Ajouter au set
            packet_json = {"raw": packet_hex}
            client.publish(TOPIC, json.dumps(packet_json), retain=False)
            print(f"🔹 Paquet unique {index+1} envoyé: {packet_hex[:50]}...")
            time.sleep(0.5)  # Pause pour simuler une transmission réelle


client.disconnect()

