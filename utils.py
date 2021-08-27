import web
import time
import datetime
import conf

# WEBPY STUFF

def initialize_session(app):
	""" initialize user session.
	Sessions are pickled in folder /sessions"""
	if web.config.get('_session') is None:
		store = web.session.DiskStore('sessions')
		session = web.session.Session(app, store, initializer={'logged_in': 'False', 'username': 'anonymous', 'password': 'None', 'ip_address': 'None'})
		web.config._session = session
		session_data = session._initializer
	else:
		session = web.config._session
		session_data = session._initializer

	web.config.session_parameters['timeout'] = 86400
	return store, session, session_data


def log_output(action, logged_in, user, recordID=None):
	""" log information in console """
	message = '*** '+str(datetime.datetime.now())+' | '+action
	if recordID:
		message += ': <'+recordID+'>'
	message += ' | LOGGED IN: '+str(logged_in)+' | USER: '+user
	print(message)

# LIMIT REQUESTS BY IP ADDRESSES

def write_ip(timestamp, ip_add, request):
	""" write IP addresses in a log file"""
	logs = open(conf.log_file, 'a')
	logs.write( str(timestamp)+' --- '+ ip_add + ' --- '+ request+'\n')
	logs.close()

def check_ip(ip_add, current_time):
	"""read log file with IP addresses
	limit user POST requests to XX a day"""

	is_user_blocked = False
	limit = conf.limit_requests
	today = current_time.split()[0]
	data = open(conf.log_file, 'r').readlines()
	user_requests = [(line.split(' --- ')[0].split()[0], line.split(' --- ')[1]) for line in data if ip_add in line.split(' --- ')[1] and line.split(' --- ')[0].split()[0] == today ]
	if len(user_requests) > limit:
		is_user_blocked = True
	return is_user_blocked, limit


# METHODS FOR TEMPLATING
def get_dropdowns(fields):
	""" retrieve Dropdowns ids to render them properly
	in Modify and Review form"""
	ids_dropdown= [field['id'] for field in fields if field['type'] == 'Dropdown']
	return ids_dropdown

def get_timestamp():
	""" return timestamp when creating a new record """
	return str(time.time()).replace('.','-')

def upper(s):
	return s.upper()
