from django.apps import AppConfig
from threading import Thread


class PersonnelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'personnel'

    def ready(self):
        from personnel.mqtt_service import start_mqtt_client
        Thread(target=start_mqtt_client).start()