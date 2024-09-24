# forms.py
from django import forms


class MoisFiltreForm(forms.Form):
    MOIS_CHOICES = [
        ('', 'Tous les mois'),
        ('01', 'Janvier'),
        ('02', 'Février'),
        ('03', 'Mars'),
        ('04', 'Avril'),
        ('05', 'Mai'),
        ('06', 'Juin'),
        ('07', 'Juillet'),
        ('08', 'Août'),
        ('09', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre'),
    ]

    mois = forms.ChoiceField(choices=MOIS_CHOICES, required=False, label='Filtrer par mois')
