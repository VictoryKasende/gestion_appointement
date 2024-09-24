from django.core.exceptions import ValidationError
from django.db import models
from datetime import datetime, time
import calendar
from django.utils import timezone

from authentication.models import Utilisateur


class Credit(models.Model):
    TYPE_CREDIT_CHOICES = [
        ('avance', 'Avance sur salaire'),
        ('bonus', 'Bonus'),
        ('prime', 'Prime'),
        ('autre', 'Autre'),
    ]

    agent = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    type_credit = models.CharField(max_length=50, choices=TYPE_CREDIT_CHOICES, default='autre')

    def __str__(self):
        return f"Crédit de {self.montant} pour {self.agent.username} le {self.date} ({self.get_type_credit_display()})"


class FichePaie(models.Model):
    employe = models.ForeignKey(Utilisateur, on_delete=models.CASCADE,
                                related_name='fiches_paie')  # Référence à l'employé ou utilisateur
    gestionnaire_paie = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True,
                                          related_name='fiches_etablies')  # Gestionnaire responsable de l'établissement de la fiche

    # Rémunération
    salaire_base = models.DecimalField(max_digits=10, decimal_places=2)  # Salaire de base (FC)
    salaire_base_retenu = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Salaire de base (FC)
    conges_payes = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Montant pour les congés payés
    jour_maladie = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Jours de maladie ou accident
    heures_supplementaires = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Heures supplémentaires
    jour_ferie_dimanche = models.DecimalField(max_digits=10, decimal_places=2,
                                              default=0)  # Paiement des jours fériés ou dimanches
    prime_intensite = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Prime d'intensité
    divers_remuneration = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Autres paiements divers

    # Indemnités
    indemnites_logement = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Indemnité de logement
    indemnites_transport = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Indemnité de transport

    # Retenues
    cotisation_syndicale = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Cotisation syndicale
    autres_retenues = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Autres retenues divers

    # Calculs totaux
    total_brut = models.DecimalField(max_digits=10, decimal_places=2)  # Total brut (Salaire + Indemnités)
    total_retenues = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total des retenues
    net_a_payer = models.DecimalField(max_digits=10, decimal_places=2)  # Montant net à payer après retenues

    # Allocations familiales
    nombre_enfants = models.IntegerField(default=0)  # Nombre d'enfants de l'employé
    taux_allocation_familiale = models.DecimalField(max_digits=10, decimal_places=2,
                                                    default=0)  # Taux journalier pour allocation familiale
    allocation_familiale = models.DecimalField(max_digits=10, decimal_places=2,
                                               default=0)  # Montant total de l'allocation familiale

    # Montant total final après allocations familiales
    montant_net = models.DecimalField(max_digits=10, decimal_places=2)  # Montant total final à payer

    # Date de création de la fiche de paie
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de création de la fiche

    def __str__(self):
        return f"Fiche de paie de {self.employe.username} (Établie par {self.gestionnaire_paie.username})"


class Presence(models.Model):
    agent = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)  # L'agent concerné par la présence
    fiche_paie = models.ForeignKey(FichePaie, on_delete=models.SET_NULL, null=True,
                                   blank=True)  # Référence à la fiche de paie, peut être vide
    date = models.DateField(auto_now_add=True)  # Date de la présence
    heure_arrivee = models.TimeField()  # Heure d'arrivée de l'agent
    heure_depart = models.TimeField()  # Heure de départ de l'agent
    heures_travail = models.DecimalField(max_digits=5, decimal_places=2, null=True,
                                         blank=True)  # Calcul des heures de travail (facultatif)

    def clean(self):
        # Définir les plages d'heures valides
        plage_arrivee_min = time(8, 0)  # 08:00
        plage_arrivee_max = time(8, 30)  # 08:30
        plage_depart_min = time(16, 0)  # 16:00
        plage_depart_max = time(16, 30)  # 16:30

        # Vérifier que les champs ne sont pas vides
        if self.heure_arrivee is None:
            raise ValidationError("L'heure d'arrivée est obligatoire.")
        if self.heure_depart is None:
            raise ValidationError("L'heure de départ est obligatoire.")

        # Validation de l'heure d'arrivée
        if not (plage_arrivee_min <= self.heure_arrivee <= plage_arrivee_max):
            raise ValidationError("L'heure d'arrivée doit être comprise entre 08h00 et 08h30.")

        # Validation de l'heure de départ
        if not (plage_depart_min <= self.heure_depart <= plage_depart_max):
            raise ValidationError("L'heure de départ doit être comprise entre 16h00 et 16h30.")

        # Validation pour s'assurer que l'heure de départ est après l'heure d'arrivée
        if self.heure_depart <= self.heure_arrivee:
            raise ValidationError("L'heure de départ doit être après l'heure d'arrivée.")

    def calcul_heures_travail(self):
        """
        Méthode pour calculer la durée de travail en heures en fonction des heures d'arrivée et de départ.
        """
        if self.heure_arrivee and self.heure_depart:
            arrivee = datetime.combine(self.date, self.heure_arrivee)
            depart = datetime.combine(self.date, self.heure_depart)
            delta = depart - arrivee
            self.heures_travail = delta.total_seconds() / 3600  # Convertir en heures
            self.save()

    @staticmethod
    def nombre_de_presences_mois_courant(agent):
        """
        Méthode statique pour calculer le nombre de présences de l'agent pour le mois en cours
        où l'heure d'arrivée et l'heure de départ sont renseignées.
        """
        # Obtenir la date actuelle
        now = timezone.now()

        # Premier jour du mois en cours
        first_day_of_month = now.replace(day=1)

        # Dernier jour du mois en cours
        last_day_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1])

        # Filtrer les présences de l'agent pour le mois en cours avec heure d'arrivée et heure de départ non nulles
        nombre_presences = Presence.objects.filter(
            agent=agent,
            date__range=(first_day_of_month, last_day_of_month),
            heure_arrivee__isnull=False,
            heure_depart__isnull=False
        ).count()

        return nombre_presences

    @staticmethod
    def total_heures_travail_mois_courant(agent):
        """
        Méthode statique pour calculer le total des heures de travail de l'agent pour le mois en cours
        où l'heure d'arrivée et l'heure de départ sont renseignées.
        """
        # Obtenir la date actuelle
        now = timezone.now()

        # Premier jour du mois en cours
        first_day_of_month = now.replace(day=1)

        # Dernier jour du mois en cours
        last_day_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1])

        # Filtrer les présences de l'agent pour le mois en cours avec heure d'arrivée et heure de départ non nulles
        presences = Presence.objects.filter(
            agent=agent,
            date__range=(first_day_of_month, last_day_of_month),
            heure_arrivee__isnull=False,
            heure_depart__isnull=False
        )

        # Calculer le total des heures travaillées
        total_heures_travail = 0
        for presence in presences:
            # Si la durée de travail a déjà été calculée, l'utiliser
            if presence.heures_travail:
                total_heures_travail += presence.heures_travail
            else:
                # Sinon, calculer la durée de travail à partir des heures d'arrivée et de départ
                arrivee = datetime.combine(presence.date, presence.heure_arrivee)
                depart = datetime.combine(presence.date, presence.heure_depart)
                delta = depart - arrivee
                heures_travail = delta.total_seconds() / 3600  # Convertir en heures
                total_heures_travail += heures_travail

        return total_heures_travail

    def __str__(self):
        return f"Présence de {self.agent.username} le {self.date}"

    class Meta:
        verbose_name = 'Présence'
        verbose_name_plural = 'Présences'
        ordering = ['date']


class HeureSupplementaire(models.Model):
    agent = models.ForeignKey(Utilisateur,
                              on_delete=models.CASCADE)  # L'agent qui a effectué les heures supplémentaires
    fiche_paie = models.ForeignKey(FichePaie, on_delete=models.SET_NULL, null=True,
                                   blank=True)  # Référence à la fiche de paie associée
    nombre_heures = models.DecimalField(max_digits=5, decimal_places=2)  # Nombre d'heures supplémentaires effectuées
    date = models.DateField(auto_now_add=True)  # Date à laquelle les heures supplémentaires ont été effectuées

    def __str__(self):
        return f"{self.nombre_heures} heures supplémentaires pour {self.agent.username} le {self.date}"

    class Meta:
        verbose_name = 'Heure Supplémentaire'
        verbose_name_plural = 'Heures Supplémentaires'
        ordering = ['date']
