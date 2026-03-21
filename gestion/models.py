from django.db import models
from django.core.validators import RegexValidator,MinValueValidator
from django.core.exceptions import ValidationError  # Import manquant ajouté ici
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User,Group

import uuid 
def generate_temp_num_secu():
    return str(uuid.uuid4().int)[:20]

class Retraite(models.Model):

    num_secu_validator = RegexValidator(
        regex=r'^[0-9]{8}$',
        message="Le numéro de sécurité sociale doit contenir 8 chiffres",
        code='invalid_num_secu'
    )
    num_secu = models.CharField(
        "Numéro de Sécurité Sociale",
        max_length=20,
        primary_key=True,  # Ceci en fait la clé primaire
        validators=[num_secu_validator],
    )

    nom_agence = models.CharField("Nom Agence", max_length=100, blank=True, null=True)
    qualite_personne = models.CharField("Qualité Personne", max_length=50, blank=True, null=True)

    id_personne_validator = RegexValidator(
        regex=r'^[0-9]{5,6}$',
        message="L'ID personne doit contenir entre 5 et 6 chiffres"
    )
    id_num_personne = models.CharField(
        "ID Numéro Personne",
        max_length=6,
        unique=True,
        blank=True,
        null=True,
        validators=[id_personne_validator],
    )

    nom = models.CharField("Nom", max_length=100)
    prenom = models.CharField("Prénom", max_length=100, default="Non spécifié")
    date_naissance = models.DateField("Date de Naissance", blank=True, null=True)
    mois_rattachement = models.CharField("Mois de Rattachement", max_length=7)

    pension_cnss = models.DecimalField("Pension CNSS", max_digits=10, decimal_places=2)
    pension_cimr = models.DecimalField("Pension CIMR", max_digits=10, decimal_places=2, blank=True, null=True)

    montant_cmss_mensuel = models.DecimalField(
        "Montant CMSS Mensuel", max_digits=10, decimal_places=2, blank=True, null=True)
    part_patronale_cmss_mensuel = models.DecimalField(
        "Part Patronale CMSS Mensuel", max_digits=10, decimal_places=2, blank=True, null=True)
    montant_cmss_trimestriel = models.DecimalField(
        "Montant CMSS Trimestriel", max_digits=10, decimal_places=2, blank=True, null=True)
    montant_cmcas_trimestriel = models.DecimalField(
        "Montant CMCAS Trimestriel", max_digits=10, decimal_places=2, blank=True, null=True)

    def clean(self):
        super().clean()
        #if self.num_secu:
            #if Retraite.objects.exclude(pk=self.pk).filter(num_secu=self.num_secu).exists():
               # raise ValidationError({'num_secu': 'Ce numéro de sécurité sociale existe déjà'})
        #if self.id_num_personne:
           # if Retraite.objects.exclude(pk=self.pk).filter(id_num_personne=self.id_num_personne).exists():
                #raise ValidationError({'id_num_personne': "Cet ID personne existe déjà"})

    def calculer_cotisations(self):
        # Conversion sécurisée en Decimal
        pension_cnss = Decimal(str(self.pension_cnss or 0))
        pension_cimr = Decimal(str(self.pension_cimr or 0))
        total = pension_cnss + pension_cimr

        self.montant_cmss_mensuel = total * Decimal('0.0333')
        self.part_patronale_cmss_mensuel = total * Decimal('0.0666')
        self.montant_cmss_trimestriel = self.montant_cmss_mensuel * Decimal('3')
        self.montant_cmcas_trimestriel = total * Decimal('0.0225') * Decimal('3')

    def save(self, *args, **kwargs):
        self.calculer_cotisations()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'gestion_retraite'
        verbose_name = "Gestion Retraite"
        verbose_name_plural = "Gestion des Retraites"

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}"

    @property
    def total_pensions(self):
        return Decimal(str(self.pension_cnss or 0)) + Decimal(str(self.pension_cimr or 0))
    def get_montant_trimestriel_attendu(self):
        """Retourne le montant trimestriel attendu pour ce retraité"""
        return (self.montant_cmss_trimestriel or Decimal('0')) + (self.montant_cmcas_trimestriel or Decimal('0'))
    
    def get_trimestres_manquants(self, annee=None):
        """Retourne les trimestres manquants pour une année donnée"""
        if annee is None:
            annee = timezone.now().year
        
        trimestres_attendus = [
            f"T1:Janvier {annee}",
            f"T2:Avril {annee}",
            f"T3:Juillet {annee}",
            f"T4:Octobre {annee}"
        ]
        
        trimestres_payes = set()
        for cotisation in self.cotisations.filter(
            operation_bancaire__date_piece__year=annee
        ):
            if cotisation.trimestre_de_remboursement:
                trimestres_payes.add(cotisation.trimestre_de_remboursement)
        
        return [t for t in trimestres_attendus if t not in trimestres_payes]
    
    def a_paye_tous_trimestres(self, annee=None):
        """Vérifie si le retraité a payé tous les trimestres pour une année"""
        if annee is None:
            annee = timezone.now().year
        
        return len(self.get_trimestres_manquants(annee)) == 0
    def __str__(self):
        return self.nom_complet

    def tms(self):
        #return self.tm_set.all()
         return self.tms.all()
    def arrieres(self):
        #return self.arriere_set.all()
        return self.arrieres.all()


class TM(models.Model):

    id = models.AutoField(primary_key=True)

    retraite = models.ForeignKey(
        Retraite,
        on_delete=models.CASCADE,
        related_name='tms',
        to_field='num_secu',  # Correct
        db_column='retraite_num_secu',  # Doit correspondre à db
    )
    date_tm = models.DateField("Date du TM")
    montant_total = models.DecimalField(
        "Montant total", 
        max_digits=10, 
        decimal_places=2,
        default=0.00
    )
    statut = models.CharField("Statut", max_length=20, choices=[
        ('EN_ATTENTE', 'En attente'),
        ('PAYE', 'Payé'),
        ('ANNULE', 'Annulé')
    ], default='EN_ATTENTE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"TM du {self.date_tm} - {self.montant_total}"
    def save(self, *args, **kwargs):
        # Validation stricte avant sauvegarde
        if not isinstance(self.retraite, Retraite):
            raise ValueError("L'instance Retraite doit être fournie")
        if not Retraite.objects.filter(num_secu=self.retraite.num_secu).exists():
            raise ValueError("Le retraité spécifié n'existe pas")
        super().save(*args, **kwargs)
    class Meta:
        db_table = 'gestion_tm'
        ordering = ['-date_tm']

class Arriere(models.Model):
    id = models.AutoField(primary_key=True)

    retraite = models.ForeignKey(
        Retraite,
        on_delete=models.CASCADE,
        related_name='arrieres',
        to_field='num_secu',
        db_column='retraite_num_secu',
    )
    date_arriere = models.DateField("Date de l'arriéré")
    type_arriere = models.CharField("Type", max_length=20, choices=[
        ('CMSS', 'CMSS'),
        ('CMCAS', 'CMCAS'),
        ('LES_DEUX', 'Les deux')
    ])
    nombre_de_mois = models.PositiveSmallIntegerField(
        "Nombre de mois", 
        default=1,
        validators=[MinValueValidator(1)]
    )  
    montant_cmss = models.DecimalField("Montant CMSS", max_digits=10, decimal_places=2, null=True, blank=True)
    montant_cmcas = models.DecimalField("Montant CMCAS", max_digits=10, decimal_places=2, null=True, blank=True)
    statut = models.CharField("Statut", max_length=20, choices=[
        ('EN_ATTENTE', 'En attente'),
        ('PAYE', 'Payé'),
        ('ANNULE', 'Annulé')
    ], default='EN_ATTENTE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Arriéré {self.get_type_arriere_display()} - {self.nombre_de_mois} mois"
    def save(self, *args, **kwargs):
        # Validation stricte avant sauvegarde
        if not isinstance(self.retraite, Retraite):
            raise ValueError("L'instance Retraite doit être fournie")
        if not Retraite.objects.filter(num_secu=self.retraite.num_secu).exists():
            raise ValueError("Le retraité spécifié n'existe pas")
        super().save(*args, **kwargs)
    def clean(self):
        super().clean()
        
        # Validate montant fields based on type_arriere
        if self.type_arriere == 'CMSS' and not self.montant_cmss:
            raise ValidationError({'montant_cmss': 'Ce champ est requis pour les arriérés CMSS'})
            
        if self.type_arriere == 'CMCAS' and not self.montant_cmcas:
            raise ValidationError({'montant_cmcas': 'Ce champ est requis pour les arriérés CMCAS'})
            
        if self.type_arriere == 'LES_DEUX':
            if not self.montant_cmss:
                raise ValidationError({'montant_cmss': 'Ce champ est requis pour les arriérés des deux types'})
            if not self.montant_cmcas:
                raise ValidationError({'montant_cmcas': 'Ce champ est requis pour les arriérés des deux types'})
    class Meta:
        db_table = 'gestion_arrieres'
        ordering = ['-date_arriere']

class Banque(models.Model):
    N_piece = models.CharField(
        verbose_name="Nº pièce",
        max_length=50
    )
    Montant_en_devise_interne = models.DecimalField(
        verbose_name="Montant en devise interne",
        max_digits=10,
        decimal_places=2
    )
    Texte = models.TextField(verbose_name="Description")
    date_piece = models.DateField(verbose_name="Date pièce")
    nom_bd = models.CharField(
        verbose_name="Nom dans la base",
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ['N_piece', 'date_piece', 'Montant_en_devise_interne']
        verbose_name = "Opération bancaire"
        verbose_name_plural = "Opérations bancaires"

    def __str__(self):
        return f"{self.N_piece} - {self.date_piece} - {self.Texte[:50]}"

class Cotisation(models.Model):
    id = models.AutoField(primary_key=True)
    
    # Relation pour récupérer nom_complet
    retraite = models.ForeignKey(
        'Retraite',
        on_delete=models.CASCADE,
        related_name='cotisations',
        verbose_name="Retraité"
    )
    
    # Clé étrangère vers Banque pour date_piece
    operation_bancaire = models.ForeignKey(
        Banque,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cotisations',
        verbose_name="Opération bancaire"
    )
    
    # Champs conformes à la structure
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant"
    )
    
    # Plus besoin de date_de_saisie indépendante, on utilise operation_bancaire.date_piece
    montant_cmss_trimestriel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant CMSS trimestriel"
    )
    
    montant_cmcas_trimestriel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant CMCAS trimestriel"
    )
    
    trimestre_de_remboursement = models.CharField(
        max_length=50,
        verbose_name="Trimestre de remboursement"
    )
    
    detail_ecart = models.TextField(
        blank=True,
        null=True,
        verbose_name="Détail des écarts"
    )
    
    # Nouveaux champs pour l'analyse des montants
    type_paiement = models.CharField(
        max_length=20,
        choices=[
            ('CMSS_EXACT', 'CMSS exact'),
            ('CMCAS_EXACT', 'CMCAS exact'),
            ('CMSS_CMCAS', 'CMSS + CMCAS'),
            ('CMSS_PROCH', 'CMSS proche'),
            ('CMCAS_PROCH', 'CMCAS proche'),
            
            ('INCOMPATIBLE', 'Incompatible'),
        ],
        default='INCOMPATIBLE',
        verbose_name="Type de paiement"
    )
    
    ecart = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Écart"
    )
    
    reste = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Reste"
    )
    
    class Meta:
        verbose_name = "Cotisation"
        verbose_name_plural = "Cotisations"
        ordering = ['-operation_bancaire__date_piece']  # Tri par date_piece de Banque

    @property
    def nom_complet(self):
        return f"{self.retraite.nom} {self.retraite.prenom}"

    @property
    def date_piece(self):
        """Accès direct à date_piece via la relation Banque"""
        return self.operation_bancaire.date_piece if self.operation_bancaire else None

    def clean(self):
        """Validation renforcée"""
        if self.operation_bancaire:
            # Synchronisation automatique des champs liés
            if self.montant != self.operation_bancaire.Montant_en_devise_interne:
                raise ValidationError({
                    'montant': "Le montant doit correspondre à celui de l'opération bancaire"
                })

    def save(self, *args, **kwargs):
        """Synchronisation automatique avant sauvegarde"""
        if self.operation_bancaire:
            self.montant = self.operation_bancaire.Montant_en_devise_interne
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cotisation {self.nom_complet} - {self.trimestre_de_remboursement}"

class NomIncoherent(models.Model):
    TRIMESTRE_CHOICES = [
        ('T1:Janvier', 'Janvier - Mars'),
        ('T2:Avril ', 'Avril - Juin'),
        ('T3:Juillet ', 'Juillet - Septembre'),
        ('T4:Octobre ', 'Octobre - Décembre'),
    ]
    
    nom = models.CharField(max_length=200)
    trimestre = models.CharField(max_length=50, choices=TRIMESTRE_CHOICES)
    date_operation = models.DateField()
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    n_piece = models.CharField(max_length=100, null=True, blank=True)  # Ajouté dans la nouvelle version
    annee = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} - {self.trimestre} {self.annee}"
    
    class Meta:
        verbose_name = "Nom incohérent"
        verbose_name_plural = "Noms incohérents"

class VirementManque(models.Model):
    STATUT_CHOICES = [
        ('en_retard', 'En retard'),
        ('non_recu', 'Non reçu'),
        ('partiel', 'Reçu partiellement'),
    ]

    TRIMESTRE_CHOICES = [
        ('T1:Janvier', 'Janvier - Mars'),
        ('T2:Avril', 'Avril - Juin'),
        ('T3:Juillet', 'Juillet - Septembre'),
        ('T4:Octobre', 'Octobre - Décembre'),
    ]

    TYPE_PAIEMENT_CHOICES = [
        ('CMSS_EXACT', 'CMSS exact'),
        ('CMCAS_EXACT', 'CMCAS exact'),
        ('CMSS_CMCAS', 'CMSS + CMCAS'),
        ('CMSS_PROCH', 'CMSS proche'),
        ('CMCAS_PROCH', 'CMCAS proche'),
        ('INCOMPATIBLE', 'Incompatible'),
    ]

    # 🔗 clé étrangère vers Retraite
    num_secu = models.ForeignKey(
        'Retraite',
        to_field='num_secu',
        on_delete=models.CASCADE,
        related_name='virements_manques',
        verbose_name="Numéro de sécurité sociale"
    )

    trimestre_manquant = models.CharField(max_length=50, choices=TRIMESTRE_CHOICES)
    montant_attendu = models.DecimalField(max_digits=10, decimal_places=2)
    type_paiement = models.CharField(
        max_length=20, 
        choices=TYPE_PAIEMENT_CHOICES,
        default='INCOMPATIBLE',
        verbose_name="Type de paiement"
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_retard')
    annee = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.num_secu} - {self.trimestre_manquant} ({self.annee})"

    class Meta:
        verbose_name = "Virement manqué"
        verbose_name_plural = "Virements manqués"

class GestionnaireProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_ajout = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Ajouter l'utilisateur au groupe "Gestionnaires"
        gestionnaire_group, created = Group.objects.get_or_create(name='Gestionnaires')
        self.user.groups.add(gestionnaire_group)