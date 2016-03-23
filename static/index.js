
function set_message(icon_class, message, is_error) {
  // set some message to $el
  $('#query_check_status').html(
      '<i class="' + icon_class + ' small red-text text-darken-4"></i>' + message);
  if (is_error) {
    $('#predict_button').addClass('disabled');
    $('#predict_button').prop("disabled", true);
  }
}

$(function(){
  // check the query
  $('#query').change(function() {
    var query_lines = $('#query').val().split("\n");
    var current_query_header = ""
      var queries = {}

    // too long sequence 
    if (query_lines.length > 10000) {
      set_message("mdi-action-report-problem",
          "Your input is too long. Please divide them into smaller chunks if possible.\n"
          + "Or you can use command line tool.",
          true);
    }

    // read the sequence and convert them to an object
    for (var i = 0; i < query_lines.length; i++) {
      if (query_lines[i][0] === '>') {
        current_query_header = query_lines[i];
        queries[current_query_header] = { "header" : query_lines[i],
          "query"  : "" };
      } else if (query_lines[i] === '') {
        continue;
      } else {
        if (current_query_header in queries) {
          queries[current_query_header]["query"] += query_lines[i];
        } else {
          // error
          set_message("mdi-action-report-problem", 
              "Your input seems lacking header line. Please input the sequence in FASTA format.",
              true);
          return;
        }
      }
    }

    // too many sequences
    if (Object.keys(queries).length > 50) {
      set_message("mdi-action-report-problem",
          "Too many input sequences (>50). "
          + "Please divide them or use client tool instead.",
          true);
      return;
    }

    for (var query_id in queries) {
      // check invalid characters
      if (queries[query_id]['query'].match(/[^ACDEFGHIKLMNPQRSTVWY]+/)) {
        // found invalid character
        if (queries[query_id]['query'].match(/[^ABCDEFGHIJKLMNPQRSTVWXYZ\*\-]+/)) {
          set_message("mdi-action-report-problem",
              "Your input includes invalid character. Please check the input.",
              true);
          return;
        } else {
          // extended characters
          set_message("mdi-action-done",
              "Your input includes ambiguious codes or special codes (i.e. X or B). These codes are ignored for prediction.",
              false);
          return;
        }
      }
    }

    // input ok
    $('#query_check_status').html('<i class="mdi-action-done teal-text text-lighten-3"></i>OK');
    $('#predict_button').removeClass("disabled");
    $('#predict_button').prop("disabled", false);

  });
});
