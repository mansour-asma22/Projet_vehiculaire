# Projet Vehiculaire - Transmission de paquets CAM/ITS

## Description
Ce projet permet de capturer, transmettre et visualiser des paquets CAM/ITS via MQTT et une interface web Flask. Il utilise Scapy pour la manipulation des paquets, PyShark pour l'analyse des paquets ITS, et Folium pour la visualisation géographique.

## Structure du projet
- `producteur.py` : Envoie les paquets CAM/ITS depuis un fichier PCAP vers le broker MQTT.  
- `consommateur.py` : Reçoit les paquets depuis MQTT, les sauvegarde dans un fichier PCAP et les affiche sur une interface web Flask.  
- `mqtt_capture.pcap` : Fichier de capture PCAP utilisé pour tester le projet.  
- `templates/` : Contient les fichiers HTML pour l’interface web.  
- `static/` : Contient les fichiers CSS, JS et images pour l’interface web.

## Prérequis
- Python 3.10+  
- Mosquitto MQTT  : sudo apt install mosquitto mosquitto-clients -y
- Bibliothèques Python : pip install scapy paho-mqtt pyshark folium flask
         scapy            : Manipulation des paquets
         paho-mqtt        : Client MQTT
         pyshark          : Analyse de paquets PCAP
         flask            : Interface web
         folium           : Cartographie et visualisation géographique
 - Wireshark : sudo apt install wireshark tshark -y
 ## Exécution

Lancer le broker MQTT (Mosquitto) : sudo service mosquitto start
Lancer le consommateur : python3 consommateur.py
Lancer le producteur pour envoyer les paquets : python3 producteur.py
Ouvrir l’interface web dans le navigateur : http://127.0.0.1:5000
