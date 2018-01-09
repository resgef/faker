import redis
import json
from tropo.utils import handle_sessionjob
import concurrent.futures
from tropo.settings import SESSION_JOB_THREAD_LIMIT
from timeit import default_timer as timer
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
import pprint

logger = logging.getLogger('tropo_outcall')


class Command(BaseCommand):
    help = 'to process outbound (fake) call requests(sessions already created and saved in redis)'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """
        now process the sessions info stored in redis
        process means, send session data back, get instructions, follow instructions, call hooks with event data, send back cdrs
        """
        logger.info('thread limit: {}'.format(SESSION_JOB_THREAD_LIMIT))
        while 1:
            r = redis.StrictRedis(host='localhost', port='6379', db=settings.REDIS_DB_OUTCALL_SESSION)
            if not r.exists(settings.REDIS_KEY_OUTCALL_SESSION):
                self.stdout.write(self.style.ERROR('session jobs entry not created'))
                continue
            session_jobs = json.loads(r.get(settings.REDIS_KEY_OUTCALL_SESSION).decode('utf-8'))  # type: dict
            jobs_count_init = len(session_jobs)
            if not len(session_jobs):
                self.stdout.write('no session jobs')
                continue
            logger.info('starting to process {} session jobs'.format(jobs_count_init))
            start_time = timer()

            sessionds_done = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=SESSION_JOB_THREAD_LIMIT) as executor:
                future_to_sessid = {executor.submit(handle_sessionjob, job): sessid for sessid, job in session_jobs.items()}
                for future in concurrent.futures.as_completed(future_to_sessid):
                    sessid = future_to_sessid[future]
                    if future.exception():
                        logger.error(str(future.exception()))
                    if future.result():
                        logger.debug('session#{} processing complete'.format(sessid))
                        sessionds_done.append(sessid)
                        # del session_jobs[sid]
            end_time = timer()
            logger.perf('sessions processed: {}, time taken: {} seconds'.format(len(sessionds_done), end_time - start_time))

            if len(session_jobs):
                r.set(settings.REDIS_KEY_OUTCALL_SESSION, json.dumps(session_jobs))
            else:
                # r.delete(settings.REDIS_KEY_OUTCALL_SESSION)
                pass
