# -*- coding: utf-8 -*
import json
import httplib, urllib
from ftplib import FTP
import os


class Error(Exception):
    def __init__(self, value, msg=None):
        Exception.__init__(self)
        self.value = value
        self.msg = msg

    def __str__(self):
        return self.msg


class UnknownProtocolException(Error):
    def __init__(self, value, msg=None):
        Error.__init__(self, value, msg)
        self.msg = msg if msg else "Unknown Protocol: \"{}\"".format(self.value)


class NotSuccessfulResponseException(Error):
    def __init__(self, value, msg=None):
        Error.__init__(self, value, msg)
        self.msg = msg if msg else "Not Successful Response came from server: \"{}\"".format(self.value)


def empty(inList):
    if isinstance(inList, list):    # Is a list
        return all(map(empty, inList))
    return False  # Not a list


class Letitbit(object):
    """Class to access to Letitbit.net file sharing services"""

    protocols = ('ftp', 'http',)

    def __init__(self, key, protocol='ftp'):
        self.key = key
        self.protocol = protocol
        
        self.headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        self.conn = httplib.HTTPConnection("api.letitbit.net")
        self.data = [self.key]

        self.servers = dict()
        for p in Letitbit.protocols:
            self.servers[p] = list()

    def add_method(self, controller, method, parameters=None):
        meth = list()
        meth.append("{}/{}".format(controller, method))
        if parameters:
            meth.append(parameters)
        self.data.append(meth)

    def run(self):
        params = urllib.urlencode({'r': json.dumps(self.data)})
        response = None
        try:
            self.conn.request("POST", "", params, self.headers)
            response = self.conn.getresponse()
            response = response.read()
            response = json.loads(response)
        finally:
            self.data = [self.key]
        return response

    def check_key_info(self):
        self.add_method('key', 'info')
        result = self.run()
        if result['status'] != 'OK':
            raise NotSuccessfulResponseException(result['status'])
        key_data = result['data'][0]
        self.max_requests = key_data['max']
        self.current_requests = key_data['cur']
        self.total_requests = key_data['total_requests']
        self.total_points = key_data['total_points']

    def get_servers_list(self, protocol):
        if protocol not in Letitbit.protocols:
            raise UnknownProtocolException(protocol)
        self.add_method(protocol, 'listing')
        result = self.run()
        if result['status'] !='OK':
            raise UnknownProtocolException(result['status'])
        servers = result['data'][0]
        servers = sorted(servers, key=lambda server: server[1])
        s = []
        for server in servers:
            s.append(server[0])
        self.servers[protocol] = servers

    def ftp_upload_file(self, file_full_path, server):
        filename = os.path.basename(file_full_path)
        file = open(file_full_path, "rb")
        ftp = FTP(server)
        ftp.login(self.login, self.password)
        ftp.storbinary('STOR ' + filename, file)
        ftp.quit()
        file.close()

    def process(self, protocol, server, filename):
        args = {
            'server': server,
            'tmpname': filename,
            'realname': filename
        }
        self.add_method(protocol, 'process', args)
        response = self.run()
        print response
        return response

    def upload_file(self, file_full_path, protocol):
        """ Method allows uploading file to one of available servers depending on protocol you chose """
        if protocol not in Letitbit.protocols:
                raise UnknownProtocolException(protocol)
        # get first server from list sorted by workload
        server = self.servers[protocol][0][0]

        if protocol == 'ftp':
            self.ftp_upload_file(file_full_path, server)
        else:
            pass

        filename = os.path.basename(file_full_path)
        response = self.process(protocol, server, filename)
        if response['status'] != 'OK' or empty(response['data']):
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0][0]['link'], response['data'][0][0]['uid']

    def _get_auth_data(self, protocol):
        if protocol not in Letitbit.protocols:
            raise UnknownProtocolException(protocol)
        self.add_method(protocol, 'auth_data')
        result = self.run()
        if result['status'] != 'OK':
            raise NotSuccessfulResponseException(result['status'])
        auth_data = result['data'][0]

        self.login = auth_data['login']
        self.password = auth_data['pass']

    def list_controllers(self, output=False):
        self.add_method('list', 'controllers')
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        if output:
            for c in response['data'][0]:
                print(c)
        return response['data'][0]

    def list_methods(self, controller=None, output=False):
        controllers = [controller]
        methods = dict()
        if not controller:
            controllers = self.list_controllers()
        for c in controllers:
            args = {'controller': c}
            self.add_method('list', 'methods', args)
            response = self.run()
            if response['status'] != 'OK':
                raise NotSuccessfulResponseException(response['status'])
            if output:
                if len(controllers) > 1:
                    print(c)
                for k, v in response['data'][0].items():
                    print ('\t' + k)
                    print("\t\tDescription: {}\n\t\tCost: {}\n\t\tCall: {}\n".format(
                        v.get('descr', str(None)).encode('utf-8'),
                        v.get('cost', 0),
                        v.get('call', "").encode('utf-8')).replace('\\', '')
                    )
                print
            methods[c] = response['data'][0]
        return methods