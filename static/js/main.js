const myPublicEndpoint = 'http://data.open.ac.uk/sparql';
const base = 'http://data.open.ac.uk/musow/';
const webMusow = 'https://musow.kmi.open.ac.uk/resources/';

 $(document).ready(function() {

    // loader
    $(".se-pre-con").fadeOut("slow");

  	// disable submit form when pressing return
  	$("input[type='text'], input[type='textarea']").on('keyup keypress', function(e) {
  	  var keyCode = e.keyCode || e.which;
  	  if (keyCode === 13) {
  	    e.preventDefault();
  	    return false;
  	  }
  	});

  	// URL detection
    $('.info-url').each(function(element) {
       var str_text = $(this).html();
       var regex = /(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
       // Replace plain text links by hyperlinks
       var replaced_text = str_text.replace(regex, "<a href='$1' target='_blank'>$1</a>");
       // Echo link
       $(this).html(replaced_text);
    });

  	// tooltips
  	$('.tip').tooltip();

  	// Named Entity Recognition in long texts
  	// nlpText('add an id without hashtag');

  	// search WD and my data
  	$("input[type='text']").click(function () {
  		searchID = $(this).attr('id');

  		if ( $(this).hasClass('searchWikidata') ) {
  			searchWD(searchID);
  		};

  		// if ( $(this).hasClass('searchGeneral') ) {
  		// 	searchARTchivesGeneral('searchGeneral');
  		// };
  	});

  	// remove tag onclick
  	$(document).on('click', '.tag', function () {
  		$(this).next().remove();
  		$(this).remove();
  		colorForm();
  	});

  	// autoresize textarea
  	$('textarea').each(function () {
  		this.setAttribute('style', 'height:' + (this.scrollHeight)/2 + 'px;overflow-y:hidden;');
  	}).on('input', function () {
  		this.style.height = 'auto';
  		this.style.height = (this.scrollHeight) + 'px';
  	});

  	// Show documentation in the right sidebar
  	if ($('header').hasClass('needDoc')) {
  		var menuRight = document.getElementById( 'cbp-spmenu-s2' ),
  		showRight = document.getElementById( 'showRight' ),
  		body = document.body;
  		showRight.onclick = function() {
  			classie.toggle( this, 'active' );
  			classie.toggle( menuRight, 'cbp-spmenu-open' );
  		};
  	};

  	// append WD icon to input fields
  	$('.searchWikidata').parent().prev().append(' <img src="https://upload.wikimedia.org/wikipedia/commons/d/d2/Wikidata-logo-without-paddings.svg" style="width:20px ; padding-bottom: 5px;"/>');

  	// hide placeholder if filled
  	//colorForm();

  	// prevent POST when deleting records
  	$('.delete').click(function(e) {
  		var result = confirm("Are you sure you want to delete this record?");
  		if (result) { } else { e.preventDefault(); return false; };
  	});

});

function colorForm() {
	$('.searchWikidata').each( function() {
		if ($(this).next('span').length > 0) {
			$(this).removeAttr('placeholder');
			$(this).parent().prev('.label').css('color','lightgrey');
			$(this).parent().prev('.label').children('img').css('opacity','0.5');
			$(this).nextAll('span').css('color','lightgrey').css('border-color','lightgrey');

			$($(this).parent().parent()).hover(function(){
				$(this).children().addClass('color_hover');
				$(this).children().children('span').addClass('color_hover').addClass('bkg_hover');
			}, function() {
				$(this).children().removeClass('color_hover');
				$(this).children().children('span').removeClass('color_hover').removeClass('bkg_hover');
			});

		} else {
			$(this).parent().prev('.label').css('color','black');
			$(this).parent().prev('.label').children('img').css('opacity','1');
			$(this).nextAll('span').css('color','black').css('border-color','black');
		};
	});

	$('.freeText').each( function() {
		if ($(this).val().length > 0) {
			$(this).parent().prev('.label').css('color','lightgrey');
			$(this).parent().prev('.label').children('img').css('opacity','0.5');
			$(this).css('color','lightgrey');
			$($(this).parent().parent()).hover(function(){
				$(this).children().addClass('color_hover');
				$(this).children().children().addClass('color_hover');
				}, function() {
					$(this).children().removeClass('color_hover');
					$(this).children().children().removeClass('color_hover');
				});
		} else {
			$(this).parent().prev('.label').css('color','black');
			$(this).parent().prev('.label').children('img').css('opacity','1');
			$(this.value).css('color','black');
		};
	});
};

// delay a function
function throttle(f, delay){
    var timer = null;
    return function(){
        var context = this, args = arguments;
        clearTimeout(timer);
        timer = window.setTimeout(function(){
            f.apply(context, args);
        },
        delay || 300);
    };
};

// search in wikidata and my catalogue
function searchWD(searchterm) {
	// wikidata autocomplete on keyup
	$('#'+searchterm).keyup(function(e) {
	  $("#searchresult").show();
	  var q = $('#'+searchterm).val();

	  $.getJSON("https://www.wikidata.org/w/api.php?callback=?", {
	      search: q,
	      action: "wbsearchentities",
	      language: "en",
	      uselang: "en",
	      format: "json",
	      strictlanguage: true,
	    },
	    function(data) {
	    	  // autocomplete positioning
	      	var position = $('#'+searchterm).position();
	      	var leftpos = position.left+15;
	      	var offset = $('#'+searchterm).offset();
    			var height = $('#'+searchterm).height();
    			var width = $('#'+searchterm).width();
    			var top = offset.top + height + "px";
    			var right = offset.left + width + "px";

    			$('#searchresult').css( {
    			    'position': 'absolute',
    			    'margin-left': leftpos+'px',
    			    'top': top,
    			    'z-index':1000,
    			    'background-color': 'white',
    			    'border':'solid 1px grey',
    			    'max-width':'600px',
    			    'border-radius': '4px'
    			});
    	    $("#searchresult").empty();

  	      // catalogue lookup in case nothing is found
  	      if(!data.search.length){
  	      	$("#searchresult").append("<div class='wditem noresults'>No matches in Wikidata...looking into the catalogue</div>");
  	      	// remove messages after 3 seconds
      			setTimeout(function(){
      			  if ($('.noresults').length > 0) {
      			    $('.noresults').remove();
      			  }
      		  }, 3000);

      			var query = "prefix bds: <http://www.bigdata.com/rdf/search#> select distinct ?s ?o ?desc FROM <http://data.open.ac.uk/context/musow> where { ?s <http://xmlns.com/foaf/0.1/homepage> ?home ; rdfs:label ?o ; rdfs:comment ?desc . ?o bds:search '"+q+"*' .}"
      			var encoded = encodeURIComponent(query)

      			$.ajax({
      				    type: 'GET',
      				    url: myPublicEndpoint+'?query=' + encoded,
      				    headers: { Accept: 'application/sparql-results+json'},
      				    success: function(returnedJson) {
      				    	$("#searchresult").empty();

                    if (!returnedJson.length) {
        		      				$("#searchresult").empty();
        					    		$("#searchresult").append("<div class='wditem noresults'>No results in Wikidata and catalogue</div>");
        		      				// remove messages after 3 seconds
        								  setTimeout(function(){ if ($('.noresults').length > 0) { $('.noresults').remove(); } }, 3000);
        		      	};

        						for (i = 0; i < returnedJson.results.bindings.length; i++) {
        							var myUrl = returnedJson.results.bindings[i].s.value;
        							// exclude named graphs from results
        							if ( myUrl.substring(myUrl.length-1) != "/") {
                        var resID = myUrl.substr(myUrl.lastIndexOf('/') + 1)
        								$("#searchresult").append("<div class='wditem'><a class='blue orangeText' target='_blank' href='"+webMusow+resID+"'><i class='fas fa-external-link-alt'></i></a> <a class='orangeText' data-id=" + returnedJson.results.bindings[i].s.value + "'>" + returnedJson.results.bindings[i].o.value + "</a> - " + returnedJson.results.bindings[i].desc.value + "</div>");
        							    };
        							};

          						// add tag if the user chooses an item from the catalogue
          						$('a[data-id^="'+base+'"]').each( function() {
          					        $(this).bind('click', function(e) {
          					        	e.preventDefault();
          					        	var oldID = this.getAttribute('data-id').substr(this.getAttribute('data-id').lastIndexOf('/') + 1);
          					        	var oldLabel = $(this).text();
          					        	$('#'+searchterm).after("<span class='tag "+oldID+"' data-input='"+searchterm+"' data-id='"+oldID+"'>"+oldLabel+"</span><input type='hidden' class='hiddenInput "+oldID+"' name='"+searchterm+"-"+oldID+"' value='"+oldID+","+encodeURIComponent(oldLabel)+"'/>");
          					        	$("#searchresult").hide();
          					        	$('#'+searchterm).val('');
          					        	// check prior records and avoid the section to be filled
          					        	// if (searchterm == 'S_KEEPER_1') {
          					        	// 	checkPriorRecords('S_KEEPER_1', 'artchives');
          					        	// };
          					        	// if (searchterm == 'S_CREATOR_1') {
          					        	// 	checkPriorRecords('S_CREATOR_1', 'artchives');
          					        	// };
          					        });

          					    });

      				    }
      			});
      			// end my catalogue
          };

  	      // fill the dropdown
  	      $.each(data.search, function(i, item) {
  	        $("#searchresult").append("<div class='wditem'><a class='blue' target='_blank' href='http://www.wikidata.org/entity/"+item.title+"'><i class='fas fa-external-link-alt'></i></a> <a class='blue' data-id='" + item.title + "'>" + item.label + "</a> - " + item.description + "</div>");

            // add tag if the user chooses an item from wd
  	      	$('a[data-id="'+ item.title+'"]').each( function() {
  		        $(this).bind('click', function(e) {
  		        	e.preventDefault();
  		        	$('#'+searchterm).after("<span class='tag "+item.title+"' data-input='"+searchterm+"' data-id='"+item.title+"'>"+item.label+"</span><input type='hidden' class='hiddenInput "+item.title+"' name='"+searchterm+"-"+item.title+"' value='"+item.title+","+encodeURIComponent(item.label)+"'/>");
  		        	$("#searchresult").hide();
  		        	$('#'+searchterm).val('');
  		        	// check prior records and alert if duplicate
  		        	// if (searchterm == 'S_KEEPER_1') {
  		        	// 	checkPriorRecords('S_KEEPER_1', 'wikidata');
  		        	// };
  		        	// if (searchterm == 'S_CREATOR_1') {
  		        	// 	checkPriorRecords('S_CREATOR_1', 'wikidata');
  		        	// };
  		        	//colorForm();
  		        });

  		    });
	      });
	  	}
	  );
	});

	// if the user presses enter - create a new entity
	$('#'+searchterm).keypress(function(e) {
	    if(e.which == 13) {
	    	e.preventDefault();
	    	var now = new Date().valueOf();
  			var newID = 'MD'+now;
  			if (!$('#'+searchterm).val() == '') {
  				$('#'+searchterm).after("<span class='tag "+newID+"' data-input='"+searchterm+"' data-id='"+newID+"'>"+$('#'+searchterm).val()+"</span><input type='hidden' class='hiddenInput "+newID+"' name='"+searchterm+"-"+newID+"' value='"+newID+","+encodeURIComponent($('#'+searchterm).val())+"'/>");
  			};
  			$("#searchresult").hide();
  	    	$('#'+searchterm).val('');
  	    	//colorForm();
	    };
	});
};

// NLP
function nlpText(searchterm) {
	$('textarea#'+searchterm).keypress( throttle(function(e) {
	  	if(e.which == 13) {
	  		//$('textarea#'+searchterm).parent().parent().append('<div class="tags-nlp col-md-9"></div>');
			$(this).next('.tags-nlp').empty();
			var textNLP = $('#'+searchterm).val();
			var encoded = encodeURIComponent(textNLP)

			// compromise.js
			var doc = nlp(textNLP);
			var listTopics = doc.nouns().toPlural().topics().out('topk');
			for (var i = 0; i < listTopics.length; i++) {
				// query WD for reconciliation
				$.getJSON("https://www.wikidata.org/w/api.php?callback=?", {
			      search: listTopics[i].normal,
			      action: "wbsearchentities",
			      language: "en",
			      limit: 1,
			      uselang: "en",
			      format: "json",
			      strictlanguage: true,
			    },
			    function(data) {
			    	$.each(data.search, function(i, item) {
				        $('textarea#'+searchterm).next('.tags-nlp').append('<span class="tag nlp '+item.title+'" data-input="'+searchterm+'" data-id="'+item.title+'">'+item.label+'</span><input type="hidden" class="hiddenInput '+item.title+'" name="'+searchterm+'-'+item.title+'" value="'+item.title+','+encodeURIComponent(item.label)+'"/>');
			    	});
			    });
			};


			// DBpedia spotlight
			$.ajax({
			    type: 'GET',
			    url: 'https://api.dbpedia-spotlight.org/en/annotate?text=' + encoded,
			    headers: { Accept: 'application/json' },
			    success: function(returnedJson) {
			    	var resources = returnedJson.Resources ;
			    	var result = new Array();
			    	for (var i = 0; i < resources.length; i++) {
			    		var uri = resources[i]['@URI'] ;
			    		// remove duplicates retrieved by DBpedia spotlight
				    	if(result.indexOf(uri) == -1){
				            result.push(uri);
				            // look for samAs in Dbpedia LDF to Wikidata
				            $.ajax({
							    type: 'GET',
							    url: 'http://data.linkeddatafragments.org/dbpedia',
							    data: {subject: uri, predicate: 'http://www.w3.org/2002/07/owl#sameAs', object: ""},
							    headers: { Accept: 'application/n-triples; charset=utf-8' },
							    success: function(data) {
							    	var myRegexp = /<http:\/\/www.w3.org\/2002\/07\/owl#sameAs> <http:\/\/wikidata.org\/entity\/(.*)>/;
									var match = myRegexp.exec(data);
									var res = match[1];
									console.log(data);
									if (res && !$('textarea#'+searchterm).parent().next('.tags-nlp').children("span[data-id="+match[1]+"]").length ) {
										// get Wikidata label
										$.ajax({
											url: "https://cors-anywhere.herokuapp.com/https://www.wikidata.org/w/api.php?action=wbgetentities&ids="+res+'&props=labels&languages=en&languagefallback=en&sitefilter=&formatversion=2&format=json',
											success: function(data) {
												$('textarea#'+searchterm).parent().next('.tags-nlp').append('<span class="tag nlp '+res+'" data-input="'+searchterm+'" data-id="'+res+'">'+data.entities[res].labels.en.value+'</span><input type="hidden" class="hiddenInput '+res+'" name="'+searchterm+'-'+res+'" value="'+res+','+encodeURIComponent(data.entities[res].labels.en.value)+'"/>');


											}
										});
									} else {
										// try to match dbpedia > wikipedia > wikidata entities
							    		var WikiPage = 'https://en.wikipedia.org/wiki/'+ uri.substr(uri.lastIndexOf('/') + 1);
							    		$.ajax({
										    type: 'GET',
										    url: 'https://query.wikidata.org/bigdata/ldf',
										    data: {subject: WikiPage, predicate: 'http://schema.org/about', object: ""},
										    headers: { Accept: 'application/n-triples; charset=utf-8' },
										    success: function(data) {
										    	// get the object URI
												var myRegexp = /<http:\/\/www.wikidata.org\/entity\/(.*)>/;
												var match = myRegexp.exec(data);
												var res = match[0];
												// remove duplicates already found by compromise.js
												if (res && !$('textarea#'+searchterm).parent().next('.tags-nlp').children("span[data-id="+match[1]+"]").length ) {
													$.ajax({
													    type: 'GET',
													    url: 'https://query.wikidata.org/bigdata/ldf',
													    data: {subject: res, predicate: 'http://www.w3.org/2000/01/rdf-schema#label', object: ""},
													    headers: { Accept: 'application/n-triples; charset=utf-8' },
													    success: function(dataLabel) {
													    	// get the object label
													    	var myRegexpLabel = /"(.*)"@en/;
													    	var matchLabel = myRegexpLabel.exec(dataLabel);
													    	var label = matchLabel[1];
													    	$('textarea#'+searchterm).parent().next('.tags-nlp').append('<span class="tag nlp '+match[1]+'" data-input="'+searchterm+'" data-id="'+match[1]+'">'+label+'</span><input type="hidden" class="hiddenInput '+match[1]+'" name="'+searchterm+'-'+match[1]+'" value="'+match[1]+','+encodeURIComponent(label)+'"/>');
													    }
													});
												};
										    }
										});

									};
							    }
							});




				        };
				    };
			    }
		    });
		};

	}) );
};

// function popUpInfo(className) {
// 	$('.'+className).each( function() {
// 		var dataID = $(this).attr('data-id');
// 		thisElem = $(this);
//
// 		$(this).attr('data-toggle','tooltip');
// 		$(this).attr('data-placement','right');
// 		$(this).attr('data-html','true');
// 		// dispatcher Artchives / WD / AAT / ULAN
// 		if (dataID.startsWith('MD')) {
// 			base = "https://w3id.org/artchives/";
// 		} // artchives
// 		else if (dataID.startsWith('Q')) {
// 			base = "http://www.wikidata.org/entity/";
// 		} // WD
// 		else {
// 			base ="http://vocab.getty.edu/ulan/";
// 			baseAAT ="http://vocab.getty.edu/aat/";
// 		}; // Getty: TODO how to distinguish AAT and ULAN?
//
// 		var entity = base+dataID ;
// 		var encoded = "PREFIX wdp: <http://www.wikidata.org/wiki/Property:> SELECT distinct ?g ?obj ?label ?type WHERE { GRAPH ?g { ?obj wdp:P921 <"+entity+"> ; a ?type ; rdfs:label ?label . } }"
// 		$.ajax({
// 		    type: 'GET',
// 		    url: 'http://artchives.fondazionezeri.unibo.it/sparql?query=' + encoded,
// 		    headers: {
// 		 		Accept: 'application/sparql-results+json'
// 		    	},
// 		    success: function(returnedJson) {
// 		    	historiansArray = new Array() ;
// 		    	collectionsArray = new Array() ;
// 		    	for (i = 0; i < returnedJson.results.bindings.length; i++) {
// 		    		if ( returnedJson.results.bindings[i].type.value == 'http://www.wikidata.org/entity/Q5' ) {
// 		    			historianArray = new Array();
// 		    			var uri = returnedJson.results.bindings[i].obj.value ;
// 						var qID = uri.substr(uri.lastIndexOf('/') + 1);
// 		    			historianArray.push(qID) ;
// 		    			historianArray.push(returnedJson.results.bindings[i].label.value) ;
// 		    			historiansArray.push( historianArray );
// 		    		};
// 		    		if ( returnedJson.results.bindings[i].type.value == 'http://www.wikidata.org/entity/Q9388534' ) {
// 		    			var uriSlash = returnedJson.results.bindings[i].g.value ;
// 						var uri = uriSlash.substr(0, uriSlash.length-1) ;
// 						var qID = uri.substr(uri.lastIndexOf('/') + 1);
//
// 		    			collectionArray = new Array();
// 		    			collectionArray.push(qID) ;
// 		    			collectionArray.push(returnedJson.results.bindings[i].label.value) ;
// 		    			collectionsArray.push( collectionArray );
// 		    		};
//
// 		    		var htmlText = '';
// 		    		if (historiansArray.length) {
// 		    			htmlText += "<p>Related art historians:</p>" ;
// 		    			for (i = 0; i < historiansArray.length; i++) {
// 		    				// TODO this has to be changed with the following when using the historian ID and not the graph ID for routing to historians' pages
// 		    				// var historianID = historiansArray[i][0].substr(historiansArray[i][0].lastIndexOf('/') + 1)
// 		    				var historianID = historiansArray[i][0];
// 		    				var historianPage = '/historian-'+historianID;
// 		    				htmlText += "<p><a href='"+historianPage+"'>"+historiansArray[i][1]+"</a></p>";
// 		    			};
// 		    		};
//
// 		    		if (collectionsArray.length) {
// 		    			htmlText += "<p>Related collections:</p>" ;
// 		    			for (i = 0; i < collectionsArray.length; i++) {
// 		    				// var collectionID = collectionsArray[i][0].substr(collectionsArray[i][0].lastIndexOf('/') + 1);
// 		    				var collectionID = collectionsArray[i][0];
// 		    				var collectionPage = '/collection-'+collectionID;
// 		    				htmlText += "<p><a href='"+collectionPage+"'>"+collectionsArray[i][1]+"</a></p>";
// 		    			};
// 		    		};
// 		    	};
// 		    	if (!historiansArray.length && !collectionsArray.length) { htmlText += "<p>No relations to other collections</p>" ; };
// 	    		$('span[data-id='+dataID+']').attr('data-original-title', htmlText);
//
// 		    }
// 		});
//
// 		$(this).tooltip({'trigger':'click'});
//
// 	});
// };

// function checkPriorRecords(term, prefix) {
// 	if (prefix == 'wikidata') { var base = 'http://www.wikidata.org/entity/'; };
// 	if (prefix == 'artchives') { var base = 'https://w3id.org/artchives/'; };
//
// 	var entity = base + $('span[data-input="'+term+'"]').attr('data-id');
// 	var queryKeeper = "PREFIX wdp: <http://www.wikidata.org/wiki/Property:> SELECT DISTINCT ?collection WHERE {<"+entity+"> wdp:P1830 ?collection .}"
// 	var queryCreator = "PREFIX wdp: <http://www.wikidata.org/wiki/Property:> SELECT DISTINCT ?collection WHERE {?collection wdp:P170 <"+entity+"> .}"
//
// 	if (term == 'S_KEEPER_1') {
// 		var encoded = encodeURIComponent(queryKeeper);
// 		var what = 'keeper';
// 	};
// 	if (term == 'S_CREATOR_1') {
// 		var encoded = encodeURIComponent(queryCreator);
// 		var what = 'creator';
// 	};
//
// 	$.ajax({
// 	    type: 'GET',
// 	    url: myPublicEndpoint+'?query=' + encoded,
// 	    headers: { Accept: 'application/sparql-results+json'},
// 	    success: function(returnedJson) {
// 	    	console.log(returnedJson);
// 			if (!returnedJson.results.bindings.length) {
//   			} else {
//   				alert("This "+what+" has already been described in another record. Let\'s skip this section!");
//   				var next = $('#'+term).parent().parent().nextAll(".sectionTitle");
//
// 		       	console.log(term);
// 		       	$('html,body').animate({ scrollTop: next.offset().top }, 600);
//
//   			};
// 	    }
// 	});
// };
