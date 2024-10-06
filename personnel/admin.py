from django.contrib import admin
from .models import Credit, FichePaie, Presence, HeureSupplementaire


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = ('agent', 'montant', 'date', 'type_credit')
    search_fields = ('agent__username', 'type_credit')
    list_filter = ('type_credit', 'date')


@admin.register(FichePaie)
class FichePaieAdmin(admin.ModelAdmin):
    list_display = ('employe', 'salaire_base', 'net_a_payer', 'gestionnaire_paie', 'date_creation')
    search_fields = ('employe__username', 'gestionnaire_paie__username')
    list_filter = ('date_creation', )
    readonly_fields = ('total_brut', 'total_retenues', 'net_a_payer', 'allocation_familiale', 'montant_net')


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ('agent', 'date', 'heure_arrivee', 'heure_depart', 'heures_travail', 'statut')
    search_fields = ('agent__username',)
    list_filter = ('date',)
    date_hierarchy = 'date'


@admin.register(HeureSupplementaire)
class HeureSupplementaireAdmin(admin.ModelAdmin):
    list_display = ('agent', 'nombre_heures', 'date', 'fiche_paie')
    search_fields = ('agent__username',)
    list_filter = ('date',)
    date_hierarchy = 'date'
