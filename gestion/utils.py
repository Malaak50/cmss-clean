# Importation des bibliothèques nécessaires
import pandas as pd  # Pour la manipulation de données
import re  # Pour les expressions régulières
from unidecode import unidecode  # Pour la normalisation des caractères
from rapidfuzz import process, fuzz  # Pour le fuzzy matching
import os  # Pour les opérations sur le système de fichiers
from datetime import datetime, date  # Pour la gestion des dates
import decimal
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta

TITRES_INUTILES = [
    "m", "mme", "mlle", "mr", "dr", "pr", "ve", "vve", "ép", "ep", "epouse",
    "épouse de", "fille de", "madame", "monsieur", "docteur", "professeur"
]

# Dictionnaire des corrections manuelles spécifiques
CORRECTIONS_SPECIFIQUES = {
    'EL.HAILI.ZHOR': 'EL HAILI VVE EL MAYYANI ZHOR',
    'BAYA ET BOUSSETTA ABDELKRIM ET FOUZIA': 'BAYA ABDELKRIM',
    'ABDELKRIM ET FOUZIA BAYA ET BOUSSETTA': 'BAYA ABDELKRIM',
    'AMELHAY ABDELKRIM': 'AMELHAY ABDELKRIM'
}

def normaliser_nom(nom):
    """
    Normalise un nom pour faciliter la comparaison.
    
    Args:
        nom (str): Le nom à normaliser
        
    Returns:
        str: Le nom normalisé
    """
    if pd.isna(nom) or not isinstance(nom, str):  # Gestion des valeurs manquantes
        return ""
    
    # Conversion en majuscules et suppression des accents
    nom = nom.upper()
    nom = unidecode(nom)
    
    # Suppression des titres (Mr, Mme, etc.)
    nom = re.sub(r'\b(MR|MME|MLLE|M)\b\.?', '', nom)
    # Normalisation des veuves (VVE, VEUVE, etc.)
    nom = re.sub(r'\b(VVE|VEUVE|EPOUSE)\b', ' VVE ', nom)
    
    # Conservation uniquement des lettres, points et tirets
    nom = re.sub(r'[^A-Z.-]', ' ', nom)
    # Ajout d'espaces autour des séparateurs (. et -)
    nom = re.sub(r'([.-])', r' \1 ', nom)
    
    # Filtrage des mots trop courts et suppression des séparateurs seuls
    mots = [mot for mot in nom.split() if mot not in ['.', '-'] and len(mot) > 1]
    
    # Reconstruction du nom en gardant l'ordre original des mots
    return ' '.join(mots)

def preparer_base_database(db_df):
    """
    Prépare un dictionnaire de la base de données avec des variantes de noms.
    
    Args:
        db_df (DataFrame): DataFrame contenant la base de données
        
    Returns:
        dict: Dictionnaire des noms normalisés avec leurs informations
    """
    db_dict = {}
    for _, row in db_df.iterrows():
        nom_complet = row['Nom Correct'] if pd.notna(row['Nom Correct']) else ""
        cle = normaliser_nom(nom_complet)
        
        if cle:
            # Création de variantes pour les noms contenant VVE/EPOUSE
            variantes = {cle}
            if 'VVE' in cle:
                variantes.add(cle.replace('VVE', '').strip())
            
            # Ajout de chaque variante dans le dictionnaire
            for variante in variantes:
                db_dict[variante] = {
                    'Nom Complet': nom_complet.strip(),  # Nom original
                    'Mois rattachement': row.get('Mois rattachement', ''),  # Mois de rattachement
                    'cotisation cmss': row.get('Cotisation CMSS', ''),  # Cotisation CMSS
                    'cotisation cmcas': row.get('Cotisation CMCAS', ''),  # Cotisation CMCAS
                    'OriginalKey': cle  # Clé originale pour référence
                }
    return db_dict

def trouver_correspondance_rapide(nom_banque, db_dict, corrections_specifiques=None):
    """
    Version rapide utilisant le dictionnaire pré-calculé avec rapidfuzz.
    
    Args:
        nom_banque (str): Nom à rechercher
        db_dict (dict): Dictionnaire de la base de données
        corrections_specifiques (dict): Corrections manuelles spécifiques
        
    Returns:
        tuple: (match_info, score, clé_trouvée)
    """
    if corrections_specifiques is None:
        corrections_specifiques = CORRECTIONS_SPECIFIQUES
    
    # Vérification des corrections spécifiques en premier
    nom_banque_upper = nom_banque.upper()
    for pattern, correction in corrections_specifiques.items():
        if pattern.upper() in nom_banque_upper:
            cle_correction = normaliser_nom(correction)
            if cle_correction in db_dict:
                return db_dict[cle_correction], 100, cle_correction
            else:
                # Si la correction n'existe pas, on crée une entrée minimale
                return {
                    'Nom Complet': correction,
                    'Mois rattachement': '',
                    'cotisation cmss': '',
                    'cotisation cmcas': '',
                    'OriginalKey': cle_correction
                }, 100, cle_correction
    
    # Recherche standard avec rapidfuzz
    cle_banque = normaliser_nom(nom_banque)
    if not cle_banque:
        return None, 0, ""
    
    # Utilisation de rapidfuzz pour trouver le meilleur match
    result = process.extractOne(
        cle_banque,
        db_dict.keys(),
        scorer=fuzz.WRatio,  # Utilisation du ratio pondéré
        score_cutoff=65  # Score minimum acceptable réduit à 65
    )
    
    if result:
        meilleure_cle, meilleur_score, _ = result
        if meilleur_score >= 75:
            # Score élevé -> correspondance certaine
            return db_dict[meilleure_cle], meilleur_score, meilleure_cle
        elif meilleur_score >= 65:
            # Score moyen -> vérification supplémentaire
            original_key = db_dict[meilleure_cle]['OriginalKey']
            if fuzz.partial_ratio(cle_banque, original_key) > 70:
                return db_dict[meilleure_cle], meilleur_score, meilleure_cle
    
    return None, 0, ""
def decouper_noms_multiples(nom):
    if not isinstance(nom, str):
        return []
    return [frag.strip() for frag in re.split(r'\bet\b|,|&|\/', nom, flags=re.IGNORECASE) if frag.strip()]

def decouper_nom_fusionne(nom):
    nom = nom.strip()
    variantes = []
    longueur = len(nom)
    for i in range(2, longueur - 2):
        variantes.append(f"{nom[:i]} {nom[i:]}")
    for i in range(2, longueur - 4):
        for j in range(i + 1, longueur - 1):
            variantes.append(f"{nom[:i]} {nom[i:j]} {nom[j:]}")
    return variantes

def comparer_noms(nom_banque, df_retraites, seuil=65):
    # Vérification d'abord des corrections spécifiques
    for pattern, correction in CORRECTIONS_SPECIFIQUES.items():
        if pattern in nom_banque:
            # Recherche directe de la correction dans la base
            nom_corrige = correction
            for _, ligne in df_retraites.iterrows():
                if ligne['Nom Correct'] == nom_corrige:
                    return {
                        "status": "✔ Correspondance (correction spécifique)",
                        "match": nom_corrige,
                        "score": 100,
                        "ligne_retraite": ligne
                    }
    
    sous_noms = decouper_noms_multiples(nom_banque)
    resultats = []

    for sous_nom in sous_noms:
        candidats = [sous_nom]
        if ' ' not in sous_nom:
            candidats.extend(decouper_nom_fusionne(sous_nom))

        for candidat in candidats:
            nom_banque_net = normaliser_nom(candidat)

            for _, ligne in df_retraites.iterrows():
                nom_complet = ligne['Nom Correct']
                nom_ref_net = normaliser_nom(nom_complet)
                score = fuzz.token_sort_ratio(nom_banque_net, nom_ref_net)

                mots_banque = set(nom_banque_net.split())
                mots_ref = set(nom_ref_net.split())

                if mots_banque <= mots_ref or mots_ref <= mots_banque:
                    score = max(score, 95)

                resultats.append((candidat, nom_complet, score, ligne))

    meilleurs = [r for r in resultats if r[2] >= seuil]

    if meilleurs:
        meilleurs.sort(key=lambda x: x[2], reverse=True)
        top = meilleurs[0]
        return {
            "status": "✔ Correspondance",
            "match": top[1],
            "score": top[2],
            "ligne_retraite": top[3]
        }
    else:
        return {
            "status": "❌ Aucune correspondance",
            "match": "",
            "score": 0,
            "ligne_retraite": None
        }

def get_corrections_specifiques():
    """
    Retourne le dictionnaire des corrections spécifiques.
    """
    return CORRECTIONS_SPECIFIQUES.copy()
def analyser_montant_cotisation(montant_paye, montant_cmss_trimestriel, montant_cmcas_trimestriel):
    from decimal import Decimal, ROUND_HALF_UP
    
    # Conversions et arrondis
    montant_paye = Decimal(str(montant_paye)) if not isinstance(montant_paye, Decimal) else montant_paye
    montant_cmss_trimestriel = Decimal(str(montant_cmss_trimestriel)) if not isinstance(montant_cmss_trimestriel, Decimal) else montant_cmss_trimestriel
    montant_cmcas_trimestriel = Decimal(str(montant_cmcas_trimestriel)) if not isinstance(montant_cmcas_trimestriel, Decimal) else montant_cmcas_trimestriel
    
    montant_paye = montant_paye.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    montant_cmss_trimestriel = montant_cmss_trimestriel.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    montant_cmcas_trimestriel = montant_cmcas_trimestriel.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Utilisation des valeurs absolues pour les comparaisons
    montant_paye_abs = abs(montant_paye)
    cmss_abs = abs(montant_cmss_trimestriel)
    cmcas_abs = abs(montant_cmcas_trimestriel)
    
    # Calcul des différences
    diff_cmss = montant_paye_abs - cmss_abs
    diff_cmcas = montant_paye_abs - cmcas_abs
    somme = cmss_abs + cmcas_abs
    diff_somme = montant_paye_abs - somme
    
    # Définition d'un seuil de tolérance pour les paiements "proches"
    tolerance = Decimal('1.00')  # 1 DH de tolérance
    
    # Cas 1 : Somme exacte des deux cotisations
    if diff_somme <= tolerance and diff_somme >= Decimal('0'):
        return ('CMSS_CMCAS', Decimal('0'), Decimal('0'), "Paiement exact CMSS + CMCAS trimestriel")
    # Cas  : Somme  des deux cotisations avec reste 
    if diff_somme >= tolerance and diff_somme > Decimal('0'):
        return ('CMSS_CMCAS', Decimal('0'), diff_somme, f"Paiement  CMSS + CMCAS avec reste:{diff_somme}")

    # Cas 2 : Égalité exacte avec CMSS (avec tolérance)
    if diff_cmss <= tolerance and montant_paye_abs >= cmss_abs and diff_cmss >= Decimal('0'):
        return ('CMSS_EXACT', Decimal('0'), max(Decimal('0'), diff_cmss), "Paiement trimestriel CMSS exact")

    # Cas 3 : Égalité exacte avec CMCAS (avec tolérance)
    if diff_cmcas <= tolerance and montant_paye_abs >= cmcas_abs and diff_cmcas >= Decimal('0'):
        return ('CMCAS_EXACT', Decimal('0'), max(Decimal('0'), diff_cmcas), "Paiement trimestriel CMCAS exact")

    # Cas 4 : CMSS exact avec reste pour CMCAS
    if diff_cmss >= tolerance and diff_cmcas > tolerance and montant_paye_abs > cmss_abs and diff_cmss >= Decimal('0'):
        return ('CMSS_EXACT', Decimal('0'), diff_cmss, f"Paiement CMSS avec reste: {diff_cmss} DH pour CMCAS")

    # Cas 5 : CMCAS exact avec reste pour CMSS
    if diff_cmcas >= -tolerance and diff_cmss > tolerance and montant_paye_abs > cmcas_abs and diff_cmcas >= Decimal('0'):
        return ('CMCAS_EXACT', Decimal('0'), diff_cmcas, f"Paiement CMCAS avec reste: {diff_cmcas} DH pour CMSS")

    # Cas 6 : Montant proche de CMSS mais insuffisant
    if abs(diff_cmss) < abs(diff_cmcas) and montant_paye_abs < cmss_abs:
        return ('CMSS_PROCH', abs(diff_cmss), Decimal('0'), f"Manque {abs(diff_cmss)} DH pour CMSS trimestriel complet")

    # Cas 7 : Montant proche de CMCAS mais insuffisant
    if abs(diff_cmcas) < abs(diff_cmss) and montant_paye_abs < cmcas_abs:
        return ('CMCAS_PROCH', abs(diff_cmcas), Decimal('0'), f"Manque {abs(diff_cmcas)} DH pour CMCAS trimestriel complet")

    # Cas 8 : Paiement excédentaire pour CMSS + CMCAS
    if diff_somme > tolerance:
        return ('CMSS_CMCAS', Decimal('0'), diff_somme, f"Paiement excédentaire, reste: {diff_somme} DH")

    

    # Cas par défaut : situation non prévue
    #return ('INDETERMINE', Decimal('0'), Decimal('0'), f"Situation non prévue. Montant payé: {montant_paye_abs}, CMSS: {cmss_abs}, CMCAS: {cmcas_abs}")
def get_trimestre_from_date_piece(date_saisie):
    if not date_saisie:
        return "Trimestre non spécifié"
    
    mois = date_saisie.month
    annee = date_saisie.year
    
    if mois in [1, 2, 3]:
        return f"T1:Janvier {annee}"
    elif mois in [4, 5, 6]:
        return f"T2:Avril {annee}"
    elif mois in [7, 8, 9]:
        return f"T3:Juillet {annee}"
    else:
        return f"T4:Octobre {annee}"

def get_mois_rattachement_trimestre(mois_rattachement):
    try:
        if isinstance(mois_rattachement, str) and '/' in mois_rattachement:
            mois, annee = mois_rattachement.split('/')
            mois = int(mois)
            annee = int(annee)
            
            if mois in [1, 2, 3]:
                return f"T1:Janvier {annee}"
            elif mois in [4, 5, 6]:
                return f"T2:Avril {annee}"
            elif mois in [7, 8, 9]:
                return f"T3:Juillet {annee}"
            elif mois in [10, 11, 12]:
                return f"T4:Octobre {annee}"
            else:
                return f"Trimestre non spécifié ({mois}/{annee})"
    except Exception as e:
        print(f"Erreur dans get_mois_rattachement_trimestre: {e}")
        pass
    return "Trimestre non spécifié"
def nettoyer_nom_colonne(nom_colonne):
    if not isinstance(nom_colonne, str):
        return str(nom_colonne)
    return nom_colonne.replace('\n', ' ').replace('\r', ' ').strip()





# Fonctions pour gérer les trimestres manquants
def get_trimestres_annee(annee):
    """Retourne tous les trimestres d'une année donnée"""
    return [
        f"Trimestre 1 (Janvier) {annee}",
        f"Trimestre 2 (Avril) {annee}",
        f"Trimestre 3 (Juillet) {annee}",
        f"Trimestre 4 (Octobre) {annee}"
    ]



def get_annee_courante():
    """Retourne l'année courante"""
    return date.today().year

def get_trimestres_manquants_par_retraite(retraite, annee=None):
    """Retourne les trimestres manquants pour un retraité spécifique"""
    if annee is None:
        annee = get_annee_courante()
    
    trimestres_attendus = get_trimestres_annee(annee)
    trimestres_payes = set()
    
    # Récupérer tous les trimestres déjà payés pour cette année
    for cotisation in retraite.cotisations.all():
        if cotisation.trimestre_de_remboursement and str(annee) in cotisation.trimestre_de_remboursement:
            trimestres_payes.add(cotisation.trimestre_de_remboursement)
    
    # Identifier les trimestres manquants
    trimestres_manquants = []
    for trimestre in trimestres_attendus:
        if trimestre not in trimestres_payes:
            trimestres_manquants.append(trimestre)
    
    return trimestres_manquants

def get_montant_trimestriel_attendu_par_retraite(retraite):
    """Retourne le montant trimestriel attendu pour un retraité"""
    montant_cmss = retraite.montant_cmss_trimestriel or Decimal('0')
    montant_cmcas = retraite.montant_cmcas_trimestriel or Decimal('0')
    return montant_cmss + montant_cmcas

def analyser_trimestres_manquants():
    """Analyse tous les trimestres manquants pour tous les retraités"""
    from gestion.models import Retraite, VirementManque
    
    annee_courante = get_annee_courante()
    trimestres_manquants_par_retraite = {}
    
    for retraite in Retraite.objects.all():
        trimestres_manquants = get_trimestres_manquants_par_retraite(retraite, annee_courante)
        
        if trimestres_manquants:
            montant_attendu = get_montant_trimestriel_attendu_par_retraite(retraite)
            montant_total_manquant = len(trimestres_manquants) * montant_attendu
            
            trimestres_manquants_par_retraite[retraite.num_secu] = {
                'nom': retraite.nom,
                'prenom': retraite.prenom,
                'num_secu': retraite.num_secu,
                'trimestres_manquants': trimestres_manquants,
                'montant_attendu_par_trimestre': montant_attendu,
                'montant_total_manquant': montant_total_manquant,
                'nombre_trimestres_manquants': len(trimestres_manquants)
            }
            
            # Stocker dans VirementManque
            for trimestre in trimestres_manquants:
                # Déterminer la date prévue (dernier jour du trimestre)
                if "Trimestre 1" in trimestre:
                    date_prevue = date(annee_courante, 3, 31)
                elif "Trimestre 2" in trimestre:
                    date_prevue = date(annee_courante, 6, 30)
                elif "Trimestre 3" in trimestre:
                    date_prevue = date(annee_courante, 9, 30)
                else:  # Trimestre 4
                    date_prevue = date(annee_courante, 12, 31)
                
                # Vérifier si ce virement manqué existe déjà
                if not VirementManque.objects.filter(
                    num_secu=retraite.num_secu,
                    trimestre_manquant=trimestre,
                    annee=annee_courante
                ).exists():
                    VirementManque.objects.create(
                        nom=retraite.nom,
                        prenom=retraite.prenom,
                        num_secu=retraite.num_secu,
                        trimestre_manquant=trimestre,
                        date_prevue=date_prevue,
                        montant_attendu=montant_attendu,
                        statut='non_recu',
                        annee=annee_courante
                    )
    
    return trimestres_manquants_par_retraite

def get_trimestres_fixes(date_reference=None):
    """
    Retourne les trimestres fixes de l'année
    """
    if date_reference is None:
        date_reference = datetime.now()
    
    annee = date_reference.year
    return [
        f"T1 {annee} (Janvier-Mars)",
        f"T2 {annee} (Avril-Juin)", 
        f"T3 {annee} (Juillet-Septembre)",
        f"T4 {annee} (Octobre-Décembre)"
    ]

def verifier_trimestres_manquants(retraite, annee=None):
    """
    Vérifie les trimestres manquants pour un retraité
    """
    if annee is None:
        annee = datetime.now().year
    
    trimestres_attendus = get_trimestres_fixes(datetime(annee, 1, 1))
    trimestres_payes = set()
    
    # Récupérer les trimestres déjà payés
    for cotisation in retraite.cotisations.filter(
        operation_bancaire_date_piece_year=annee
    ):
        if cotisation.trimestre_de_remboursement:
            trimestres_payes.add(cotisation.trimestre_de_remboursement)
    
    # Identifier les trimestres manquants
    return [t for t in trimestres_attendus if t not in trimestres_payes]
