from django.core.management.base import BaseCommand
from django.conf import settings
import logging

logger = logging.getLogger('tropo_outcall')


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        logfile_path = logger.handlers[0].baseFilename
        print('logfile is : {}'.format(logfile_path))
        with open(logfile_path, 'r') as f:
            for line in f:
                if 'PERF:' in line:
                    print('found')
                    self.stdout.write(line)
