import multiprocessing

bind = "127.0.0.1:8001"
workers = multiprocessing.cpu_count() * 2 + 1

worker_class = 'gthread'  # check http://docs.gunicorn.org/en/stable/design.html

accesslog = '/var/log/faker/gunicorn/access.log'
access_log_format = 'remote_address:%(h)s %(l)s user_name:%(u)s date:%(t)s status_line:"%(r)s" path:%(U)s qstring:%(q)s status:%(s)s resp_len:%(b)s response_header:%({Header}o)s referrer:"%(f)s" uagent:"%(a)s"'
errorlog = '/var/log/faker/gunicorn/error.log'
