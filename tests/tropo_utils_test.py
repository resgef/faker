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

from tropo.utils import get_app_by_voice_apikey, get_tropo_appname, get_tropo_appid, get_tropo_accountid, get_tropo_voice_script, get_tropo_webhook

token = '564e44774257594f6f6359497a6e4767656153577769414c7051487a4d6342556d4f504d7447517451536275'
data = get_tropo_webhook(token)
print(data)
