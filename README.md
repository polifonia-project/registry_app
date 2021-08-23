# crowdsourcing linked data

## How does it look like

https://user-images.githubusercontent.com/6443007/124133891-924c2700-da82-11eb-95fe-e525d57d0b47.mov


## Install and run

 * download blazegraph ([link](https://github.com/blazegraph/database/releases/tag/BLAZEGRAPH_2_1_6_RC))

 * run the triplestore `java -Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8 -server -Xmx2g -Djetty.port=3000 -Dbigdata.propertyFile=blaze.properties -jar blazegraph.jar`

 * install the requirements `pip3 install -r requirements.txt`

 * run the app `nohup python3 app.py 80` (NB. nohup is required!)

## Customize

#### Configuration file `conf.py`

```
# data
myEndpoint = 'local endpoint api url' # to update data in localhost
myPublicEndpoint = 'public endpoint api url' # to fill in the autocomplete dropdown
wikidataEndpoint = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql' # to fill in the autocomplete dropdown
base = 'URI base of the dataset'
name = 'name of the dataset' # same as the last bit of base
myform = 'PATH to the JSON file to set up the form'
main_entity = "https://schema.org/CreativeWork" # the class of the entity described in the form

# backend
log_file = 'ip_logs.log' # log file with IP addresses of POST requests
limit_requests = 50 # set the max number of new records that can be created by IP address per day
pagination = 4 # number of results shown per page in backend

# github
github_backup = True # change to False and ignore the following fields if you don't want data backup on github
token = 'ghp_eL1OfbEnq**************************' # github access token
owner = "marilenadaquino" # github owner of the repo (as it appears in the URL of the repo)
repo_name = "crowdsourcing" # name of the repo where to dump files
author = "marilenadaquino" # github username of the author of commits
author_email = "marilena.daquino2@unibo.it" # author's email
```

#### `main.js`

```
const myPublicEndpoint = 'http://127.0.0.1:3000/blazegraph/sparql'; # lookup (autocomplete helper, search), leave "http://127.0.0.1:3000/blazegraph/sparql" if there is no remote SPARQL endpoint
const base = 'http://data.open.ac.uk/musow/'; # URI base of the dataset
const graph = 'http://data.open.ac.uk/context/musow'; # to specify in which graph to look into. leave empty if data is in the default graph
const webBase = 'https://musow.kmi.open.ac.uk/resources/'; # URL base of the records on the web app (autocomplete helper). leave "http://0.0.0.0:8080/view-" if not served online

```

#### The form `myform.json`

So far, only text boxes and dropdowns (select) are supported.  

**Textbox**

Example

```
{
  "type":"Textbox",
  "id":"resource_title", # unique id of the field, DO NOT USE "_label"
  "label":"Title", # field name shown to users
  "placeholder":"e.g. Listening Experience database",
  "prepend":"The title as recorded on the website of the resource",
  "disabled":"False", # True|False if the input is disabled
  "class":"col-md-11",
  "searchWikidata":"False", # True|False lookup into Wikidata and the dataset
  "cache_autocomplete":"off", # if the prior is True, this should be False
  "property":"http://www.w3.org/2000/01/rdf-schema#label", # absolute URI of the property
  "value":"Literal", # Literal|URI the type of value (if searchWikidata is True, set value as URI)
  "disambiguate":"True", # True|False if True, this field value is used to disambiguate new entries (to prevent users creating duplicates) and to assign a title to the named graph
  "browse":"True" # True|False if you want records sorted by this field in the Explore page
}
```

When `searchWikidata` is True, multiple values are allowed (e.g. multiple creator names). If no match is found in Wikidata or the dataset, new entities are created with the base URI specified in configs.

**Dropdown**

Example

```
{
  "type":"Dropdown",
  "id":"resource_type",
  "label":"Type",
  "prepend":"The type of resource described, choose from the list",
  "disabled":"False",
  "class":"col-md-11",
  "cache_autocomplete":"off",
  "property":"http://purl.org/spar/datacite/hasGeneralResourceType",
  "value":"URI", # always use a controlled vocabulary
  "values":{
      "http://data.open.ac.uk/musow/type/33fcf2b3ec4686d9cd06051c726d0ba2":"Repository",
      "http://data.open.ac.uk/musow/type/7146a60667b422e69fd050fe1df6859a":"Schema",
      "http://data.open.ac.uk/musow/type/520d0db389f362bf79ef56ca0af3dcab":"Format"
    },
  "disambiguate":"False",
  "browse":"True" # True|False if you want records grouped by this field in the Explore page 
}
```

For each `key,value` in `values` a triple `<key rdfs:label value>` is uploaded in a dedicated named graph called `base+'vocabularies/'`. Dropdowns allow only one term to be selected.

#### The dataset

Every new resource is associated with the class specified in the config file.

For every new record (resource) a named graph is generated, which includes triples all having the same subject `<resourceURI>`. The named graph appears in the form `<resourceURI/>` (final slash added). Basic provenance is associated to graphs (creators, modifiers, dates, publication stage).
