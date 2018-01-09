from django.core.management.base import BaseCommand, CommandError
import tempfile


class Command(BaseCommand):
    help = 'generate fake numbers and save to a temporary csv file'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int)

    def handle(self, *args, **options):
        count = options['count']
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w')
        for num in range(0, count, 1):
            number = str(num).rjust(10, '0')
            tfile.write(number + '\n')
        tfile.close()
        self.stdout.write(self.style.SUCCESS('numbers save to %s' % tfile.name))
