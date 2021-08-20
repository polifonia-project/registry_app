# -*- coding: utf-8 -*-
import os
import datetime
import json
import urllib.parse
import web
from web import form
import rdflib
from rdflib import URIRef , XSD, Namespace , Literal
from rdflib.namespace import OWL, DC , DCTERMS, RDF , RDFS
from rdflib.plugins.sparql import prepareQuery
from SPARQLWrapper import SPARQLWrapper, JSON
from pymantic import sparql
import conf , queries

# NAMESPACES
WD = Namespace("http://www.wikidata.org/entity/")
WDP = Namespace("http://www.wikidata.org/wiki/Property:")
OL = Namespace("http://openlibrary.org/works/")
ULAN = Namespace("http://vocab.getty.edu/ulan/")
AAT = Namespace("http://vocab.getty.edu/aat/")
PROV = Namespace("http://www.w3.org/ns/prov#")
# CHANGE remove
SCHEMA = Namespace("https://schema.org/")
base = conf.base

# DATA ENDPOINT AND DIRECTORY
server = sparql.SPARQLServer(conf.myEndpoint)
dir_path = os.path.dirname(os.path.realpath(__file__))

def getValuesFromFields(fieldPrefix, recordData, fields=None):
	""" request form fields by field prefix, check if multiple values are available,
	 returns a set of tuples including ID (for the URI) and label of values """
	results = set()
	for key, value in recordData.items():
		if key.startswith(fieldPrefix+'-'): # multiple values from text box (wikidata)
			values = value.split(',', 1)
			results.add(( values[0], urllib.parse.unquote(values[1]) )) # (id, label)
		elif key == fieldPrefix: # uri from dropdown (single value from controlled vocabulary)
			if fields:
				field = next(field for field in fields if field["id"] == fieldPrefix)
				label = field['values'][value] if 'values' in field else None
				if label:
					results.add(( value, label ))

	return results


def getRightURIbase(value):
	return WD if value.startswith('Q') else '' if value.startswith("http") else base


def inputToRDF(recordData, userID, stage, graphToClear=None):
	""" transform input data into RDF, upload data to the triplestore, dump data locally """

	# MAPPING FORM / PROPERTIES
	with open(conf.myform) as config_form:
		fields = json.load(config_form)

	# CREATE/MODIFY A NAMED GRAPH for each new record

	recordID = recordData.recordID
	graph_name = recordID
	wd = rdflib.Graph(identifier=URIRef(base+graph_name+'/'))

	# PROVENANCE: creator, contributor, publication stage

	if stage == 'not modified':
		wd.add(( URIRef(base+graph_name+'/'), PROV.wasGeneratedBy, URIRef(base+userID) ))
		wd.add(( URIRef(base+userID), RDFS.label , Literal(userID.replace('-dot-','.').replace('-at-', '@') ) ))
	else:
		# modifier
		wd.add(( URIRef(base+graph_name+'/'), PROV.wasInfluencedBy, URIRef(base+userID) ))
		wd.add(( URIRef(base+userID), RDFS.label , Literal(userID.replace('-dot-','.').replace('-at-', '@') ) ))
		# creator
		creatorIRI, creatorLabel = queries.getRecordCreator(graphToClear)
		if creatorIRI is not None and creatorLabel is not None:
			wd.add(( URIRef(base+graph_name+'/'), PROV.wasGeneratedBy, URIRef(creatorIRI) ))
			wd.add(( URIRef(creatorIRI), RDFS.label , Literal(creatorLabel ) ))
		queries.clearGraph(graphToClear)
	wd.add(( URIRef(base+graph_name+'/'), PROV.generatedAtTime, Literal(datetime.datetime.now(),datatype=XSD.dateTime)  ))
	wd.add(( URIRef(base+graph_name+'/'), URIRef(base + 'publicationStage'), Literal(stage, datatype="http://www.w3.org/2001/XMLSchema#string")  ))

	# GET VALUES FROM FIELDS, MAP THEIR TYPE, TRANSFORM TO RDF

	wd.add(( URIRef(base+graph_name), RDF.type, URIRef(conf.main_entity) )) # type of catalogued resource

	for field in fields:
		value = getValuesFromFields(field['id'], recordData, fields) if field['value'] == 'URI' else recordData[field['id']] # URI,literal or literal values
		# TODO disambiguate as URI, value
		if field["disambiguate"] == 'True': # use the key 'disambiguate' as title of the graph
			wd.add(( URIRef(base+graph_name+'/'), URIRef(field['property']), Literal(value) ))

		# the main entity has the same URI of the graph but the final /

		if isinstance(value,str): # data properties
			wd.add(( URIRef(base+graph_name), URIRef(field['property']), Literal(value) ))
		else: # object properties
			for entity in value:
				entityURI = getRightURIbase(entity[0])+entity[0] # Wikidata or new entity
				wd.add(( URIRef(base+graph_name), URIRef(field['property']), URIRef(entityURI) ))
				wd.add(( URIRef( entityURI ), RDFS.label, Literal(entity[1].lstrip().rstrip(), datatype="http://www.w3.org/2001/XMLSchema#string") ))

	# DUMP TTL
	wd.serialize(destination='records/'+recordID+'.ttl', format='ttl', encoding='utf-8')

	# UPLOAD TO TRIPLESTORE
	server.update('load <file:///'+dir_path+'/records/'+recordID+'.ttl> into graph <'+base+graph_name+'/>')
