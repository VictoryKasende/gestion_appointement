from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Sum
from datetime import date
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone
import calendar

from .models import Utilisateur, FichePaie, Credit, HeureSupplementaire, Presence
from .forms import MoisFiltreForm

# Obtenir la date actuelle
now = timezone.now()


def remuneration(request):
    # Nombre total d'agents
    total_agents = Utilisateur.objects.filter(role=Utilisateur.AGENT).count()

    # Salaire moyen des agents (basé sur les fiches de paie)
    salaire_moyen = FichePaie.objects.aggregate(Avg('salaire_base'))['salaire_base__avg'] or 0

    # Obtenir le mois et l'année courants
    aujourdhui = date.today()
    mois_courant = aujourdhui.month
    annee_courante = aujourdhui.year

    # Calculer le total des salaires versés ce mois-ci
    total_salaires = FichePaie.objects.filter(date_creation__year=annee_courante, date_creation__month=mois_courant).aggregate(
        Sum('net_a_payer'))['net_a_payer__sum'] or 0

    # Total des bonus distribués ce mois
    premier_jour_mois = date(annee_courante, mois_courant, 1)
    total_bonus = Credit.objects.filter(type_credit='bonus', date__gte=premier_jour_mois).aggregate(Sum('montant'))[
                      'montant__sum'] or 0

    # Filtrer les présences pour le mois et l'année en cours
    presences = Presence.objects.filter(date__year=annee_courante, date__month=mois_courant).select_related('agent')

    # Gérer le filtrage par mois
    if request.method == 'GET':
        form = MoisFiltreForm(request.GET)
        if form.is_valid():
            mois = form.cleaned_data.get('mois')
            if mois:
                presences = Presence.objects.filter(date__month=int(mois)).select_related(
                    'agent')
    else:
        form = MoisFiltreForm()

    # Créer un dictionnaire pour éviter les doublons par agent
    fiches_paie_dict = {}

    for presence in presences:
        agent_id = presence.agent.id

        # Vérifie si l'agent est déjà traité
        if agent_id not in fiches_paie_dict:
            # Appel des méthodes de classe avec l'agent en paramètre
            heures_travail = Presence.total_heures_travail_mois_courant(presence.agent)  # Méthode de classe
            nombre_jours = Presence.nombre_de_presences_mois_courant(presence.agent)  # Méthode de classe
            print(presence.fiche_paie)
            # Stocke les données de la fiche de paie dans un dictionnaire pour éviter les doublons
            fiches_paie_dict[agent_id] = {
                'presence': presence,
                'heures_travail': heures_travail,
                'nombre_jours': nombre_jours,
            }

    # Convertir le dictionnaire en liste pour le contexte
    fiches_paie = list(fiches_paie_dict.values())


    # Contexte pour passer à la vue
    context = {
        'fiches_paie': fiches_paie,
        'total_agents': total_agents,
        'salaire_moyen': round(salaire_moyen, 2),
        'total_salaires': round(total_salaires, 2),
        'total_bonus': round(total_bonus, 2),
        'form': form
    }
    return render(request, 'personnel/remuneration.html', context)


def fichedepaie_add(request):
    if request.method == 'POST':
        employe_id = request.POST.get('employe')

        # Gestion des champs qui peuvent être vides
        salaire_base = float(request.POST.get('salaire_base') or 0)
        conges_payes = float(request.POST.get('conges_payes') or 0)
        jour_maladie = float(request.POST.get('jour_maladie') or 0)
        heures_supplementaires = float(request.POST.get('heures_supplementaires') or 0)
        jour_ferie_dimanche = float(request.POST.get('jour_ferie_dimanche') or 0)
        prime_intensite = float(request.POST.get('prime_intensite') or 0)
        divers_remuneration = float(request.POST.get('divers_remuneration') or 0)
        indemnites_logement = float(request.POST.get('indemnites_logement') or 0)
        indemnites_transport = float(request.POST.get('indemnites_transport') or 0)

        # Champs optionnels avec valeurs par défaut si vide
        cotisation_syndicale = float(request.POST.get('cotisation_syndicale') or 0)
        autres_retenues = float(request.POST.get('autres_retenues') or 0)

        nombre_enfants = int(request.POST.get('nombre_enfants') or 0)
        taux_allocation_familiale = float(request.POST.get('taux_allocation_familiale') or 0)

        # Récupération de l'employé
        employe = get_object_or_404(Utilisateur, id=employe_id)

        # Premier et dernier jour du mois en cours
        first_day_of_month = now.replace(day=1)
        last_day_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1])

        # Calculer le nombre de présences pour l'agent durant le mois en cours
        jours_presence = Presence.objects.filter(
            agent=employe,
            date__range=(first_day_of_month, last_day_of_month)
        ).count()

        # Calcul des heures supplémentaires
        heures_supplementaires_total = HeureSupplementaire.objects.filter(agent=employe).aggregate(
            total_heures=Sum('nombre_heures')
        )['total_heures'] or 0

        # Calcul du total brut : salaire_base * jours de présence + heures supplémentaires
        total_brut = (salaire_base * jours_presence) + (heures_supplementaires * heures_supplementaires_total)
        total_brut += jour_ferie_dimanche + prime_intensite + divers_remuneration

        # Calcul du total des retenues
        total_retenues = cotisation_syndicale + autres_retenues + indemnites_logement + indemnites_transport

        # Calcul salaire base retenu
        salaire_base_retenu = salaire_base * jours_presence

        # Calcul du net à payer (total brut - retenues)
        net_a_payer = total_brut - total_retenues

        # Calcul des allocations familiales
        allocation_familiale = nombre_enfants * taux_allocation_familiale

        # Calcul du montant net final
        montant_net = net_a_payer + allocation_familiale

        # Création de la fiche de paie
        fiche_paie = FichePaie.objects.create(
            employe=employe,
            gestionnaire_paie=request.user,  # Associer le gestionnaire qui crée la fiche
            salaire_base=salaire_base,
            salaire_base_retenu = salaire_base_retenu,
            conges_payes=conges_payes,
            jour_maladie=jour_maladie,
            heures_supplementaires=heures_supplementaires_total,
            jour_ferie_dimanche=jour_ferie_dimanche,
            prime_intensite=prime_intensite,
            divers_remuneration=divers_remuneration,
            indemnites_logement=indemnites_logement,
            indemnites_transport=indemnites_transport,
            cotisation_syndicale=cotisation_syndicale,
            autres_retenues=autres_retenues,
            total_brut=total_brut,
            total_retenues=total_retenues,
            net_a_payer=net_a_payer,
            nombre_enfants=nombre_enfants,
            taux_allocation_familiale=taux_allocation_familiale,
            allocation_familiale=allocation_familiale,
            montant_net=montant_net,
        )

        messages.success(request, 'Fiche de paie créée avec succès.')
        return redirect('personnel:remuneration')

    # Si la méthode est GET, afficher le formulaire
    employes = Utilisateur.objects.all()  # Récupérer tous les employés
    return render(request, 'personnel/add_fiche.html', {'employes': employes})


def modifier_fichedepaie(request, fiche_id):
    # Récupérer la fiche de paie à modifier
    fiche = get_object_or_404(FichePaie, id=fiche_id)

    if request.method == 'POST':
        employe_id = request.POST.get('employe')
        salaire_base = Decimal(request.POST.get('salaire_base', 0))
        conges_payes = Decimal(request.POST.get('conges_payes', 0))
        jour_maladie = Decimal(request.POST.get('jour_maladie', 0))
        heures_supplementaires = Decimal(request.POST.get('heures_supplementaires', 0))
        jour_ferie_dimanche = Decimal(request.POST.get('jour_ferie_dimanche', 0))
        prime_intensite = Decimal(request.POST.get('prime_intensite', 0))
        divers_remuneration = Decimal(request.POST.get('divers_remuneration', 0))
        indemnites_logement = Decimal(request.POST.get('indemnites_logement', 0))
        indemnites_transport = Decimal(request.POST.get('indemnites_transport', 0))

        # Gérer les champs facultatifs
        cotisation_syndicale = Decimal(request.POST.get('cotisation_syndicale') or 0)
        autres_retenues = Decimal(request.POST.get('autres_retenues') or 0)

        nombre_enfants = int(request.POST.get('nombre_enfants', 0))
        taux_allocation_familiale = Decimal(request.POST.get('taux_allocation_familiale', 0))

        # Récupération de l'employé
        employe = get_object_or_404(Utilisateur, id=employe_id)

        # Premier et dernier jour du mois en cours
        first_day_of_month = now.replace(day=1)
        last_day_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1])

        # Calculer le nombre de présences pour l'agent durant le mois en cours
        jours_presence = Presence.objects.filter(
            agent=employe,
            date__range=(first_day_of_month, last_day_of_month)
        ).count()

        # Calcul des heures supplémentaires
        heures_supplementaires_total = HeureSupplementaire.objects.filter(agent=employe).aggregate(
            total_heures=Sum('nombre_heures')
        )['total_heures'] or Decimal(0)

        # Calcul du total brut : salaire_base * jours de présence + heures supplémentaires
        total_brut = (salaire_base * Decimal(jours_presence)) + (heures_supplementaires * heures_supplementaires_total)
        total_brut += jour_ferie_dimanche + prime_intensite + divers_remuneration

        #Calcul salaire base retenu
        salaire_base_retenu = salaire_base * jours_presence

        # Calcul du total des retenues
        total_retenues = cotisation_syndicale + autres_retenues + indemnites_logement + indemnites_transport

        # Calcul du net à payer (total brut - retenues)
        net_a_payer = total_brut - total_retenues

        # Calcul des allocations familiales
        allocation_familiale = nombre_enfants * taux_allocation_familiale

        # Calcul du montant net final
        montant_net = net_a_payer + allocation_familiale

        # Mise à jour de la fiche de paie avec les nouvelles données
        fiche.employe = employe
        fiche.salaire_base = salaire_base
        fiche.salaire_base_retenu = salaire_base_retenu
        fiche.conges_payes = conges_payes
        fiche.jour_maladie = jour_maladie
        fiche.heures_supplementaires = heures_supplementaires_total
        fiche.jour_ferie_dimanche = jour_ferie_dimanche
        fiche.prime_intensite = prime_intensite
        fiche.divers_remuneration = divers_remuneration
        fiche.indemnites_logement = indemnites_logement
        fiche.indemnites_transport = indemnites_transport
        fiche.cotisation_syndicale = cotisation_syndicale
        fiche.autres_retenues = autres_retenues
        fiche.total_brut = total_brut
        fiche.total_retenues = total_retenues
        fiche.net_a_payer = net_a_payer
        fiche.nombre_enfants = nombre_enfants
        fiche.taux_allocation_familiale = taux_allocation_familiale
        fiche.allocation_familiale = allocation_familiale
        fiche.montant_net = montant_net

        # Sauvegarder les modifications dans la base de données
        fiche.save()

        # Ajouter un message de succès et rediriger vers la liste des fiches de paie
        messages.success(request, 'Fiche de paie modifiée avec succès.')
        return redirect('personnel:remuneration')  # Redirection vers une page adéquate

    # Si la méthode est GET, pré-remplir le formulaire avec les données existantes
    employes = Utilisateur.objects.all()  # Récupérer tous les employés

    return render(request, 'personnel/update_fiche.html', {
        'fiche': fiche,
        'employes': employes,
    })


def fichedepaie_detail(request, fiche_id):
    fiche = get_object_or_404(FichePaie, id=fiche_id)
    return render(request, 'personnel/detail_fiche.html', {'fiche': fiche})


def print_fichedepaie(request, fiche_id):
    fiche = get_object_or_404(FichePaie, id=fiche_id)
    return render(request, 'personnel/print_fichedepaie.html', {'fiche': fiche})


def demande_credit(request):
    return render(request, 'personnel/demande_credit.html')


def traiter_demande_credit(request):
    return render(request, 'personnel/traiter_demande.html')


def heure_supplementaire(request):
    return render(request, 'personnel/heure_supplementaires.html')


def rapport_presences(request):
    return render(request, 'personnel/rapport_presence.html')


def presence(request):
    return render(request, 'personnel/presence.html')
