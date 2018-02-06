from django.http.request import HttpRequest
import json
import time
import hashlib
from datetime import datetime, timedelta, date
import pytz
from .settings import ISO8601
import requests
import os
import logging

logger = logging.getLogger('tropo_outcall')


def get_client_ip_address(request):
    """
    :param HttpRequest request:
    :return:
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')  # type: str
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_tropo_sessid(ip: str, api_token: str, command: str, number_to_dial: str):
    """
    :return: returns our generated tropo session id
    :rtype: str
    """
    sessid = 'faker-' + hashlib.sha1('{}-{}-{}-{}-{}'.format(ip, api_token, command, number_to_dial, time.time()).encode('utf-8')).hexdigest()
    return sessid


def generate_transfer_sessid(parent_sessid, transfer_to):
    sessid = 'faker-' + hashlib.sha1('{}-{}-{}'.format(parent_sessid, transfer_to, time.time()).encode('utf-8')).hexdigest()
    return sessid


def generate_callid(sessionid, _from, to):
    callid = 'faker-' + hashlib.sha1('{}-{}-{}'.format(sessionid, _from, to).encode('utf-8')).hexdigest()
    return callid


def generate_transfer_callid(parent_callid, transfer_to):
    callid = 'faker-' + hashlib.sha1('{}-{}-{}'.format(parent_callid, transfer_to, time.time()).encode('utf-8')).hexdigest()
    return callid


def get_app_by_voice_apikey(api_key_voice):
    from .settings import TROPO_ACCOUNTS
    for account in TROPO_ACCOUNTS:
        for app in account['applications']:
            if app['api_key_voice'] == api_key_voice:
                return app
    return None


def get_tropo_appname(api_key_voice):
    app = get_app_by_voice_apikey(api_key_voice)
    return app['name']


def get_tropo_appid(api_key_voice):
    app = get_app_by_voice_apikey(api_key_voice)
    if app:
        return app['applicationId']
    else:
        return None


def get_tropo_accountid(api_key_voice):
    from .settings import TROPO_ACCOUNTS
    for account in TROPO_ACCOUNTS:
        for app in account['applications']:
            if app['api_key_voice'] == api_key_voice:
                return account['accountId']
    return None


def get_tropo_voice_script(api_key_voice):
    from .settings import TROPO_ACCOUNTS
    for account in TROPO_ACCOUNTS:
        for app in account['applications']:
            if app['api_key_voice'] == api_key_voice:
                return app['voice_script']
    return None


def get_tropo_webhook(api_key_voice):
    app = get_app_by_voice_apikey(api_key_voice)
    return app['webhook']


def get_call_instructions(tropo_instructions: dict):
    for ins in tropo_instructions['tropo']:
        if 'call' in ins:
            return ins['call']
    return None


def get_ask_instructions(tropo_instructions: dict):
    for ins in tropo_instructions['tropo']:
        if 'ask' in ins:
            return ins['ask']
    return None


def get_transfer_instructions(tropo_instructions: dict):
    for ins in tropo_instructions['tropo']:
        if 'transfer' in ins:
            return ins['transfer']
    return None


def get_continue_instructions(tropo_instructions: dict):
    for ins in tropo_instructions['tropo']:
        if 'on' in ins and ins['on']['event'] == 'continue':
            return ins['on']
    return None


class TropoFakerWebhookException(Exception):
    pass


class CannotProcessTransferException(Exception):
    pass


def to_tropo_datetime(datetime_obj: datetime):
    return datetime_obj.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+0000'


def handle_sessionjob(sessjob: dict):
    """
    here we handle a session in a fixed IVR sequence: YES to ask1, NO to ask2, YES to ask3, then transfer
    :param dict sessjob: a dictionary containing information about voice call session to process.
    must have indexes are: sessid, to, token, campaignid, command
    :return: void
    :rtype: None
    """
    sessionid = sessjob['sessid']
    token = sessjob['token']
    appid = get_tropo_appid(token)
    accountid = get_tropo_accountid(token)
    voice_script = get_tropo_voice_script(token)
    app_name = get_tropo_appname(token)
    session_create_timestamp = datetime.now(pytz.utc)
    call_connect_timestamp = session_create_timestamp + timedelta(seconds=30)

    log_prefix = 'session#{} '.format(sessionid)

    # send session data
    session_data = {
        'session': {
            'id': sessionid,
            'accountId': accountid,
            'applicationId': appid,
            'timestamp': session_create_timestamp.strftime(ISO8601),
            'userType': 'NONE',
            'initialText': None,
            'callId': None,
            'parameters': sessjob['params']
        }
    }
    session_data_json = json.dumps(session_data)
    resp = requests.post(voice_script, data=session_data_json)
    if resp.status_code != 200:
        raise TropoFakerWebhookException(
            log_prefix + 'session data callback failed: http status code: {}, session data: {}, response: {}'.format(resp.status_code, session_data, resp.content))
    instructions_json = resp.content.decode('utf-8')
    instructions = json.loads(instructions_json)
    print(instructions)

    # call and ask1
    call_ins = get_call_instructions(instructions)
    _from = call_ins['from']
    callerid = call_ins['from']
    to = call_ins['to']
    callid = generate_callid(sessionid, _from, to)
    call_label = call_ins['label']
    ask1_ins = get_ask_instructions(instructions)
    ask1_name = ask1_ins['name']
    ask1_continue_ins = get_continue_instructions(instructions)
    ask1_event_callback_url = os.path.dirname(voice_script).rstrip('/') + '/' + ask1_continue_ins['next'].lstrip('/')
    event_result = {
        "result": {
            "sessionId": sessionid,
            "callId": callid,
            "state": "ANSWERED",
            "sessionDuration": 43,
            "sequence": 1,
            "complete": True,
            "error": None,
            "calledid": to,
            "actions": {
                "name": ask1_name,
                "attempts": 1,
                "disposition": "SUCCESS",
                "confidence": 73,
                "interpretation": "yes",
                "utterance": "yes",
                "concept": "yes",
                "value": "yes",
                "xml": "<?xml version='1.0'?><result><interpretation grammar=\"session:0@7b509fb2.vxmlgrammar\" confidence=\"73\"><input mode=\"speech\">yes</input><instance><SWI_literal>yes</SWI_literal><SWI_grammarName>session:0@7b509fb2.vxmlgrammar</SWI_grammarName><SWI_meaning>{SWI_literal:yes}</SWI_meaning></instance></interpretation></result>"
            }
        }
    }
    event_result_json = json.dumps(event_result)
    resp = requests.post(ask1_event_callback_url, data=event_result_json)
    if resp.status_code != 200:
        raise TropoFakerWebhookException(
            log_prefix + 'cannot send back ask1 continue event data, http status code: {}, event data: {}, response: {}'.format(resp.status_code, event_result, resp.content))
    instructions_json = resp.content.decode('utf-8')
    instructions = json.loads(instructions_json)
    # print(instructions)

    # ask2
    ask2_ins = get_ask_instructions(instructions)
    ask2_continue_ins = get_continue_instructions(instructions)
    ask2_name = ask2_ins['name']
    ask2_event_callback_url = os.path.dirname(voice_script).rstrip('/') + '/' + ask2_continue_ins['next'].lstrip('/')
    ask2_session_duration = 55
    ask2_event_result = {
        "result": {
            "sessionId": sessionid,
            "callId": callid,
            "state": "ANSWERED",
            "sessionDuration": ask2_session_duration,
            "sequence": 2,
            "complete": True,
            "error": None,
            "calledid": to,
            "actions": {
                "name": ask2_name,
                "attempts": 1,
                "disposition": "SUCCESS",
                "confidence": 72,
                "interpretation": "no",
                "utterance": "no",
                "concept": "no",
                "value": "no",
                "xml": "<?xml version='1.0'?><result><interpretation grammar=\"session:1@7b509fb2.vxmlgrammar\" confidence=\"72\"><input mode=\"speech\">no</input><instance><SWI_literal>no</SWI_literal><SWI_grammarName>session:1@7b509fb2.vxmlgrammar</SWI_grammarName><SWI_meaning>{SWI_literal:no}</SWI_meaning></instance></interpretation></result>"
            }
        }
    }
    ask2_event_result_json = json.dumps(ask2_event_result)
    resp = requests.post(ask2_event_callback_url, data=ask2_event_result_json)
    if resp.status_code != 200:
        raise TropoFakerWebhookException(
            log_prefix + 'failed ask2 continue event hook. http status code: {}, event data: {}, response: {}'.format(resp.status_code, ask2_event_result, resp.content))
    instructions_json = resp.content.decode('utf-8')
    instructions = json.loads(instructions_json)
    print(instructions)

    # ask3
    ask3_ins = get_ask_instructions(instructions)
    ask3_continue_ins = get_continue_instructions(instructions)
    ask_name = ask3_ins['name']
    ask3_event_callback_url = os.path.dirname(voice_script).rstrip('/') + '/' + ask3_continue_ins['next'].lstrip('/')
    ask3_session_duration = 74
    event_result = {
        "result": {
            "sessionId": sessionid,
            "callId": callid,
            "state": "ANSWERED",
            "sessionDuration": ask3_session_duration,
            "sequence": 3,
            "complete": True,
            "error": None,
            "calledid": to,
            "actions": {
                "name": ask_name,
                "attempts": 1,
                "disposition": "SUCCESS",
                "confidence": 69,
                "interpretation": "yes",
                "utterance": "yes",
                "concept": "yes",
                "value": "yes",
                "xml": "<?xml version='1.0'?><result><interpretation grammar=\"session:2@7b509fb2.vxmlgrammar\" confidence=\"69\"><input mode=\"speech\">yes</input><instance><SWI_literal>yes</SWI_literal><SWI_grammarName>session:2@7b509fb2.vxmlgrammar</SWI_grammarName><SWI_meaning>{SWI_literal:yes}</SWI_meaning></instance></interpretation></result>"
            }
        }
    }
    event_result_json = json.dumps(event_result)
    resp = requests.post(ask3_event_callback_url, data=event_result_json)
    if resp.status_code != 200:
        raise TropoFakerWebhookException(
            log_prefix + 'failed ask3 continue event hook. http status code {}, event data {}, response: {}'.format(resp.status_code, event_result, resp.content))
    instructions_json = resp.content.decode('utf-8')
    instructions = json.loads(instructions_json)
    print(instructions)

    # transfer
    transfer_start_timestamp = session_create_timestamp + timedelta(seconds=ask3_session_duration)
    transfer_session_duration = 118
    transfer_duration = 32
    transfer_connected_duration = 30
    transfer_end_timestamp = session_create_timestamp + timedelta(seconds=transfer_session_duration)
    transfer_ins = get_transfer_instructions(instructions)

    if transfer_ins:
        transfer_continue_ins = get_continue_instructions(instructions)
        transfer_from = transfer_ins['from']
        transfer_to = transfer_ins['to']
        transfer_name = transfer_ins['name']
        transfer_label = transfer_ins['label']
        transfer_continue_callback_url = os.path.dirname(voice_script).rstrip('/') + '/' + transfer_continue_ins['next'].lstrip('/')
        transfer_callid = generate_transfer_callid(callid, transfer_to)
        event_result = {
            "result": {
                "sessionId": sessionid,
                "callId": callid,
                "state": "DISCONNECTED",
                "sessionDuration": transfer_session_duration,
                "sequence": 4,
                "complete": True,
                "error": None,
                "calledid": transfer_to,
                "actions": {
                    "name": transfer_name,
                    "duration": transfer_duration,
                    "connectedDuration": transfer_session_duration,
                    "disposition": "SUCCESS",
                    "timestamp": transfer_end_timestamp.strftime(ISO8601),
                }
            }
        }
        event_result_json = json.dumps(event_result)
        resp = requests.post(transfer_continue_callback_url, data=event_result_json)
        if resp.status_code != 200:
            raise TropoFakerWebhookException(
                log_prefix + 'failed transfer continue event hook, http status code {}, event data {}, response {}'.format(resp.status_code, event_result, resp.content))

        # transfer cdr
        transfer_cdr = {
            "data": {
                "callId": transfer_callid,
                "applicationType": "tropo-web",
                "messageCount": 0,
                "parentCallId": callid,
                "parentSessionId": sessionid,
                "sessionId": sessionid,
                "label": transfer_label,
                "network": "PSTN",
                "initiationTime": to_tropo_datetime(transfer_start_timestamp),
                "duration": 33258,
                "accountId": get_tropo_accountid(token),
                "startUrl": voice_script,
                "from": transfer_from,
                "startTime": to_tropo_datetime(transfer_start_timestamp),
                "to": "tel:{}".format(transfer_to),
                "endTime": to_tropo_datetime(transfer_end_timestamp),
                "applicationId": get_tropo_appid(token),
                "eventTimeStamp": transfer_start_timestamp.timestamp(),
                "applicationName": get_tropo_appname(token),
                "direction": "out",
                "status": "Success"
            },
            "resource": "call",
            "name": "Tropo Webform Webhook",
            "id": "c284f5ba-a1c5-4b01-bf86-7f85f700879b",
            "event": "cdrCreated"
        }
        transfer_cdr_json = json.dumps(transfer_cdr)
        resp = requests.post(get_tropo_webhook(token), data=transfer_cdr_json)
        if resp.status_code != 200:
            # print('failed cdr hook, transfer cdr, http status code: {}'.format(resp.status_code))
            raise TropoFakerWebhookException('failed cdr hook, transfer cdr, http status code: {}, cdr: {}, response: {}'.format(resp.status_code, transfer_cdr, resp.content))
        # transfer bill cdr
        transfer_bill_cdr = {
            "data": {
                "reason": None,
                "applicationType": "tropo-web",
                "messageCount": 0,
                "network": "PSTN",
                "initiationTime": to_tropo_datetime(transfer_start_timestamp),
                "duration": transfer_duration,
                "startUrl": voice_script,
                "from": transfer_from,
                "startTime": to_tropo_datetime(transfer_start_timestamp),
                "applicationName": get_tropo_appname(token),
                "direction": "out",
                "callId": transfer_callid,
                "roundedDuration": 60,
                "cost": 0,
                "parentCallId": callid,
                "created": to_tropo_datetime(transfer_start_timestamp),
                "parentSessionId": sessionid,
                "sessionId": sessionid,
                "label": transfer_label,
                "ratingVersion": 1,
                "accountId": get_tropo_accountid(token),
                "to": transfer_to,
                "endTime": to_tropo_datetime(transfer_end_timestamp),
                "previousCost": 0,
                "applicationId": get_tropo_appid(token),
                "status": "Success"
            },
            "resource": "call",
            "name": "Tropo Webform Webhook",
            "id": "10faee98-a4ee-45a0-939e-cbc90a58f5c2",
            "event": "cdrRated"
        }
        transfer_bill_cdr_json = json.dumps(transfer_bill_cdr)
        resp = requests.post(get_tropo_webhook(token), data=transfer_bill_cdr_json)
        if resp.status_code != 200:
            raise TropoFakerWebhookException(
                log_prefix + 'cdr hook failed, transfer billing cdr, http status code: {}, cdr: {}, response: {}'.format(resp.status_code, transfer_bill_cdr, resp.content))
    # now send the cdrs
    # call cdr
    call_cdr = {
        "data": {
            "callId": callid,
            "applicationType": "tropo-web",
            "messageCount": 0,
            "parentCallId": "none",
            "parentSessionId": "none",
            "sessionId": sessionid,
            "label": call_label,
            "network": "PSTN",
            "initiationTime": to_tropo_datetime(session_create_timestamp),
            "duration": 103002,
            "accountId": get_tropo_accountid(token),
            "startUrl": voice_script,
            "from": callerid,
            "startTime": to_tropo_datetime(session_create_timestamp),
            "to": "tel:{}".format(to),
            "endTime": to_tropo_datetime(transfer_start_timestamp),
            "applicationId": get_tropo_appid(token),
            "eventTimeStamp": session_create_timestamp.timestamp(),
            "applicationName": get_tropo_appname(token),
            "direction": "out",
            "status": "Success"
        },
        "resource": "call",
        "name": "Tropo Webform Webhook",
        "id": "29bdb799-8efb-40e1-9e28-320711c5e5b6",
        "event": "cdrCreated"
    }
    call_cdr_json = json.dumps(call_cdr)
    resp = requests.post(get_tropo_webhook(token), data=call_cdr_json)
    if resp.status_code != 200:
        # print(log_prefix + 'failed cdr hook. call cdr. http status code {}'.format(resp.status_code))
        raise TropoFakerWebhookException(log_prefix + 'failed cdr hook. call cdr. http status code {}, cdr {}, response {}'.format(resp.status_code, call_cdr, resp.content))

    # call bill cdr
    call_bill_cdr = {
        "data": {
            "reason": None,
            "applicationType": "tropo-web",
            "messageCount": 0,
            "network": "PSTN",
            "initiationTime": to_tropo_datetime(session_create_timestamp),
            "duration": 104,
            "startUrl": voice_script,
            "from": callerid,
            "startTime": to_tropo_datetime(session_create_timestamp),
            "applicationName": get_tropo_appname(token),
            "direction": "out",
            "callId": callid,
            "roundedDuration": 120,
            "cost": 0,
            "parentCallId": "none",
            "created": to_tropo_datetime(datetime.now(pytz.UTC)),
            "parentSessionId": "none",
            "sessionId": sessionid,
            "label": call_label,
            "ratingVersion": 1,
            "accountId": get_tropo_accountid(token),
            "to": to,
            "endTime": to_tropo_datetime(transfer_start_timestamp),
            "previousCost": 0,
            "applicationId": get_tropo_appid(token),
            "status": "Success"
        },
        "resource": "call",
        "name": "Tropo Webform Webhook",
        "id": "60cd18c3-a550-4416-b56c-4aac23f75d91",
        "event": "cdrRated"
    }
    call_bill_cdr_json = json.dumps(call_bill_cdr)
    resp = requests.post(get_tropo_webhook(token), data=call_bill_cdr_json)
    if resp.status_code != 200:
        raise TropoFakerWebhookException('cdr hook failed. call bill cdr. http status code: {}, cdr: {}, response: {}'.format(resp.status_code, call_bill_cdr, resp.content))
    return True
