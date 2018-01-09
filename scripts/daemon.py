#!/usr/bin/env python3
import os, sys, time, imp

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
set_env = imp.load_source(
    "set_env",
    os.path.join(ROOT_DIR, "set_env.py")
)
try:
    set_env.activate_venv()
except set_env.SFToolsError as err:
    sys.exit(str(err))

import redis
import json
from faker.utils import get_tropo_appname, get_tropo_voice_script, get_tropo_accountid, get_tropo_appid, generate_callid, get_call_instructions, get_ask_instructions, \
    get_continue_instructions, get_transfer_instructions, get_tropo_webhook, generate_transfer_sessid, generate_transfer_callid, handle_sessionjob
import requests
import os
from datetime import datetime, timedelta
import pytz
import concurrent.futures
from faker.settings import ISO8601, SESSION_JOB_THREAD_LIMIT
from timeit import default_timer as timer
import logging

logger = logging.getLogger('fakerlog')

if __name__ == '__main__':
    """
    now process the sessions info stored in redis
    process means, send session data back, get instructions, follow instructions, call hooks with event data, send back cdrs
    """
    r = redis.StrictRedis(host='localhost', port='6379', db=0)
    while 1:
        if not r.exists('session_jobs'):
            print('session jobs entry not created')
            pass
        session_jobs = json.loads(r.get('session_jobs').decode('utf-8'))  # type: dict
        jobs_count_init = len(session_jobs)
        if not len(session_jobs):
            print('no session jobs')
        print('starting to process {} session jobs'.format(jobs_count_init))
        logger.info('starting to process {} session jobs'.format(jobs_count_init))
        start_time = timer()
        with concurrent.futures.ThreadPoolExecutor(max_workers=SESSION_JOB_THREAD_LIMIT) as executor:
            future_to_sessid = {executor.submit(handle_sessionjob, job): sessid for sessid, job in session_jobs}
            for future in concurrent.futures.as_completed(future_to_sessid):
                sessid = future_to_sessid[future]
                del future_to_sessid[sessid]
        end_time = timer()
        print('sessions processed count: {}, remain: {}. Time taken: {} seconds'.format(jobs_count_init - len(session_jobs), len(session_jobs), end_time - start_time))
        logger.perf('sessions processed count: {}, remain: {}. Time taken: {} seconds'.format(jobs_count_init - len(session_jobs), len(session_jobs), end_time - start_time))
        if len(session_jobs):
            r.set('session_jobs', json.dumps(session_jobs))
        else:
            r.delete('session_jobs')
