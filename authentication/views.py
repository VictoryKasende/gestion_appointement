from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import render, reverse, redirect

from authentication.forms import ProfilForm


class CustomLoginView(LoginView):
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return reverse('admin:index')
        elif user.role == 'Manager':
            return reverse('personnel:traiter_demande_credit')
        elif user.role == 'Administrateur IT':
            return reverse('admin:index')
        elif user.role == 'Gestionnaire Paie':
            return reverse('personnel:remuneration')
        elif user.role == 'Agent':
            return reverse('personnel:presence')
        return super().get_success_url()


@login_required
def profil(request):
    user = request.user  # Récupérer l'utilisateur connecté
    context = {
        'user': user  # Passez l'utilisateur au contexte
    }
    return render(request, 'authentication/profil.html', context)