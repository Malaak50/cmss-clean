from django import forms
from .models import Retraite, TM, Arriere,  Cotisation , Banque 
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from django.db import transaction
import pandas as pd
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Retraite
import re
from decimal import Decimal
from django.contrib.auth.models import User
from .models import GestionnaireProfile

class RetraiteForm(forms.ModelForm):
    class Meta:
        model = Retraite
        fields = [
            'num_secu',
            'id_num_personne',
            'nom',
            'prenom',
            'date_naissance',
            'mois_rattachement',
            'pension_cnss',
            'pension_cimr',
            'nom_agence',
            'montant_cmss_mensuel',
            'part_patronale_cmss_mensuel',
            'montant_cmss_trimestriel',
            'montant_cmcas_trimestriel',
        ]
        widgets = {
            'num_secu': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro de sécurité sociale'
            }),
            'id_num_personne': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID personne'
            }),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'date_naissance': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': timezone.now().date().isoformat()
            }),
            'mois_rattachement': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MM/YYYY',
                'pattern': r'\d{2}/\d{4}',
            }),
            'pension_cnss': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'pension_cimr': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'montant_cmss_mensuel': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True,
                'tabindex': '-1'
            }),
            'part_patronale_cmss_mensuel': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True,
                'tabindex': '-1'
            }),
            'montant_cmss_trimestriel': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True,
                'tabindex': '-1'
            }),
            'montant_cmcas_trimestriel': forms.NumberInput(attrs={
                'class': 'form-control bg-light',
                'readonly': True,
                'tabindex': '-1'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        calcul_fields = [
            'montant_cmss_mensuel',
            'part_patronale_cmss_mensuel',
            'montant_cmss_trimestriel',
            'montant_cmcas_trimestriel',
        ]
        for field_name in calcul_fields:
            self.fields[field_name].disabled = True
            self.fields[field_name].required = False
            if self.instance and self.instance.pk:
                self.initial[field_name] = getattr(self.instance, field_name)

class TMForm(forms.ModelForm):
    class Meta:
        model = TM
        fields = ['date_tm', 'montant_total', 'statut']
        widgets = {
            'date_tm': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'montant_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'statut': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        self.retraite = kwargs.pop('retraite', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.retraite:
            instance.retraite = self.retraite
        if commit:
            instance.save()
        return instance

class ArriereForm(forms.ModelForm):

    class Meta:
        model = Arriere
        fields = ['date_arriere', 'type_arriere', 'nombre_de_mois', 'montant_cmss', 'montant_cmcas', 'statut']
        widgets = {
            'date_arriere': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'type_arriere': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        self.retraite = kwargs.pop('retraite', None)
        super().__init__(*args, **kwargs)
        
        # Masquer les champs montant en fonction du type sélectionné
        if 'type_arriere' in self.data:
            type_arriere = self.data.get('type_arriere')
            self._update_fields_visibility(type_arriere)
        elif self.instance.pk:
            self._update_fields_visibility(self.instance.type_arriere)
    
    def _update_fields_visibility(self, type_arriere):
        if type_arriere == 'CMSS':
            self.fields['montant_cmcas'].widget = forms.HiddenInput()
        elif type_arriere == 'CMCAS':
            self.fields['montant_cmss'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()
        type_arriere = cleaned_data.get('type_arriere')
        
        if type_arriere in ['CMSS', 'LES_DEUX'] and not cleaned_data.get('montant_cmss'):
            self.add_error('montant_cmss', "Ce champ est obligatoire pour le type sélectionné")
        
        if type_arriere in ['CMCAS', 'LES_DEUX'] and not cleaned_data.get('montant_cmcas'):
            self.add_error('montant_cmcas', "Ce champ est obligatoire pour le type sélectionné")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.retraite:
            instance.retraite = self.retraite  # Utilisez l'objet retraite directement
        if commit:
            instance.save()
        return instance

class BanqueForm(forms.ModelForm):
    class Meta:
        model = Banque
        fields = '__all__'
        widgets = {
            'date_piece': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'Texte': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'nom_dans_bd': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'N_piece': forms.NumberInput(attrs={'class': 'form-control'}),
            'Montant_en_devise_interne': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
        }

    def clean_date_piece(self):
        date_piece = self.cleaned_data.get('date_piece')
        if date_piece and date_piece > timezone.now().date():
            raise ValidationError("La date ne peut pas être dans le futur")
        return date_piece

class CotisationForm(forms.ModelForm):
    class Meta:
        model = Cotisation
        exclude = ['montant']  # Montant géré automatiquement
        widgets = {
            'retraite': forms.Select(attrs={'class': 'form-control'}),
            'operation_bancaire': forms.Select(attrs={'class': 'form-control'}),
            'montant_cmss_trimestriel': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'montant_cmcas_trimestriel': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'trimestre_de_remboursement': forms.TextInput(attrs={'class': 'form-control'}),
            'detail_ecart': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtre les retraités actifs si nécessaire
        self.fields['retraite'].queryset = Retraite.objects.all()
        
        if self.instance and self.instance.operation_bancaire:
            self.fields['operation_bancaire'].disabled = True
            self.initial['montant'] = self.instance.operation_bancaire.Montant_en_devise_interne

    def clean(self):
        cleaned_data = super().clean()
        operation_bancaire = cleaned_data.get('operation_bancaire')
        
        if operation_bancaire:
            if not operation_bancaire.date_piece:
                raise ValidationError("L'opération bancaire doit avoir une date valide")
        
        return cleaned_data

class ImportBanqueForm(forms.Form):
    fichier = forms.FileField(
        label="Fichier Excel de la banque",
        help_text="Format attendu: .xlsx avec les colonnes: Nº pièce, Date pièce, Montant en devise interne, Texte",
        validators=[]
    )
    
    def clean_fichier(self):
        file = self.cleaned_data.get('fichier')
        if not file:
            raise forms.ValidationError("Aucun fichier n'a été téléchargé")
        
        if not file.name:
            raise forms.ValidationError("Le fichier n'a pas de nom")
        
        # Vérifications plus permissives
        allowed_extensions = ['.xlsx', '.xls', '.XLSX', '.XLS']
        if not any(file.name.endswith(ext) for ext in allowed_extensions):
            raise forms.ValidationError("Seuls les fichiers Excel (.xlsx, .xls) sont acceptés")
        
        # Vérification du type MIME
        if hasattr(file, 'content_type'):
            if file.content_type not in [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel',
                'application/octet-stream'
            ]:
                raise forms.ValidationError("Le type de fichier n'est pas un fichier Excel valide")
        
        # Vérification de la taille du fichier (max 10MB)
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Le fichier est trop volumineux (max 10MB)")
        
        if file.size == 0:
            raise forms.ValidationError("Le fichier est vide")
        
        return file

class CotisationForm(forms.ModelForm):
    class Meta:
        model = Cotisation
        exclude = ['montant']
        widgets = {
            'retraite': forms.Select(attrs={'class': 'form-control'}),
            'operation_bancaire': forms.Select(attrs={'class': 'form-control'}),
            'montant_cmss_trimestriel': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'montant_cmcas_trimestriel': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'trimestre_de_remboursement': forms.TextInput(attrs={'class': 'form-control'}),
            'detail_ecart': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['retraite'].queryset = Retraite.objects.all()
        
        if self.instance and self.instance.operation_bancaire:
            self.fields['operation_bancaire'].disabled = True
            self.initial['montant'] = self.instance.operation_bancaire.Montant_en_devise_interne

    def clean(self):
        cleaned_data = super().clean()
        operation_bancaire = cleaned_data.get('operation_bancaire')
        
        if operation_bancaire:
            if not operation_bancaire.date_piece:
                raise ValidationError("L'opération bancaire doit avoir une date valide")
        
        return cleaned_data
class GestionnaireForm(forms.ModelForm):
    # Champs du modèle User
    username = forms.CharField(
        max_length=150, 
        required=True,
        label="Nom d'utilisateur"
    )
    email = forms.EmailField(
        required=True,
        label="Email"
    )
    
    # Champs du modèle GestionnaireProfile
    nom = forms.CharField(
        max_length=100, 
        required=True,
        label="Nom"
    )
    prenom = forms.CharField(
        max_length=100, 
        required=True,
        label="Prénom"
    )
    
    # Champs pour les mots de passe
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Mot de passe",
        min_length=8
    )
    confirmation_password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Confirmation du mot de passe"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email']
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation_password = cleaned_data.get("confirmation_password")
        
        if password and confirmation_password and password != confirmation_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Créer l'utilisateur
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password']
        )
        
        # Créer le profil gestionnaire avec les champs personnalisés
        gestionnaire_profile = GestionnaireProfile(
            user=user,
            nom=self.cleaned_data['nom'],
            prenom=self.cleaned_data['prenom']
        )
        
        if commit:
            gestionnaire_profile.save()
        
        return user