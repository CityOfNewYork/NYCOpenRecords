/**
 * Created by atan on 9/27/16.
 */

"use strict";

window.Parsley.addValidator('maxFileSize', {
  validateString: function(_value, maxSize, parsleyInstance) {
    var files = parsleyInstance.$element[0].files;
    return files.length != 1  || files[0].size <= maxSize * 1000000;
  },
  requirementType: 'integer',
  messages: {
    en: '<span class="glyphicon glyphicon-exclamation-sign"></span>&nbsp;<strong>The file cannot be larger than %s Mb.</strong> Please choose a smaller file.'
  }
});