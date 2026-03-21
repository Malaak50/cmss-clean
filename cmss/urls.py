from django.contrib import admin
from django.urls import path,include, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.conf import settings
from django.conf.urls.static import static

app_name = 'dashboard'  # Add this at the top
class CustomPasswordChangeView(auth_views.PasswordChangeView):
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('password_change')
    
    def form_valid(self, form):
        # Vérification supplémentaire côté serveur
        if not self.request.user.check_password(form.cleaned_data['old_password']):
            form.add_error('old_password', "L'ancien mot de passe est incorrect")
            return self.form_invalid(form)
            
        if form.cleaned_data['new_password1'] != form.cleaned_data['new_password2']:
            form.add_error('new_password2', "Les nouveaux mots de passe ne correspondent pas")
            return self.form_invalid(form)
            
        messages.success(self.request, "Mot de passe changé avec succès!")
        return super().form_valid(form)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('', include('gestion.urls', namespace='gestion')),
    path('gestion/', include('gestion.urls', namespace='gestion')),

    path('dashboard/', include('gestion.urls')),  # Inclure avec le préfixe 'dashboard/'

    path('dashboard/accueil/', views.accueil, name='dashboard_home'),  # Consistent naming
    path('dashboard/patients/', views.patients, name='patients'),
    path('dashboard/cotisations/', views.cotisations, name='cotisations'),
    path('dashboard/profile/', views.profile, name='profile'),
    path('dashboard/agents/', views.agents, name='agents'),  # Fixed typo
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
