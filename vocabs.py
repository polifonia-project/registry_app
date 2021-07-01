# -*- coding: utf-8 -*-
from pymantic import sparql
import conf , os , rdflib
from rdflib import URIRef , XSD, Namespace , Literal
from rdflib.namespace import RDFS

server = sparql.SPARQLServer(conf.myEndpoint)
dir_path = os.path.dirname(os.path.realpath(__file__))

def import_vocabs(fields):
    """ get all controlled vocabularies and uploads to the triplestore"""
    list_vocab = [field['values'] for field in fields if 'values' in field]
    if len(list_vocab) > 0:
        vocab = rdflib.Graph()
        for dict_vocab in list_vocab:
            for uri,label in dict_vocab.items():
                vocab.add(( URIRef( uri), RDFS.label, Literal(label) ))

        vocab.serialize(destination='vocabs/vocabs.ttl', format='ttl', encoding='utf-8')
        server.update('load <file:///'+dir_path+'/vocabs/vocabs.ttl> into graph <'+conf.base+'vocabularies/>')
