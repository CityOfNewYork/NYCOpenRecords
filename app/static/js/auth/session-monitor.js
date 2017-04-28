sessionMonitor = function(options) {
    "use strict";

    var defaults = {
            // Session lifetime (milliseconds)
            sessionLifetime: 60 * 60 * 1000,
            // Amount of time before session expiration when the warning is shown (milliseconds)
            timeBeforeWarning: 5 * 60 * 1000,
            // Minimum time between pings to the server (milliseconds)
            minPingInterval: 60 * 1000,
            // Space-separated list of events passed to $(document).on() that indicate a user is active
            activityEvents: 'mouseup',
            // URL to ping the server using HTTP POST to extend the session
            pingUrl: '/ping',
            // URL used to log out when the user clicks a "Log out" button
            logoutUrl: '/logout',
            // URL used to log out when the session times out
            timeoutUrl: '/logout?timeout=1',
            ping: function() {
                // Ping the server to extend the session expiration using a POST request.
                $.ajax({
                    type: 'POST',
                    url: self.pingUrl
                });
            },
            logout: function() {
                // Go to the logout page.
                window.location.href = self.logoutUrl;
            },
            onwarning: function() {
                // Below is example code to demonstrate basic functionality. Use this to warn
                // the user that the session will expire and allow the user to take action.
                // Override this method to customize the warning.
                var warningMinutes = Math.round(self.timeBeforeWarning / 60 / 1000),
                    $alert = $('<div id="jqsm-warning">Your session will expire in ' + warningMinutes + ' minutes. ' +
                               '<button id="jqsm-stay-logged-in">Stay Logged In</button>' +
                               '<button id="jqsm-log-out">Log Out</button>' +
                               '</div>');

                if (!$('body').children('div#jqsm-warning').length) {
                    $('body').prepend($alert);
                }
                $('div#jqsm-warning').show();
                $('button#jqsm-stay-logged-in').on('click', self.extendsess)
                    .on('click', function() { $alert.hide(); });
                $('button#jqsm-log-out').on('click', self.logout);
            },
            onbeforetimeout: function() {
                // By default this does nothing. Override this method to perform actions
                // (such as saving draft data) before the user is automatically logged out.
                // This may optionally return a jQuery Deferred object, in which case
                // ontimeout will be executed when the deferred is resolved or rejected.
            },
            ontimeout: function() {
                // Go to the timeout page.
                window.location.href = self.timeoutUrl;
            }
        },
        self = {},
        _warningTimeoutID,
        _expirationTimeoutID,
        // The time of the last ping to the server.
        _lastPingTime = 0;

    function extendsess() {
        // Extend the session expiration. Ping the server and reset the timers if
        // the minimum interval has passed since the last ping.
        var now = $.now(),
            timeSinceLastPing = now - _lastPingTime;

        if (timeSinceLastPing > self.minPingInterval) {
            _lastPingTime = now;
            _resetTimers();
            self.ping();
        }
    }

    function _resetTimers() {
        // Reset the session warning and session expiration timers.
        var warningTimeout = self.sessionLifetime - self.timeBeforeWarning;

        window.clearTimeout(_warningTimeoutID);
        window.clearTimeout(_expirationTimeoutID);
        _warningTimeoutID = window.setTimeout(self.onwarning, warningTimeout);
        _expirationTimeoutID = window.setTimeout(_onTimeout, self.sessionLifetime);
    }

    function _onTimeout() {
        // A wrapper that calls onbeforetimeout and ontimeout and supports asynchronous code.
        $.when(self.onbeforetimeout()).always(self.ontimeout);
    }

    // Add default variables and methods, user specified options, and non-overridable
    // public methods to the session monitor instance.
    $.extend(self, defaults, options, {
        extendsess: extendsess
    });
    // Set an event handler to extend the session upon user activity (e.g. mouseup).
    $(document).on(self.activityEvents, extendsess);
    // Start the timers and ping the server to ensure they are in sync with the backend session expiration.
    extendsess();

    return self;
};