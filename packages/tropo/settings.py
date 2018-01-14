TROPO_ACCOUNTS = [
    {
        'accountId': '5073147',
        'applications': [
            {
                'applicationId': '5173947',
                'api_key_voice': '5569645149776d4f6150585474435273414c4a66717a7666645a7166664e695046425157635a6e6f52534352',
                'voice_script': 'http://localhost:8000/index.json',
                'text_script': '',
                'webhook': 'http://localhost:8000/cdrhook',
                'name': 'asrivr ngrok',
            },
            # {
            #     'applicationId': '5174138',
            #     'api_key_voice': '564e44774257594f6f6359497a6e4767656153577769414c7051487a4d6342556d4f504d7447517451536275',
            #     'voice_script': 'http://asrivr.dev.concitus.com/index.json',
            #     'text_script': '',
            #     'webhook': 'http://asrivr.dev.concitus.com/cdrhook',
            #     'name': 'asrivr dokku'
            # }
        ]
    },
]

ISO8601 = '%Y-%m-%dT%H:%M:%S.%fZ'  # which is tropo timestamp format
SESSION_JOB_THREAD_LIMIT = 200
