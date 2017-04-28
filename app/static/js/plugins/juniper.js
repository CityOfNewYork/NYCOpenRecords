/*
 * Juniper.js allows you to add Parsley.js validation to X-editable form elements
 * Author: Ben Tempchin
*/
;(function ($, window, document, undefined) {
    // Create the defaults once
    var pluginName = 'juniper';

    // The actual plugin constructor
    function Juniper (element, options) {
        this.$element = $(element);

        this.options = $.extend({}, $.fn[pluginName].defaults, options) ;

        this._defaults = $.fn[pluginName].defaults;
        this._name = pluginName;

        this.init();
    }

    Juniper.prototype = {
        _createDomApi: function () {
            if (typeof $.fn.domApi === 'undefined') {
                // Zepto deserializeValue function
                var deserializeValue = function(value) {
                    var num;
                    try {
                        return value ?
                            value === "true" ||
                            (value === "false" ? false :
                             value === "null" ? null :
                             !isNaN(num = Number(value)) ? num :
                             /^[\[\{]/.test(value) ? $.parseJSON(value) :
                             value)
                                 : value;
                    } catch (e) {
                        return value;
                    }
                };

                // Zepto camelize function
                var camelize = function (str) {
                    return str.replace(/-+(.)?/g, function (match, chr) {
                        return chr ? chr.toUpperCase() : '';
                    });
                };

                /* PARSLEY DOM API
                 * =================================================== */
                $.fn.domApi = function (namespace) {
                    var attribute,
                        obj = {},
                        regex = new RegExp("^" + namespace, 'i');

                    if ('undefined' === typeof this[0]) {
                        return {};
                    }

                    for (var i in this[0].attributes) {
                        attribute = this[0].attributes[i];

                        if ('undefined' !== typeof attribute && null !== attribute && attribute.specified && regex.test(attribute.name)) {
                            obj[camelize(attribute.name.replace(namespace, ''))] = deserializeValue(attribute.value);
                        }
                    }

                    return obj;
                };
            }
        },
        _decamelize: function (str) {
            return str.replace(/(\w)([A-Z])/g, function (match, chr0, chr1) {
                return (chr0 && chr1) ? chr0 + '-' + chr1.toLowerCase() : '';
            }).toLowerCase();
        },
        _getElementData: function () {
            this.validationData = this.$element.domApi(this.options.namespace);
        },
        _getElements: function (editable) {
            this.$input = editable.input.$input,
            this.$form = this.$input.parents('form'),
            this.$editableErrorContainer = this.$form.find('.editable-error-block');
            this.$formGroup = $('.form-group', this.$form);
        },
        _onElementShown: function (e, editable) {
            // if arguments.length !== 2 it is not an x-editable callback, but rather bootstrap
            if (arguments.length !== 2) { return; }

            var base = this;

            // get global variables for each element we will work with
            this._getElements(editable);

            // make the editable object globally available
            this.editable = editable;

            // add parsley attributes to form
            this.$form.attr('parsley-validate', true);

            // add parsley attributes to input
            this.$input.attr('parsley-trigger', this.options.trigger);
            $.each(this.validationData, function (key, value) {
                if (typeof value !== 'string' && typeof value !== 'boolean') {
                    try {
                        value = JSON.stringify(value);
                    } catch (e) {
                        value = value;
                    }
                }
                // key has been camelized
                // undo it
                key = base._decamelize(key);

                base.$input.attr('parsley-' + key, value);
            });

            // initialize parsley on the form
            this.$form.parsley({
                animate: base.options.parsleyDefaults.animate,
                errorClass: base.options.errorClass,
                errors: {
                    classHandler: function () {
                        return base.$form.find(base.options.controlGroupClass);
                    },
                    container: function () {
                        // create a parsley error container above the
                        // x-editable error container
                        var $container = base.$editableErrorContainer.find(".parsley-container");
                        if ($container.length === 0) {
                            $container = $("<div class='parsley-container help-block'></div>").insertBefore(base.$editableErrorContainer);
                        }
                        base.$errorContainer = $container;
                        return $container;
                    }
                }
            });
        },
        // if we have an error, find the messages and return them
        _validateElement: function () {
            // if there is an error, return and empty string.
            if (this.$formGroup.hasClass(this.options.errorClass)) {
                return ' ';
            }
        }
    };

    Juniper.prototype.init = function () {
        // in case $.fn.domApi does not exist ( should be part of parsley ), create it
        this._createDomApi();

        // using $.fn.domApi, get and store the element validation data
        this._getElementData();

        // if there are no juniper data attributes, return
        var count = 0;
        $.each(this.validationData, function () { count += 1; });
        if (count === 0) { return; }

        this.$element.on('shown', $.proxy(this._onElementShown, this));

        this.$element.editable('option', 'validate', $.proxy(this._validateElement, this));
    };


    // A really lightweight plugin wrapper around the constructor,
    // preventing against multiple instantiations
    $.fn[pluginName] = function (options) {
        return this.each(function () {
            if (!$.data(this, 'plugin_' + pluginName)) {
                $.data(this, 'plugin_' + pluginName,
                       new Juniper(this, options));
            }
        });
    };

    // globally accessable defaults
    $.fn[pluginName].defaults = {
        namespace: 'data-juniper',
        trigger: 'keyup',
        errorClass: 'has-error parsley-error',
        controlGroupClass: '.control-group',
        parsleyDefaults: {
            animate: true
        }
    };
}(jQuery, window, document));