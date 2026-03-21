from django.shortcuts import render ,redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from gestion.models import Retraite
from django.db import models  # Pour utiliser models.Q
from django.http import JsonResponse

@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if new_password1 != new_password2:
            return JsonResponse({
                'success': False,
                'message': 'Les nouveaux mots de passe ne correspondent pas.',
                'error_field': 'new_password2'
            }, status=400)
        
        # Vérifier la complexité du mot de passe
        if len(new_password1) < 8 or not any(char.isdigit() for char in new_password1) or not any(char.isalpha() for char in new_password1):
            return JsonResponse({
                'success': False,
                'message': 'Le mot de passe doit contenir au moins 8 caractères avec des lettres et des chiffres.',
                'error_field': 'new_password1'
            }, status=400)
        
        user = request.user
        if not user.check_password(old_password):
            return JsonResponse({
                'success': False,
                'message': 'Mot de passe actuel incorrect.',
                'error_field': 'old_password'
            }, status=400)
        
        try:
            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Votre mot de passe a été changé avec succès!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Une erreur s\'est produite lors du changement de mot de passe.'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    }, status=405)
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    
    def form_invalid(self, form):
        form.add_error(None, "Identifiants incorrects")
        return super().form_invalid(form)
def home(request):
    return render(request, 'home.html')

def login_view(request):
    return render(request, 'login.html')

def signup(request):
    return render(request, 'signup.html')
def accueil(request):
    return render(request, "dashboard/accueil.html")


def liste_retraites(request):
    # Récupérer les 10 derniers retraités par date d'ajout
    derniers_retraites = Retraite.objects.all().order_by('-date_ajout')[:10]
    
    # Pour une recherche éventuelle
    query = request.GET.get('q')
    if query:
        derniers_retraites = Retraite.objects.filter(
            models.Q(nom_per__icontains=query) | 
            models.Q(prenom_per__icontains=query) |
            models.Q(matricule__icontains=query)
        ).order_by('-date_ajout')
    
    context = {
        'derniers_retraites': derniers_retraites,
        'query': query if query else ''
    }
    return render(request, 'dashboard/patients.html', context)

def ajouter_retraite(request):
    if request.method == 'POST':
        try:
            Retraite.objects.create(
                nom_agence=request.POST.get('nom_agence'),
                qualite_personne=request.POST.get('qualite_personne'),
                id_num_personne=request.POST.get('id_num_personne'),
                num_secu=request.POST.get('num_secu'),
                nom=request.POST.get('nom'),
                prenom=request.POST.get('prenom'),
                date_naissance=request.POST.get('date_naissance'),
                mois_rattachement=request.POST.get('mois_rattachement'),  # Format YYYY-MM
                pension_cnss=request.POST.get('pension_cnss'),
                pension_cimr=request.POST.get('pension_cimr') or 0
            )
            messages.success(request, 'Retraité ajouté avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'ajout: {str(e)}')
        
        return redirect('gestion:patients')
    
    return redirect('gestion:patients')
def generate_matricule():
    """Génère un matricule unique"""
    # Implémentation basique - à adapter selon vos besoins
    from datetime import datetime
    return f"RET{datetime.now().strftime('%Y%m%d%H%M%S')}"
@login_required
def patients(request):
    # Récupérer les 10 derniers retraités
    derniers_retraites = Retraite.objects.all().order_by('-id')[:10]
    
    # Ajouter le nom complet pour chaque retraité
    for retraite in derniers_retraites:
        retraite.nom_complet = f"{retraite.nom} {retraite.prenom}"
    
    context = {
        'derniers_retraites': derniers_retraites
    }
    return render(request, 'dashboard/patients.html', context)
@login_required
def cotisations(request):
    return render(request, 'dashboard/cotisations.html')
def agents(request):
    return render(request, 'dashboard/agents.html')


@login_required
def profile(request):
    user = request.user
    context = {
        'user': user,
        'show_security': request.GET.get('security', 'false') == 'true'
    }
    password_errors = {}

    if request.method == 'POST':
        if 'form_type' in request.POST and request.POST['form_type'] == 'password_change':
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            # Validation des mots de passe
            if new_password1 != new_password2:
                password_errors['new_password2'] = "Les nouveaux mots de passe ne correspondent pas."
            
            if len(new_password1) < 8 or not any(char.isdigit() for char in new_password1) or not any(char.isalpha() for char in new_password1):
                password_errors['new_password1'] = "Le mot de passe doit contenir au moins 8 caractères avec des lettres et des chiffres."
            
            if not user.check_password(old_password):
                password_errors['old_password'] = "Mot de passe actuel incorrect."
            
            if not password_errors:
                try:
                    user.set_password(new_password1)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Votre mot de passe a été changé avec succès!")
                    return redirect(f"{reverse('profile')}?security=true")
                except Exception as e:
                    messages.error(request, f"Une erreur s'est produite: {str(e)}")
                    return redirect('profile')
            else:
                context['password_errors'] = password_errors
                context['show_security'] = True
                return render(request, 'dashboard/profile.html', context)
        
        else:  # Formulaire de profil normal
            try:
                user.email = request.POST.get('email', user.email)
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.save()
                messages.success(request, 'Profil mis à jour !')
                return redirect('profile')
            except Exception as e:
                messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
                return redirect('profile')

    return render(request, 'dashboard/profile.html', context)
@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if new_password1 != new_password2:
            messages.error(request, "Les nouveaux mots de passe ne correspondent pas.")
            return redirect('profile')
        
        user = request.user
        if user.check_password(old_password):
            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)  # Important pour ne pas déconnecter l'utilisateur
            messages.success(request, "Votre mot de passe a été changé avec succès!")
            return redirect('profile')
        else:
            messages.error(request, "Ancien mot de passe incorrect.")
    
    return redirect('profile')