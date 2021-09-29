# -*- coding: utf-8 -*-
import os
import json
import datetime
import time
import sys
import re
import logging
import cgi
from importlib import reload
from urllib.parse import parse_qs
import requests
import web
from web import form
import forms, mapping, conf, queries , vocabs  , github_sync
import utils as u
#import threading

web.config.debug = False

# ROUTING

prefix = ''
#prefixLocal = '/musow/'
prefixLocal = prefix
urls = (
	prefix + '/', 'Login',
	prefix + '/setup', 'Setup',
	prefix + '/template', 'Template',
	prefix + '/logout', 'Logout',
	prefix + '/gitauth', 'Gitauth',
	prefix + '/oauth-callback', 'Oauthcallback',
	prefix + '/welcome-(.+)','Index',
	prefix + '/record-(.+)', 'Record',
	prefix + '/modify-(.+)', 'Modify',
	prefix + '/review-(.+)', 'Review',
	prefix + '/documentation', 'Documentation',
	prefix + '/records', 'Records',
	prefix + '/model', 'DataModel',
	prefix + '/view-(.+)', 'View',
	prefix + '/term-(.+)', 'Term',
	prefix + '/(sparql)','sparql'
)

app = web.application(urls, globals())

# SESSIONS

store, session, session_data = u.initialize_session(app)


# TEMPLATING

render = web.template.render('templates/', base="layout", cache=False,
								globals={'session':session,'time_now':u.get_timestamp,
								'isinstance':isinstance,'str':str, 'next':next,
								'upper':u.upper, 'toid':u.toid, 'get_type':web.form.Checkbox.get_type, 'type':type,
								'Checkbox':web.form.Checkbox})
render2 = web.template.render('templates/', globals={'session':session})

# LOAD FORM, IMPORT VOCABS, QUERY LOV VOCABULARIES

with open(conf.myform) as config_form:
	fields = json.load(config_form)

vocabs.import_vocabs(fields)
res_class = conf.main_entity # get main class from conf py
res_class_label = u.get_LOV_labels(res_class,'class')
props_labels = [ u.get_LOV_labels(field["property"],'property') for field in fields]

# ERROR HANDLER

def notfound():
	return web.notfound(render.notfound(user=session['username']))

def internalerror():
	return web.internalerror(render.internalerror(user=session['username']))

class Notfound:
	def GET(self):
		raise web.notfound()

app.notfound = notfound
app.internalerror = internalerror

# UTILS

def key(s):
	fmt = "%Y-%m-%dT%H:%M:%S"
	return datetime.datetime.strptime(s, fmt)


def create_record(data):
	if data and 'action' in data and data.action.startswith('createRecord'):
		record = data.action.split("createRecord",1)[1]
		u.log_output('START NEW RECORD', session['logged_in'], session['username'])
		raise web.seeother(prefixLocal+'record-'+record)
	else:
		u.log_output('ELSE', session['logged_in'], session['username'])
		#raise web.seeother(prefixLocal+'/')

def init_js_config(data):
	"""Initializes the JS config by the given data

	Parameters
	----------
	data: dict
		Dictionary that is either the initial config or the given data record.
	"""
	with open('static/js/conf.js', 'w') as jsfile:
		jsfile.writelines('var myPublicEndpoint = "'+data.myPublicEndpoint+'";\n')
		jsfile.writelines('var base = "'+ data.base +'";\n')
		# TODO, support for data served in a single graph
		jsfile.writelines('var graph = "";\n')

# GITHUB LOGIN
clientId = conf.gitClientID

class Gitauth:
	def GET(self):
		return web.seeother("https://github.com/login/oauth/authorize?client_id="+clientId+"&scope=repo read:user")


class Oauthcallback:
	def GET(self):
		data = web.input()
		code = data.code

		res = github_sync.ask_user_permission(code)

		if res:
			userlogin, usermail, bearer_token = github_sync.get_user_login(res)
			is_valid_user = github_sync.get_github_users(userlogin)
			if is_valid_user == True:
				session['logged_in'] = 'True'
				session['username'] = usermail
				session['gituser'] = userlogin
				session['ip_address'] = str(web.ctx['ip'])
				session['bearer_token'] = bearer_token
				# do not store the token
				u.log_output('LOGIN VIA GITHUB', session['logged_in'], session['username'])
				raise web.seeother(prefixLocal+'welcome-1')

		else:
			print("bad request to github oauth")
			return internalerror()

# INITIAL SETUP
u.reload_config()
init_js_config(conf)


class Setup:
	def GET(self):

		# reload conf
		u.log_output("SETUP:GET",session['logged_in'], session['username'])
		u.reload_config()
		f = forms.get_form('setup.json')
		data = u.get_vars_from_module('conf')
		return render.setup(f=f,user='anonymous',data=data)

	def POST(self):
		data = web.input()
		if 'action' in data:
			create_record(data)
		else:
			u.log_output("SETUP:POST",session['logged_in'], session['username'])

			original_status=conf.status
			# override the module conf and conf.json
			file = open('conf.py', 'w')
			file.writelines('# -*- coding: utf-8 -*-\n')
			file.writelines('status= "modified"\n')
			file.writelines('myform = "myform.json"\n')
			file.writelines('log_file = "ip_logs.log"\n')
			file.writelines('wikidataEndpoint = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"\n')
			for k,v in data.items():
				file.writelines(k+'''="'''+v+'''"\n''')
			# write the json config file for javascript
			# TODO, support for data served in a single graph
			init_js_config(data)
			u.reload_config()
			# render login
			if original_status == 'modified':
				raise web.seeother(prefixLocal+'/welcome-1')
			else:
				raise web.seeother(prefixLocal+'template')

class Template:
	def GET(self):
		with open(conf.myform) as config_form:
			fields = json.load(config_form)
		res_type = conf.main_entity
		return render.template(f=fields,user='anonymous',res_type=res_type)

	def POST(self):
		data = web.input()
		if 'action' in data:
			create_record(data)
		else:
			u.fields_to_json(data, conf.myform)
			u.reload_config()
			#threading.Thread(target=u.fileWatcher).start()
			raise web.seeother(prefixLocal+'/welcome-1')
# CLASSIC LOGIN : TO BE REMOVED

class Login:
	def GET(self):
		if conf.status=='not modified':
			raise web.seeother('setup')
		if session.username != 'anonymous':
			u.log_output('HOMEPAGE LOGGED IN', session['logged_in'], session['username'])
			raise web.seeother(prefixLocal+'welcome-1')
		else:
			u.log_output('HOMEPAGE ANONYMOUS', session['logged_in'], session['username'])
			return render.login(user='anonymous')

	def POST(self):
		data = web.input()
		create_record(data)


class Logout:
	def GET(self):
		u.log_output('LOGOUT', session['logged_in'], session['username'])
		session['logged_in'] = 'False'
		session['username'] = 'anonymous'
		session['ip_address'] = str(web.ctx['ip'])
		session['bearer_token'] = 'None'
		session['gituser'] = 'None'
		raise web.seeother(prefixLocal+'/')

	def POST(self):
		data = web.input()
		create_record(data)

# BACKEND Index: show list or records (only logged users)

class Index:
	def GET(self, page):
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		session['ip_address'] = str(web.ctx['ip'])
		filterRecords = ''
		userID = session['username'].replace('@','-at-').replace('.','-dot-')
		alll = queries.countAll()
		all, notreviewed, underreview, published = queries.getCountings()
		results = queries.getRecordsPagination(page)
		records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))

		session_data['logged_in'] = 'True' if (session['username'] != 'anonymous') or \
							(clientId == '' and session['username'] == 'anonymous') else 'False'

		if (session['username'] != 'anonymous') or \
			(clientId == '' and session['username'] == 'anonymous'):
			u.log_output('WELCOME PAGE', session['logged_in'], session['username'])

			return render.index(wikilist=records, user=session['username'],
				varIDpage=str(time.time()).replace('.','-'), alll=alll, all=all,
				notreviewed=notreviewed,underreview=underreview,
				published=published, page=page,pagination=int(conf.pagination),
				filter=filterRecords, filterName = 'filterAll')
		else:
			if clientId == '':
				session['logged_in'] = 'False'
				return render.index(wikilist=records, user=session['username'],
					varIDpage=str(time.time()).replace('.','-'), alll=alll, all=all,
					notreviewed=notreviewed,underreview=underreview,
					published=published, page=page,pagination=int(conf.pagination),
					filter=filterRecords, filterName = 'filterAll')
			else:
				session['logged_in'] = 'False'
				u.log_output('WELCOME PAGE NOT LOGGED IN', session['logged_in'], session['username'])
				raise web.seeother(prefixLocal+'/')

	def POST(self, page):
		actions = web.input()
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		session['ip_address'] = str(web.ctx['ip'])

		filter_values = {
			"filterNew": "?g base:publicationStage ?anyValue . FILTER (isLiteral(?anyValue) && lcase(str(?anyValue)) = 'not modified') .",
			"filterReviewed": "?g base:publicationStage ?anyValue . FILTER (isLiteral(?anyValue) && lcase(str(?anyValue)) = 'modified') .",
			"filterPublished": "?g base:publicationStage ?anyValue . FILTER (isLiteral(?anyValue) && lcase(str(?anyValue)) = 'published') .",
			"filterAll": "none"
		}

		# filter records
		if actions.action.startswith('filter'):
			filterRecords = filter_values[actions.action]
			filterRecords = filterRecords if filterRecords not in ['none',None] else ''
			filterName = actions.action
			page = 1
			results = queries.getRecordsPagination(page, filterRecords)
			records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))
			alll = queries.countAll()
			all, notreviewed, underreview, published = queries.getCountings(filterRecords)
			filterRecords = filterRecords if filterRecords != '' else 'none'

			return render.index(wikilist=records, user=session['username'],
				varIDpage=str(time.time()).replace('.','-'),
				alll=alll, all=all, notreviewed=notreviewed,
				underreview=underreview, published=published,
				page=page, pagination=int(conf.pagination),
				filter= filterRecords, filterName = filterName)

		# create a new record (logged users)
		elif actions.action.startswith('createRecord'):
			record = actions.action.split("createRecord",1)[1]
			u.log_output('START NEW RECORD (LOGGED IN)', session['logged_in'], session['username'], record )
			raise web.seeother(prefixLocal+'record-'+record)

		# delete a record (but not the dump in /records folder)
		elif actions.action.startswith('deleteRecord'):
			graph = actions.action.split("deleteRecord",1)[1].split(' __')[0]
			filterRecords = actions.action.split('deleteRecord',1)[1].split(' __')[1]
			queries.deleteRecord(graph)
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			if conf.github_backup == "True": # path hardcoded, to be improved
				file_path = "records/"+graph.split(conf.base)[1].rsplit('/',1)[0]+".ttl"
				github_sync.delete_file(file_path,"main", session['gituser'], session['username'], session['bearer_token'])
			u.log_output('DELETE RECORD', session['logged_in'], session['username'], graph )
			if filterRecords in ['none',None]:
				raise web.seeother(prefixLocal+'welcome-'+page)
			else:
				filterName = [k if v == filterRecords else 'filterName' for k,v in filter_values.items()][0]
				results = queries.getRecordsPagination(page,filterRecords)
				records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))
				alll = queries.countAll()
				all, notreviewed, underreview, published = queries.getCountings(filterRecords)

				return render.index(wikilist=records, user=session['username'],
					varIDpage=str(time.time()).replace('.','-'),
					alll=alll, all=all, notreviewed=notreviewed,
					underreview=underreview, published=published,
					page=page, pagination=int(conf.pagination),
					filter= filterRecords, filterName = filterName)

		# modify a record
		elif actions.action.startswith('modify'):
			record = actions.action.split(conf.base,1)[1].replace('/','')
			u.log_output('MODIFY RECORD', session['logged_in'], session['username'], record )
			raise web.seeother(prefixLocal+'modify-'+record)

		# start review of a record
		elif actions.action.startswith('review'):
			record = actions.action.split(conf.base,1)[1].replace('/','')
			u.log_output('REVIEW RECORD', session['logged_in'], session['username'], record )
			raise web.seeother(prefixLocal+'review-'+record)

		# change page
		elif actions.action.startswith('changepage'):
			pag = actions.action.split('changepage-',1)[1].split(' __')[0]
			filterRecords = actions.action.split('changepage-',1)[1].split(' __')[1]
			if filterRecords in ['none',None]:
				raise web.seeother(prefixLocal+'welcome-'+pag)
			else:
				filterName = [k if v == filterRecords else '' for k,v in filter_values.items()][0]
				results = queries.getRecordsPagination(pag, filterRecords)
				records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))
				alll = queries.countAll()
				all, notreviewed, underreview, published = queries.getCountings(filterRecords)

				return render.index( wikilist=records, user=session['username'],
					varIDpage=str(time.time()).replace('.','-'),
					alll=alll, all=all, notreviewed=notreviewed,
					underreview=underreview, published=published,
					page=page, pagination=int(conf.pagination),
					filter= filterRecords, filterName = filterName)

		# login or create a new record
		else:
			create_record(data)

# FORM: create a new record (both logged in and anonymous users)

class Record(object):
	def GET(self, name):
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		session['ip_address'] = str(web.ctx['ip'])
		user = session['username']
		logged_in = True if user != 'anonymous' else False
		u.log_output('GET RECORD FORM', session['logged_in'], session['username'])
		block_user, limit = u.check_ip(str(web.ctx['ip']), str(datetime.datetime.now()) )
		f = forms.get_form(conf.myform)
		return render.record(record_form=f, pageID=name, user=user, alert=block_user, limit=limit)

	def POST(self, name):
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		f = forms.get_form(conf.myform)
		user = session['username']
		session['ip_address'] = str(web.ctx['ip'])
		u.write_ip(str(datetime.datetime.now()), str(web.ctx['ip']), 'POST')

		if not f.validates():
			u.log_output('SUBMIT INVALID FORM', session['logged_in'], session['username'],recordID)
			return render.record(record_form=f, pageID=name, user=user)
		else:
			recordData = web.input()
			#print(recordData)
			if 'action' in recordData:
				create_record(recordData)
			recordID = recordData.recordID if 'recordID' in recordData else None
			u.log_output('CREATED RECORD', session['logged_in'], session['username'],recordID)
			if recordID:
				userID = user.replace('@','-at-').replace('.','-dot-')
				file_path = mapping.inputToRDF(recordData, userID, 'not modified')
				if conf.github_backup == "True":
					github_sync.push(file_path,"main", session['gituser'], session['username'], session['bearer_token'])
				whereto = prefixLocal+'/' if user == 'anonymous' else prefixLocal+'welcome-1'
				raise web.seeother(whereto)
			else:
				create_record(data)

# FORM: modify a  record (only logged in users)

class Modify(object):
	def GET(self, name):
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		session['ip_address'] = str(web.ctx['ip'])
		session_data['logged_in'] = 'True' if (session['username'] != 'anonymous') or \
							(clientId == '' and session['username'] == 'anonymous') else 'False'

		if (session['username'] != 'anonymous') or \
			(clientId == '' and session['username'] == 'anonymous'):
			graphToRebuild = conf.base+name+'/'
			recordID = name
			data = queries.getData(graphToRebuild)
			u.log_output('START MODIFY RECORD', session['logged_in'], session['username'], recordID )
			f = forms.get_form(conf.myform)
			ids_dropdown = u.get_dropdowns(fields)
			return render.modify(graphdata=data, pageID=recordID, record_form=f,
							user=session['username'],ids_dropdown=ids_dropdown)
		else:
			session['logged_in'] = 'False'
			raise web.seeother(prefixLocal+'/')

	# TODO validate form!
	def POST(self, name):
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		recordData = web.input()
		session['ip_address'] = str(web.ctx['ip'])

		if 'action' in recordData:
			create_record(recordData)
		else:
			recordID = recordData.recordID
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			graphToClear = conf.base+name+'/'
			file_path = mapping.inputToRDF(recordData, userID, 'modified', graphToClear)
			if conf.github_backup == "True":
				github_sync.push(file_path,"main", session['gituser'], session['username'], session['bearer_token'], '(modified)')
			u.log_output('MODIFIED RECORD', session['logged_in'], session['username'], recordID )
			raise web.seeother(prefixLocal+'welcome-1')

# FORM: review a record for publication (only logged in users)

class Review(object):
	def GET(self, name):
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		session_data['logged_in'] = 'True' if (session['username'] != 'anonymous') or \
							(clientId == '' and session['username'] == 'anonymous') else 'False'

		if (session['username'] != 'anonymous') or \
			(clientId == '' and session['username'] == 'anonymous'):
			graphToRebuild = conf.base+name+'/'
			recordID = name
			data = queries.getData(graphToRebuild)
			session['ip_address'] = str(web.ctx['ip'])
			u.log_output('START REVIEW RECORD', session['logged_in'], session['username'], recordID )
			f = forms.get_form(conf.myform)
			ids_dropdown = u.get_dropdowns(fields)
			return render.review(graphdata=data, pageID=recordID, record_form=f,
								graph=graphToRebuild, user=session['username'],
								ids_dropdown=ids_dropdown)
		else:
			session['logged_in'] = 'False'
			raise web.seeother(prefixLocal+'/')

	def POST(self, name):
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		actions = web.input()
		session['ip_address'] = str(web.ctx['ip'])

		# save the new record for future publication
		if actions.action.startswith('save'):
			recordData = web.input()
			recordID = recordData.recordID
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			graphToClear = conf.base+name+'/'
			file_path = mapping.inputToRDF(recordData, userID, 'modified',graphToClear)
			if conf.github_backup == "True":
				github_sync.push(file_path,"main", session['gituser'], session['username'], session['bearer_token'], '(reviewed)')
			u.log_output('REVIEWED (NOT PUBLISHED) RECORD', session['logged_in'], session['username'], recordID )
			raise web.seeother(prefixLocal+'welcome-1')

		# publish
		elif actions.action.startswith('publish'):
			recordData = web.input()
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			graphToClear = conf.base+name+'/'
			file_path= mapping.inputToRDF(recordData, userID, 'published',graphToClear)
			if conf.github_backup == "True":
				github_sync.push(file_path,"main", session['gituser'], session['username'], session['bearer_token'], '(published)')
			u.log_output('PUBLISHED RECORD', session['logged_in'], session['username'], name )
			raise web.seeother(prefixLocal+'welcome-1')

		# login or create new record
		else:
			create_record(actions)

# FORM: view documentation

class Documentation:
	def GET(self):
		return render.documentation(user=session['username'])

	def POST(self):
		data = web.input()
		if 'action' in data:
			create_record(data)

# VIEW : lists of types of records of the catalogue

class Records:
	def GET(self):
		#threading.Thread(target=u.fileWatcher).start()
		records = queries.getRecords()
		alll = queries.countAll()
		filtersBrowse = queries.getBrowsingFilters()
		return render.records(user=session['username'], data=records,
							title='Latest added resources', r_base=conf.base,
							alll=alll, filters=filtersBrowse)

	def POST(self):
		data = web.input()
		if 'action' in data:
			create_record(data)

# VIEW : single record

class View(object):
	def GET(self, name):
		base = conf.base
		record = base+name
		data = dict(queries.getData(record+'/'))
		stage = data['stage'][0]
		title = [data[k][0] for k,v in data.items() \
				for field in fields if (field['disambiguate'] == "True" \
				and k == field['id'])][0]
		data_labels = { field['label']:v for k,v in data.items() \
						for field in fields if k == field['id']}

		return render.view(user=session['username'], graphdata=data_labels,
						graphID=name, title=title, stage=stage, base=base)

	def POST(self,name):
		data = web.input()
		if 'action' in data:
			create_record(data)

# TERM : vocabulary terms and newly created entities

class Term(object):
	def GET(self, name):
		data = queries.describeTerm(name)
		#print(data)
		count = len([ result["subject"]["value"] \
					for result in data["results"]["bindings"] \
					if (name in result["object"]["value"] and result["object"]["type"] == 'uri') ])

		return render.term(user=session['username'], data=data, count=count)

	def POST(self,name):
		data = web.input()
		if 'action' in data:
			create_record(data)
# DATA MODEL

class DataModel:
	def GET(self):
		return render.datamodel(user=session['username'], data=props_labels, res_class=res_class_label)

	def POST(self):
		data = web.input()
		if 'action' in data:
			create_record(data)

# QUERY: endpoint GUI

class sparql:
	def GET(self, active):
		# u.log_output("SPARQL:GET", session['logged_in'], session['username'])
		content_type = web.ctx.env.get('CONTENT_TYPE')
		return self.__run_query_string(active, web.ctx.env.get("QUERY_STRING"), content_type)

	def POST(self, active):
		# u.log_output("SPARQL:POST", session['logged_in'], session['username'])
		content_type = web.ctx.env.get('CONTENT_TYPE')
		web.debug("The content_type value: ")
		web.debug(content_type)

		data = web.input()
		if 'action' in data:
			create_record(data)

		cur_data = web.data()
		if "application/x-www-form-urlencoded" in content_type:
			# print ("QUERY TO ENDPOINT:", cur_data)
			return self.__run_query_string(active, cur_data, True, content_type)
		elif "application/sparql-query" in content_type:
			# print("QUERY TO ENDPOINT:", cur_data)
			return self.__contact_tp(cur_data, True, content_type)
		else:
			raise web.redirect("/sparql")

	def __contact_tp(self, data, is_post, content_type):
		accept = web.ctx.env.get('HTTP_ACCEPT')
		# u.log_output("__contact_tp", session['logged_in'], session['username'])
		if accept is None or accept == "*/*" or accept == "":
			# u.log_output("--accept None", session['logged_in'], session['username'])
			accept = "application/sparql-results+xml"
		if is_post: # CHANGE
			# u.log_output("--post", session['logged_in'], session['username'])
			req = requests.post(conf.myEndpoint, data=data,
								headers={'content-type': content_type, "accept": accept})
		else: # CHANGE
			# u.log_output("--get", session['logged_in'], session['username'])
			req = requests.get("%s?%s" % (conf.myEndpoint, data),
							   headers={'content-type': content_type, "accept": accept})

		# u.log_output("--result received", session['logged_in'], session['username'])

		if req.status_code == 200:
			# u.log_output("--200", session['logged_in'], session['username'])

			web.header('Access-Control-Allow-Origin', '*')
			web.header('Access-Control-Allow-Credentials', 'true')
			web.header('Content-Type', req.headers["content-type"])

			return req.text
		else:
			# u.log_output("--ERROR", session['logged_in'], session['username'])

			raise web.HTTPError(
				str(req.status_code), {"Content-Type": req.headers["content-type"]}, req.text)

	def __run_query_string(self, active, query_string, is_post=False,
						   content_type="application/x-www-form-urlencoded"):

		# u.log_output("__run_query_string", session['logged_in'], session['username'])
		try:
			query_str_decoded = query_string.decode('utf-8')
		except Exception as e:
			# u.log_output("--not bytes but string", session['logged_in'], session['username'])
			query_str_decoded = query_string
		# u.log_output(query_str_decoded, session['logged_in'], session['username'])
		parsed_query = parse_qs(query_str_decoded)

		if query_str_decoded is None or query_str_decoded.strip() == "":
			# u.log_output('->render', session['logged_in'], session['username'])
			return render.sparql(active, user='anonymous')
		if re.search("updates?", query_str_decoded, re.IGNORECASE) is None:
			# u.log_output('-update=NO', session['logged_in'], session['username'])
			if "query" in parsed_query:
				# u.log_output('--query=YES', session['logged_in'], session['username'])
				return self.__contact_tp(query_string, is_post, content_type)
			else:
				# u.log_output('--query=NO', session['logged_in'], session['username'])
				raise web.redirect(conf.myPublicEndpoint)
		else:
			# u.log_output('-update=YES', session['logged_in'], session['username'])
			raise web.HTTPError(
				"403", {"Content-Type": "text/plain"}, "SPARQL Update queries are not permitted.")


if __name__ == "__main__":
	app.run()
