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

# VARS

WIKIDATA_SPARQL = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"
DEFAULT_FORM_JSON = conf.myform
IP_LOGS = "ip_logs.log"

# ROUTING

prefix = ''
prefixLocal = prefix # REPLACE IF IN SUBFOLDER
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
wsgiapp = app.wsgifunc()

# SESSIONS

store, session, session_data = u.initialize_session(app)

# TEMPLATING

render = web.template.render('templates/', base="layout", cache=False,
								globals={'session':session,'time_now':u.get_timestamp,
								'isinstance':isinstance,'str':str, 'next':next,
								'upper':u.upper, 'toid':u.toid,
								'get_type':web.form.Checkbox.get_type, 'type':type,
								'Checkbox':web.form.Checkbox})

# INITIAL SETUP

# LOAD FORM
with open(conf.myform) as config_form:
	fields = json.load(config_form)

# LOAD CONFIG AND CONTROLLED VOCABULARIES
u.reload_config()
u.init_js_config(conf)
vocabs.import_vocabs(fields)

# ERROR HANDLER

def notfound():
	is_git_auth = github_sync.is_git_auth()
	return web.notfound(render.notfound(user=session['username'],
		is_git_auth=is_git_auth,project=conf.myProject))

def internalerror():
	is_git_auth = github_sync.is_git_auth()
	return web.internalerror(render.internalerror(user=session['username'],
		is_git_auth=is_git_auth,project=conf.myProject))

class Notfound:
	def GET(self):
		raise web.notfound()

app.notfound = notfound
app.internalerror = internalerror

# UTILS

def create_record(data):
	""" POST method in static pages. The only accepted request is
	Create a new record.

	Parameters
	----------
	data: dict
		Dictionary of user input -- web.input().
	"""
	if data and 'action' in data and data.action.startswith('createRecord'):
		record = data.action.split("createRecord",1)[1]
		u.log_output('START NEW RECORD', session['logged_in'], session['username'])
		raise web.seeother(prefixLocal+'record-'+record)
	else:
		u.log_output('ELSE', session['logged_in'], session['username'])
		return internalerror()
		#raise web.seeother(prefixLocal+'/')


# GITHUB AUTHENTICATION

class Gitauth:
	def GET(self):
		""" When the user clicks on Member area
		s/he is redirected to github authentication interface"""

		github_auth = "https://github.com/login/oauth/authorize"
		clientId = conf.gitClientID
		scope = "&scope=repo read:user"

		return web.seeother(github_auth+"?client_id="+clientId+scope)

class Oauthcallback:
	def GET(self):
		""" Redirect from class Gitauth.
		After the user authenticates, get profile information (ask_user_permission).
		Check the user is a collaborator of the repository (get_github_users)
		"""

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
				# store the token in session
				u.log_output('LOGIN VIA GITHUB', session['logged_in'], session['username'])
				raise web.seeother(prefixLocal+'welcome-1')
		else:
			print("bad request to github oauth")
			return internalerror()


class Setup:
	def GET(self):
		""" /setup webpage. Modify config.py and reload the module
		"""

		u.log_output("SETUP:GET",session['logged_in'], session['username'])
		is_git_auth = github_sync.is_git_auth()
		u.reload_config() # reload conf
		f = forms.get_form('setup.json') # get the form template
		data = u.get_vars_from_module('conf') # fill in the form with conf values
		return render.setup(f=f,user=session['username'],
							data=data, is_git_auth=is_git_auth,project=conf.myProject)

	def POST(self):
		""" Modify config.py and static/js/conf.json and reload the module
		"""

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
			file.writelines('myform = "'+DEFAULT_FORM_JSON+'"\n')
			file.writelines('myEndpoint = "'+DEFAULT_FORM_JSON+'"\n')
			file.writelines('log_file = "'+IP_LOGS+'"\n')
			file.writelines('wikidataEndpoint = "'+WIKIDATA_SPARQL+'"\n')
			data = u.validate_setup(data)

			for k,v in data.items():
				file.writelines(k+'''="'''+v+'''"\n''')

			# write the json config file for javascript
			u.init_js_config(data)
			u.reload_config()


			if original_status == 'modified': # render login
				raise web.seeother(prefixLocal+'/welcome-1')
			else: # render template
				raise web.seeother(prefixLocal+'template')


class Template:
	def GET(self):
		""" Modify the form template for data entry
		"""

		is_git_auth = github_sync.is_git_auth()
		res_type = conf.main_entity

		# reload template form
		with open(conf.myform) as config_form:
			fields = json.load(config_form)

		return render.template(f=fields,user=session['username'],
								res_type=res_type, is_git_auth=is_git_auth,project=conf.myProject)

	def POST(self):
		""" Modify the form template for data entry and reload config files
		"""

		data = web.input()
		if 'action' in data:
			create_record(data)
		else:
			u.fields_to_json(data, conf.myform)
			u.reload_config()
			#threading.Thread(target=u.fileWatcher).start()
			raise web.seeother(prefixLocal+'/welcome-1')

# LOGIN : Homepage

class Login:
	def GET(self):
		""" Homepage """

		is_git_auth = github_sync.is_git_auth()
		if conf.status=='not modified':
			raise web.seeother('setup')
		if session.username != 'anonymous':
			u.log_output('HOMEPAGE LOGGED IN', session['logged_in'], session['username'])
			raise web.seeother(prefixLocal+'welcome-1')
		else:
			u.log_output('HOMEPAGE ANONYMOUS', session['logged_in'], session['username'])
			return render.login(user='anonymous',is_git_auth=is_git_auth,project=conf.myProject)

	def POST(self):
		data = web.input()
		create_record(data)


class Logout:
	def GET(self):
		"""Logout"""
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
		""" Member area

		Parameters
		----------
		page: str
			pagination of records in the backend (1= first page)
		"""

		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		is_git_auth = github_sync.is_git_auth()
		session['ip_address'] = str(web.ctx['ip'])
		filterRecords = ''
		userID = session['username'].replace('@','-at-').replace('.','-dot-')
		alll = queries.countAll()
		all, notreviewed, underreview, published = queries.getCountings()
		results = queries.getRecordsPagination(page)
		records = reversed(sorted(results, key=lambda tup: u.key(tup[4][:-5]) ))

		session_data['logged_in'] = 'True' if (session['username'] != 'anonymous') or \
							(conf.gitClientID == '' and session['username'] == 'anonymous') else 'False'

		if (session['username'] != 'anonymous') or \
			(conf.gitClientID == '' and session['username'] == 'anonymous'):
			u.log_output('WELCOME PAGE', session['logged_in'], session['username'])

			return render.index(wikilist=records, user=session['username'],
				varIDpage=str(time.time()).replace('.','-'), alll=alll, all=all,
				notreviewed=notreviewed,underreview=underreview,
				published=published, page=page,pagination=int(conf.pagination),
				filter=filterRecords, filterName = 'filterAll',is_git_auth=is_git_auth,
				project=conf.myProject)
		else:
			if conf.gitClientID == '':
				session['logged_in'] = 'False'
				return render.index(wikilist=records, user=session['username'],
					varIDpage=str(time.time()).replace('.','-'), alll=alll, all=all,
					notreviewed=notreviewed,underreview=underreview,
					published=published, page=page,pagination=int(conf.pagination),
					filter=filterRecords, filterName = 'filterAll',is_git_auth=is_git_auth,
					project=conf.myProject)
			else:
				session['logged_in'] = 'False'
				u.log_output('WELCOME PAGE NOT LOGGED IN', session['logged_in'], session['username'])
				raise web.seeother(prefixLocal+'/')

	def POST(self, page):
		""" Member area

		Parameters
		----------
		page: str
			pagination of records in the backend (1= first page)
		"""

		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		actions = web.input()
		session['ip_address'] = str(web.ctx['ip'])
		is_git_auth = github_sync.is_git_auth()

		pub_stage = "?g base:publicationStage ?anyValue . "
		filter = "isLiteral(?anyValue) && lcase(str(?anyValue))"
		# filters on the list of records
		filter_values = {
			"filterNew": pub_stage+"FILTER ("+filter+" = 'not modified') .",
			"filterReviewed": pub_stage+"FILTER ("+filter+" = 'modified') .",
			"filterPublished": pub_stage+ "FILTER ("+filter+" = 'published') .",
			"filterAll": "none"
		}

		# filter records
		if actions.action.startswith('filter'):
			filterRecords = filter_values[actions.action]
			filterRecords = filterRecords if filterRecords not in ['none',None] else ''
			filterName = actions.action
			page = 1
			results = queries.getRecordsPagination(page, filterRecords)
			records = reversed(sorted(results, key=lambda tup: u.key(tup[4][:-5]) ))
			alll = queries.countAll()
			all, notreviewed, underreview, published = queries.getCountings(filterRecords)
			filterRecords = filterRecords if filterRecords != '' else 'none'

			return render.index(wikilist=records, user=session['username'],
				varIDpage=str(time.time()).replace('.','-'),
				alll=alll, all=all, notreviewed=notreviewed,
				underreview=underreview, published=published,
				page=page, pagination=int(conf.pagination),
				filter= filterRecords, filterName = filterName, is_git_auth=is_git_auth,
				project=conf.myProject)

		# create a new record
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
				github_sync.delete_file(file_path,"main", session['gituser'],
										session['username'], session['bearer_token'])
			u.log_output('DELETE RECORD', session['logged_in'], session['username'], graph )
			if filterRecords in ['none',None]:
				raise web.seeother(prefixLocal+'welcome-'+page)
			else:
				filterName = [k if v == filterRecords else 'filterName' for k,v in filter_values.items()][0]
				results = queries.getRecordsPagination(page,filterRecords)
				records = reversed(sorted(results, key=lambda tup: u.key(tup[4][:-5]) ))
				alll = queries.countAll()
				all, notreviewed, underreview, published = queries.getCountings(filterRecords)

				return render.index(wikilist=records, user=session['username'],
					varIDpage=str(time.time()).replace('.','-'),
					alll=alll, all=all, notreviewed=notreviewed,
					underreview=underreview, published=published,
					page=page, pagination=int(conf.pagination),
					filter= filterRecords, filterName = filterName, is_git_auth=is_git_auth,
					project=conf.myProject)

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
				records = reversed(sorted(results, key=lambda tup: u.key(tup[4][:-5]) ))
				alll = queries.countAll()
				all, notreviewed, underreview, published = queries.getCountings(filterRecords)

				return render.index( wikilist=records, user=session['username'],
					varIDpage=str(time.time()).replace('.','-'),
					alll=alll, all=all, notreviewed=notreviewed,
					underreview=underreview, published=published,
					page=page, pagination=int(conf.pagination),
					filter= filterRecords, filterName = filterName, is_git_auth=is_git_auth,
					project=conf.myProject)

		# login or create a new record
		else:
			create_record(data)

# FORM: create a new record (both logged in and anonymous users)

class Record(object):
	def GET(self, name):
		""" Create a new record

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""

		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		u.log_output('GET RECORD FORM', session['logged_in'], session['username'])

		is_git_auth = github_sync.is_git_auth()
		session['ip_address'] = str(web.ctx['ip'])
		user = session['username']
		logged_in = True if user != 'anonymous' else False
		block_user, limit = u.check_ip(str(web.ctx['ip']), str(datetime.datetime.now()) )
		f = forms.get_form(conf.myform)

		return render.record(record_form=f, pageID=name, user=user,
							alert=block_user, limit=limit,
							is_git_auth=is_git_auth,invalid=False,
							project=conf.myProject)

	def POST(self, name):
		""" Submit a new record

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""

		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		is_git_auth = github_sync.is_git_auth()
		f = forms.get_form(conf.myform)
		user = session['username']
		session['ip_address'] = str(web.ctx['ip'])
		u.write_ip(str(datetime.datetime.now()), str(web.ctx['ip']), 'POST')
		block_user, limit = u.check_ip(str(web.ctx['ip']), str(datetime.datetime.now()) )

		# form validation
		if not f.validates():
			u.log_output('SUBMIT INVALID FORM', session['logged_in'], session['username'],name)
			return render.record(record_form=f, pageID=name, user=user, alert=block_user,
								limit=limit, is_git_auth=is_git_auth,invalid=True,
								project=conf.myProject)
		else:
			recordData = web.input()
			if 'action' in recordData:
				create_record(recordData)

			recordID = recordData.recordID if 'recordID' in recordData else None
			u.log_output('CREATED RECORD', session['logged_in'], session['username'],recordID)

			if recordID:
				userID = user.replace('@','-at-').replace('.','-dot-')
				file_path = mapping.inputToRDF(recordData, userID, 'not modified')
				if conf.github_backup == "True":
					try:
						github_sync.push(file_path,"main", session['gituser'], session['username'], session['bearer_token'])
					except Exception as e:
						print(e)
				whereto = prefixLocal+'/' if user == 'anonymous' else prefixLocal+'welcome-1'
				raise web.seeother(whereto)
			else:
				create_record(data)

# FORM: modify a record (only logged in users)

class Modify(object):
	def GET(self, name):
		""" Modify an existing record

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""

		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		is_git_auth = github_sync.is_git_auth()
		session['ip_address'] = str(web.ctx['ip'])
		session_data['logged_in'] = 'True' if (session['username'] != 'anonymous') or \
							(conf.gitClientID == '' and session['username'] == 'anonymous') else 'False'

		if (session['username'] != 'anonymous') or \
			(conf.gitClientID == '' and session['username'] == 'anonymous'):
			graphToRebuild = conf.base+name+'/'
			recordID = name
			data = queries.getData(graphToRebuild)
			u.log_output('START MODIFY RECORD', session['logged_in'], session['username'], recordID )
			f = forms.get_form(conf.myform)
			ids_dropdown = u.get_dropdowns(fields)
			return render.modify(graphdata=data, pageID=recordID, record_form=f,
							user=session['username'],ids_dropdown=ids_dropdown,
							is_git_auth=is_git_auth,invalid=False,
							project=conf.myProject)
		else:
			session['logged_in'] = 'False'
			raise web.seeother(prefixLocal+'/')

	def POST(self, name):
		""" Modify an existing record

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""

		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		recordData = web.input()
		session['ip_address'] = str(web.ctx['ip'])
		is_git_auth = github_sync.is_git_auth()
		f = forms.get_form(conf.myform)

		if 'action' in recordData:
			create_record(recordData)
		else:
			if not f.validates():
				graphToRebuild = conf.base+name+'/'
				recordID = name
				data = queries.getData(graphToRebuild)
				u.log_output('INVALID MODIFY RECORD', session['logged_in'], session['username'], recordID )
				f = forms.get_form(conf.myform)
				ids_dropdown = u.get_dropdowns(fields)
				return render.modify(graphdata=data, pageID=recordID, record_form=f,
								user=session['username'],ids_dropdown=ids_dropdown,
								is_git_auth=is_git_auth,invalid=True,
								project=conf.myProject)
			else:
				recordID = recordData.recordID
				userID = session['username'].replace('@','-at-').replace('.','-dot-')
				graphToClear = conf.base+name+'/'
				file_path = mapping.inputToRDF(recordData, userID, 'modified', graphToClear)
				if conf.github_backup == "True":
					try:
						github_sync.push(file_path,"main", session['gituser'],
									session['username'], session['bearer_token'], '(modified)')
					except Exception as e:
						print(e)
				u.log_output('MODIFIED RECORD', session['logged_in'], session['username'], recordID )
				raise web.seeother(prefixLocal+'welcome-1')

# FORM: review a record for publication (only logged in users)

class Review(object):
	def GET(self, name):
		""" Review and publish an existing record

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""

		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		is_git_auth = github_sync.is_git_auth()
		session_data['logged_in'] = 'True' if (session['username'] != 'anonymous') or \
							(conf.gitClientID == '' and session['username'] == 'anonymous') else 'False'

		# anonymous or authenticated user
		if (session['username'] != 'anonymous') or \
			(conf.gitClientID == '' and session['username'] == 'anonymous'):
			graphToRebuild = conf.base+name+'/'
			recordID = name
			data = queries.getData(graphToRebuild)
			session['ip_address'] = str(web.ctx['ip'])
			u.log_output('START REVIEW RECORD', session['logged_in'], session['username'], recordID )
			f = forms.get_form(conf.myform)
			ids_dropdown = u.get_dropdowns(fields)
			return render.review(graphdata=data, pageID=recordID, record_form=f,
								graph=graphToRebuild, user=session['username'],
								ids_dropdown=ids_dropdown,is_git_auth=is_git_auth,
								invalid=False,project=conf.myProject)
		else:
			session['logged_in'] = 'False'
			raise web.seeother(prefixLocal+'/')

	def POST(self, name):
		""" Review and publish an existing record

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""

		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		actions = web.input()
		session['ip_address'] = str(web.ctx['ip'])
		f = forms.get_form(conf.myform)

		# save the new record for future publication
		if actions.action.startswith('save'):
			if not f.validates():
				graphToRebuild = conf.base+name+'/'
				recordID = name
				data = queries.getData(graphToRebuild)
				session['ip_address'] = str(web.ctx['ip'])
				u.log_output('INVALID REVIEW RECORD', session['logged_in'], session['username'], recordID )
				f = forms.get_form(conf.myform)
				ids_dropdown = u.get_dropdowns(fields)
				return render.review(graphdata=data, pageID=recordID, record_form=f,
									graph=graphToRebuild, user=session['username'],
									ids_dropdown=ids_dropdown,is_git_auth=is_git_auth,
									invalid=True,project=conf.myProject)
			else:
				recordData = web.input()
				recordID = recordData.recordID
				userID = session['username'].replace('@','-at-').replace('.','-dot-')
				graphToClear = conf.base+name+'/'
				file_path = mapping.inputToRDF(recordData, userID, 'modified',graphToClear)
				if conf.github_backup == "True":
					try:
						github_sync.push(file_path,"main", session['gituser'],
									session['username'], session['bearer_token'], '(reviewed)')
					except Exception as e:
						print(e)
				u.log_output('REVIEWED (NOT PUBLISHED) RECORD', session['logged_in'], session['username'], recordID )
				raise web.seeother(prefixLocal+'welcome-1')

		# publish the record
		elif actions.action.startswith('publish'):
			if not f.validates():
				graphToRebuild = conf.base+name+'/'
				recordID = name
				data = queries.getData(graphToRebuild)
				session['ip_address'] = str(web.ctx['ip'])
				u.log_output('INVALID REVIEW RECORD', session['logged_in'], session['username'], recordID )
				f = forms.get_form(conf.myform)
				ids_dropdown = u.get_dropdowns(fields)
				return render.review(graphdata=data, pageID=recordID, record_form=f,
									graph=graphToRebuild, user=session['username'],
									ids_dropdown=ids_dropdown,is_git_auth=is_git_auth,
									invalid=True,project=conf.myProject)
			else:
				recordData = web.input()
				userID = session['username'].replace('@','-at-').replace('.','-dot-')
				graphToClear = conf.base+name+'/'
				file_path= mapping.inputToRDF(recordData, userID, 'published',graphToClear)
				if conf.github_backup == "True":
					try:
						github_sync.push(file_path,"main", session['gituser'],
								session['username'], session['bearer_token'], '(published)')
					except Exception as e:
						print(e)

				# send a request to wayback machine
				savetheweb = recordData['res_homepage'].strip() if "res_homepage" in recordData \
					and recordData['res_homepage'] != '' else None
				if savetheweb:
					resp = requests.get("http://web.archive.org/save/"+requests.utils.quote(savetheweb),
							headers={"Content-Type": "application/x-www-form-urlencoded"} )
					
				u.log_output('PUBLISHED RECORD', session['logged_in'], session['username'], name )
				raise web.seeother(prefixLocal+'welcome-1')

		# login or create new record
		else:
			create_record(actions)

# FORM: view documentation

class Documentation:
	def GET(self):
		""" Editorial guidelines"""
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		is_git_auth = github_sync.is_git_auth()
		return render.documentation(user=session['username'],
									is_git_auth=is_git_auth,project=conf.myProject)

	def POST(self):
		""" Editorial guidelines"""

		data = web.input()
		if 'action' in data:
			create_record(data)

# VIEW : lists of types of records of the catalogue

class Records:
	def GET(self):
		""" EXPLORE page """
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		#threading.Thread(target=u.fileWatcher).start()
		is_git_auth = github_sync.is_git_auth()
		records = queries.getRecords()
		alll = queries.countAll()
		filtersBrowse = queries.getBrowsingFilters()

		return render.records(user=session['username'], data=records,
							title='Latest resources', r_base=conf.base,
							alll=alll, filters=filtersBrowse,is_git_auth=is_git_auth,
							project=conf.myProject)

	def POST(self):
		""" EXPLORE page """

		data = web.input()
		if 'action' in data:
			create_record(data)

# VIEW : single record

class View(object):
	def GET(self, name):
		""" Record web page

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		is_git_auth = github_sync.is_git_auth()
		base = conf.base
		record = base+name
		data = dict(queries.getData(record+'/'))
		stage = data['stage'][0]

		try:
			title = [data[k][0] for k,v in data.items() \
				for field in fields if (field['disambiguate'] == "True" \
				and k == field['id'])][0]
		except Exception as e:
			title = "No title"

		data_labels = { field['label']:v for k,v in data.items() \
						for field in fields if k == field['id']}
		properties = {field["label"]:field["property"] for field in fields}
		return render.view(user=session['username'], graphdata=data_labels,
						graphID=name, title=title, stage=stage, base=base,properties=properties,
						is_git_auth=is_git_auth,project=conf.myProject)

	def POST(self,name):
		""" Record web page

		Parameters
		----------
		name: str
			the record ID (a timestamp)
		"""

		data = web.input()
		if 'action' in data:
			create_record(data)

# TERM : vocabulary terms and newly created entities

class Term(object):
	def GET(self, name):
		""" controlled vocabulary term web page

		Parameters
		----------
		name: str
			the ID of the term, generally the last part of the URL
		"""
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		data = queries.describeTerm(name)
		is_git_auth = github_sync.is_git_auth()

		count = len([ result["subject"]["value"] \
					for result in data["results"]["bindings"] \
					if (name in result["object"]["value"] and result["object"]["type"] == 'uri') ])

		return render.term(user=session['username'], data=data, count=count,
						is_git_auth=is_git_auth,project=conf.myProject,base=conf.base,name=name)

	def POST(self,name):
		""" controlled vocabulary term web page

		Parameters
		----------
		name: str
			the ID of the term, generally the last part of the URL
		"""

		data = web.input()
		if 'action' in data:
			create_record(data)

# DATA MODEL

class DataModel:
	def GET(self):
		""" Data model page """

		is_git_auth = github_sync.is_git_auth()
		res_class = conf.main_entity # get main class from conf py
		res_class_label = u.get_LOV_labels(res_class,'class')
		props_labels = [ u.get_LOV_labels(field["property"],'property') for field in fields]
		return render.datamodel(user=session['username'], data=props_labels,
								res_class=res_class_label,is_git_auth=is_git_auth,
								project=conf.myProject)

	def POST(self):
		""" Data model page """

		data = web.input()
		if 'action' in data:
			create_record(data)

# QUERY: endpoint GUI

class sparql:
	def GET(self, active):
		""" SPARQL endpoint GUI and request handler

		Parameters
		----------
		active: str
			Query string or None
			If None, renders the GUI, else parse the query (__run_query_string)
			If the query string includes an update, return error, else sends
			the query to the endpoint (__contact_tp)
		"""
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		u.log_output("SPARQL:GET", session['logged_in'], session['username'])
		content_type = web.ctx.env.get('CONTENT_TYPE')
		return self.__run_query_string(active, web.ctx.env.get("QUERY_STRING"), content_type)

	def POST(self, active):
		""" SPARQL endpoint GUI and request handler

		Parameters
		----------
		active: str
			Query string or None
			If None, renders the GUI, else parse the query (__run_query_string)
			If the query string includes an update, return error, else sends
			the query to the endpoint (__contact_tp)
		"""

		u.log_output("SPARQL:POST", session['logged_in'], session['username'])
		content_type = web.ctx.env.get('CONTENT_TYPE')
		web.debug("The content_type value: ")
		web.debug(content_type)

		data = web.input()
		if 'action' in data:
			create_record(data)

		cur_data = web.data()
		if "application/x-www-form-urlencoded" in content_type:
			return self.__run_query_string(active, cur_data, True, content_type)
		elif "application/sparql-query" in content_type:
			return self.__contact_tp(cur_data, True, content_type)
		else:
			raise web.redirect(prefixLocal+"sparql")

	def __contact_tp(self, data, is_post, content_type):
		accept = web.ctx.env.get('HTTP_ACCEPT')
		if accept is None or accept == "*/*" or accept == "":
			accept = "application/sparql-results+xml"
		if is_post: # CHANGE
			req = requests.post(conf.myEndpoint, data=data,
								headers={'content-type': content_type, "accept": accept})
		else: # CHANGE
			req = requests.get("%s?%s" % (conf.myEndpoint, data),
							   headers={'content-type': content_type, "accept": accept})


		if req.status_code == 200:
			web.header('Access-Control-Allow-Origin', '*')
			web.header('Access-Control-Allow-Credentials', 'true')
			web.header('Content-Type', req.headers["content-type"])
			return req.text
		else:
			raise web.HTTPError(
				str(req.status_code), {"Content-Type": req.headers["content-type"]}, req.text)

	def __run_query_string(self, active, query_string, is_post=False,
						   content_type="application/x-www-form-urlencoded"):

		try:
			query_str_decoded = query_string.decode('utf-8')
		except Exception as e:
			query_str_decoded = query_string

		parsed_query = parse_qs(query_str_decoded)

		if query_str_decoded is None or query_str_decoded.strip() == "":
			is_git_auth = github_sync.is_git_auth()
			return render.sparql(active, user=session['username'],
								is_git_auth=is_git_auth,project=conf.myProject)

		if re.search("updates?", query_str_decoded, re.IGNORECASE) is None:
			if "query" in parsed_query:
				return self.__contact_tp(query_string, is_post, content_type)
			else:
				raise web.redirect(conf.myPublicEndpoint)
		else:
			raise web.HTTPError(
				"403", {"Content-Type": "text/plain"}, "SPARQL Update queries are not permitted.")


if __name__ == "__main__":
	app.run()
