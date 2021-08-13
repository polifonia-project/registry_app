# -*- coding: utf-8 -*-
import os
import json
import datetime
import time
import sys
import re
import logging
import cgi
from urllib.parse import parse_qs
import requests
import web
from web import form
import forms, mapping, conf, queries , vocabs , allowed


web.config.debug = False
wikidir = os.path.realpath('records/') # RDF dump of records

# ROUTING

prefix = ''
#prefixLocal = '/musow/'
prefixLocal = ''
urls = (
	prefix + '/', 'Login',
	prefix + '/logout', 'Logout',
	prefix + '/welcome-(.+)','Index',
	prefix + '/record-(.+)', 'Record',
	prefix + '/modify-(.+)', 'Modify',
	prefix + '/review-(.+)', 'Review',
	prefix + '/documentation', 'Documentation',
	prefix + '/records', 'Records',
	prefix + '/view-(.+)', 'View',
	prefix + '/(sparql)','sparql'
)

app = web.application(urls, globals())

# SESSIONS

if web.config.get('_session') is None:
	store = web.session.DiskStore('sessions')
	session = web.session.Session(app, store, initializer={'logged_in': 'False', 'username': 'anonymous', 'password': 'None', 'ip_address': 'None'})
	web.config._session = session
	session_data = session._initializer
else:
	session = web.config._session
	session_data = session._initializer

# USERS: TODO Hash passwords, usernames must be emails

allowed = allowed.allowed()

def get_timestamp():
	return str(time.time()).replace('.','-')

# TEMPLATING

render = web.template.render('templates/', base="layout", cache=False, globals={'session':session, 'time_now':get_timestamp, 'isinstance':isinstance,'str':str})
render2 = web.template.render('templates/', globals={'session':session})
render_no_login = web.template.render('templates/', base="layout_no_login", globals={'session':session, 'time_now':get_timestamp})

# LOGS

def log_output(action, logged_in, user, recordID=None):
	""" log information in console """
	message = '*** '+str(datetime.datetime.now())+' | '+action
	if recordID:
		message += ': <'+recordID+'>'
	message += ' | LOGGED IN: '+str(logged_in)+' | USER: '+user
	print(message)

# LOAD FORM

with open(conf.myform) as config_form:
	fields = json.load(config_form)

# IMPORT VOCABS

vocabs.import_vocabs(fields)

def get_dropdowns(fields):
	ids_dropdown= [field['id'] for field in fields if field['type'] == 'Dropdown']
	return ids_dropdown

# ERROR HANDLER

def notfound():
    return web.notfound(render.notfound(user=session['username']))

def internalerror():
    return web.internalerror(render.internalerror(user=session['username']))

# UTILS

def key(s):
	fmt = "%Y-%m-%dT%H:%M:%S"
	return datetime.datetime.strptime(s, fmt)

class Notfound:
    def GET(self):
        raise web.notfound()

# LIMIT REQUESTS BY IP ADDRESSES

def write_ip(timestamp, ip_add, request):
	logs = open(conf.log_file, 'a')
	logs.write( str(timestamp)+' --- '+ ip_add + ' --- '+ request+'\n')
	logs.close()

def check_ip(ip_add, current_time):
	" limit user POST requests to XX a day"
	is_user_blocked = False
	limit = conf.limit_requests
	today = current_time.split()[0]
	data = open(conf.log_file, 'r').readlines()
	user_requests = [(line.split(' --- ')[0].split()[0], line.split(' --- ')[1]) for line in data if ip_add in line.split(' --- ')[1] and line.split(' --- ')[0].split()[0] == today ]
	if len(user_requests) > limit:
		is_user_blocked = True
	return is_user_blocked, limit

# LOGIN / LOGOUT

def login_or_create(data,allowed):
	if data:
		login = data.login if data and 'login' in data else None
		passwd = data.passwd if data and 'passwd' in data else None
		session['ip_address'] = str(web.ctx['ip'])
		if (login,passwd) in allowed:
			session['logged_in'] = True
			session['username'] = login
			session['password'] = passwd
			log_output('LOGIN CORRECT', session['logged_in'], session['username'])
			raise web.seeother(prefixLocal+'welcome-1')
		elif login and passwd and (login,passwd) not in allowed:
			log_output('LOGIN WRONG ATTEMPT', session['logged_in'], session['username'])
			raise web.seeother(prefixLocal+'/')
		elif 'action' in data and data.action.startswith('createRecord'):
			record = data.action.split("createRecord",1)[1]
			log_output('START NEW RECORD', session['logged_in'], session['username'])
			raise web.seeother(prefixLocal+'record-'+record)
		else:
			log_output('ELSE', session['logged_in'], session['username'])
			raise web.seeother(prefixLocal+'/')
	else:
		print("what??")

class Login:
	def GET(self):
		if(session.username,session.password) in allowed:
			session.logged_in = True
			log_output('HOMEPAGE LOGGED IN', session['logged_in'], session['username'])
			raise web.seeother(prefixLocal+'welcome-1')
		else:
			log_output('HOMEPAGE ANONYMOUS', session['logged_in'], session['username'])
			return render.login(user='anonymous')

	def POST(self):
		data = web.input()
		login_or_create(data,allowed)


class Logout:
	def GET(self):
		log_output('LOGOUT', session['logged_in'], session['username'])
		session['logged_in'] = 'False'
		session['username'] = 'anonymous'
		session['ip_address'] = str(web.ctx['ip'])
		raise web.seeother(prefixLocal+'/')

	def POST(self):
		data = web.input()
		login_or_create(data,allowed)

# BACKEND Index: show list or records (only logged users)

class Index:
	def GET(self, page):
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		session['ip_address'] = str(web.ctx['ip'])
		filterRecords = ''
		if (session['username'],session['password']) in allowed:
			session['logged_in'] = 'True'
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			# countings
			alll = queries.countAll()
			all, notreviewed, underreview, published = queries.getCountings()
			results = queries.getRecordsPagination(page)
			records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))
			log_output('WELCOME PAGE', session['logged_in'], session['username'])

			return render.index(
				wikilist=records,
				user=session['username'],
				varIDpage=str(time.time()).replace('.','-'),
				alll=alll,
				all=all,
				notreviewed=notreviewed,
				underreview=underreview,
				published=published,
				page=page,
				pagination=conf.pagination,
				filter=filterRecords,
				filterName = 'filterAll'
				)
		else:
			session['logged_in'] = 'False'
			log_output('WELCOME PAGE NOT LOGGED IN', session['logged_in'], session['username'])
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
			filterRecords = filterRecords if filterRecords != 'none' else ''
			filterName = actions.action
			page = 1
			results = queries.getRecordsPagination(page, filterRecords)
			records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))
			alll = queries.countAll()
			all, notreviewed, underreview, published = queries.getCountings(filterRecords)
			filterRecords = filterRecords if filterRecords != '' else 'none'
			return render.index(
				wikilist=records,
				user=session['username'],
				varIDpage=str(time.time()).replace('.','-'),
				alll=alll,
				all=all,
				notreviewed=notreviewed,
				underreview=underreview,
				published=published,
				page=page,
				pagination=conf.pagination,
				filter= filterRecords,
				filterName = filterName
				)
		# create a new record (logged users)

		elif actions.action.startswith('createRecord'):
			record = actions.action.split("createRecord",1)[1]
			log_output('START NEW RECORD (LOGGED IN)', session['logged_in'], session['username'], actions.action.split("createRecord",1)[1] )
			raise web.seeother(prefixLocal+'record-'+record)

		# delete a record (but not the dump in /records folder)
		elif actions.action.startswith('deleteRecord'):
			graph = actions.action.split("deleteRecord",1)[1].split(' __')[0]
			filterRecords = actions.action.split('deleteRecord',1)[1].split(' __')[1]
			queries.deleteRecord(graph)
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			log_output('DELETE RECORD', session['logged_in'], session['username'], graph )
			if filterRecords == 'none':
				raise web.seeother(prefixLocal+'welcome-'+page)
			else:
				filterName = [k for k,v in filter_values.items() if v == filterRecords][0]
				results = queries.getRecordsPagination(page,filterRecords)
				records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))
				alll = queries.countAll()
				all, notreviewed, underreview, published = queries.getCountings(filterRecords)
				return render.index(
					wikilist=records,
					user=session['username'],
					varIDpage=str(time.time()).replace('.','-'),
					alll=alll,
					all=all,
					notreviewed=notreviewed,
					underreview=underreview,
					published=published,
					page=page,
					pagination=conf.pagination,
					filter= filterRecords,
					filterName = filterName
					)

		# modify a record
		elif actions.action.startswith('modify'):
			record = actions.action.split(conf.name,1)[1].replace('/','')
			log_output('MODIFY RECORD', session['logged_in'], session['username'], record )
			raise web.seeother(prefixLocal+'modify-'+record)

		# start review of a record
		elif actions.action.startswith('review'):
			record = actions.action.split(conf.name,1)[1].replace('/','')
			log_output('REVIEW RECORD', session['logged_in'], session['username'], record )
			raise web.seeother(prefixLocal+'review-'+record)

		# change page
		elif actions.action.startswith('changepage'):
			pag = actions.action.split('changepage-',1)[1].split(' __')[0]
			filterRecords = actions.action.split('changepage-',1)[1].split(' __')[1]
			if filterRecords == 'none':
				raise web.seeother(prefixLocal+'welcome-'+pag)
			else:
				filterName = [k for k,v in filter_values.items() if v == filterRecords][0]
				results = queries.getRecordsPagination(pag, filterRecords)
				records = reversed(sorted(results, key=lambda tup: key(tup[4][:-5]) ))
				alll = queries.countAll()
				all, notreviewed, underreview, published = queries.getCountings(filterRecords)
				return render.index(
					wikilist=records,
					user=session['username'],
					varIDpage=str(time.time()).replace('.','-'),
					alll=alll,
					all=all,
					notreviewed=notreviewed,
					underreview=underreview,
					published=published,
					page=page,
					pagination=conf.pagination,
					filter= filterRecords,
					filterName = filterName
					)



		# login or create a new record
		else:
			login_or_create(data,allowed)

# FORM: create a new record (both logged in and anonymous users)

class Record(object):
	def GET(self, name):
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

		session['ip_address'] = str(web.ctx['ip'])
		user = session['username'] if (session['username'],session['password']) in allowed else 'anonymous'
		logged_in = True if (session['username'],session['password']) in allowed else False
		log_output('GET RECORD FORM', session['logged_in'], session['username'])
		block_user, limit = check_ip(str(web.ctx['ip']), str(datetime.datetime.now()) )
		f = forms.get_form(conf.myform)
		return render.record(record_form=f, pageID=name, user=user, alert=block_user, limit=limit)

	def POST(self, name):
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		f = forms.get_form(conf.myform)
		user = session['username'] if (session['username'],session['password']) in allowed else 'anonymous'
		session['ip_address'] = str(web.ctx['ip'])
		write_ip(str(datetime.datetime.now()), str(web.ctx['ip']), 'POST')

		if not f.validates():
			log_output('SUBMIT INVALID FORM', session['logged_in'], session['username'],recordID)
			return render.record(record_form=f, pageID=name, user=user)
		else:
			recordData = web.input()
			if 'login' in recordData or 'action' in recordData:
				login_or_create(recordData,allowed)
			recordID = recordData.recordID if 'recordID' in recordData else None
			log_output('CREATED RECORD', session['logged_in'], session['username'],recordID)
			if recordID:
				userID = user.replace('@','-at-').replace('.','-dot-')
				mapping.inputToRDF(recordData, userID, 'not modified')
				if user == 'anonymous':
					raise web.seeother(prefixLocal+'/')
				else:
					raise web.seeother(prefixLocal+'/welcome')
			else:
				login_or_create(data,allowed)

# FORM: modify a  record (only logged in users)

class Modify(object):
	def GET(self, name):
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		session['ip_address'] = str(web.ctx['ip'])
		if (session['username'],session['password']) in allowed:
			session_data['logged_in'] = 'True'
			graphToRebuild = conf.base+name+'/'
			recordID = name
			data = queries.getData(graphToRebuild)
			log_output('START MODIFY RECORD', session['logged_in'], session['username'], recordID )
			f = forms.get_form(conf.myform)
			ids_dropdown = get_dropdowns(fields)
			return render.modify(graphdata=data, pageID=recordID, record_form=f, user=session['username'],ids_dropdown=ids_dropdown) # render the form filled
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

		if 'login' in recordData or 'action' in recordData:
			login_or_create(recordData,allowed)
		else:
			recordID = recordData.recordID
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			graphToClear = conf.base+name+'/'
			mapping.inputToRDF(recordData, userID, 'modified', graphToClear)
			log_output('MODIFIED RECORD', session['logged_in'], session['username'], recordID )
			raise web.seeother(prefixLocal+'welcome-1')

# FORM: review a record for publication (only logged in users)

class Review(object):
	def GET(self, name):
		web.header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		web.header("Content-Type","text/html; charset=utf-8")
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		graphToRebuild = conf.base+name+'/'
		recordID = name
		data = queries.getData(graphToRebuild)
		session['ip_address'] = str(web.ctx['ip'])
		log_output('START REVIEW RECORD', session['logged_in'], session['username'], recordID )
		f = forms.get_form(conf.myform)
		ids_dropdown = get_dropdowns(fields)
		return render.review(graphdata=data, pageID=recordID, record_form=f, graph=graphToRebuild, user=session['username'], ids_dropdown=ids_dropdown) # render the form filled


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
			mapping.inputToRDF(recordData, userID, 'modified',graphToClear)
			log_output('REVIEWED (NOT PUBLISHED) RECORD', session['logged_in'], session['username'], recordID )
			raise web.seeother(prefixLocal+'welcome-1')

		# publish
		elif actions.action.startswith('publish'):
			recordData = web.input()
			userID = session['username'].replace('@','-at-').replace('.','-dot-')
			graphToClear = conf.base+name+'/'
			mapping.inputToRDF(recordData, userID, 'published',graphToClear)
			log_output('PUBLISHED RECORD', session['logged_in'], session['username'], name )
			raise web.seeother(prefixLocal+'welcome-1')

		# login or create new record
		else:
			login_or_create(actions,allowed)
# FORM: view documentation

class Documentation:
	def GET(self):
		return render.documentation(user=session['username'])

	def POST(self):
		actions = web.input()
		login_or_create(actions,allowed)

# VIEW : lists of types of records of the catalogue

class Records:
	def GET(self):
		records = queries.getRecords()
		fh = forms.searchRecord()

		return render.records(form=None, user=session['username'], data=records, title='Latest music resources', r_base=conf.base)

	def POST(self):
		actions = web.input()
		login_or_create(actions,allowed)

# VIEW : single record

class View(object):
	def GET(self, name):
		record = conf.base+name
		data = dict(queries.getData(record+'/'))
		stage = data['stage'][0]
		title = [data[k][0] for k,v in data.items() for field in fields if (field['disambiguate'] == "True" and k == field['id'])][0]
		data_labels = { field['label']:v for k,v in data.items() for field in fields if k == field['id']}
		return render.view(user=session['username'], graphdata=data_labels, graphID=name, title=title, stage=stage)

	def POST(self,name):
		actions = web.input()

		login_or_create(actions,allowed)

# QUERY: endpoint GUI

class sparql:
    def GET(self, active):
        content_type = web.ctx.env.get('CONTENT_TYPE')
        return self.__run_query_string(active, web.ctx.env.get("QUERY_STRING"), content_type)

    def POST(self, active):
        content_type = web.ctx.env.get('CONTENT_TYPE')
        web.debug("The content_type value: ")
        web.debug(content_type)

        cur_data = web.data()
        if "application/x-www-form-urlencoded" in content_type:
            print ("QUERY TO ENDPOINT:", cur_data)
            return self.__run_query_string(active, cur_data, True, content_type)
        elif "application/sparql-query" in content_type:
            print("QUERY TO ENDPOINT:", cur_data)
            return self.__contact_tp(cur_data, True, content_type)
        else:
            raise web.redirect("/sparql")

    def __contact_tp(self, data, is_post, content_type):
        accept = web.ctx.env.get('HTTP_ACCEPT')
        if accept is None or accept == "*/*" or accept == "":
            accept = "application/sparql-results+xml"
        if is_post: # CHANGE
            req = requests.post('http://artchives.fondazionezeri.unibo.it:3000/sparql', data=data,
                                headers={'content-type': content_type, "accept": accept})
        else: # CHANGE
            req = requests.get("%s?%s" % ('http://artchives.fondazionezeri.unibo.it:3000/sparql', data),
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
        parsed_query = parse_qs(query_string)
        if query_string is None or query_string.strip() == "":
            return render2.sparql(active, user='anonymous')
        if re.search("updates?", query_string, re.IGNORECASE) is None:
            if "query" in parsed_query:
                return self.__contact_tp(query_string, is_post, content_type)
            else:
                raise web.redirect(conf.myPublicEndpoint)
        else:
            raise web.HTTPError(
                "403", {"Content-Type": "text/plain"}, "SPARQL Update queries are not permitted.")





app.notfound = notfound
app.internalerror = internalerror

if __name__ == "__main__":
	app.run()
