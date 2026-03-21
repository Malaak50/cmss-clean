from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Retraite, TM, Arriere, Cotisation, Banque, NomIncoherent, VirementManque,GestionnaireProfile, User
from .forms import RetraiteForm, TMForm, ArriereForm, ImportBanqueForm,GestionnaireForm
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
import json
import logging
from django.db import transaction, models
import pandas as pd
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from datetime import datetime,date, timedelta
import os
import tempfile
import csv
import unidecode
import re
from rapidfuzz import fuzz
from django.db.models import Sum, Count, Q
from . import utils
import json
from django.http import request
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.http import require_POST
from django.db import transaction
from django.shortcuts import redirect
from django.contrib import messages
import pandas as pd
from decimal import Decimal
import logging
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import logging
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from gestion.models import Cotisation, Retraite, Banque, NomIncoherent, VirementManque
logger = logging.getLogger(__name__)

def ajouter_alerte_session(request, message, type_alerte):
    """Ajoute une alerte à la session pour affichage"""
    if 'alertes' not in request.session:
        request.session['alertes'] = []
    
    request.session['alertes'].append({
        'message': message,
        'type': type_alerte
    })
    request.session.modified = True
@require_POST
def clear_alertes(request):
    """Efface les alertes de la session"""
    if 'alertes' in request.session:
        del request.session['alertes']
    return JsonResponse({'success': True})
logger = logging.getLogger(__name__)
@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

def home(request):
    return render(request, 'home.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def check_duplicate(request):
    field = request.GET.get('field')
    value = request.GET.get('value')
    exists = False
    if field in ['id_num_personne', 'num_secu'] and value:
        exists = Retraite.objects.filter(**{field: value}).exists()
    return JsonResponse({'exists': exists})

def agents(request):
    return render(request, 'dashboard/agents.html')

@csrf_exempt
@login_required
def ajouter_retraite(request):
    if request.method == 'POST':
        try:
            data = {
                'nom_agence': request.POST.get('nom_agence'),
                'qualite_personne': request.POST.get('qualite_personne'),
                'num_secu': request.POST.get('num_secu'),
                'nom': request.POST.get('nom'),
                'prenom': request.POST.get('prenom'),
                'date_naissance': request.POST.get('date_naissance'),
                'mois_rattachement': request.POST.get('mois_rattachement'),
                'pension_cnss': request.POST.get('pension_cnss'),
                'pension_cimr': request.POST.get('pension_cimr') or None,
                'id_num_personne': request.POST.get('id_num_personne') or None
            }

            required_fields = ['nom_agence', 'qualite_personne', 'num_secu', 'nom', 
                             'prenom', 'date_naissance', 'mois_rattachement', 'pension_cnss']
            
            errors = {}
            for field in required_fields:
                if not data[field]:
                    errors[field] = "Ce champ est obligatoire"

            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            if Retraite.objects.filter(num_secu=data['num_secu']).exists():
                return JsonResponse({
                    'success': False,
                    'errors': {'num_secu': "Ce numéro existe déjà"}
                }, status=400)

            retraite = Retraite.objects.create(**data)
            
            return JsonResponse({
                'success': True,
                'message': "Retraité ajouté avec succès !",
                'retraite_id': retraite.num_secu
            })

        except IntegrityError as e:
            return JsonResponse({
                'success': False,
                'error': f"Erreur de base de données: {str(e)}"
            }, status=400)

        except Exception as e:
            logger.error(f"Erreur ajout retraité: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': "Une erreur technique est survenue"
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': "Seules les requêtes POST sont autorisées"
    }, status=405)
@login_required
def patients(request):
    retraites = Retraite.objects.all().order_by('-num_secu')
    
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
                mois_rattachement=request.POST.get('mois_rattachement'),
                pension_cnss=request.POST.get('pension_cnss'),
                pension_cimr=request.POST.get('pension_cimr')
            )
            messages.success(request, "Retraité ajouté avec succès!")
            return redirect('patients')
            
        except IntegrityError as e:
            if 'id_num_personne' in str(e):
                messages.error(request, "Erreur: Ce numéro de personne existe déjà!")
            elif 'num_secu' in str(e):
                messages.error(request, "Erreur: Ce numéro de sécurité sociale existe déjà!")
            else:
                messages.error(request, "Erreur lors de l'ajout du retraité")
            
            context = {
                'retraites': retraites,
                'form_data': request.POST,
                'today': timezone.now().date(),
                'show_modal': 'true'
            }
            return render(request, 'dashboard/patients.html', context)
    
    return render(request, 'dashboard/patients.html', {'retraites': retraites})

def verifier_num_personne(request):
    num = request.GET.get('num')
    exists = Retraite.objects.filter(id_num_personne=num).exists()
    return JsonResponse({'exists': exists})

@login_required
def details_retraite(request, num_secu):
    try:
        retraite = get_object_or_404(Retraite, num_secu=num_secu)
        
        pension_cnss = retraite.pension_cnss if retraite.pension_cnss is not None else Decimal('0')
        pension_cimr = retraite.pension_cimr if retraite.pension_cimr is not None else Decimal('0')
        total_pensions = pension_cnss + pension_cimr
        # Ajouter les trimestres manquants
        trimestres_manquants = retraite.get_trimestres_manquants()
        montant_attendu_par_trimestre = retraite.get_montant_trimestriel_attendu()
        data = {
            'success': True,
            'retraite': {
                'id': retraite.pk,
                'nom_complet': f"{retraite.nom} {retraite.prenom}",
                'num_secu': retraite.num_secu,
                'id_num_personne': retraite.id_num_personne if retraite.id_num_personne else 'Non spécifié',
                'date_naissance': retraite.date_naissance.strftime('%d/%m/%Y') if retraite.date_naissance else 'Non spécifié',
                'qualite_personne': retraite.qualite_personne if retraite.qualite_personne else 'Retraité',
                'nom_agence': retraite.nom_agence if retraite.nom_agence else 'Non spécifié',
                'mois_rattachement': retraite.mois_rattachement if retraite.mois_rattachement else 'Non spécifié',
                'pension_cnss': str(pension_cnss),
                'pension_cimr': str(pension_cimr),
            },
            'calculs': {
                'mensuel_cmss': str((total_pensions * Decimal('0.0333')).quantize(Decimal('0.00')) if total_pensions else '0.00'),
                'patronal': str((total_pensions * Decimal('0.0666')).quantize(Decimal('0.00')) if total_pensions else '0.00'),
                'trim_cmss': str((total_pensions * Decimal('0.0999')).quantize(Decimal('0.00')) if total_pensions else '0.00'),
                'trim_cmcas': str((total_pensions * Decimal('0.0675')).quantize(Decimal('0.00')) if total_pensions else '0.00'),
            },
            'tms': [{
                'date': tm.date_tm.strftime('%d/%m/%Y'),
                'montant': str(tm.montant_total),
                'mois': tm.mois_concerne if hasattr(tm, 'mois_concerne') else 'N/A',
                'statut': tm.get_statut_display()
            } for tm in retraite.tms.all().order_by('-date_tm')[:5]],
            'arrieres': [{
                'date_arriere': arr.date_arriere.strftime('%d/%m/%Y') if arr.date_arriere else None,
                'type_arriere': arr.type_arriere,
                'nombre_de_mois': arr.nombre_de_mois,
                'montant_cmss': str(arr.montant_cmss) if arr.montant_cmss else None,
                'montant_cmcas': str(arr.montant_cmcas) if arr.montant_cmcas else None,
                'statut': arr.get_statut_display()
            } for arr in retraite.arrieres.all().order_by('-date_arriere')[:5]],
            'trimestres_manquants': {
                'liste': trimestres_manquants,
                'nombre': len(trimestres_manquants),
                'montant_total_manquant': len(trimestres_manquants) * montant_attendu_par_trimestre,
                'montant_par_trimestre': montant_attendu_par_trimestre
            }
        }
        return JsonResponse(data)

    except Exception as e:
        logger.error(f"Erreur détails retraité {num_secu}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Une erreur technique est survenue',
            'details': str(e)
        }, status=500)

def liste_retraites(request):
    retraites = Retraite.objects.all().order_by('nom')
    context = {'retraites': retraites}
    return render(request, 'gestion/liste_retraites.html', context)

@csrf_exempt
@require_POST
@login_required
@transaction.atomic
def enregistrer_tm(request, retraite_num_secu):
    try:
        retraite = Retraite.objects.only('num_secu').get(num_secu=retraite_num_secu)
        
        tm = TM(
            retraite=retraite,
            date_tm=request.POST.get('date_tm'),
            montant_total=request.POST.get('montant_total'),
            statut=request.POST.get('statut', 'EN_ATTENTE')
        )
        
        tm.full_clean()
        tm.save()
        
        return JsonResponse({
            'success': True,
            'message': 'TM enregistré avec succès',
            'retraite_num_secu': retraite.num_secu,
            'saved_retraite_num_secu': tm.retraite.num_secu
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'retraite_num_secu_attempted': retraite_num_secu
        }, status=400)

def historique_tm(request, retraite_num_secu):
    try:
        retraite = Retraite.objects.get(num_secu=retraite_num_secu)
        tms = retraite.tms.all().order_by('-date_tm').values(
            'id', 
            'date_tm', 
            'montant_total', 
            'statut'
        )
        return JsonResponse({
            'success': True,
            'data': list(tms)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
@login_required
@transaction.atomic
def enregistrer_arrieres(request, retraite_num_secu):
    try:
        retraite = get_object_or_404(Retraite, num_secu=retraite_num_secu)
        
        # Utilisez votre formulaire existant ArriereForm
        form = ArriereForm(request.POST, retraite=retraite)
        
        if form.is_valid():
            arriere = form.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Arriéré enregistré avec succès',
                'retraite_num_secu': retraite.num_secu,
                'arriere_id': arriere.id
            })
        else:
            # Retournez les erreurs de validation du formulaire
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = [str(error) for error in field_errors]
            
            return JsonResponse({
                'success': False,
                'error': 'Erreur de validation du formulaire',
                'errors': errors
            }, status=400)

    except Exception as e:
        logger.error(f"Erreur enregistrement arriéré: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)
@login_required
def gestion_tm_arrieres(request, retraite_num_secu):
    try:
        retraite = Retraite.objects.get(num_secu=retraite_num_secu)
        context = {
            'retraite': retraite,
            'today': timezone.now().date()
        }
        return render(request, 'dashboard/gestion_tm_arrieres.html', context)
        
    except Retraite.DoesNotExist:
        return JsonResponse({'error': 'Retraité introuvable'}, status=404)
    except Exception as e:
        logger.error(f"Erreur gestion TM/Arriérés: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)



def historique_arrieres(request, retraite_num_secu):
    try:
        retraite = get_object_or_404(Retraite, num_secu=retraite_num_secu)
        arrieres = retraite.arrieres.all().order_by('-date_arriere').values(
            'id', 
            'date_arriere', 
            'type_arriere', 
            'nombre_de_mois', 
            'montant_cmss', 
            'montant_cmcas', 
            'statut'
        )
        
        # Convertir les Decimal en string pour la sérialisation JSON
        arrieres_list = []
        for arriere in arrieres:
            arriere_data = {
                'id': arriere['id'],
                'date_arriere': arriere['date_arriere'].isoformat() if arriere['date_arriere'] else None,
                'type_arriere': arriere['type_arriere'],
                'nombre_de_mois': arriere['nombre_de_mois'],
                'montant_cmss': str(arriere['montant_cmss']) if arriere['montant_cmss'] is not None else '0.00',
                'montant_cmcas': str(arriere['montant_cmcas']) if arriere['montant_cmcas'] is not None else '0.00',
                'statut': arriere['statut']
            }
            arrieres_list.append(arriere_data)
        
        return JsonResponse({
            'arrieres': arrieres_list,
            'success': True
        })
    except Exception as e:
        logger.error(f"Erreur historique arriérés: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
def test_view(request, retraite_num_secu):
    try:
        retraite = Retraite.objects.get(num_secu=retraite_num_secu)
        return JsonResponse({
            'status': 'success',
            'retraite': retraite.num_secu,
            'tm_count': retraite.tms.count(),
            'arrieres_count': retraite.arrieres.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@require_POST
@login_required
@transaction.atomic
def import_cotisations(request):
    """
    Importation des cotisations depuis un fichier Excel avec vérification des doublons.
    """
    try:
        if 'fichier' not in request.FILES:
            messages.error(request, "Aucun fichier fourni")
            return redirect('cotisations')

        fichier = request.FILES['fichier']

        # Vérification du format de fichier
        if not fichier.name.lower().endswith(('.xlsx', '.xls')):
            messages.error(request, "Format de fichier non supporté. Veuillez utiliser un fichier Excel (.xlsx ou .xls)")
            return redirect('cotisations')

        # Lecture du fichier Excel
        try:
            df = pd.read_excel(fichier, header=0)
            df.columns = [str(col).replace('\n', ' ').replace('\r', ' ').strip() for col in df.columns]
            lignes_fichier = len(df)
        except Exception as e:
            messages.error(request, f"Erreur lors de la lecture du fichier: {str(e)}")
            return redirect('cotisations')

        # Mapping des colonnes
        colonnes_obligatoires = {
            'N_piece': ['Nº pièce', 'N° pièce', 'Numéro pièce', 'N piece', 'N_piece', 'Ref'],
            'Montant': ['Montant en devise interne', 'Montant en MAD', 'Montant', 'Amount', 'Montant devise interne', 'Mnt'],
            'Texte': ['Texte', 'Description', 'Libellé', 'Text', 'Commentaire'],
            'Date_piece': ['Date pièce', 'Date', 'Date operation', 'Date opération', 'Date_piece']
        }

        colonnes_map = {}
        for col_standard, variantes in colonnes_obligatoires.items():
            for variante in variantes:
                for col_dispo in df.columns:
                    if col_dispo.lower().replace(' ', '') == variante.lower().replace(' ', ''):
                        colonnes_map[col_standard] = col_dispo
                        break
                if col_standard in colonnes_map:
                    break

        # Vérification des colonnes manquantes
        colonnes_manquantes = [col for col in colonnes_obligatoires.keys() if col not in colonnes_map]
        if colonnes_manquantes:
            messages.error(request, f"Colonnes manquantes: {', '.join(colonnes_manquantes)}")
            return redirect('cotisations')

        # Nettoyage des données - NE PAS SUPPRIMER LES LIGNES AVEC dropna()
        df_renamed = df.rename(columns={v: k for k, v in colonnes_map.items()})
        
        # Remplacer les valeurs NaN par des valeurs par défaut au lieu de les supprimer
        df_clean = df_renamed[list(colonnes_obligatoires.keys())].copy()
        
        # Remplir les valeurs manquantes avec des valeurs par défaut
        df_clean['N_piece'] = df_clean['N_piece'].fillna('N/A')
        df_clean['Texte'] = df_clean['Texte'].fillna('')
        df_clean['Montant'] = df_clean['Montant'].fillna(0)
        
        # Conversion des dates et montants
        try:
            # Convertir les dates - gérer les valeurs manquantes
            df_clean['Date_piece'] = pd.to_datetime(df_clean['Date_piece'], errors='coerce')
            # Filtrer uniquement les dates à partir de 2023, mais garder toutes les lignes
            df_clean = df_clean[df_clean['Date_piece'].isna() | (df_clean['Date_piece'].dt.year >= 2023)]
            df_clean['Date_piece'] = df_clean['Date_piece'].dt.date
        except Exception as e:
            messages.error(request, f"Erreur dans le format des dates: {str(e)}")
            return redirect('cotisations')

        try:
            # Conversion des montants avec gestion des erreurs
            def convert_montant(x):
                try:
                    if pd.isna(x):
                        return Decimal('0')
                    return abs(Decimal(str(x)))
                except (InvalidOperation, ValueError):
                    return Decimal('0')
            
            df_clean['Montant'] = df_clean['Montant'].apply(convert_montant)
        except Exception as e:
            messages.error(request, f"Erreur dans le format des montants: {str(e)}")
            return redirect('cotisations')
        
        # ÉTAPE 1: Matching des noms optimisé
        operations_avec_nom = []
        noms_incoherents_details = []
        erreurs_import = []  # Pour suivre les erreurs d'importation

        if not hasattr(import_cotisations, 'db_dict'):
            retraites_data = []
            for retraite in Retraite.objects.all():
                retraites_data.append({
                    'Nom Correct': f"{retraite.nom} {retraite.prenom}",
                    'Mois rattachement': retraite.mois_rattachement,
                    'Cotisation CMSS': retraite.montant_cmss_trimestriel,
                    'Cotisation CMCAS': retraite.montant_cmcas_trimestriel
                })
            db_df = pd.DataFrame(retraites_data)
            import_cotisations.db_dict = utils.preparer_base_database(db_df)

        for index, row in df_clean.iterrows():
            try:
                texte = str(row['Texte']) if pd.notna(row['Texte']) else ''
                montant = row['Montant']
                date_piece = row['Date_piece'] if pd.notna(row['Date_piece']) else None
                n_piece = str(row['N_piece']) if pd.notna(row['N_piece']) else f"INCONNU_{index}"

                # Recherche optimisée
                resultat = utils.trouver_correspondance_rapide(texte, import_cotisations.db_dict)

                if resultat[0] and resultat[1] >= 65:
                    match_info, meilleur_score, cle_trouvee = resultat
                    nom_bd = match_info['Nom Complet']

                    try:
                        meilleur_retraite = Retraite.objects.get(
                            Q(nom__icontains=nom_bd.split()[0]) &
                            Q(prenom__icontains=nom_bd.split()[-1])
                        )
                    except (Retraite.DoesNotExist, Retraite.MultipleObjectsReturned):
                        meilleur_retraite = None

                    operations_avec_nom.append({
                        'N_piece': n_piece,
                        'Montant': montant,
                        'Texte': texte,
                        'date_piece': date_piece,
                        'nom_bd': nom_bd,
                        'retraite': meilleur_retraite,
                        'score': meilleur_score,
                        'ligne_originale': index   # Garder la trace de la ligne originale
                    })
                else:
                    operations_avec_nom.append({
                        'N_piece': n_piece,
                        'Montant': montant,
                        'Texte': texte,
                        'date_piece': date_piece,
                        'nom_bd': None,
                        'retraite': None,
                        'score': 0,
                        'ligne_originale': index + 2
                    })
                    noms_incoherents_details.append({
                        'nom': texte,
                        'date': date_piece.strftime('%Y-%m-%d') if date_piece else 'N/A',
                        'montant': float(montant),
                        'n_piece': n_piece,
                        'ligne': index + 2
                    })
            except Exception as e:
                # Enregistrer l'erreur mais continuer le traitement
                erreurs_import.append({
                    'ligne': index + 2,
                    'erreur': str(e),
                    'donnees': dict(row) if hasattr(row, 'to_dict') else str(row)
                })
                logger.error(f"Erreur ligne {index }: {str(e)}")

        # ÉTAPE 2: Vérification des doublons + sauvegarde des opérations valides
        operations_valides = []
        doublons_detectes = []

        # Création de sets pour vérification des doublons
        operations_vues_db_avec_nom = set()
        operations_vues_db_sans_nom = set()

        for op_db in Banque.objects.exclude(nom_bd__isnull=True):
            cle = (op_db.nom_bd, op_db.date_piece, float(op_db.Montant_en_devise_interne))
            operations_vues_db_avec_nom.add(cle)

        for op_db in Banque.objects.filter(nom_bd__isnull=True):
            cle = (op_db.N_piece, op_db.date_piece, float(op_db.Montant_en_devise_interne))
            operations_vues_db_sans_nom.add(cle)

        operations_vues_fichier_avec_nom = set()
        operations_vues_fichier_sans_nom = set()

        for op in operations_avec_nom:
            try:
                montant_float = float(op['Montant'])

                if op['nom_bd']:
                    cle_unique = (op['nom_bd'], op['date_piece'], montant_float)
                    if cle_unique in operations_vues_fichier_avec_nom or cle_unique in operations_vues_db_avec_nom:
                        doublons_detectes.append({
                            'reference': op['N_piece'],
                            'date': op['date_piece'],
                            'montant': montant_float,
                            'description': op['Texte'],
                            'nom_bd': op['nom_bd'],
                            'type': 'doublon',
                            'ligne': op.get('ligne_originale', 'N/A')
                        })
                        continue
                    operations_vues_fichier_avec_nom.add(cle_unique)
                else:
                    cle_unique = (op['N_piece'], op['date_piece'], montant_float)
                    if cle_unique in operations_vues_fichier_sans_nom or cle_unique in operations_vues_db_sans_nom:
                        doublons_detectes.append({
                            'reference': op['N_piece'],
                            'date': op['date_piece'],
                            'montant': montant_float,
                            'description': op['Texte'],
                            'nom_bd': None,
                            'type': 'doublon',
                            'ligne': op.get('ligne_originale', 'N/A')
                        })
                        continue
                    operations_vues_fichier_sans_nom.add(cle_unique)

                # Déterminer le trimestre
                trimestre = utils.get_trimestre_from_date_piece(op['date_piece']) if op['date_piece'] else "N/A"
                operations_valides.append({**op, 'trimestre': trimestre})
            except Exception as e:
                erreurs_import.append({
                    'ligne': op.get('ligne_originale', 'N/A'),
                    'erreur': f"Erreur vérification doublons: {str(e)}",
                    'donnees': op
                })

        # ÉTAPE 3: Sauvegarde des données
        operations_sauvegardees = 0
        erreurs_sauvegarde = []
        
        with transaction.atomic():
            for op in operations_valides:
                try:
                    if op['nom_bd']:
                        if Banque.objects.filter(
                            nom_bd=op['nom_bd'],
                            date_piece=op['date_piece'],
                            Montant_en_devise_interne=op['Montant']
                        ).exists():
                            continue
                    else:
                        if Banque.objects.filter(
                            N_piece=op['N_piece'],
                            date_piece=op['date_piece'],
                            Montant_en_devise_interne=op['Montant']
                        ).exists():
                            continue

                    operation_bancaire = Banque.objects.create(
                        N_piece=op['N_piece'],
                        Montant_en_devise_interne=op['Montant'],
                        Texte=op['Texte'],
                        date_piece=op['date_piece'],
                        nom_bd=op['nom_bd']
                    )

                    if op['retraite']:
                        retraite = op['retraite']
                        type_paiement, ecart, reste, details = utils.analyser_montant_cotisation(
                            op['Montant'],
                            retraite.montant_cmss_trimestriel or Decimal('0'),
                            retraite.montant_cmcas_trimestriel or Decimal('0')
                        )

                        # Déterminer le trimestre avec précision
                        trimestre = op['trimestre']
                        if trimestre == "N/A" and op['date_piece']:
                            # Essayer de déterminer le trimestre à partir de la date
                            trimestre = utils.get_trimestre_from_date_piece(op['date_piece'])
                        
                        Cotisation.objects.create(
                            retraite=retraite,
                            operation_bancaire=operation_bancaire,
                            montant=op['Montant'],
                            montant_cmss_trimestriel=retraite.montant_cmss_trimestriel or Decimal('0'),
                            montant_cmcas_trimestriel=retraite.montant_cmcas_trimestriel or Decimal('0'),
                            trimestre_de_remboursement=trimestre,
                            detail_ecart=details,
                            type_paiement=type_paiement,
                            ecart=abs(ecart),
                            reste=abs(reste)
                        )

                    operations_sauvegardees += 1
                except Exception as e:
                    erreurs_sauvegarde.append({
                        'ligne': op.get('ligne_originale', 'N/A'),
                        'erreur': f"Erreur sauvegarde: {str(e)}",
                        'donnees': op
                    })
                    logger.error(f"Erreur sauvegarde ligne {op.get('ligne_originale', 'N/A')}: {str(e)}")

            # CORRECTION: Sauvegarder les noms incohérents avec gestion des erreurs
            for nom in noms_incoherents_details:
                try:
                    # Gestion de la date
                    if nom['date'] != 'N/A':
                        try:
                            date_operation = datetime.strptime(nom['date'], '%Y-%m-%d').date()
                        except ValueError:
                            date_operation = timezone.now().date()
                    else:
                        date_operation = timezone.now().date()
                    
                    # Déterminer le trimestre et l'année
                    trimestre = utils.get_trimestre_from_date_piece(date_operation)
                    annee = date_operation.year
                    
                    # Créer l'enregistrement NomIncoherent
                    NomIncoherent.objects.create(
                        nom=nom['nom'][:200],  # Limiter à la longueur du champ
                        trimestre=trimestre,
                        date_operation=date_operation,
                        montant=Decimal(str(nom['montant'])),
                        annee=annee,
                        n_piece=nom['n_piece'][:100] if nom['n_piece'] else None,  # Limiter à la longueur du champ
                        ligne_origine=nom.get('ligne', 'N/A')
                    )
                except Exception as e:
                    logger.error(f"Erreur sauvegarde nom incohérent: {str(e)}")
                    continue

            # Stocker les résultats dans la session
            doublons_serialisables = []
            for doublon in doublons_detectes:
                doublon_serialisable = doublon.copy()
                if isinstance(doublon_serialisable['date'], (datetime, date)):
                    doublon_serialisable['date'] = doublon_serialisable['date'].isoformat()
                doublons_serialisables.append(doublon_serialisable)
            
            request.session['doublons_import'] = doublons_serialisables
            request.session['import_stats'] = {
                'lignes_fichier': lignes_fichier,
                'operations_sauvegardees': operations_sauvegardees,
                'noms_incoherents_count': len(noms_incoherents_details),
                'doublons_count': len(doublons_detectes),
                'erreurs_count': len(erreurs_import) + len(erreurs_sauvegarde),
                'timestamp': timezone.now().isoformat()
            }
            
            # Stocker aussi les erreurs pour débogage (limité à 50 erreurs)
            request.session['import_erreurs'] = (erreurs_import + erreurs_sauvegarde)[:50]
            
            request.session.modified = True

            # Message de succès détaillé
            pourcentage_reussi = (operations_sauvegardees / lignes_fichier * 100) if lignes_fichier > 0 else 0
            messages.success(
                request,
                f"Importation terminée : {operations_sauvegardees}/{lignes_fichier} lignes traitées ({pourcentage_reussi:.1f}%) • "
                f"{len(doublons_detectes)} doublons • {len(noms_incoherents_details)} noms incohérents • "
                f"{len(erreurs_import) + len(erreurs_sauvegarde)} erreurs"
            )
            
            # Détection des virements manquants
            try:
                detecter_virements_manquants()
                detecter_paiements_partiels_et_retards()
            except Exception as e:
                logger.error(f"Erreur lors de la détection des virements manquants: {str(e)}")

            return redirect('cotisations')
        logger.info(f"Nombre de noms incohérents détectés: {len(noms_incoherents_details)}")
        logger.info(f"Exemple de nom incohérent: {noms_incoherents_details[0] if noms_incoherents_details else 'Aucun'}")
        logger.info(f"Nombre de doublons détectés: {len(doublons_detectes)}")
    except Exception as e:
        logger.error(f"Erreur importation cotisations: {str(e)}", exc_info=True)
        messages.error(request, f"Erreur serveur lors de l'importation: {str(e)}")
        return redirect('cotisations')

def detecter_paiements_partiels_et_retards():
    """
    Détecte les paiements partiels (PROCH) et les retards
    """
    current_year = timezone.now().year
    logger.info(f"Paiements partiels détectés: {paiements_partiels.count()}")
    logger.info(f"Paiements incompatibles détectés: {paiements_incompatibles.count() if 'paiements_incompatibles' in locals() else 0}")
    # Paiements partiels pour l'année courante
    paiements_partiels = Cotisation.objects.filter(
        type_paiement__in=['CMSS_PROCH', 'CMCAS_PROCH'],
        operation_bancaire__date_piece__year=current_year
    )
    
    for cotisation in paiements_partiels:
        VirementManque.objects.get_or_create(
            num_secu=cotisation.retraite,
            trimestre_manquant=cotisation.trimestre_de_remboursement,
            defaults={
                'montant_attendu': cotisation.ecart,  # Montant manquant
                'type_paiement': cotisation.type_paiement,
                'statut': 'partiel',
                'annee': current_year
            }
        )
    
    # Paiements incompatibles pour les années précédentes (non reçus)
    current_year = timezone.now().year
    if current_year > 2023:
        annees_precedentes = range(2023, current_year)
        for annee in annees_precedentes:
            paiements_incompatibles = Cotisation.objects.filter(
                type_paiement='INCOMPATIBLE',
                operation_bancaire__date_piece__year=annee
            )
            
            for cotisation in paiements_incompatibles:
                VirementManque.objects.get_or_create(
                    num_secu=cotisation.retraite,
                    trimestre_manquant=cotisation.trimestre_de_remboursement,
                    defaults={
                        'montant_attendu': cotisation.montant,
                        'type_paiement': 'INCOMPATIBLE',
                        'statut': 'non_recu',
                        'annee': annee
                    }
                )

def ajouter_alerte_session(request, message, type_alerte):
    """
    Ajoute une alerte à la session pour affichage ultérieur.
    Exemple d'utilisation :
        ajouter_alerte_session(request, "Opération réussie", "success")
    Les types possibles peuvent être : success, info, warning, danger
    """
    if 'alertes' not in request.session:
        request.session['alertes'] = []

    request.session['alertes'].append({
        'message': message,
        'type': type_alerte
    })
    request.session.modified = True

@login_required
def cotisations_view(request):
    """
    Vue principale pour l'analyse des cotisations.
    Les virements manquants sont stockés dans VirementManque.
    """
    # Récupérer doublons et stats depuis la session
    doublons_detectes = request.session.get('doublons_import', [])
    import_stats = request.session.get('import_stats', {})
    import_erreurs = request.session.get('import_erreurs', [])
    
    # Convertir les dates string en objets date si nécessaire
    for doublon in doublons_detectes:
        if isinstance(doublon['date'], str):
            try:
                doublon['date'] = datetime.fromisoformat(doublon['date']).date()
            except (ValueError, TypeError):
                doublon['date'] = timezone.now().date()

    # Vérifier présence de données
    has_data_in_db = Banque.objects.exists() or Cotisation.objects.exists()

    # INITIALISATION DES VARIABLES AVANT TOUTE CONDITION
    reglees = []
    non_reglees = []
    manquants = []
    reglees_count = 0
    non_reglees_count = 0
    manquants_count = 0

    if has_data_in_db:
        # Comptage des cotisations importées
        imported_count = import_stats.get('operations_sauvegardees', Banque.objects.count())
        incoherent_names_count = import_stats.get('noms_incoherents_count', NomIncoherent.objects.count())
        duplicates_count = import_stats.get('doublons_count', len(doublons_detectes))
        erreurs_count = import_stats.get('erreurs_count', 0)
        noms_incoherents = NomIncoherent.objects.all().order_by('-date_operation')[:100]

        # Gestion des virements manquants
        virements_manquants = VirementManque.objects.all()
        virements_manquants_count = virements_manquants.count()
        virements_cmss_count = virements_manquants.filter(type_paiement__contains='CMSS').count()
        virements_cmcas_count = virements_manquants.filter(type_paiement__contains='CMCAS').count()
        virements_total_montant = virements_manquants.aggregate(Sum('montant_attendu'))['montant_attendu__sum'] or 0

        # Classement des cotisations : réglées / non réglées / manquantes
        classement = classer_resultats()
        reglees = classement.get('reglees', [])
        non_reglees = classement.get('non_reglees', [])
        manquants = classement.get('manquants', [])
        
        # Récupérer les virements manquants avec les statuts
        virements_manquants = VirementManque.objects.all()
        virements_en_retard = virements_manquants.filter(statut='en_retard')
        virements_non_recus = virements_manquants.filter(statut='non_recu')
        virements_partiels = virements_manquants.filter(statut='partiel')
        
        # Calcul des comptages
        reglees_count = len(reglees)
        non_reglees_count = len(non_reglees)
        manquants_count = len(manquants)
        
        context = {
            'has_data_in_db': True,
            'imported_count': imported_count,
            'duplicates_count': duplicates_count,
            'erreurs_count': erreurs_count,
            'doublons': doublons_detectes,
            'import_erreurs': import_erreurs,
            'incoherent_names_count': incoherent_names_count,
            'noms_incoherents': noms_incoherents,
            'reglees': reglees,
            'non_reglees': non_reglees,
            'manquants': manquants,
            'reglees_count': reglees_count,
            'non_reglees_count': non_reglees_count,
            'manquants_count': manquants_count,
            'virements_manquants_count': virements_manquants_count,
            'virements_cmss_count': virements_cmss_count,
            'virements_cmcas_count': virements_cmcas_count,
            'virements_total_montant': virements_total_montant,
            'timestamp': timezone.now(),
            'virements_en_retard': virements_en_retard,
            'virements_non_recus': virements_non_recus,
            'virements_partiels': virements_partiels,
            'virements_en_retard_count': virements_en_retard.count(),
            'virements_non_recus_count': virements_non_recus.count(),
            'virements_partiels_count': virements_partiels.count(),
        }
    else:
        context = {
            'has_data_in_db': False,
            'doublons': doublons_detectes,
            'import_erreurs': import_erreurs,
            'duplicates_count': len(doublons_detectes),
            'erreurs_count': len(import_erreurs),
            'reglees': reglees,
            'non_reglees': non_reglees,
            'manquants': manquants,
            'reglees_count': reglees_count,
            'non_reglees_count': non_reglees_count,
            'manquants_count': manquants_count
        }

    # Nettoyage de la session
    request.session.pop('doublons_import', None)
    request.session.pop('import_stats', None)
    request.session.pop('import_erreurs', None)

    return render(request, 'dashboard/cotisations.html', context)
def detecter_doublons_fichier(df):
    """
    Détecte les doublons dans le fichier Excel avant importation
    """
    doublons_fichier = []
    
    # Vérifier les doublons basés sur les colonnes clés
    colonnes_unicite = ['N_piece', 'Date_piece', 'Montant', 'Texte']
    
    # S'assurer que les colonnes existent
    colonnes_existantes = [col for col in colonnes_unicite if col in df.columns]
    
    if colonnes_existantes:
        # Trouver les lignes dupliquées
        duplicates = df[df.duplicated(subset=colonnes_existantes, keep=False)]
        
        for index, row in duplicates.iterrows():
            doublons_fichier.append({
                'reference': row.get('N_piece', 'N/A'),
                'date': row.get('Date_piece', timezone.now().date()),
                'montant': float(row.get('Montant', 0)),
                'description': row.get('Texte', ''),
                'nom_bd': None,
                'type': 'doublon_fichier',
                'ligne': index + 2  # +2 car index 0-based + header
            })
    
    return doublons_fichier#utuliser dans importation de cotisations

def detecter_virements_manquants():
    """
    Détecte les virements manquants selon les contraintes métier, y compris les paiements partiels
    """
    from django.db.models import Q
    from decimal import Decimal
    
    current_year = timezone.now().year
    virements_manquants = []
    
    # Récupérer tous les retraités
    retraites = Retraite.objects.all()
    
    # Définir les trimestres attendus
    trimestres_attendus = [
        f"T1:Janvier {current_year}",
        f"T2:Avril {current_year}", 
        f"T3:Juillet {current_year}",
        f"T4:Octobre {current_year}"
    ]
    
    for retraite in retraites:
        # Pour chaque trimestre attendu
        for trimestre in trimestres_attendus:
            # Vérifier si le retraité a payé ce trimestre
            cotisations_trimestre = Cotisation.objects.filter(
                retraite=retraite,
                trimestre_de_remboursement=trimestre
            )
            
            if not cotisations_trimestre.exists():
                # Trimestre complètement manquant
                montant_attendu = (retraite.montant_cmss_trimestriel or Decimal('0')) + (retraite.montant_cmcas_trimestriel or Decimal('0'))
                
                VirementManque.objects.get_or_create(
                    num_secu=retraite,
                    trimestre_manquant=trimestre,
                    defaults={
                        'montant_attendu': montant_attendu,
                        'type_paiement': 'NON_PAYE',
                        'statut': 'non_recu',
                        'annee': current_year
                    }
                )
            else:
                # Vérifier les paiements partiels
                for cotisation in cotisations_trimestre:
                    if cotisation.type_paiement in ['CMSS_PROCH', 'CMCAS_PROCH']:
                        # Paiement partiel - écart manquant
                        VirementManque.objects.get_or_create(
                            num_secu=retraite,
                            trimestre_manquant=trimestre,
                            type_paiement=cotisation.type_paiement,
                            defaults={
                                'montant_attendu': cotisation.ecart,
                                'statut': 'partiel',
                                'annee': current_year
                            }
                        )
    
    return virements_manquants
def classer_resultats():
    """
    Classifie les retraités selon leur statut de paiement avec détection des trimestres manquants
    """
    reglees = []
    non_reglees = []
    manquants = []  # Toujours initialiser la liste
    
    current_year = timezone.now().year
    
    try:
        # Récupérer tous les retraités
        tous_retraites = Retraite.objects.all()
        
        # Définir les trimestres attendus pour l'année en cours
        trimestres_attendus = [
            f"T1:Janvier {current_year}",
            f"T2:Avril {current_year}",
            f"T3:Juillet {current_year}",
            f"T4:Octobre {current_year}"
        ]
        
        for retraite in tous_retraites:
            current_year = date.today().year

            cotisations_annee = retraite.cotisations.filter(
    operation_bancaire__date_piece__year__range=(2023, current_year)
)

            
            # Déterminer les trimestres déjà payés
            trimestres_payes = set()
            for cotisation in cotisations_annee:
                if cotisation.trimestre_de_remboursement:
                    trimestres_payes.add(cotisation.trimestre_de_remboursement)
            
            # Déterminer les trimestres manquants
            trimestres_manquants = [t for t in trimestres_attendus if t not in trimestres_payes]
            
            if not cotisations_annee.exists():
                # Aucune cotisation cette année - NON RÉGLÉS
                non_reglees.append({
                    'nom': retraite.nom,
                    'prenom': retraite.prenom,
                    'num_secu': retraite.num_secu,
                    'mois_rattachement': retraite.mois_rattachement,
                    'raison': 'Aucune cotisation cette année',
                    'trimestres_manquants': trimestres_manquants,
                    'montant_attendu_par_trimestre': retraite.get_montant_trimestriel_attendu(),
                    'montant_total_manquant': len(trimestres_manquants) * retraite.get_montant_trimestriel_attendu(),
                    'statut': 'non_cotise'
                })
                continue
            
            # Analyser chaque cotisation
            for cotisation in cotisations_annee:
                # PAIEMENTS EXACTS - À METTRE DANS RÉGLÉS
                if cotisation.type_paiement in ['CMSS_EXACT', 'CMCAS_EXACT', 'CMSS_CMCAS']:
                    reglees.append({
                        'nom': retraite.nom,
                        'prenom': retraite.prenom,
                        'num_secu': retraite.num_secu,
                        'trimestre': cotisation.trimestre_de_remboursement,
                        'montant': str(cotisation.montant),
                        'type': cotisation.type_paiement,
                        'detail': cotisation.detail_ecart or "Paiement exact",
                        'statut': 'réglé'
                    })
                
                # PAIEMENTS PARTIELS - À METTRE DANS MANQUANTS
                elif cotisation.type_paiement in ['CMSS_PROCH', 'CMCAS_PROCH']:
                    manquants.append({
                        'nom': retraite.nom,
                        'prenom': retraite.prenom,
                        'num_secu': retraite.num_secu,
                        'trimestre': cotisation.trimestre_de_remboursement,
                        'trimestres_manquants': trimestres_manquants,
                        'montant_paye': str(cotisation.montant),
                        'montant_manquant': str(cotisation.ecart),
                        'type': cotisation.type_paiement,
                        'detail': cotisation.detail_ecart or "Paiement partiel",
                        'statut': 'partiel'                    })
                
                # PAIEMENTS INCOMPATIBLES - À METTRE DANS MANQUANTS
                elif cotisation.type_paiement == 'INCOMPATIBLE':
                    manquants.append({
                        'nom': retraite.nom,
                        'prenom': retraite.prenom,
                        'num_secu': retraite.num_secu,
                        'trimestre': cotisation.trimestre_de_remboursement,
                        'trimestres_manquants': trimestres_manquants,
                        'montant_manquant': str(cotisation.montant),
                        'type': 'INCOMPATIBLE',
                        'detail': cotisation.detail_ecart or "Montant incompatible",
                        'statut': 'non_recu'
                    })
            
            # Ajouter les trimestres complètement manquants (uniquement si le retraité a des cotisations mais manque des trimestres)
            if cotisations_annee.exists() and trimestres_manquants:
                for trimestre_manquant in trimestres_manquants:
                    # Vérifier si ce trimestre n'a pas déjà été traité dans les cotisations existantes
                    trimestre_deja_traite = any(
                        m.get('trimestre') == trimestre_manquant for m in manquants
                    )
                    
                    if not trimestre_deja_traite:
                        manquants.append({
                            'nom': retraite.nom,
                            'prenom': retraite.prenom,
                            'num_secu': retraite.num_secu,
                            'trimestre': trimestre_manquant,
                            'trimestres_manquants': [trimestre_manquant],
                            'montant_attendu': str(retraite.get_montant_trimestriel_attendu()),
                            'type': 'NON_PAYE',
                            'detail': f"Trimestre {trimestre_manquant} non payé",
                            'statut': 'non_recu' if int(trimestre_manquant.split()[-1]) < current_year else 'en_retard'
                        })
    
    except Exception as e:
        logger.error(f"Erreur classement résultats: {str(e)}", exc_info=True)
    
    return {
        'reglees': reglees,
        'non_reglees': non_reglees,
        'manquants': manquants
    }

def get_trimestres_manquants_par_retraite():
    trimestres_manquants = {}
    
    for retraite in Retraite.objects.all():
        manquants = retraite.get_trimestres_manquants()
        if manquants:
            trimestres_manquants[retraite.num_secu] = {
                'nom': retraite.nom,
                'prenom': retraite.prenom,
                'trimestres_manquants': manquants,
                'montant_attendu': retraite.get_montant_trimestriel_attendu(),
                'montant_total_manquant': len(manquants) * retraite.get_montant_trimestriel_attendu()
            }
    
    return trimestres_manquants

@require_POST
@login_required
def marquer_comme_paye(request, num_secu, type_objet, objet_id):
    try:
        retraite = get_object_or_404(Retraite, num_secu=num_secu)
        
        if type_objet == 'tm':
            objet = get_object_or_404(TM, id=objet_id, retraite=retraite)
            objet.statut = 'PAYE'
            objet.save()
        elif type_objet == 'arriere':
            objet = get_object_or_404(Arriere, id=objet_id, retraite=retraite)
            objet.statut = 'PAYE'
            objet.save()
        
        return JsonResponse({'success': True, 'message': 'Statut mis à jour avec succès'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
def get_virements_manques_par_retraite():
    virements_manques = []
    current_year = timezone.now().year
    
    for retraite in Retraite.objects.all():
        # Vérifier les cotisations de l'année en cours
        cotisations_annee_courante = retraite.cotisations.filter(
            operation_bancaire_date_piece_year=current_year
        )
        
        # Si aucune cotisation pour l'année en cours
        if not cotisations_annee_courante.exists():
            trimestres_manquants = retraite.get_trimestres_manquants(current_year)
            
            if trimestres_manquants:
                virements_manques.append({
                    'retraite': retraite,
                    'trimestres_manquants': trimestres_manquants,
                    'montant_attendu': retraite.get_montant_trimestriel_attendu(),
                    'statut': 'non_recu'
                })
    return virements_manques


def get_trimestres_rattachement(mois_rattachement):
    try:
        if isinstance(mois_rattachement, str) and '/' in mois_rattachement:
            mois, annee = mois_rattachement.split('/')
            mois = int(mois)
            annee = int(annee)
            
            trimestres = []
            if mois in [1, 2, 3]:
                trimestre_initial = f"Trimestre 1 (Janvier) {annee}"
            elif mois in [4, 5, 6]:
                trimestre_initial = f"Trimestre 2 (Avril) {annee}"
            elif mois in [7, 8, 9]:
                trimestre_initial = f"Trimestre 3 (Juillet) {annee}"
            else:
                trimestre_initial = f"Trimestre 4 (Octobre) {annee}"
            
            trimestres.append(trimestre_initial)
            
            trimestres_annee_suivante = [
                f"Trimestre 1 (Janvier) {annee+1}",
                f"Trimestre 2 (Avril) {annee+1}",
                f"Trimestre 3 (Juillet) {annee+1}",
                f"Trimestre 4 (Octobre) {annee+1}"
            ]
            
            trimestres.extend(trimestres_annee_suivante)
            return trimestres
            
    except Exception as e:
        print(f"Erreur dans get_trimestres_rattachement: {e}")
    
    return []
# permettre de rafraîchir manuellement les données :
@require_POST
@login_required
def refresh_cotisations(request):
    """
    Rafraîchir les données des cotisations depuis la base de données
    """
    try:
        # Recréer les données depuis la base
        imported_count = Banque.objects.count()
        
        from django.db.models import Count
        # Calculer le nombre de doublons
        duplicates_count = Banque.objects.values('nom_bd', 'date_piece', 'Montant_en_devise_interne')\
            .annotate(count=Count('id'))\
            .filter(count__gt=1)\
            .count()
        
        incoherent_names_count = NomIncoherent.objects.count()
        
        # Récupérer les détails des doublons pour la session
        doublons_detectes = []
        duplicates = Banque.objects.values('nom_bd', 'date_piece', 'Montant_en_devise_interne')\
            .annotate(count=Count('id'))\
            .filter(count__gt=1)
        
        for dup in duplicates:
            # Récupérer les opérations correspondantes
            operations = Banque.objects.filter(
                nom_bd=dup['nom_bd'],
                date_piece=dup['date_piece'],
                Montant_en_devise_interne=dup['Montant_en_devise_interne']
            )
            
            for op in operations:
                doublons_detectes.append({
                    'reference': op.N_piece,
                    'date': op.date_piece,
                    'montant': float(op.Montant_en_devise_interne),
                    'description': op.Texte,
                    'nom_bd': op.nom_bd,
                    'type': 'doublon_base'  # Car provenant de la base
                })
        
        # Mettre à jour la session avec les doublons
        request.session['dernier_import'] = {
            'imported_count': imported_count,
            'duplicates_count': duplicates_count,
            'incoherent_names_count': incoherent_names_count,
            'timestamp': timezone.now().isoformat(),
            'classement': classer_resultats(),
            'from_database': True
        }
        
        # Stocker aussi les doublons dans la session pour la vue cotisations
        request.session['doublons_import'] = doublons_detectes
        request.session.modified = True
        
        messages.success(request, "Données rafraîchies avec succès depuis la base de données.")
        
    except Exception as e:
        logger.error(f"Erreur rafraîchissement données: {str(e)}", exc_info=True)
        messages.error(request, f"Erreur lors du rafraîchissement des données: {str(e)}")
    
    return redirect('cotisations')


def preview_columns(request):
    try:
        if 'fichier' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Aucun fichier fourni'})
        
        fichier = request.FILES['fichier']
        
        df = pd.read_excel(fichier, nrows=5)
        
        return JsonResponse({
            'success': True,
            'columns': df.columns.tolist(),
            'preview': df.fillna('').to_dict('records')
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


    return stats



logger = logging.getLogger(__name__)

def accueil(request):
    # Récupérer l'année sélectionnée ou utiliser l'année courante
    selected_year = request.GET.get('year', timezone.now().year)
    try:
        selected_year = int(selected_year)
    except (ValueError, TypeError):
        selected_year = timezone.now().year
    
    # Générer la liste des années disponibles (2023 à année courante + 1)
    current_year = timezone.now().year
    years = list(range(2023, current_year + 2))
    
    # Calcul des dates pour le trimestre en cours
    now = timezone.now()
    current_month = now.month
    
    # Déterminer le trimestre en cours
    if current_month in [1, 2, 3]:
        current_quarter = 1
        quarter_start = datetime(current_year, 1, 1).date()
        quarter_end = datetime(current_year, 3, 31).date()
    elif current_month in [4, 5, 6]:
        current_quarter = 2
        quarter_start = datetime(current_year, 4, 1).date()
        quarter_end = datetime(current_year, 6, 30).date()
    elif current_month in [7, 8, 9]:
        current_quarter = 3
        quarter_start = datetime(current_year, 7, 1).date()
        quarter_end = datetime(current_year, 9, 30).date()
    else:
        current_quarter = 4
        quarter_start = datetime(current_year, 10, 1).date()
        quarter_end = datetime(current_year, 12, 31).date()
    
    # CORRECTION : Syntaxe correcte avec double underscore
    try:
        # Cotisations CMSS pour le trimestre en cours
        cmss_total = Cotisation.objects.filter(
            operation_bancaire__date_piece__gte=quarter_start,
            operation_bancaire__date_piece__lte=quarter_end,
            type_paiement__in=['CMSS_EXACT', 'CMSS_CMCAS', 'CMSS_PROCH']
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        # Cotisations CMCAS pour le trimestre en cours
        cmcas_total = Cotisation.objects.filter(
            operation_bancaire__date_piece__gte=quarter_start,
            operation_bancaire__date_piece__lte=quarter_end,
            type_paiement__in=['CMCAS_EXACT', 'CMSS_CMCAS', 'CMCAS_PROCH']
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
    except Exception as e:
        logger.error(f"Erreur dans le calcul des totaux: {str(e)}")
        cmss_total = Decimal('0')
        cmcas_total = Decimal('0')
    
    # Autres statistiques
    total_retraites = Retraite.objects.count()
    total_cotisations = Cotisation.objects.count()
    
    # Dernières cotisations (limité à 5)
    recent_cotisations = Cotisation.objects.select_related(
        'retraite', 'operation_bancaire'
    ).order_by('-operation_bancaire__date_piece')[:5]
    
    # Statistiques des retraités réglés vs non réglés
    retraites_regles = Retraite.objects.filter(
        cotisations__isnull=False
    ).distinct().count()
    
    retraites_non_regles = total_retraites - retraites_regles
    
    # Total des cotisations de l'année en cours
    total_annee_courante = Cotisation.objects.filter(
        operation_bancaire__date_piece__year=current_year
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # Données pour les statistiques trimestrielles
    stats_data = get_trimestrial_stats(selected_year)
    
    # Données pour les alertes
    alertes_noms_incoherents = NomIncoherent.objects.filter(
        date_operation__year=selected_year
    ).count()
    
    alertes_virements_manques = VirementManque.objects.filter(
        annee=selected_year
    ).count()
    
    # Total des remboursements pour l'année sélectionnée
    total_remboursements = Cotisation.objects.filter(
        operation_bancaire__date_piece__year=selected_year
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # Arriérés (à adapter selon votre logique métier)
    arrieres = calculate_arrieres(selected_year)
    
    # Noms incohérents pour l'année sélectionnée
    noms_incoherents = NomIncoherent.objects.filter(
        date_operation__year=selected_year
    )[:8000]  # Limiter à 8000 résultats
    
    # Virements manqués pour l'année sélectionnée
    virements_manques = VirementManque.objects.filter(
        annee=selected_year
    )[:8000]  # Limiter à 8000 résultats
    
    # Historique des opérations pour l'année sélectionnée
    historique = Cotisation.objects.filter(
        operation_bancaire__date_piece__year=selected_year
    ).select_related('retraite', 'operation_bancaire').order_by('-operation_bancaire__date_piece')[:5]
    
    # Préparer les données JSON pour le graphique
    stats_data_json = json.dumps({
        'labels': stats_data['labels'],
        'montants_cmss': [float(m) for m in stats_data['montants_cmss']],
        'montants_cmcas': [float(m) for m in stats_data['montants_cmcas']],
        'total_cmss_annuel': float(stats_data['total_cmss_annuel']),
        'total_cmcas_annuel': float(stats_data['total_cmcas_annuel'])
    })
    retraites_avec_trimestres = get_retraites_avec_trimestres(request)
     # Calculer les statistiques
    retraites_en_retard = sum(1 for r in retraites_avec_trimestres if r['trimestres_manquants'])
    total_manquant_global = sum(r['total_manquant'] for r in retraites_avec_trimestres)
    context = {
        'total_retraites': total_retraites,
        'total_cotisations': total_cotisations,
        'cmss_total': cmss_total,
        'cmcas_total': cmcas_total,
        'total_annee_courante': total_annee_courante,
        'recent_cotisations': recent_cotisations,
        'current_quarter': current_quarter,
        'current_year': current_year,
        'retraites_regles': retraites_regles,
        'retraites_non_regles': retraites_non_regles,
        'retraites_avec_trimestres': retraites_avec_trimestres,
        'retraites_avec_trimestres': retraites_avec_trimestres,
        'retraites_en_retard': retraites_en_retard,
        'total_manquant_global': total_manquant_global,
        # Nouvelles données pour le template
        'years': years,
        'selected_year': selected_year,
        'stats_data': stats_data,
        'stats_data_json': stats_data_json,
        'alertes_noms_incoherents': alertes_noms_incoherents,
        'alertes_virements_manques': alertes_virements_manques,
        'total_remboursements': total_remboursements,
        'arrieres': arrieres,
        'noms_incoherents': noms_incoherents,
        'virements_manques': virements_manques,
        'historique': historique,
    }
    
    return render(request, 'dashboard/accueil.html', context)

def get_trimestrial_stats(year):
    """Calcule les statistiques trimestrielles pour une année donnée"""
    stats = {
        'labels': ['T1:Janvier', 'T2:Avril', 'T3:Juillet', 'T4:Octobre'],
        'montants_cmss': [Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')],
        'montants_cmcas': [Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')],
        'total_cmss_annuel': Decimal('0'),
        'total_cmcas_annuel': Decimal('0')
    }
    
    # Périodes des trimestres
    trimestres = [
        (datetime(year, 1, 1).date(), datetime(year, 3, 31).date()),
        (datetime(year, 4, 1).date(), datetime(year, 6, 30).date()),
        (datetime(year, 7, 1).date(), datetime(year, 9, 30).date()),
        (datetime(year, 10, 1).date(), datetime(year, 12, 31).date())
    ]
    
    for i, (debut, fin) in enumerate(trimestres):
        # CMSS par trimestre - CORRECTION DES TYPES
        cmss_trimestre = Cotisation.objects.filter(
            operation_bancaire__date_piece__gte=debut,
            operation_bancaire__date_piece__lte=fin,
            type_paiement__in=['CMSS_EXACT', 'CMSS_CMCAS', 'CMSS_PROCH']
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        # CMCAS par trimestre - CORRECTION DES TYPES
        cmcas_trimestre = Cotisation.objects.filter(
            operation_bancaire__date_piece__gte=debut,
            operation_bancaire__date_piece__lte=fin,
            type_paiement__in=['CMCAS_EXACT', 'CMSS_CMCAS', 'CMCAS_PROCH']
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        stats['montants_cmss'][i] = cmss_trimestre
        stats['montants_cmcas'][i] = cmcas_trimestre
    
    # Totaux annuels
    stats['total_cmss_annuel'] = sum(stats['montants_cmss'])
    stats['total_cmcas_annuel'] = sum(stats['montants_cmcas'])
    
    return stats

def calculate_arrieres(year):
    """Calcule les arriérés pour une année donnée - CORRECTION DES TYPES"""
    # Somme des écarts des cotisations partielles
    arrieres_cmss = Cotisation.objects.filter(
        operation_bancaire__date_piece__year=year,
        type_paiement='CMSS_PROCH'
    ).aggregate(total=Sum('ecart'))['total'] or Decimal('0')
    
    arrieres_cmcas = Cotisation.objects.filter(
        operation_bancaire__date_piece__year=year,
        type_paiement='CMCAS_PROCH'
    ).aggregate(total=Sum('ecart'))['total'] or Decimal('0')
    
    # Ajouter les trimestres complètement manquants
    virements_manques = VirementManque.objects.filter(
        annee=year,
        statut__in=['non_recu', 'en_retard']
    ).aggregate(total=Sum('montant_attendu'))['total'] or Decimal('0')
    
    return abs(arrieres_cmss + arrieres_cmcas + virements_manques)
@require_GET
@csrf_exempt
def api_accueil_data(request):
    """API pour récupérer les données actualisées de la page d'accueil"""
    try:
        selected_year = int(request.GET.get('year', timezone.now().year))
        
        # Total des remboursements pour l'année
        total_remboursements = Cotisation.objects.filter(
            operation_bancaire__date_piece__year=selected_year
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        # Arriérés
        arrieres = calculate_arrieres(selected_year)
        
        # Alertes
        alertes_noms_incoherents = NomIncoherent.objects.filter(
            date_operation__year=selected_year
        ).count()
        
        alertes_virements_manques = VirementManque.objects.filter(
            annee=selected_year
        ).count()
        
        return JsonResponse({
            'success': True,
            'total_remboursements': str(total_remboursements),
            'arrieres': str(arrieres),
            'alertes_noms_incoherents': alertes_noms_incoherents,
            'alertes_virements_manques': alertes_virements_manques
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
def get_retraites_avec_trimestres(request):
    """
    Récupère tous les retraités avec leurs trimestres payés et manquants
    """
    selected_year = request.GET.get('year', timezone.now().year)
    try:
        selected_year = int(selected_year)
    except (ValueError, TypeError):
        selected_year = timezone.now().year
    
    retraites_data = []
    
    for retraite in Retraite.objects.all():
        # Trimestres payés pour l'année sélectionnée
        trimestres_payes = []
        cotisations_annee = retraite.cotisations.filter(
            operation_bancaire__date_piece__year=selected_year
        )
        
        total_paye = Decimal('0')
        for cotisation in cotisations_annee:
            if cotisation.trimestre_de_remboursement:
                trimestres_payes.append(cotisation.trimestre_de_remboursement)
            total_paye += cotisation.montant
        
        # Trimestres manquants pour l'année sélectionnée
        trimestres_manquants = []
        trimestres_attendus = [
            f"T1:Janvier {selected_year}",
            f"T2:Avril {selected_year}",
            f"T3:Juillet {selected_year}",
            f"T4:Octobre {selected_year}"
        ]
        
        for trimestre in trimestres_attendus:
            if trimestre not in trimestres_payes:
                trimestres_manquants.append(trimestre)
        
        montant_trimestriel = retraite.get_montant_trimestriel_attendu()
        total_manquant = len(trimestres_manquants) * montant_trimestriel
        
        retraites_data.append({
            'nom_complet': retraite.nom_complet,
            'num_secu': retraite.num_secu,
            'trimestres_payes': trimestres_payes,
            'trimestres_manquants': trimestres_manquants,
            'montant_trimestriel': montant_trimestriel,
            'total_paye': total_paye,
            'total_manquant': total_manquant
        })
    
    return retraites_data
@require_GET
@csrf_exempt
def api_noms_incoherents(request):
    try:
        year = request.GET.get('year')
        if not year:
            return JsonResponse({'error': 'Le paramètre year est requis'}, status=400)
        
        noms_incoherents = NomIncoherent.objects.filter(date_operation__year=year)
        
        data = []
        for item in noms_incoherents:
            data.append({
                'nom': item.nom,
                'trimestre': item.trimestre or "N/A",
                'date': item.date_operation.strftime('%d/%m/%Y'),
                'montant': str(item.montant)
            })
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@csrf_exempt
def api_virements_manques(request):
    try:
        year = request.GET.get('year')
        if not year:
            return JsonResponse({'error': 'Le paramètre year est requis'}, status=400)
        
        virements_manques = VirementManque.objects.filter(annee=year)
        
        data = []
        for item in virements_manques:
            data.append({
                'nom': item.nom,
                'prenom': item.prenom,
                'num_secu': item.num_secu,
                
                'trimestres_manquants': item.trimestres_manquants or [],
                'type': item.type,
                'montant_attendu': str(item.montant_attendu),
            })
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_trimestre(date):
    month = date.month
    if month <= 3:
        return 'T1:Janvier'
    elif month <= 6:
        return 'T2:Avril'
    elif month <= 9:
        return 'T3:Juillet'
    else:
        return 'T4:Octobre'


def is_superuser(user):
    return user.is_superuser
def is_gestionnaire(user):
    return hasattr(user, 'gestionnaireprofile') or user.is_superuser
# Vue pour les agents (superuser seulement)
@user_passes_test(is_superuser)
def gestionnaires_view(request):
    return render(request, 'dashboard/agents.html')
# Vue pour les patients (gestionnaires et superusers)
@user_passes_test(is_gestionnaire)
@login_required
def patients_view(request):
    # Empêcher l'ajout de patients si c'est un gestionnaire normal
    if hasattr(request.user, 'gestionnaireprofile') and not request.user.is_superuser:
        # Passer un flag pour désactiver les boutons d'ajout
        return render(request, 'dashboard/patients.html', {'can_add': False})
    return render(request, 'dashboard/patients.html', {'can_add': True})
@user_passes_test(is_superuser)
@require_POST
@csrf_exempt
def ajouter_gestionnaire(request):
    form = GestionnaireForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Gestionnaire ajouté avec succès'})
    else:
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({'success': False, 'errors': errors})
# Vue pour les cotisations (gestionnaires et superusers)
#@user_passes_test(is_gestionnaire)


@user_passes_test(is_superuser)
def get_gestionnaires(request):
    gestionnaires = GestionnaireProfile.objects.select_related('user').all()
    data = []
    
    for gestionnaire in gestionnaires:
        data.append({
            'username': gestionnaire.user.username,
            'email': gestionnaire.user.email,
            'nom': gestionnaire.nom,
            'prenom': gestionnaire.prenom,
            'date_ajout': gestionnaire.date_ajout.strftime('%d/%m/%Y'),
            'est_actif': gestionnaire.est_actif,
            'id': gestionnaire.id
        })
    
    return JsonResponse({'gestionnaires': data})
