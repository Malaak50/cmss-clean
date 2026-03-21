from django.contrib import admin
from .models import Retraite,Arriere,TM
#admin.site.register(Retraite)
#admin.site.register(TM)
#admin.site.register(Arriere)
@admin.register(Retraite)
class GestionRetraiteAdmin(admin.ModelAdmin):
  list_display = ('num_secu', 'nom', 'prenom', 'nom_complet', 'pension_cnss')
  search_fields = ('num_secu', 'nom', 'prenom','id_num_personne')
  list_filter = ('mois_rattachement',)
@admin.register(TM)
class TMAdmin(admin.ModelAdmin):
    list_display = ('id', 'retraite', 'date_tm', 'montant_total', 'statut')  # Supprimez num_secu
    list_filter = ('statut', 'date_tm')
    search_fields = ('retraite__num_secu', 'retraite__nom', 'retraite__prenom')
    raw_id_fields = ('retraite',)
    date_hierarchy = 'date_tm'
@admin.register(Arriere)
class ArriereAdmin(admin.ModelAdmin):
    list_display = ('id', 'date_arriere', 'type_arriere', 'nombre_de_mois', 'display_montant_total', 'statut', 'display_retraite')
    list_filter = ('statut', 'type_arriere', 'date_arriere')
    search_fields = ('retraite__num_secu', 'retraite__nom', 'retraite__prenom')
    raw_id_fields = ('retraite',)
    readonly_fields = ('created_at', 'updated_at')

    def display_montant_total(self, obj):
        """
        Affiche le montant total selon le type d'arriéré
        """
        if obj.type_arriere == 'CMSS':
            return f"{obj.montant_cmss or 0:.2f}" if obj.montant_cmss is not None else "-"
        elif obj.type_arriere == 'CMCAS':
            return f"{obj.montant_cmcas or 0:.2f}" if obj.montant_cmcas is not None else "-"
        elif obj.type_arriere == 'LES_DEUX':
            total = (obj.montant_cmss or 0) + (obj.montant_cmcas or 0)
            return f"{total:.2f}"
        return "-"
    display_montant_total.short_description = "Montant Total"

    def display_retraite(self, obj):
        """
        Affiche le numéro de sécurité sociale du retraité
        """
        return obj.retraite.num_secu if obj.retraite else "-"
    display_retraite.short_description = "Num. Secu Retraité"