# -*- coding: utf-8 -*
"""
Simple module for accessing letitbit.net filesharing services.
Unfortunately not all methods from api implemented for now because they are not described good enough
Just use Letitbit class to upload your files and do other stuff.
"""
import json
import httplib, urllib, urllib2, cookielib
from ftplib import FTP
import os


class Error(Exception):
    """Base exception class for all other exceptions in module"""
    def __init__(self, value, msg=None):
        Exception.__init__(self)
        self.value = value
        self.msg = msg

    def __str__(self):
        return self.msg


class UnknownProtocolException(Error):
    """When not right protocol used in arguments list"""
    def __init__(self, value, msg=None):
        Error.__init__(self, value, msg)
        self.msg = msg if msg else "Unknown Protocol: \"{}\"".format(self.value)


class NotSuccessfulResponseException(Error):
    """When response status from server is not 'OK'"""
    def __init__(self, value, msg=None):
        Error.__init__(self, value, msg)
        self.msg = msg if msg else "Not Successful Response came from server: \"{}\"".format(self.value)


def empty(inList):
    if isinstance(inList, list):    # Is a list
        return all(map(empty, inList))
    return False  # Not a list


class Letitbit(object):
    """Class to access to Letitbit.net file sharing services"""

    protocols = ('ftp', 'http',)  # list of protocols which can be used for files uploading

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
        """Creates dictionary that will be converted to JSON representation"""
        meth = list()
        meth.append("{}/{}".format(controller, method))
        if parameters:
            meth.append(parameters)
        self.data.append(meth)

    def run(self):
        """Creates JSON to request data from server"""
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
        """Checks statistics for current user's key"""
        self.add_method('key', 'info')
        result = self.run()
        if result['status'] != 'OK':
            raise NotSuccessfulResponseException(result['status'])
        key_data = result['data'][0]
        self.max_requests = key_data['max']
        self.current_requests = key_data['cur']
        self.total_requests = key_data['total_requests']
        self.total_points = key_data['total_points']

    def get_key_auth(self, login, passwd, project='letitbit.net'):
        """Returns key that is needed to access several projects like sms4file and others"""
        import hashlib
        passwd_hash = hashlib.md5(hashlib.md5(passwd).hexdigest()).hexdigest()
        args = {
            'login': login,
            'pass': passwd_hash,
            'project': project
        }
        self.add_method('key', 'auth', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_servers_list(self, protocol):
        """Gets servers list for chosen protocol and saves them in object's servers attribute"""
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
        """Returns links list for uploaded file"""
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
        """Gets authentication information for ftp and saves it in object's attributes login and password"""
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
        """Returns list of available controllers"""
        self.add_method('list', 'controllers')
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        if output:
            for c in response['data'][0]:
                print(c)
        return response['data'][0]

    def list_methods(self, controller=None, output=False):
        """Returns methods list in chosen controller. If there is nothing in controller attribute then it returns info about all controllers. If output is True - prints out all info."""
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

    def set_ftp_flag_auto(self, value=True):
        args = {
            'flag': int(value)
        }
        self.add_method('ftp', 'flag_auto', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])

    def get_direct_links(self, link, passwd=None):
        """Returns direct links to file"""
        args = {
            'link': link,
            'pass': "" if not passwd else passwd
        }
        self.add_method('download', 'direct_links', args)
        response = self.run()
        return response['data'][0]

    def check_link(self, link):
        """Returns True if file is on one or more servers and False otherwise"""
        args = {
            'link': link
        }
        self.add_method('download', 'check_link', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return bool(response['data'][0])

    def get_file_info(self, link):
        """Returns dictionary which contains some info about file like file size, uid and etc."""
        args = {
            'link': link
        }
        self.add_method('download', 'info', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_filemanager_listing(self, limit=50, page=1, folder=0):
        """Returns list of dictionaries containing various info about all files which you chose with function parameters"""
        args = {
            'limit': limit,
            'page': page,
            'folder': folder
        }
        self.add_method('filemanager', 'listing', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_filemanager_folders(self):
        """Returns list of folders existing in file manager"""
        self.add_method('filemanager', 'folders')
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_filemanager_aliases(self, files_info):
        """Returns uids of files aliases in other projects. files_info should be dictionary where key is file's md5 hash string and value is it's size"""
        args = {
            'files': files_info
        }
        self.add_method('filemanager', 'aliases', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_filemanager_vipaliases(self, files_info):
        """Returns list of aliases for vip-file.com"""
        args = {
            'files': files_info
        }
        self.add_method('filemanager', 'vipaliases', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def delete(self, files_uids):
        """Removes files which uids are in files_uids from hosts. Returns amount of removed files"""
        args = {
            'uids': files_uids
        }
        self.add_method('filemanager', 'delete', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def rename(self, file_uid, name):
        """Renames file"""
        args = {
            'uid': file_uid,
            'name': name
        }
        self.add_method('filemanager', 'rename', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return bool(response['data'][0])

    def get_user_aliases(self):
        """Returns dictionary with current user's ID in all projects (letitbit, vip-file, etc)"""
        self.add_method('user', 'aliases')
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return bool(response['data'][0])

    def get_user_aliases_login(self, project='letitbit.net'):
        """Returns user's login for chosen project"""
        args = {
            'project': project
        }
        self.add_method('user', 'aliases_login', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_user_info(self, login=None, passwd_hash=None, project='letitbit.net'):
        if login and passwd_hash:
            args = {
                'login': login,
                'pass': passwd_hash,
                'project': project
            }
            self.add_method('user', 'info', args)
        else:
            self.add_method('user', 'info')
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def register_user(self, login, passwd, project='letitbit.net'):
        args = {
            'login': login,
            'pass': passwd,
            'project': project
        }
        self.add_method('user', 'register', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def assume_user(self, login, passwd, project='letitbit.net'):
        """Allows you to change current user"""
        args = {
            'login': login,
            'pass': passwd,
            'project': project
        }
        self.add_method('user', 'assume', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])

    def get_skymonk_link(self, uid):
        """Returns skymonk installation file link for chosen file"""
        args = {
            'uid': uid
        }
        self.add_method('preview', 'skymonk_link', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_flv_image(self, uid):
        """Returns flv video images link for chosen file"""
        args = {
            'uid': uid
        }
        self.add_method('preview', 'flv_image', args)
        response = self.run()
        if response['status'] != 'OK':
            raise NotSuccessfulResponseException(response['status'])
        return response['data'][0]

    def get_flv_paste_code(self, link, width=600, height=450):
        """Returns html code which you can paste in your pages"""
        file_info = self.get_file_info()
        uid = file_info['uid']
        paste_code = "<script language=\"JavaScript\" type=\"text/javascript\" src=\"http://moevideo.net/video.php?file={}&width={}&height={}\"></script>".format(uid, width, height)
        return paste_code

    def convert_videos(self, files_uids, login, password):
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        login_data = urllib.urlencode({'log': login, 'pas': password, 'inout': ""})

        # try to login twice, first time you will just get cookies
        opener.open('http://lib.wm-panel.com/wm-panel/user/signin-do', login_data)
        opener.open('http://lib.wm-panel.com/wm-panel/user/signin-do', login_data)

        msg = dict()
        msg['path'] = 'ROOT/HOME/letitbit.net'
        msg['fileuids[]'] = files_uids
        convert_data = urllib.urlencode(msg, True)
        opener.open('http://lib.wm-panel.com/wm-panel/File-Manager-Ajax?module=fileman_myfiles&section=ajax&page=grid_action_convert', convert_data)