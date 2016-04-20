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
    formatted += "SEQUENCE: " + splitted_original[i] + "\n";
    formatted += " DECODED: " + splitted_decoded[i] + "\n";
    formatted += "\n";
  }
  return formatted;
}

$(function () {
  // setup the modal help
  $('.modal-trigger').leanModal();

  // setup an email address
  $('#mailsend').click(function() {
    // check if there is a valid mail address
    if (! $('#email').val().match(/^[A-Za-z0-9]{1}[A-Za-z0-9_.-]*@{1}[A-Za-z0-9_.-]{1,}\.[A-Za-z0-9]{1,}$/)) {
      alert('Please enter a valid address');
    } else {
      // send mail
      $.post('../mail/' + $('#query_id').text(),
          {"email": $('#email').val()});
      // disable the button
      $('#mailsend').text('Mail sent');
      $('#mailsend').addClass('disabled');
      $('#mailsend').prop('disabled', true);
    }
  });

  // Directives for Transparency template engine
  var directives_summary = {
    seq_id: {
      id: function(params) {
        return 'Summary_' + this.seq_id;
      },
      text: function(params) {
        var first_20digits = this.seq_id.substr(0, 40);
        if (this.seq_id.length > 20) {
          first_20digits += '...';
        }
        return first_20digits;
      },
      href: function(params) {
        return '#Detail_' + this.seq_id;
      },
    },
    score: {
      text: function(params) {
        return Math.round(this.score * Math.pow(10, 5)) / Math.pow(10, 5);
      },
    }
  };

  // Directives for Transparency template engine
  var directives_detail = {
    // root for each result
    result: {
      id: function(params) {
        return 'Detail_' + this.seq_id;
      },
    },
    // individual elements in a result
    seq_id: {
      text: function(params) {
        return 'ID: ' + this.seq_id;
      }
    },
    score: {
      text: function(params) {
        return 'Score: ' + Math.round(this.score * Math.pow(10, 5)) / Math.pow(10, 5);
      },
    },
    path: {
      text: function(params) {
        return formatSequences(this.seq, this.path);
      },
    },
    is_ta: {
      text: function(params) {
        return 'Result: ' + this.is_ta;
      },
    }
  };


  // retreieve date before requesting result
  var date_before = new Date();
  // perform ajax to retrieve prediction result
  var url = '../predict/' + $('#query_id').text();
  var predicted = $.getJSON(url)
    .done(function(data){
      // if data is null, return.
      // maybe still under the calculation.
      if (data === null) {
        return;
      }

      // retreieve another date
      var timediff = (new Date() - date_before) / 1000.0;

      // update status
      $('#status-text').text('CALCULATION FINISHED');
      $('#status-progress').text(
          Object.keys(data).length + ' seqs '
          + '| took ' + timediff + ' secs');

      // render the data using Transparency template engine
      $('#result_summary_list').render(data, directives_summary);
      $('#result_detail_list').render(data, directives_detail);
    });
});
