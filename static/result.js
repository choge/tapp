function selectorEscape(val){
  return val.replace(/[ !"#$%&'()*+,.\/:;<=>?@\[\\\]^`{|}~]/g, '\\$&');
}

function formatSequences(original, decoded) {
  // format each string to 60 columns for each row
  // @param original : original amino acid sequences
  // @param decoded  : decoded sequences which comprises G, C, H, T
  //                 : (G .. Globular, C .. Cap, H .. Hydrophobic, T .. Tail)
  splitted_original = original.match(/.{1,60}/g);
  splitted_decoded  = decoded.match(/.{1,60}/g);
  formatted = "";
  for (var i = 0; i < splitted_original.length; i++) {
    formatted += "SEQUENCE:" + splitted_original[i] + "<br>";
    formatted += "&nbsp;DECODED:" + splitted_decoded[i] + "<br>";
    formatted += "<br>";
  }
  return formatted;
}

function tableHead() {
  return '<thead><tr>'
    + '<th data-field="is_ta">Result</th>'
    + '<th data-field="score">Score</th>'
    + '<th data-field="has_tmd">TMD</th>'
    + '</tr></thead>'
}

$(function () {
  // setup the modal help
  $('.modal-trigger').leanModal();

  // setup an email address
  $('#mailsend').click(function() {
    $.post('mail/' + $('#query_id').text(),
        {"email": $('#email').val()});
  });

  // retreieve date before requesting result
  var date_before = new Date();
  // perform ajax to retrieve prediction result
  var url = 'predict/' + $('#query_id').text();
  var predicted = $.getJSON(url)
    .done(function(data){
      // retreieve another date
      var timediff = (new Date() - date_before) / 1000.0;

      // update status
      $('#status-text').text('CALCULATION FINISHED');
      $('#status-progress').text(
          Object.keys(data).length + ' seqs '
          + '| took ' + timediff + ' secs');

      // show each result
      $.each(data, function(id, result) {
        var seq = $('#detail_' + selectorEscape(id) + ' > .hide').text();
        var $summary = $('#summary_' + selectorEscape(id))
        var $detail = $('#detail_' + selectorEscape(id) + ' > .query_detail');
        var score = result["score"];
        var has_tmd = result["has_tmd"];
        var is_ta = result["is_ta"];

        // update summary
        if (is_ta) {
          $summary.find('td.result').html('<i class="mdi-action-done small circle green lighten-4"></i>TA Protein');
        } else {
          $summary.find('td.result').html('<i class="mdi-content-clear small circle red lighten-4"></i>Not TA Protein');
        }
        $summary.find('td.score').html(score);
        $summary.find('td.tmd').html(has_tmd);

        // update detail
        $detail.html(
            '<div class="row valign-wrapper">'
            + '<div class="col s2 offset-s1 valign">Likelihood</div>'
            + '<div class="col s9 valign">'
            + '<table class="striped responsive-table">' + tableHead()
            + '<tbody><tr>' 
            + '<td>' + is_ta + '</td>' 
            + '<td>' + score + '</td>' 
            + '<td>' + has_tmd + '</td></tr></tbody></table>'
            + '</div>'
            + '</div>'
            + '<div class="row valign-wrapper">'
            + '<div class="col s2 offset-s1 valign">Decoded Sequence</div>'
            + '<blockquote class="col s9 valign" style="overflow: scroll; font-family: monospace;">'
            + formatSequences(seq, result["path"])
            + '</blockquote>'
            );
      });
    });
});
