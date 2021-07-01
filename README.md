# crowdsourcing linked data

## How does it look like

https://user-images.githubusercontent.com/6443007/124133891-924c2700-da82-11eb-95fe-e525d57d0b47.mov


## Install and run

 * download blazegraph ([link](https://github.com/blazegraph/database/releases/tag/BLAZEGRAPH_2_1_6_RC))

 * run the triplestore `java -Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8 -server -Xmx2g -Djetty.port=3000 -Dbigdata.propertyFile=blaze.properties -jar blazegraph.jar`

 * install the requirements `pip3 install -r requirements.txt`

 * run the app `python3 app.py 80`

## Customize

#### Configuration file `conf.py`

```
myEndpoint = 'local endpoint api url' # to update data in localhost
myPublicEndpoint = 'public endpoint api url' # to fill in the autocomplete dropdown
wikidataEndpoint = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql' # to fill in the autocomplete dropdown
base = 'URI base of the dataset'
name = 'name of the dataset' # same as the last bit of base
myform = 'PATH to the JSON file to set up the form'
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
  "disambiguate":"True" # True|False if True, this field value is used to disambiguate new entries (to prevent users creating duplicates) and to assign a title to the named graph
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
  "disambiguate":"False"
}
```

For each `key,value` in `values` a triple `<key rdfs:label value>` is uploaded in a dedicated named graph called `base+'vocabularies/'`. Dropdowns allow only one term to be selected.

#### The dataset

Every new resource is associated with the class `schema:CreativeWork`.

For every new record (resource) a named graph is generated, which includes triples all having the same subject `<resourceURI>`. The named graph appears in the form `<resourceURI/>` (final slash added). Basic provenance is associated to graphs (creators, modifiers, dates, publication stage).


## TODO

Development

- [ ] hash passwords (store them separately)
- [ ] extend form with text area
- [ ] extend form with multiple value select
- [ ] extend form with the class to be associated to the main entity
- [ ] extend form to describe different entities (e.g. resources and their creators, corresponding to different sections of the form)
- [ ] implement (i.e. refactor existing) lookup service to alert users when they start entering data about an existing entry (see js checkRecords)
- [ ] dump/update (and sync) data on github
- [x] extend form with dropdowns

Specific to musow use case
- [ ] define **classes / properties** to create the form. Change the current model or simply extend it?
- [ ] decide whether to **integrate** this app with the current online catalogue or to **replace** it. In the first case, more development would be needed (send update requests to an external triplestore, e.g. via github dump). In the second case, existing data should be imported in the application (as-is or according to the new model).
- [ ] work on the **UI** (homepage, record view, index of resources, other aggregated views?) and change links in footer, add documentation, etc.
