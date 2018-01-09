from .utils import generate_tropo_sessid, get_client_ip_address
from django.http import HttpResponse
import json
import redis
import logging
import time
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.http import HttpResponseForbidden
import requests
from .forms import SessionCreateForm
from django.conf import settings

logger = logging.getLogger('tropo_outcall')


# Create your views here.
@require_GET
@csrf_exempt
def tropo_outcall_session_create(request):
    form = SessionCreateForm(request.GET)

    if not form.is_valid():
        return HttpResponseForbidden(form.errors.as_json())

    params = form.cleaned_data.__dict__
    token = params['token']
    sessid = generate_tropo_sessid(get_client_ip_address(request), token, params['command'], params['numberToDial'])
    print('faker: incoming session request, with params: {}, generated sessionid: {}'.format(params, sessid))
    logger.info('faker: incoming session request, with params: {}, generated sessionid: {}'.format(params, sessid))
    # now save the session info in redis to be processed later
    r = redis.StrictRedis(host='localhost', port='6379', db=settings.REDIS_DB_OUTCALL_SESSION)
    if r.exists(settings.REDIS_KEY_OUTCALL_SESSION):
        sessions_to_process = r.get(settings.REDIS_KEY_OUTCALL_SESSION)
        sessions_to_process = json.loads(sessions_to_process.decode('utf-8'))
    else:
        sessions_to_process = {}
    sessions_to_process[sessid] = {
        'sessid': sessid,
        'to': form.cleaned_data['numberToDial'],
        'token': form.cleaned_data['token'],
        'campaignid': form.cleaned_data['campaignid'],
        'command': form.cleaned_data['command'],
        'params': params
    }
    r.set('session_jobs', json.dumps(sessions_to_process))

    xml = '<session><success>true</success><token>{}</token><id>{}</id></session>'.format(token, sessid)

    # now spend some seconds
    time.sleep(1.7)
    # requests.get('https://api.tropo.com/1.0/sessions')

    return HttpResponse(xml, content_type='text/xml')
