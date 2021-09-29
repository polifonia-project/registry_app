# -*- coding: utf-8 -*-
import conf , os , operator , pprint , ssl , rdflib , json
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import defaultdict
from rdflib import URIRef , XSD, Namespace , Literal
from rdflib.namespace import OWL, DC , DCTERMS, RDF , RDFS
from rdflib.plugins.sparql import prepareQuery
from pymantic import sparql
import utils as u

u.reload_config()

ssl._create_default_https_context = ssl._create_unverified_context
server = sparql.SPARQLServer(conf.myEndpoint)
dir_path = os.path.dirname(os.path.realpath(__file__))

def hello_blazegraph(q):
	sparql = SPARQLWrapper(conf.myEndpoint)
	sparql.setQuery(q)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()
	return results


# LIST OF RECORDS IN THE BACKEND

queryRecords = """
	PREFIX prov: <http://www.w3.org/ns/prov#>
	PREFIX base: <"""+conf.base+""">
	SELECT DISTINCT ?g ?title ?userLabel ?modifierLabel ?date ?stage
	WHERE
	{ GRAPH ?g {
		?s ?p ?o .

		OPTIONAL { ?g rdfs:label ?title; prov:wasGeneratedBy ?user; prov:generatedAtTime ?date ; base:publicationStage ?stage. ?user rdfs:label ?userLabel .
			OPTIONAL {?g prov:wasInfluencedBy ?modifier. ?modifier rdfs:label ?modifierLabel .} }
		OPTIONAL {?g rdfs:label ?title; prov:generatedAtTime ?date ; base:publicationStage ?stage . }

		BIND(COALESCE(?date, '-') AS ?date ).
		BIND(COALESCE(?stage, '-') AS ?stage ).
		BIND(COALESCE(?userLabel, '-') AS ?userLabel ).
		BIND(COALESCE(?modifierLabel, '-') AS ?modifierLabel ).
		BIND(COALESCE(?title, 'none', '-') AS ?title ).
		filter not exists {
		  ?g prov:generatedAtTime ?date2
		  filter (?date2 > ?date)
		}

	  }
	  FILTER( str(?g) != '"""+conf.base+"""vocabularies/' )
	}
	"""



def getRecords():
	""" get all the records created by users to list them in the backend welcome page """
	records = set()
	sparql = SPARQLWrapper(conf.myEndpoint)
	sparql.setQuery(queryRecords)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	for result in results["results"]["bindings"]:
		records.add( (result["g"]["value"], result["title"]["value"], result["userLabel"]["value"], result["modifierLabel"]["value"], result["date"]["value"], result["stage"]["value"] ))
	return records


def getRecordsPagination(page, filterRecords=''):
	""" get all the records created by users to list them in the backend welcome page """
	newpage = int(page)-1
	offset = str(0) if int(page) == 1 \
		else str(( int(conf.pagination) *newpage))
	queryRecordsPagination = """
		PREFIX prov: <http://www.w3.org/ns/prov#>
		PREFIX base: <"""+conf.base+""">
		SELECT DISTINCT ?g ?title ?userLabel ?modifierLabel ?date ?stage
		WHERE
		{ GRAPH ?g {
			?s ?p ?o .

			OPTIONAL { ?g rdfs:label ?title; prov:wasGeneratedBy ?user; prov:generatedAtTime ?date ; base:publicationStage ?stage. ?user rdfs:label ?userLabel .
				OPTIONAL {?g prov:wasInfluencedBy ?modifier. ?modifier rdfs:label ?modifierLabel .} }
			OPTIONAL {?g rdfs:label ?title; prov:generatedAtTime ?date ; base:publicationStage ?stage . }

			BIND(COALESCE(?date, '-') AS ?date ).
			BIND(COALESCE(?stage, '-') AS ?stage ).
			BIND(COALESCE(?userLabel, '-') AS ?userLabel ).
			BIND(COALESCE(?modifierLabel, '-') AS ?modifierLabel ).
			BIND(COALESCE(?title, 'none', '-') AS ?title ).
			filter not exists {
			  ?g prov:generatedAtTime ?date2
			  filter (?date2 > ?date)
			}

		  }
		  """+filterRecords+"""
		  FILTER( str(?g) != '"""+conf.base+"""vocabularies/' )

		}
		ORDER BY DESC(?date)
		LIMIT """+conf.pagination+"""
		OFFSET  """+offset+"""
		"""
	print("filterRecords",filterRecords)
	records = set()
	sparql = SPARQLWrapper(conf.myEndpoint)
	sparql.setQuery(queryRecordsPagination)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()
	for result in results["results"]["bindings"]:
		records.add( (result["g"]["value"], result["title"]["value"], result["userLabel"]["value"], result["modifierLabel"]["value"], result["date"]["value"], result["stage"]["value"] ))
	return records


def getCountings(filterRecords=''):
	countRecords = """
		PREFIX prov: <http://www.w3.org/ns/prov#>
		PREFIX base: <"""+conf.base+""">
		SELECT (COUNT(DISTINCT ?g) AS ?count) ?stage
		WHERE
		{ GRAPH ?g { ?s ?p ?o .
			?g base:publicationStage ?stage .
			"""+filterRecords+"""
			}
			FILTER( str(?g) != '"""+conf.base+"""vocabularies/' ) .

		}
		GROUP BY ?stage
		"""
	sparql = SPARQLWrapper(conf.myEndpoint)
	sparql.setQuery(countRecords)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()
	all, notreviewed, underreview, published = 0,0,0,0
	for result in results["results"]["bindings"]:
		notreviewed = int(result["count"]["value"]) if result["stage"]["value"] == "not modified" else notreviewed
		underreview = int(result["count"]["value"]) if result["stage"]["value"] == "modified" else underreview
		published = int(result["count"]["value"]) if result["stage"]["value"] == "published" else published
		all = notreviewed + underreview + published
	return all, notreviewed, underreview, published


def countAll():
	countall = """
		PREFIX prov: <http://www.w3.org/ns/prov#>
		PREFIX base: <"""+conf.base+""">
		SELECT (COUNT(DISTINCT ?g) AS ?count)
		WHERE
		{ GRAPH ?g { ?s ?p ?o .}
			FILTER( str(?g) != '"""+conf.base+"""vocabularies/' ) .
		}
		"""
	sparql = SPARQLWrapper(conf.myEndpoint)
	sparql.setQuery(countall)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()
	alll = results["results"]["bindings"][0]['count']['value']
	return alll


def getRecordCreator(graph_name):
	""" get the label of the creator of a record """
	creatorIRI, creatorLabel = None, None
	queryRecordCreator = """
		PREFIX prov: <http://www.w3.org/ns/prov#>
		SELECT DISTINCT ?creatorIRI ?creatorLabel
		WHERE { <"""+graph_name+"""> prov:wasGeneratedBy ?creatorIRI .
		?creatorIRI rdfs:label ?creatorLabel . }"""

	sparql = SPARQLWrapper(conf.myEndpoint)
	sparql.setQuery(queryRecordCreator)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()
	for result in results["results"]["bindings"]:
		creatorIRI, creatorLabel = result["creatorIRI"]["value"],result["creatorLabel"]["value"]
	return creatorIRI, creatorLabel


# TRIPLE PATTERNS FROM THE FORM



# REBUILD GRAPH TO MODIFY/REVIEW RECORD

def getData(graph):
	""" get a named graph and rebuild results for modifying the record"""
	with open(conf.myform) as config_form:
		fields = json.load(config_form)

	patterns = [ 'OPTIONAL {?subject <'+field['property']+'> ?'+field['id']+'.}. ' if field['value'] == 'Literal' else 'OPTIONAL {?subject <'+field['property']+'> ?'+field['id']+'. ?'+field['id']+' rdfs:label ?'+field['id']+'_label .} .' for field in fields]
	patterns_string = ''.join(patterns)

	queryNGraph = '''
		PREFIX base: <'''+conf.base+'''>
		PREFIX schema: <https://schema.org/>
		SELECT DISTINCT *
		WHERE { <'''+graph+'''> rdfs:label ?graph_title ;
								<'''+conf.base+'''publicationStage> ?stage
				GRAPH <'''+graph+'''>
				{	?subject a <'''+conf.main_entity+'''> .
					'''+patterns_string+'''}
		}
		'''

	sparql = SPARQLWrapper(conf.myEndpoint)
	sparql.setQuery(queryNGraph)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	def compare_sublists(l, lol):
		for sublist in lol:
			temp = [i for i in sublist if i in l]
			if sorted(temp) == sorted(l):
				return True
		return False

	data = defaultdict(list)
	for result in results["results"]["bindings"]:
		result.pop('subject',None)
		result.pop('graph_title',None)
		for k,v in result.items():
			if '_label' not in k and v['type'] == 'literal': # string values
				if v['value'] not in data[k]: # unique values
					data[k].append(v['value'])
			elif v['type'] == 'uri': # uri values
				uri = v['value'].rsplit('/', 1)[-1]
				label = [value['value'] for key,value in result.items() if key == k+'_label'][0]

				if compare_sublists([uri,label], data[k]) == False:
					data[k].append([uri,label])
	print("############ data",data)
	return data


# BROWSE ENTITY (VOCAB TERMS; NEW ENTITIES MENTIONED IN RECORDS)


def describeTerm(name):
	""" ask if the resource exists, then describe it."""
	ask = """ASK { ?s ?p <""" +conf.base+name+ """> .}"""
	results = hello_blazegraph(ask)
	if results["boolean"] == True: # new entity
		describe = """DESCRIBE <"""+conf.base+name+ """>"""
		return hello_blazegraph(describe)
	else: # vocab term
		ask = """ASK { ?s ?p ?o .
				filter( regex( str(?o), '"""+name+"""$' ) )
				}"""
		results = hello_blazegraph(ask)
		if results["boolean"] == True:
			describe = """DESCRIBE ?o
				WHERE { ?s ?p ?o .
				filter( regex( str(?o), '"""+name+"""$' ) ) .
				filter( regex( str(?o), '^"""+conf.base+"""' ) ) . }"""
			print(hello_blazegraph(describe))
			return hello_blazegraph(describe)
		else:
			return None


# EXPLORE METHODS

def getBrowsingFilters():
	with open(conf.myform) as config_form:
		fields = json.load(config_form)
	props = [(f["property"], f["label"], f["type"], f["value"]) for f in fields if "browse" in f and f["browse"] == "True"]
	return props

def getFreqProps():
	""" DO NOT USE THIS
	return ordered list of property / field name / value type
	returns only properties that have at least a value in every record """
	queryProps = '''
		select distinct ?p {
		  { select distinct ?p {
			{ select ?ex { ?ex a '''+conf.base+''' } limit 1 }
			?ex ?p ?o
			}
		  }

		  filter not exists {
			?f a '''+conf.base+''' .
			filter not exists { ?f ?p ?o }
		  }
		}
	'''
	results = hello_blazegraph(queryProps)
	with open(conf.myform) as config_form:
		fields = json.load(config_form)
	for result in results["results"]["bindings"]:
		prop = result["p"]["value"]
		field = [f["label"] for f in fields if f["property"] == prop][0]
		value_type = ['Literal' if f["property"] == prop and f["value"] == 'Literal' \
			else 'URI' if f["property"] == prop and f["value"] == 'URI' and "values" not in f \
			else 'vocabulary'
			for f in fields][0]

# GRAPH methods

def deleteRecord(graph):
	""" delete a named graph and related record """
	if graph:
		clearGraph = ' CLEAR GRAPH <'+graph+'> '
		deleteGraph = ' DROP GRAPH <'+graph+'> '
		sparql = SPARQLWrapper(conf.myEndpoint)
		sparql.setQuery(clearGraph)
		sparql.method = 'POST'
		sparql.query()
		sparql.setQuery(deleteGraph)
		sparql.method = 'POST'
		sparql.query()


def clearGraph(graph):
	if graph:
		clearGraph = ' CLEAR GRAPH <'+graph+'> '
		sparql = SPARQLWrapper(conf.myEndpoint)
		sparql.setQuery(clearGraph)
		sparql.method = 'POST'
		sparql.query()
