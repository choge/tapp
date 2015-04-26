function selectorEscape(val){
  return val.replace(/[ !"#$%&'()*+,.\/:;<=>?@\[\\\]^`{|}~]/g, '\\$&');
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
        var $result = $('#' + selectorEscape(id) + ' > .collapsible-body');
        $result.html(
            '<div class="row">'
            + '<div class="col s2 offset-s1">Likelihood</div>'
            + '<div class="col s9">' + result["likelihood"] + '</div>'
            + '</div>'
            + '<div class="row">'
            + '<div class="col s2 offset-s1">Decoded Sequences</div>'
            + '<blockquote class="col s9">' + result["path"] + '</div>'
            + '</div>'
            );
      });
    });
});
