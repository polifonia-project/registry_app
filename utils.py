import re
import time
import datetime
import json
import web
import requests
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

# METHODS FOR DATA MODEL



def camel_case_split(identifier):
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return " ".join([m.group(0) for m in matches])

def split_uri(term):
	last_term = term.rsplit("/",1)[1]
	last_term = last_term.split("#")[1] if '#' in last_term else last_term
	return camel_case_split(last_term)

def get_LOV_labels(term, term_type=None):
	""" get class/ property labels from the form"""
	term, label = term, split_uri(term)
	lov_api = "https://lov.linkeddata.es/dataset/lov/api/v2/term/search?q="
	t = "&type="+term_type if term_type else ''
	label_en = "http://www.w3.org/2000/01/rdf-schema#label@en"
	req = requests.get(lov_api+term+t)



	if req.status_code == 200:
		res = req.json()
		for result in res["results"]:
			if result["uri"][0] in [term, term.replace("https","http")]:
				label = result["highlight"][label_en][0] \
					if label_en in result["highlight"] \
					else result["highlight"][label_en.replace("@en","")][0]\
					if label_en not in result["highlight"]  \
					and label_en.replace("@en","") in result["highlight"]\
					else split_uri(term)

	return term, label
