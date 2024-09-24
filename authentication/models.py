from django.contrib.auth.models import AbstractUser, Group
from django.core.validators import RegexValidator
from django.db import models

from django.contrib.auth.models import AbstractUser, Group
from django.core.validators import RegexValidator
from django.db import models


class Utilisateur(AbstractUser):
    MANAGER = 'Manager'
    ADMINISTRATEUR_IT = 'Administrateur IT'
    GESTIONNAIRE_PAIE = 'Gestionnaire Paie'
    AGENT = 'Agent'

    ROLE_CHOICES = (
        (MANAGER, 'Manager'),
        (ADMINISTRATEUR_IT, 'Administrateur IT'),
        (GESTIONNAIRE_PAIE, 'Gestionnaire Paie'),
        (AGENT, 'Agent'),
    )

    # Ajout des champs supplémentaires
    profile_photo = models.ImageField(verbose_name='Photo de profil', upload_to='profile_photos/', null=True,
                                      blank=True)
    genre = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin')])
    telephone = models.CharField(max_length=15, validators=[
        RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Le numéro de téléphone doit être entré au format: '+999999999'. Jusqu'à 15 chiffres autorisés."
        )
    ])
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, verbose_name='Rôle')

    # Ajout du numéro RFID de l'agent
    rfid_number = models.CharField(max_length=50, verbose_name='Numéro RFID', unique=True, null=True, blank=True)
    matricule = models.CharField(max_length=50, verbose_name='Matricule', unique=True, null=True, blank=True)

    # Attributs supplémentaires pour l'agent
    poste = models.CharField(max_length=100, verbose_name='Poste', null=True, blank=True)
    departement = models.CharField(max_length=100, verbose_name='Département', null=True, blank=True)
    date_entree = models.DateField(verbose_name="Date d'entrée", null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Gestion des groupes en fonction du rôle de l'utilisateur
        if self.role == self.MANAGER:
            group, _ = Group.objects.get_or_create(name='Manager')
            group.user_set.add(self)
        elif self.role == self.ADMINISTRATEUR_IT:
            group, _ = Group.objects.get_or_create(name='Administrateur IT')
            group.user_set.add(self)
        elif self.role == self.GESTIONNAIRE_PAIE:
            group, _ = Group.objects.get_or_create(name='Gestionnaire Paie')
            group.user_set.add(self)
        elif self.role == self.AGENT:
            group, _ = Group.objects.get_or_create(name='Agent')
            group.user_set.add(self)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

