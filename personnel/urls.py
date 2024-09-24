from django.urls import path, include

from personnel import views

app_name = 'personnel'

urlpatterns = [
    path('', views.remuneration, name='remuneration'),
    path('create/fiche', views.fichedepaie_add, name='fichedepaie_add'),
    path('modifier/fiche/<int:fiche_id>/', views.modifier_fichedepaie, name='modifier_fichedepaie'),
    path('affiche/fiche/<int:fiche_id>/', views.fichedepaie_detail, name='fichedepaie_detail'),
    path('print/<int:fiche_id>/', views.print_fichedepaie, name='print_fichedepaie'),
    path('demande/credit/', views.demande_credit, name='demande_credit'),
    path('traiter/demande/credit/', views.traiter_demande_credit, name='traiter_demande_credit'),
    path('presence', views.presence, name='presence'),

    path('notifier/heures/', views.heure_supplementaire, name='heure_supplementaire'),
    path('rapport/presences/', views.rapport_presences, name='rapport_presences'),
]
