# middleware.py (créez ce fichier dans votre app)
from django.http import HttpResponseForbidden
from django.contrib.auth.models import Group

class GestionnaireAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Vérifier si l'utilisateur est authentifié et n'est pas superutilisateur
        if request.user.is_authenticated and not request.user.is_superuser:
            # Vérifier si l'utilisateur est un gestionnaire
            if hasattr(request.user, 'gestionnaireprofile'):
                # Bloquer l'accès à la page des agents
                if request.path.startswith('/dashboard/agents/'):
                    return HttpResponseForbidden("Accès refusé")
        return None