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
    + '<th data-field="score">score</th>'
    + '<th data-field="ta">TA model</th>'
    + '<th data-field="sp">SP model</th>'
    + '<th data-field="mp">MP model</th>'
    + '</tr></thead>'
}

$(function () {
  // collapsible initialization
  $('.collapsible').collapsible({
    expandable : true // A setting that changes the collapsible behavior to expandable instead of the default accordion style
  });

  // retreieve date before requesting result
  var date_before = new Date();
  // perform ajax to retrieve prediction result
  var url = '/predict/' + $('#query_id').text();
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
        var seq = $('#' + selectorEscape(id) + ' > .hide').text();
        var $result = $('#' + selectorEscape(id) + ' > .collapsible-body');
        var l_ta = result["likelihood"];
        var l_sp = result["likelihood_sp"];
        var l_mp = result["likelihood_mp"];
        var len = seq.length;
        $result.html(
            '<div class="row valign-wrapper">'
            + '<div class="col s2 offset-s1 valign">Likelihood</div>'
            + '<div class="col s9 valign">'
            + '<table class="striped">' + tableHead()
            + '<tbody><tr><td>tmp</td><td>' + l_ta + '</td><td>' + l_sp + '</td><td>' + l_mp + '</td></tr></tbody></table>'
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
