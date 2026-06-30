"""
Commande de gestion pour charger les données initiales des templates.
Usage: python manage.py load_template_data
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from pathlib import Path


class Command(BaseCommand):
    help = "Charge les données initiales des templates CV"

    def handle(self, *args, **options):
        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "templates_data.json"

        try:
            self.stdout.write(f"Chargement des données depuis {fixture_path}...")
            call_command("loaddata", str(fixture_path), verbosity=2)
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Données des templates chargées avec succès!"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Erreur: {e}")
            )
