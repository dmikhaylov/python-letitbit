# -*- coding: utf-8 -*
import json
import httplib, urllib
from ftplib import FTP
import os

def empty(inList):
    if isinstance(inList, list):    # Is a list
        return all( map(empty, inList) )
    return False # Not a list

class Letitbit(object):
    "Class for access to Letitbit.net file sharing services"
    def __init__(self, private_key):
        self.private_key = private_key
        
        self.headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        self.conn = httplib.HTTPConnection("api.letitbit.net")
        
        self.data = [self.private_key]

    def add_method(self, controller, method, parameters=None):
        meth = []
        meth.append("{}/{}".format(controller, method))
        if parameters:
            meth.append(parameters)
        self.data.append(meth)

    def run(self):
        response = None
        try:
            print(json.dumps(self.data))
            params = urllib.urlencode({'r': json.dumps(self.data)})
            self.conn.request("POST", "", params, self.headers)
            response = self.conn.getresponse()
            response = response.read()
            response = json.loads(response)
        except:
            print('Exception occured while tried to send request')
        finally:
            # clean up response
            self.data = [self.private_key]
        return response

    def check_key_info(self):
        self.add_method('key', 'info')
        result = self.run()
        if result['status'] != 'OK':
                raise Exception("Error occured while trying to access API.\nConnection status: %s" % result['status'])
        key_data = result['data'][0]
        self.max_requests = key_data['max']
        self.current_requests = key_data['cur']

class Ftp(Letitbit):
        "Class enables Ftp uploading functionalities"
        def __init__(self, private_key):
            Letitbit.__init__(self, private_key)
            self._get_auth_data()
            self._get_servers_list()

        def _get_auth_data(self):
            self.add_method('ftp', 'auth_data')
            result = self.run()
            if result['status'] != 'OK':
                raise Exception("Error occured while trying to access API.\nConnection status: %s" % result['status'])
            auth_data = result['data'][0]

            self.login = auth_data['login']
            self.password = auth_data['pass']

        def _get_servers_list(self):
            self.add_method('ftp', 'listing')
            result = self.run()
            if result['status'] !='OK':
                raise Exception("Error occured while trying to access API:\n%s" % result['status'])
            ftp_servers = result['data'][0]
            ftp_servers = sorted(ftp_servers, key=lambda server: server[1])
            servers = []
            for server in ftp_servers:
                servers.append(server[0])
            self.servers = servers

        def upload_file(self, file_full_path):
            # get random server from servers list
            import random
            ftp_server = random.choice(self.servers)
            filename = os.path.basename(file_full_path)
            file = open(file_full_path, "rb")
            ftp = FTP(ftp_server)
            ftp.login(self.login, self.password)
            ftp.storbinary('STOR ' + filename, file)
            ftp.quit()
            file.close()
            args = {
                'server': ftp_server,
                'tmpname': filename,
                'realname': filename
            }
            self.add_method('ftp', 'process', args)
            response = self.run()
            print response
            if response['status'] != 'OK' or empty(response['data']):
                raise Exception('File is not processed, maybe the server-side problem, try again')
            return (response['data'][0][0]['link'], response['data'][0][0]['uid'])

