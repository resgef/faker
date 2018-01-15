from django.core.management.base import BaseCommand
import redis
import time
import json
from django.conf import settings


class Command(BaseCommand):
    help = 'view current outcall sessions waiting to be processed'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # monkeypatching to prevent console flooding with stale messages
        statuscode = 0
        while 1:
            r = redis.StrictRedis(host='localhost', port='6379', db=settings.REDIS_DB_OUTCALL_SESSION)
            if not r.exists(settings.REDIS_KEY_OUTCALL_SESSION):
                if statuscode != 1:
                    statuscode = 1
                    self.stdout.write(self.style.ERROR('session jobs entry key `{}` not created'.format(settings.REDIS_KEY_OUTCALL_SESSION)))
                    continue

            red_val = r.get(settings.REDIS_KEY_OUTCALL_SESSION)
            session_jobs = json.loads(red_val.decode('utf-8'))  # type: dict
            jobs_count_init = len(session_jobs)
            if statuscode != 3 + jobs_count_init:
                statuscode = 3 + jobs_count_init
                self.stdout.write('{} session jobs'.format(jobs_count_init))
                continue

            # statuscode = 0
            time.sleep(1)
