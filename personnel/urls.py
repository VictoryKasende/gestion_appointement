from django.urls import path, include

from personnel import views

app_name = 'personnel'

urlpatterns = [
    path('', views.remuneration, name='remuneration'),
    path('create/fiche', views.fichedepaie_add, name='fichedepaie_add'),
    path('modifier/fiche/<int:fiche_id>/', views.modifier_fichedepaie, name='modifier_fichedepaie'),
    path('affiche/fiche/<int:fiche_id>/', views.fichedepaie_detail, name='fichedepaie_detail'),
    path('print/<int:fiche_id>/', views.print_fichedepaie, name='print_fichedepaie'),
    path('demande-credit/', views.demande_credit, name='demande_credit'),
    path('traiter-demande-credit/', views.traiter_demande_credit, name='traiter_demande_credit'),
    path('approuver-credit/<int:id>/', views.approuver_credit, name='approuver_credit'),
    path('rejeter-credit/<int:id>/', views.rejeter_credit, name='rejeter_credit'),
    path('voir-detail-credit/<int:id>/', views.voir_detail_credit, name='voir_detail_credit'),
    path('presence', views.presence, name='presence'),
    path('notifier/heures/', views.heures_supplementaires, name='heure_supplementaire'),
    path('edit/<int:heure_id>/', views.edit_overtime, name='edit_overtime'),
    path('delete/<int:heure_id>/', views.delete_overtime, name='delete_overtime'),
    path('rapport/presences/', views.rapport_presences, name='rapport_presences'),
    path('rapport/imprimer/<int:agent_id>/', views.imprimer_rapport, name='imprimer_rapport'),
]
