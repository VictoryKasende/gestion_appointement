from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Sum, Count, Q
from datetime import date
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone
import calendar
from django.utils.timezone import now
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import Utilisateur, FichePaie, Credit, HeureSupplementaire, Presence
from .forms import MoisFiltreForm, HeureSupplementaireForm

MANAGER = 'Manager'
ADMINISTRATEUR_IT = 'Administrateur IT'
GESTIONNAIRE_PAIE = 'Gestionnaire Paie'
AGENT = 'Agent'


def is_gestionnaire(user):
    return user.role == GESTIONNAIRE_PAIE


def is_agent(user):
    return user.role == AGENT


def is_manager(user):
    return user.role == MANAGER


@login_required
@user_passes_test(is_gestionnaire)
def remuneration(request):
    # Obtenir la date actuelle
    aujourdhui = date.today()
    mois_courant = aujourdhui.month
    annee_courante = aujourdhui.year

    # Gérer le filtrage par mois via GET
    if request.method == 'GET':
        form = MoisFiltreForm(request.GET)
        if form.is_valid():
            mois = form.cleaned_data.get('mois')
            if mois:
                mois_courant = int(mois)  # Remplace le mois courant par celui sélectionné
        else:
            form = MoisFiltreForm()
    else:
        form = MoisFiltreForm()

    # Nombre total d'agents
    total_agents = Utilisateur.objects.filter(role=Utilisateur.AGENT).count()

    # Salaire moyen des agents pour le mois sélectionné
    salaire_moyen = FichePaie.objects.filter(
        date_creation__year=annee_courante,
        date_creation__month=mois_courant
    ).aggregate(Avg('salaire_base'))['salaire_base__avg'] or 0

    # Calculer le total des salaires versés pour le mois sélectionné
    total_salaires = FichePaie.objects.filter(
        date_creation__year=annee_courante,
        date_creation__month=mois_courant
    ).aggregate(Sum('net_a_payer'))['net_a_payer__sum'] or 0

    # Total des bonus distribués pour le mois sélectionné
    premier_jour_mois = date(annee_courante, mois_courant, 1)
    total_bonus = Credit.objects.filter(
        type_credit='bonus',
        date__gte=premier_jour_mois
    ).aggregate(Sum('montant'))['montant__sum'] or 0

    # Filtrer les fiches de paie du mois sélectionné et récupérer les informations des présences via annotations
    fiches_paie = FichePaie.objects.filter(
        date_creation__year=annee_courante,
        date_creation__month=mois_courant
    ).select_related('employe').annotate(
        heures_travail=Sum('employe__presence__heures_travail', filter=Q(employe__presence__date__month=mois_courant)),
        nombre_jours=Count('employe__presence__id', filter=Q(employe__presence__date__month=mois_courant))
    )

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


@login_required
@user_passes_test(is_gestionnaire)
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
        first_day_of_month = now().replace(day=1)
        last_day_of_month = now().replace(day=calendar.monthrange(now().year, now().month)[1])

        # Calculer le nombre de présences pour l'agent durant le mois en cours
        jours_presence = Presence.objects.filter(
            agent=employe,
            date__range=(first_day_of_month, last_day_of_month)
        ).count()

        # Calcul des heures supplémentaires pour le mois en cours
        heures_supplementaires_total = HeureSupplementaire.objects.filter(
            agent=employe,
            date__range=(first_day_of_month, last_day_of_month)
        ).aggregate(
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
            salaire_base_retenu=salaire_base_retenu,
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


@login_required
@user_passes_test(is_gestionnaire)
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
        current_now = now()  # Appel de la fonction now() pour obtenir l'heure actuelle
        first_day_of_month = current_now.replace(day=1)
        last_day_of_month = current_now.replace(day=calendar.monthrange(current_now.year, current_now.month)[1])

        # Calculer le nombre de présences pour l'agent durant le mois en cours
        jours_presence = Presence.objects.filter(
            agent=employe,
            date__range=(first_day_of_month, last_day_of_month)
        ).count()

        print(jours_presence)
        # Calcul des heures supplémentaires pour le mois en cours
        heures_supplementaires_total = HeureSupplementaire.objects.filter(
            agent=employe,
            date__range=(first_day_of_month, last_day_of_month)
        ).aggregate(
            total_heures=Sum('nombre_heures')
        )['total_heures'] or 0

        # Calcul du total brut
        total_brut = (salaire_base * Decimal(jours_presence)) + (heures_supplementaires * heures_supplementaires_total)
        total_brut += jour_ferie_dimanche + prime_intensite + divers_remuneration

        # Calcul salaire base retenu
        salaire_base_retenu = salaire_base * jours_presence

        # Calcul du total des retenues
        total_retenues = cotisation_syndicale + autres_retenues + indemnites_logement + indemnites_transport

        # Calcul du net à payer
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


@login_required
@user_passes_test(is_gestionnaire)
def fichedepaie_detail(request, fiche_id):
    fiche = get_object_or_404(FichePaie, id=fiche_id)
    return render(request, 'personnel/detail_fiche.html', {'fiche': fiche})


@login_required
@user_passes_test(is_gestionnaire)
def print_fichedepaie(request, fiche_id):
    fiche = get_object_or_404(FichePaie, id=fiche_id)
    return render(request, 'personnel/print_fichedepaie.html', {'fiche': fiche})


@login_required
@user_passes_test(is_agent)
def demande_credit(request):
    if request.method == 'POST':
        # Récupérer les données du formulaire
        montant = request.POST.get('montant')
        type_credit = request.POST.get('type_credit')
        date_demande = request.POST.get('date')
        commentaires = request.POST.get('comments')

        # Validation simple pour s'assurer que tous les champs requis sont remplis
        if montant and type_credit and date_demande:
            # Créer une nouvelle demande de crédit
            Credit.objects.create(
                agent=request.user,
                montant=montant,
                type_credit=type_credit,
                date=date_demande
            )
            messages.success(request, 'Votre demande de crédit a été soumise avec succès.')
            return redirect('personnel:demande_credit')  # Rediriger vers la même page après la soumission
        else:
            messages.error(request, 'Veuillez remplir tous les champs requis.')

    # Récupérer toutes les demandes de crédit pour l'agent connecté
    demandes = Credit.objects.filter(agent=request.user).order_by('-date')[:5]

    context = {
        'demandes': demandes,
        'today': timezone.now(),  # Passer la date du jour pour préremplir le champ date
    }

    return render(request, 'personnel/demande_credit.html', context)


@login_required
@user_passes_test(is_manager)
def traiter_demande_credit(request):
    # Récupérer toutes les demandes
    demandes = Credit.objects.all()

    # Statistiques pour l'affichage
    total_demandes = demandes.count()
    montant_total = demandes.aggregate(Sum('montant'))['montant__sum'] or 0
    montant_approuve = demandes.filter(statut='approuve').aggregate(Sum('montant'))['montant__sum'] or 0
    montant_refuse = demandes.filter(statut='rejete').aggregate(Sum('montant'))['montant__sum'] or 0

    context = {
        'demandes': demandes,
        'total_demandes': total_demandes,
        'montant_total': montant_total,
        'montant_approuve': montant_approuve,
        'montant_refuse': montant_refuse,
    }

    return render(request, 'personnel/traiter_demande.html', context)


@login_required
@user_passes_test(is_manager)
def approuver_credit(request, id):
    credit = get_object_or_404(Credit, id=id)
    credit.statut = 'approuve'
    credit.save()
    messages.success(request, f'La demande de crédit pour {credit.agent.username} a été approuvée.')
    return redirect('personnel:traiter_demande_credit')


@login_required
@user_passes_test(is_manager)
def rejeter_credit(request, id):
    credit = get_object_or_404(Credit, id=id)
    credit.statut = 'rejete'
    credit.save()
    messages.error(request, f'La demande de crédit pour {credit.agent.username} a été rejetée.')
    return redirect('personnel:traiter_demande_credit')


@login_required
@user_passes_test(is_manager)
def voir_detail_credit(request, id):
    demande = get_object_or_404(Credit, id=id)
    return render(request, 'personnel/detail_credit.html', {'demande': demande})


@login_required
@user_passes_test(is_agent)
def heures_supplementaires(request):
    if request.method == 'POST':
        # Récupération des données du formulaire
        heures_travaillees = request.POST.get('hours-worked')
        motif = request.POST.get('reason')

        if heures_travaillees:
            # Récupérer l'utilisateur connecté
            utilisateur = request.user

            # Obtenir l'année et le mois en cours
            maintenant = now()
            annee_courante = maintenant.year
            mois_courant = maintenant.month

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

            try:
                # Création de l'enregistrement d'heures supplémentaires
                heures_supp = HeureSupplementaire(
                    agent=utilisateur,  # L'utilisateur connecté
                    nombre_heures=heures_travaillees,
                    fiche_paie=fiche_paie,  # La fiche de paie récupérée
                    date=timezone.now(),
                    motif=motif,
                )
                heures_supp.save()

                messages.success(request, 'Heures supplémentaires ajoutées avec succès.')
                return redirect('personnel:heure_supplementaire')
            except Exception as e:
                messages.error(request, f'Erreur lors de l\'ajout des heures supplémentaires: Nombre trop grand ')
        else:
            messages.error(request, 'Veuillez fournir le nombre d\'heures travaillées.')

    # Affichage de la liste des heures supplémentaires
    heures_list = HeureSupplementaire.objects.filter(agent=request.user).order_by('-date')[:5]

    context = {
        'heures_list': heures_list,
    }
    return render(request, 'personnel/heure_supplementaires.html', context)


@login_required
@user_passes_test(is_agent)
def edit_overtime(request, heure_id):
    # Récupérer l'instance des heures supplémentaires à modifier
    heure_supp = get_object_or_404(HeureSupplementaire, id=heure_id)

    if request.method == 'POST':
        form = HeureSupplementaireForm(request.POST, instance=heure_supp)
        print(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Heure supplémentaire modifiée avec succès.")
            return redirect('personnel:heure_supplementaire')  # Rediriger vers la liste des heures supplémentaires
    else:
        form = HeureSupplementaireForm(instance=heure_supp)

    return render(request, 'personnel/edit_overtime.html', {'form': form, 'heure_supp': heure_supp})


@login_required
@user_passes_test(is_agent)
def delete_overtime(request, heure_id):
    heure_supp = get_object_or_404(HeureSupplementaire, id=heure_id)

    if request.method == 'POST':  # Vérification si une confirmation est faite via POST
        heure_supp.delete()
        messages.success(request, "Heure supplémentaire supprimée avec succès.")
        return redirect('personnel:heure_supplementaire')  # Rediriger vers la liste des heures supplémentaires

    return render(request, 'personnel/delete_overtime.html', {'heure_supp': heure_supp})


@login_required
@user_passes_test(is_gestionnaire)
def rapport_presences(request):
    # Total des employés avec le rôle 'Agent'
    total_employes = Utilisateur.objects.filter(role='Agent').count()

    # Présences ce mois, filtrées par statut 'P'
    presences_mois = Presence.objects.filter(date__month=now().month, statut='P')
    total_presences = presences_mois.count()

    # Absences ce mois, filtrées par statut 'A'
    absences_mois = Presence.objects.filter(date__month=now().month, statut='A')
    total_absences = absences_mois.count()

    # Nombre de jours dans le mois en cours
    month_days = calendar.monthrange(now().year, now().month)[1]

    # Taux de présence et d'absence
    taux_presence = (total_presences / (total_employes * month_days) * 100) if total_employes > 0 else 0
    taux_absence = (total_absences / (total_employes * month_days) * 100) if total_employes > 0 else 0

    # Obtenir les données de présence (jours travaillés et heures travaillées) par agent pour le mois en cours
    details_presences = (
        Presence.objects.filter(date__month=now().month)
        .values('agent__id', 'agent__first_name', 'agent__last_name')
        .annotate(
            nombres_de_jours=Count('date'),
            heures_travaillees=Sum('heures_travail')
        )
    )

    # Obtenir les heures supplémentaires par agent pour le mois en cours
    details_heures_supp = (
        HeureSupplementaire.objects.filter(date__month=now().month)
        .values('agent__id', 'agent__first_name', 'agent__last_name')
        .annotate(
            heures_supplementaires=Sum('nombre_heures')
        )
    )

    # Créer un dictionnaire pour accéder aux heures supplémentaires par agent
    heures_supp_dict = {
        f"{hs['agent__first_name']} {hs['agent__last_name']}": hs['heures_supplementaires']
        for hs in details_heures_supp
    }

    # Fusionner les deux ensembles de données
    rapport = []
    for presence in details_presences:
        agent_name = f"{presence['agent__first_name']} {presence['agent__last_name']}"
        heures_supplementaires = heures_supp_dict.get(agent_name,
                                                      0)  # Récupérer les heures supplémentaires ou 0 si absent

        rapport.append({
            'employe': agent_name,
            'jours': presence['nombres_de_jours'],
            'heures_travaillees': presence['heures_travaillees'],
            'heures_supplementaires': heures_supplementaires,
            'agent_id': presence['agent__id'],
        })

    context = {
        'total_employes': total_employes,
        'taux_presence': taux_presence,
        'taux_absence': taux_absence,
        'rapport': rapport,
    }

    return render(request, 'personnel/rapport_presence.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def imprimer_rapport(request, agent_id):
    # Récupérer les détails de l'agent
    agent = get_object_or_404(Utilisateur, id=agent_id)

    # Récupérer les présences journalières de l'agent pour le mois en cours
    details_jours = Presence.objects.filter(agent=agent, date__month=now().month)

    # Calculer le nombre de jours travaillés et les heures totales par agent pour le mois en cours
    details_presences = (
        Presence.objects.filter(agent=agent, date__month=now().month)  # Filtrer par agent et mois
        .values('agent__id', 'agent__first_name', 'agent__last_name')  # Inclure agent__id
        .annotate(
            nombres_de_jours=Count('date'),  # Compter le nombre de jours de présence
            heures_travaillees=Sum('heures_travail')  # Somme des heures travaillées
        )
    )

    # Obtenir les heures supplémentaires de l'agent pour le mois en cours
    details_heures_supp = (
        HeureSupplementaire.objects.filter(agent=agent, date__month=now().month)
        .values('date')  # Obtenir les dates d'heures supplémentaires
        .annotate(
            heures_supplementaires=Sum('nombre_heures')  # Somme des heures supplémentaires par date
        )
    )

    # Créer un dictionnaire pour associer les heures supplémentaires à chaque jour
    heures_supplementaires_dict = {supp['date']: supp['heures_supplementaires'] for supp in details_heures_supp}

    # Préparer les données pour chaque jour
    jours_avec_heures = []
    for jour in details_jours:
        jour_data = {
            'date': jour.date,
            'heures_travaillees': jour.heures_travail,
            'heures_supplementaires': heures_supplementaires_dict.get(jour.date, 0)  # 0 si pas d'heures supp ce jour-là
        }
        jours_avec_heures.append(jour_data)

    # Calcul des totaux (heures travaillées et supplémentaires)
    heures_travaillees_totales = details_presences[0]['heures_travaillees'] if details_presences else 0
    heures_supplementaires_totales = sum(heures_supplementaires_dict.values())

    context = {
        'agent': agent,
        'nombres_de_jours': details_presences[0]['nombres_de_jours'] if details_presences else 0,
        'heures_travaillees': heures_travaillees_totales,
        'heures_supplementaires': heures_supplementaires_totales,
        'details_jours': jours_avec_heures,  # Liste des jours avec heures travaillées et supp
        'current_year': now().year,
    }

    # Charger le template PDF
    template = get_template('personnel/rapport_pdf.html')
    html = template.render(context)

    # Générer le fichier PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_{agent.first_name}_{agent.last_name}.pdf"'

    # Générer le PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Erreur lors de la génération du PDF', status=500)

    return response



@login_required
@user_passes_test(is_agent)
def presence(request):
    # Récupérer les présences de l'utilisateur connecté
    user_presences = Presence.objects.filter(agent=request.user).order_by('-date')  # Remplacez 'user' par le nom du champ d'utilisateur dans votre modèle

    context = {
        'user_presences': user_presences,
    }
    return render(request, 'personnel/presence.html', context)
