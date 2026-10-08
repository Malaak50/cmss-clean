
# 💳 CMSS  - Système de Gestion des Cotisations des Retraités

## 📖 Présentation

CMSS Clean est une application web développée avec Django permettant la gestion, le suivi et l'analyse des cotisations des retraités.

L'application centralise les informations des retraités, automatise le calcul des cotisations CMSS et CMCAS, gère les arriérés et les TM (Titres de Mouvement), et permet l'importation de relevés bancaires afin de rapprocher automatiquement les paiements reçus avec les dossiers des retraités.

Le système détecte également :

- les paiements exacts ;
- les paiements partiels ;
- les virements manquants ;
- les doublons ;
- les noms incohérents présents dans les relevés bancaires.

---

# 🎯 Objectifs

- Digitaliser la gestion des cotisations.
- Faciliter le suivi des retraités.
- Automatiser le rapprochement bancaire.
- Détecter les anomalies de paiement.
- Réduire les erreurs de traitement manuel.
- Fournir des indicateurs et tableaux de bord de suivi.

---

# ✨ Fonctionnalités

## 👤 Gestion des retraités

- Ajout de retraités
- Modification et consultation des informations
- Gestion du numéro de sécurité sociale
- Gestion du numéro de personne
- Suivi des pensions CNSS et CIMR
- Calcul automatique des cotisations

### Calcul automatique

Le système calcule automatiquement :

- CMSS mensuelle
- Part patronale CMSS
- CMSS trimestrielle
- CMCAS trimestrielle

À partir des montants des pensions :

```text
Pension CNSS + Pension CIMR
```

---

## 💰 Gestion des cotisations

Chaque cotisation est automatiquement liée :

- à un retraité ;
- à une opération bancaire ;
- à un trimestre de remboursement.

Le système identifie plusieurs types de paiements :

- CMSS exact
- CMCAS exact
- CMSS + CMCAS
- CMSS proche
- CMCAS proche
- Incompatible

---

## 🏦 Importation des opérations bancaires

Importation de fichiers :

```text
.xlsx
.xls
```

Traitements réalisés :

- Lecture automatique du fichier Excel
- Vérification des colonnes obligatoires
- Nettoyage des données
- Détection des doublons
- Association des virements aux retraités
- Création automatique des cotisations
- Génération de rapports d'import

---

## 🔍 Rapprochement automatique des paiements

Le système compare :

- le montant reçu ;
- le montant attendu.

Puis classe les opérations :

### ✅ Réglées

Paiements conformes aux montants attendus.

### ⚠️ Partiellement réglées

Montants proches mais incomplets.

### ❌ Non réglées

Absence de paiement ou montant incompatible.

---

## 🚨 Détection des anomalies

### Noms incohérents

Le rapprochement bancaire utilise :

- RapidFuzz
- FuzzyWuzzy
- Levenshtein

pour retrouver automatiquement les correspondances malgré les fautes d'orthographe.

Les opérations non identifiées sont enregistrées comme :

```text
NomIncoherent
```

---

### Virements manquants

Détection automatique :

- trimestres non payés ;
- paiements en retard ;
- paiements partiels ;
- virements absents.

---

## 📑 Gestion des TM

Gestion des Titres de Mouvement :

- création d'un TM ;
- historique des TM ;
- changement de statut ;

Statuts disponibles :

- En attente
- Payé
- Annulé

---

## 📄 Gestion des arriérés

Gestion des arriérés CMSS et CMCAS :

- CMSS
- CMCAS
- Les deux

Fonctionnalités :

- calcul du montant dû ;
- suivi du nombre de mois ;
- historique ;
- gestion du statut.

---

## 📊 Tableau de bord

Le tableau de bord fournit :

- nombre total de retraités ;
- nombre de cotisations ;
- montants CMSS encaissés ;
- montants CMCAS encaissés ;
- virements manquants ;
- noms incohérents détectés ;
- statistiques trimestrielles ;
- historique des opérations récentes.

---

## 🔐 Gestion des utilisateurs

### Super Administrateur

Peut :

- gérer les retraités ;
- gérer les cotisations ;
- gérer les gestionnaires ;
- consulter toutes les statistiques.

### Gestionnaire

Peut :

- consulter les données ;
- effectuer le suivi.

Les permissions sont gérées via les groupes Django.

---

# 🏗️ Architecture du projet

```text
cmss-clean/
│
├── cmss/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── gestion/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── middleware.py
│   └── utils.py
│
├── static/
├── templates/
│
├── manage.py
├── requirements.txt
└── README.md
```

---

# 🛠️ Technologies utilisées

## Backend

- Python 3.13
- Django 4.2

## Base de données

- MySQL

## Frontend

- HTML5
- CSS3
- Bootstrap 5
- JavaScript

## Bibliothèques principales

- Pandas
- OpenPyXL
- Django Crispy Forms
- Django Import Export
- Django REST Framework
- RapidFuzz
- FuzzyWuzzy
- Levenshtein
- Unidecode

---

# ⚙️ Installation

## 1. Cloner le dépôt

```bash
git clone https://github.com/Malaak50/cmss-clean.git
cd cmss-clean
```

## 2. Créer un environnement virtuel

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux

```bash
source .venv/bin/activate
```

---

## 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## 4. Configurer MySQL

Créer la base :

```sql
CREATE DATABASE cmss_db;
```

Configurer :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'cmss_db',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

---

## 5. Effectuer les migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 6. Créer un compte administrateur

```bash
python manage.py createsuperuser
```

---

## 7. Lancer l'application

```bash
python manage.py runserver
```

Accès :

```text
http://127.0.0.1:8000/
```

---

# 📈 Compétences mobilisées

- Développement Backend avec Django
- Architecture MVC/MVT
- Manipulation de données avec Pandas
- Traitement de fichiers Excel
- Base de données relationnelle MySQL
- Authentification et gestion des rôles
- Détection d'anomalies métiers
- Rapprochement bancaire automatisé
- Analyse de données et reporting
- Gestion de projet avec Git et GitHub

---

Cette version reflète réellement ce que font tes modèles (Retraite, Cotisation, Banque, TM, Arriere, VirementManque, NomIncoherent) ainsi que les fonctionnalités visibles dans views.py et les dépendances du projet. Elle est adaptée à GitHub et à un portfolio professionnel.
