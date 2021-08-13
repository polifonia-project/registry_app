# -*- coding: utf-8 -*-
import conf , os , operator , pprint , ssl , rdflib , json
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import defaultdict
from rdflib import URIRef , XSD, Namespace , Literal
from rdflib.namespace import OWL, DC , DCTERMS, RDF , RDFS
from rdflib.plugins.sparql import prepareQuery
from pymantic import sparql

ssl._create_default_https_context = ssl._create_unverified_context
server = sparql.SPARQLServer(conf.myEndpoint)
dir_path = os.path.dirname(os.path.realpath(__file__))

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
		else str((conf.pagination*newpage))
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
		LIMIT """+str(conf.pagination)+"""
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

with open(conf.myform) as config_form:
	fields = json.load(config_form)

patterns = [ 'OPTIONAL {?subject <'+field['property']+'> ?'+field['id']+'.}. ' if field['value'] == 'Literal' else 'OPTIONAL {?subject <'+field['property']+'> ?'+field['id']+'. ?'+field['id']+' rdfs:label ?'+field['id']+'_label .} .' for field in fields]
patterns_string = ''.join(patterns)

# REBUILD GRAPH TO MODIFY/REVIEW RECORD

def getData(graph):
	""" get a named graph and rebuild results for modifying the record"""
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

	data = defaultdict(list)
	for result in results["results"]["bindings"]:
		result.pop('subject',None)
		result.pop('graph_title',None)
		for k,v in result.items():
			if '_label' not in k and v['type'] == 'literal': # string values
				if v['value'] not in data[k]:
					data[k].append(v['value'])
			elif v['type'] == 'uri': # uri values
				uri = v['value'].rsplit('/', 1)[-1]
				label = [value['value'] for key,value in result.items() if key == k+'_label'][0]
				data[k].append([uri,label])
	#print("############ data",data)
	return data


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
