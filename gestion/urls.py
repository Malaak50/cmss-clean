from django.urls import path
from . import views
# SUPPRIMEZ cette ligne: from .views import ajouter_retraite, details_retraite, patients, ... etc.

app_name = 'gestion'

urlpatterns = [
    path('retraites/', views.liste_retraites, name='liste_retraites'),
    path('dashboard/patients/', views.patients, name='patients'),
    path('retraite/<str:num_secu>/', views.details_retraite, name='details_retraite'),
    path('dashboard/accueil/', views.accueil, name='accueil'),
    path('dashboard/cotisations/', views.cotisations_view, name='cotisations'),
    path('check-duplicate/', views.check_duplicate, name='check_duplicate'),
    path('ajouter-retraite/', views.ajouter_retraite, name='ajouter_retraite'),

    path('retraite/<str:retraite_num_secu>/gestion/', 
     views.gestion_tm_arrieres, 
     name='gestion_tm_arrieres'),
     
    path('retraite/<str:retraite_num_secu>/enregistrer-tm/', 
     views.enregistrer_tm, 
     name='enregistrer_tm'),
     
    path('retraite/<str:retraite_num_secu>/enregistrer-arrieres/', views.enregistrer_arrieres, name='enregistrer_arrieres'),

     
    path('retraite/<str:retraite_num_secu>/historique-tm/', 
     views.historique_tm, 
     name='historique_tm'),
     
    path('retraite/<str:retraite_num_secu>/historique-arrieres/', views.historique_arrieres, name='historique_arrieres'),

     
    path('cotisations/import/', views.import_cotisations, name='import_cotisations'),
    path('cotisations/preview-columns/', views.preview_columns, name='preview_columns'),
    path('accueil/', views.accueil, name='accueil'),
    path('api/accueil-data/', views.api_accueil_data, name='api_accueil_data'),
    path('api/noms-incoherents/', views.api_noms_incoherents, name='api_noms_incoherents'),
    path('api/virements-manques/', views.api_virements_manques, name='api_virements_manques'),
     
     
    path('cotisations/refresh/', views.refresh_cotisations, name='refresh_cotisations'),
    path('agents/', views.agents, name='agents_page'),
    path('clear-alertes/', views.clear_alertes, name='clear_alertes'),
    # URLs réservées aux superutilisateurs
    path('agents/', views.gestionnaires_view, name='agents'),
    path('agents/ajouter/', views.ajouter_gestionnaire, name='ajouter_gestionnaire'),
    path('agents/data/', views.get_gestionnaires, name='get_gestionnaires'),
]
