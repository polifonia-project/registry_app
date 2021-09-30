import os
import re
import time
import datetime
import json
from dotenv import load_dotenv
import web
import requests
import conf
from collections import defaultdict,OrderedDict
from importlib import reload

# WEBPY STUFF
template_json = open(conf.myform)
template_text = template_json.read()

def reload_config():
	"""Reload the config from conf.py and overrides the blazegraph endpoint
	   if the env variable is specified.
	"""
	load_dotenv()
	reload(conf)
	myEndpoint = os.getenv('BLAZEGRAPH_ENDPOINT', conf.myEndpoint)
	myPublicEndpoint = os.getenv('PUBLIC_BLAZEGRAPH_ENDPOINT', conf.myPublicEndpoint)

	conf.myEndpoint = myEndpoint
	conf.myPublicEndpoint = myPublicEndpoint

def fileWatcher():
	""" Read changes in myform.json and reload it"""
	global template_json , template_text
	while True:
		f = open(conf.myform)
		content = f.read()
		f.close()
		if content != template_text:
			print("Template modified! Reloading it...")
			template_json = json.loads(content)
			template_text = content
		time.sleep(0.5)

def initialize_session(app):
	""" initialize user session.
	Sessions are pickled in folder /sessions"""
	if web.config.get('_session') is None:
		store = web.session.DiskStore('sessions')
		session = web.session.Session(app, store, initializer={'logged_in': 'False', 'username': 'anonymous', 'gituser': 'None', 'bearer_token': 'None', 'ip_address': 'None'})
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
	logs = open(conf.log_file, 'a+')
	logs.write( str(timestamp)+' --- '+ ip_add + ' --- '+ request+'\n')
	logs.close()

def check_ip(ip_add, current_time):
	"""read log file with IP addresses
	limit user POST requests to XX a day"""

	is_user_blocked = False
	limit = int(conf.limit_requests)
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

# CONFIG STUFF

def get_vars_from_module(module_name):
	""" get all variables from a python module, e.g. conf"""
	module = globals().get(module_name, None)
	book = {}
	if module:
		book = {key: value for key, value in module.__dict__.items() if not (key.startswith('__') or key.startswith('_'))}
	return book

def toid(s):
	s = s.lower()
	s = s.replace(" ", "_")
	return s

def fields_to_json(data, json_file):
	""" setup/update the json file with the form template
	as modified via the web page *template* """
	print(data)
	list_dicts = defaultdict(dict)
	list_ids = sorted([k.split("__")[0] for k in data.keys()])

	for k,v in data.items():
		# group k,v by number in the k to preserve the order
		# e.g. '4__type__scope': 'Checkbox'
		idx, json_key , field_id = k.split("__")
		list_dicts[int(idx)]["id"] = field_id
		list_dicts[int(idx)][json_key] = v
	list_dicts = dict(list_dicts)
	print(list_dicts)
	for n,d in list_dicts.items():
		# cleanup existing k,v
		if 'values' in d:
			values_pairs = d['values'].replace('\r','').strip().split('\n')
			d["value"] = "URI"
			d['values'] = { pair.split(",")[0].strip():pair.split(",")[1].strip() for pair in values_pairs }
		d["disambiguate"] = "True" if 'disambiguate' in d else "False"
		d["browse"] = "True" if 'browse' in d else "False"
		# default if missing
		if d["type"] == "None":
			d["type"] = "Textbox" if "values" not in d else "Dropdown"
		if len(d["label"]) == 0:
			d["label"] = "no label"
		if len(d["property"]) == 0:
			d["property"] = "http://example.org/"+d["id"]
		# add default values
		d['searchWikidata'] = "True" if d['type'] == 'Textbox' and d['value'] == 'URI' else "False"
		d["disabled"] = "False"
		d["class"]= "col-md-11"
		d["cache_autocomplete"] ="off"
	# add a default disambiguate if none is selected
	is_any_disambiguate = ["yes" for n,d in list_dicts.items() if d['disambiguate'] == 'True']
	if len(is_any_disambiguate) == 0:
		ids_disamb = [[n, d["disambiguate"]] for n,d in list_dicts.items() if d['type'] == 'Textbox' and d['value'] == 'URI']
		if len(ids_disamb) > 0:
			list_dicts[ids_disamb[0][0]]["disambiguate"] = "True"

	ordict = OrderedDict(sorted(list_dicts.items()))
	ordlist = [d for k,d in ordict.items()]
	# store the dict as json file
	with open(json_file, 'w') as fout:
		fout.write(json.dumps(ordlist, indent=1))

def validate_setup(data):
	""" Validate user input in setup page and check errors / missing values"""
	for k,v in data.items():
		k["myEndpoint"] = k["myEndpoint"] if k["myEndpoint"].startswith("http") else "http://127.0.0.1:3000/blazegraph/sparql"
		k["myPublicEndpoint"] = k["myPublicEndpoint"] if k["myPublicEndpoint"].startswith("http") else "http://127.0.0.1:3000/blazegraph/sparql"
		k["base"] = k["base"] if k["base"].startswith("http") else "http://example.org/base/"
		k["main_entity"] = k["main_entity"] if k["main_entity"].startswith("http") else "http://example.org/entity/"
		k["limit_requests"] = k["limit_requests"] if isinstance(int(k["limit_requests"]), int) else "50"
		k["pagination"] = k["pagination"] if isinstance(int(k["pagination"]), int) else "10"
		k["github_backup"] = k["github_backup"] if k["github_backup"] in ["True", "False"] else "False"
		# github backup
		if k["github_backup"] == "True" \
			and (len(k["repo_name"]) > 1 and len(k["owner"]) > 1 and len(k["author_email"]) > 1 and len(k["token"]) > 1):
			k["github_backup"] = "True"
		else:
			k["github_backup"] = "False"

	return data
