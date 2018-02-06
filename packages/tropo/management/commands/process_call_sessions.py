import redis
import json
from tropo.utils import handle_sessionjob
import concurrent.futures
from tropo.settings import SESSION_JOB_THREAD_LIMIT
from timeit import default_timer as timer
import logging
from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings
from tropo.utils import CannotProcessTransferException, TropoFakerWebhookException
from bs4 import BeautifulSoup
import os, sys

logger = logging.getLogger('tropo_outcall')


def dump(filename, content):
    filepath = os.path.join(settings.BASE_DIR, 'dump', filename)
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


class Command(BaseCommand):
    help = 'to process outbound (fake) call requests(sessions already created and saved in redis)'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--one', dest='one', type=bool, help='process only one session')

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
            else:
                self.stdout.write('{} session jobs'.format(len(session_jobs)))
            logger.info('starting to process {} session jobs'.format(jobs_count_init))
            start_time = timer()

            job_chunks = {}
            counter = 0
            for sessid, job in session_jobs.items():
                job_chunks[sessid] = job
                counter += 1
                if counter >= SESSION_JOB_THREAD_LIMIT:
                    break
                if options['one']:
                    break

            sessionds_done = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=SESSION_JOB_THREAD_LIMIT) as executor:
                future_to_sessid = {executor.submit(handle_sessionjob, job): sessid for sessid, job in job_chunks.items()}
                for future in concurrent.futures.as_completed(future_to_sessid):
                    sessid = future_to_sessid[future]
                    try:
                        if future.result():
                            logger.debug('session#{} processing complete'.format(sessid))
                            sessionds_done.append(sessid)

                    except CannotProcessTransferException as e:
                        exception_text = str(e)
                        if bool(BeautifulSoup(exception_text, 'html.parser').find()):
                            logger.error('exception: {}'.format(exception_text[:200]))
                            dumpfile = dump(sessid + '.html', exception_text)
                            self.stdout.write('exception text dumped into: {}'.format(dumpfile))
                        else:
                            logger.error(str(e))
                    except TropoFakerWebhookException as e:
                        exception_text = str(e)
                        if bool(BeautifulSoup(exception_text, 'html.parser').find()):
                            logger.error('exception: {}'.format(exception_text[:200]))
                            dumpfile = dump(sessid + '.html', exception_text)
                            self.stdout.write('exception text dumped into: {}'.format(dumpfile))
                        else:
                            logger.error(str(e))

                    del session_jobs[sessid]
                    self.stdout.write('session id: {} removed from jobs to process'.format(sessid))
                    if len(session_jobs):
                        r.set(settings.REDIS_KEY_OUTCALL_SESSION, json.dumps(session_jobs))
                    else:
                        r.delete(settings.REDIS_KEY_OUTCALL_SESSION)
            end_time = timer()
            logger.perf('sessions processed: {}, jobs chunk size was: {} time taken: {} seconds'.format(len(sessionds_done), len(job_chunks), end_time - start_time))

            if options['one']:
                break
