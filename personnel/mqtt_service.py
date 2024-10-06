import paho.mqtt.client as mqtt
from datetime import datetime
from personnel.models import Utilisateur, Presence, FichePaie

# Informations de connexion au serveur MQTT
mqtt_server = "64.225.15.231"
mqtt_port = 1883
mqtt_user = "salama"
mqtt_password = "1234"


def on_connect(client, userdata, flags, rc):
    print("Connecté avec le code de résultat:", rc)
    client.subscribe("rfid/detection")


def on_message(client, userdata, msg):
    print(f"Message reçu sur {msg.topic}: {msg.payload.decode()}")

    try:
        rfid_message = eval(msg.payload.decode())
        rfid_id = rfid_message.get("card_id")
        detection_time = rfid_message.get("heure")
        detection_time_obj = datetime.strptime(detection_time, "%H:%M").time()

        try:
            utilisateur = Utilisateur.objects.get(rfid_number=rfid_id)
            print(f"Utilisateur {utilisateur.username} trouvé.")

            # Obtenir le mois et l'année en cours
            now = datetime.now()
            mois_courant = now.month
            annee_courante = now.year

            # Récupérer la fiche de paie du mois en cours pour l'utilisateur
            try:
                fiche_paie = FichePaie.objects.get(
                    employe=utilisateur,
                    date_creation__year=annee_courante,
                    date_creation__month=mois_courant
                )
                print(f"Fiche de paie pour {utilisateur.username} trouvée pour le mois en cours.")
            except FichePaie.DoesNotExist:
                print(f"Aucune fiche de paie trouvée pour {utilisateur.username} ce mois-ci.")
                fiche_paie = None

            # Vérifier la présence et l'heure
            if detection_time_obj <= datetime.strptime("12:01", "%H:%M").time():
                presence, created = Presence.objects.get_or_create(
                    agent=utilisateur,
                    date=now.date(),
                    defaults={'fiche_paie': fiche_paie, 'heure_arrivee': detection_time_obj, 'statut': 'P'}
                )
                if created:
                    response = f"Bon arrivee {utilisateur.username}."
                else:
                    response = f"Presence deja enregistree pour {utilisateur.username}."
                client.publish("rfid/response", response)
                print(f"Réponse envoyée: {response}")

            elif detection_time_obj >= datetime.strptime("12:01", "%H:%M").time():
                try:
                    presence = Presence.objects.get(agent=utilisateur, date=now.date())
                    presence.heure_depart = detection_time_obj
                    presence.save()
                    response = f"Bon depart {utilisateur.username}."
                    client.publish("rfid/response", response)
                    print(f"Réponse envoyée: {response}")
                except Presence.DoesNotExist:
                    response = f"Aucune heure d'arrivee trouvée pour {utilisateur.username}."
                    client.publish("rfid/response", response)
                    print(f"Réponse envoyée: {response}")
        except Utilisateur.DoesNotExist:
            response = "non trouve"
            client.publish("rfid/response", response)
            print(f"Réponse envoyée: {response}")
    except Exception as e:
        print(f"Erreur lors du traitement du message : {e}")


def start_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(mqtt_user, mqtt_password)
    client.connect(mqtt_server, mqtt_port, 60)
    client.loop_start()



