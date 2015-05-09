
$(function(){
  // check the query
  $('#query').change(function() {
    var query_lines = $('#query').val().split("\n");
    var current_query_header = ""
    var queries = {}

    // read the sequence and convert them to an object
    for (var i = 0; i < query_lines.length; i++) {
      if (query_lines[i][0] === '>') {
        current_query_header = query_lines[i];
        queries[current_query_header] = { "header" : query_lines[i],
                                          "query"  : "" };
      } else {
        if (! current_query_header in queries) {
          // error
          Materialize.toast('It seems your input does not contain the header line.', 
            4000, '',
            function () {
              $('#query').addClass('teal lighten-4');
            });
        }
        queries[current_query_header]["query"] += query_lines[i];
      }
    }

    // check invalid characters

  });

});
