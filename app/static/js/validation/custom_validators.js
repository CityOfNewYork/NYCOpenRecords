/**
 * Created by atan on 9/27/16.
 */

window.Parsley.addValidator('maxFileSize', {
  validateString: function(_value, maxSize, parsleyInstance) {
    var files = parsleyInstance.$element[0].files;
    return files.length != 1  || files[0].size <= maxSize * 1000000;
  },
  requirementType: 'integer',
  messages: {
    en: 'The file cannot not be larger than %s Mb',
  }
});