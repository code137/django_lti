import os

CONSUMER_KEY_PEM_FILE = os.path.abspath('consumer_key.pem')

with open(CONSUMER_KEY_PEM_FILE, 'w') as wfile:
    wfile.write(os.environ.get('CONSUMER_KEY_CERT', ''))

CONSUMERS = {
            "__consumer_key__": {
                "secret": os.environ.get("CONSUMER_KEY_SECRET", "__lti_secret__"),
                "cert": CONSUMER_KEY_PEM_FILE
            }
        }