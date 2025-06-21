import sys

from gevent import pywsgi

from main import app

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 5000
    try:
        port = int(port)
    except Exception as e:
        sys.exit('Invalid port number: %s' % port)
    print('Starting server on port %s...' % port)
    server = pywsgi.WSGIServer(('0.0.0.0', port), app)
    server.serve_forever()