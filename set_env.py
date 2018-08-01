# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.join(PROJECT_ROOT, 'packages')


class SFToolsError(Exception):
    pass


def activate_venv():
    try:
        VENV = os.environ['CM_VENV']
    except KeyError:
        VENV = os.path.join(PROJECT_ROOT, 'env')

    if os.path.isfile(os.path.join(VENV, 'bin/activate_this.py')):
        activate_this = os.path.join(VENV, 'bin/activate_this.py')
        exec(open(activate_this).read(), dict(__file__=activate_this))

    try:
        import django
    except ImportError:
        raise SFToolsError("Failed to import django")
    else:
        sys.path.extend([PROJECT_ROOT, PACKAGE_DIR])
        os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings"
        django.setup()
