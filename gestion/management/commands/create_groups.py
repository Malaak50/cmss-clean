# management/commands/create_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Crée les groupes de permissions par défaut'

    def handle(self, *args, **options):
        # Créer le groupe Gestionnaires
        groupe_gestionnaires, created = Group.objects.get_or_create(name='Gestionnaires')
        
        if created:
            self.stdout.write(self.style.SUCCESS('Groupe Gestionnaires créé avec succès'))
        else:
            self.stdout.write(self.style.WARNING('Groupe Gestionnaires existe déjà'))