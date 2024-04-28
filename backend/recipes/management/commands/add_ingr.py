import csv
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Add ingredients'

    def handle(self, *args, **options):
        count = 0
        path = os.path.join(settings.BASE_DIR, 'data/ingredients.csv')
        try:
            with open(path, 'r', encoding='utf-8') as file:
                file_reader = csv.reader(file)
                for line_num, row in enumerate(file_reader):
                    try:
                        Ingredient.objects.create(
                            name=row[0], measurement_unit=row[1])
                        count += 1
                    except IntegrityError:
                        self.stdout.write(
                            f'Ingredient {", ".join(row)} - already exists'
                        )
                    except IndexError:
                        logging.error(
                            f'Not correct ingredient. Line:{line_num + 1}'
                        )
                        return
        except FileNotFoundError as ex:
            self.stdout.write(str(ex))
        self.stdout.write(f'Added {count} ingredients')
