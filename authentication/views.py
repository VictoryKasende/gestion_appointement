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
            return reverse('personnel:remuneration')
        elif user.role == 'Administrateur IT':
            return reverse('admin:index')
        elif user.role == 'Gestionnaire Paie':
            return reverse('personnel:remuneration')
        elif user.role == 'Agent':
            pass
        return super().get_success_url()


@login_required
def profil(request):
    user = request.user

    if request.method == 'POST':
        form = ProfilForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre profil a été mis à jour avec succès.")
            return redirect('profil')
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = ProfilForm(instance=user)

    return render(request, 'authentication/profil.html', {'form': form})
