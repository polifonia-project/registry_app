# -*- coding: utf-8 -*-

# data
myEndpoint = 'http://127.0.0.1:3000/blazegraph/sparql'
myPublicEndpoint = 'http://data.open.ac.uk/sparql'
wikidataEndpoint = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
base = 'http://data.open.ac.uk/musow/'
name = 'musow' # last bit of base
myform = 'myform.json'
main_entity = "https://schema.org/CreativeWork"

# backend
log_file = 'ip_logs.log' # log file with IP addresses of POST requests
limit_requests = 50 # max number of records per IP address/day
pagination = 4 # results per page in backend

# github
github_backup = True # change to False and ignore the token field if you don't want data backup on github
token = 'ghp_eL1OfbEnqPC******************' # github access token
# owner = "polifonia-project" # polifonia-project
# repo_name = "registry" # registry
owner = "marilenadaquino"
repo_name = "crowdsourcing"
author = "marilenadaquino" # default author of commits
author_email = "marilena.daquino2@unibo.it" # default author of commits
# github authentication
gitClientID = "09f******************" # create a OAuth app if you want to enable github authentication
gitClientSecret = "47c1e0******************"
