from django.core.management import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    help = 'Добавление тегов'

    def handle(self, *args, **kwargs):
        data = [
            {'name': 'Ужин', 'slug': 'dinner', 'color': '#0000ff'},
            {'name': 'Обед', 'slug': 'lunch', 'color': '#cd7f32'},
            {'name': 'Завтрак', 'slug': 'breakfast', 'color': '#61db5c'}
        ]
        Tag.objects.bulk_create(Tag(**tag) for tag in data)
        self.stdout.write(self.style.SUCCESS('Все тэги загружены!'))
