import cherrypy
import json
import socket
import time

class RootServer(object):
    @cherrypy.expose
    def index(self, **keywords):
        with open('index.html') as index:
            return index.readlines()

    @cherrypy.expose
    def post(self, **kwargs):
        for key, value in kwargs.items():
            print('{key}:{value}'.format(key=key, value=value))

        ua = cherrypy.request.headers.get('User-Agent', '').strip()
        kwargs['useragent'] = ua
        with open('out.json', 'a') as out:
            out.write(json.dumps(kwargs) + '\n')
        return ''


if __name__ == '__main__':
    cherrypy.tree.mount(RootServer())

    cherrypy.server.unsubscribe()

    server1 = cherrypy._cpserver.Server()
    server1.socket_port = 4443
    server1._socket_host = '0.0.0.0'
    server1.thread_pool = 30
    server1.ssl_module = 'builtin'
    server1.ssl_certificate = 'location-test-new-certificate.pem'
    server1.ssl_private_key = 'location-test-private-key.pem'
    server1.subscribe()

    server2 = cherrypy._cpserver.Server()
    server2.socket_port = 8080
    server2._socket_host = '0.0.0.0'
    server2.thread_pool = 30
    server2.subscribe()

    cherrypy.engine.start()
    cherrypy.engine.block()
