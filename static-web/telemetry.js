// TODO(2016-04-27): Use goog.provide
var sparkfun = sparkfun || {};
sparkfun.telemetry = sparkfun.telemetry || {};

/**
 * @param {
 *  run: Object,
 *  stop: Object,
 *  send: Object,
 *  stopSending: Object
 * } buttons
 * @param {
 *  latitude:Object,
 *  longitude:Object,
 *  altitude:Object,
 *  accuracy:Object,
 *  heading:Object,
 *  speed:Object,
 *  timestamp:Object
 * } telemetryFields
 * @param {string} webSocketAddress
 */
sparkfun.telemetry.init = function(
        buttons,
        telemetryFields,
        webSocketAddress
) {
    'use strict';
    buttons.run.click(sparkfun.telemetry.run);
    buttons.stop.click(sparkfun.telemetry.stop);
    buttons.send.click(sparkfun.telemetry.send);
    buttons.stopSending.click(sparkfun.telemetry.stopSending);

    sparkfun.telemetry.latitude = telemetryFields.latitude;
    sparkfun.telemetry.longitude = telemetryFields.longitude;
    sparkfun.telemetry.altitude = telemetryFields.altitude;
    sparkfun.telemetry.accuracy = telemetryFields.accuracy;
    sparkfun.telemetry.heading = telemetryFields.heading;
    sparkfun.telemetry.speed = telemetryFields.speed;
    sparkfun.telemetry.timestamp = telemetryFields.timestamp;

    sparkfun.telemetry._noSleep = new NoSleep();
    document.addEventListener('touchstart', sparkfun.telemetry.enableNoSleep, false);

    sparkfun.telemetry.webSocket = null;
    if (window.WebSocket) {
        sparkfun.telemetry.webSocket = new WebSocket(webSocketAddress);
    } else if (window.MozWebSocket) {
        sparkfun.telemetry.webSocket = new MozWebSocket(webSocketAddress);
    }
    if (sparkfun.telemetry.webSocket === null) {
        sparkfun.telemetry.addAlert('Your browser does not support websockets, telemetry disabled');
        return;
    }

    window.onbeforeunload = function(e) {
        sparkfun.telemetry.webSocket.close(1000);
        if (!e) {
            e = window.event;
        }
        e.stopPropogation();
        e.preventDefault();
    };

    sparkfun.telemetry.webSocket.onmessage = function (evt) {
        // TODO(2016-04-27) Figure out where this message is coming from and
        // prevent it from sending
        if (evt.isTrusted !== undefined) {
            return;
        }
        sparkfun.telemetry.addAlert('Unknown message: ' + JSON.stringify(evt));
    };

    sparkfun.telemetry.webSocket.onclose = function (evt) {
        sparkfun.telemetry.addAlert('Connection closed by server');
    };

    sparkfun.telemetry.watchId = null;
};


sparkfun.telemetry.run = function () {
    'use strict';
    sparkfun.telemetry._poke('/run');
};


sparkfun.telemetry.stop = function () {
    'use strict';
    if (sparkfun.telemetry.followInterval !== null) {
        clearInterval(sparkfun.telemetry.followInterval);
    }
    sparkfun.telemetry._poke('/stop');
};


/**
 * Sends position changes to the server.
 * @param {Position} position
 */
sparkfun.telemetry.watch = function(position) {
    'use strict';
    sparkfun.telemetry.webSocket.send(
        JSON.stringify({
            latitude_d: position.coords.latitude,
            longitude_d: position.coords.longitude,
            speed_m_s: position.coords.speed,
            heading_d: position.coords.heading,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            timestamp: position.timestamp}));
    sparkfun.telemetry.latitude.text(position.coords.latitude);
    sparkfun.telemetry.longitude.text(position.coords.longitude);
    sparkfun.telemetry.speed.text(position.coords.speed);
    sparkfun.telemetry.heading.text(position.coords.heading);
    sparkfun.telemetry.accuracy.text(position.coords.accuracy);
    sparkfun.telemetry.altitude.text(position.coords.altitude);
    sparkfun.telemetry.timestamp.text(position.timestamp);
};


/**
 * @param {string} url
 */
sparkfun.telemetry._poke = function(url) {
    'use strict';
    $.post(url, '', function (data, textStatus, jqXHR) {
        if (data.success !== true) {
            if (data.message) {
                sparkfun.telemetry.addAlert('Failed: ' + data.message);
            } else {
                sparkfun.telemetry.addAlert('Failed due to unknown server-side reason');
            }
        }
    }).fail(function () {
        sparkfun.telemetry.addAlert('Failed to contact server');
    });
};


/**
 * @param {string} message
 */
sparkfun.telemetry.addAlert = function (message) {
    $('#alerts').append(
        '<div class="alert alert-danger">' +
            '<button type="button" class="close" data-dismiss="alert">' +
            '&times;</button>' + message + '</div>');
};


/**
 * Start sending the telemetry data.
 */
sparkfun.telemetry.send = function () {
    document.addEventListener('touchstart', sparkfun.telemetry.enableNoSleep, false);
    sparkfun.telemetry.watchId = navigator.geolocation.watchPosition(
        sparkfun.telemetry.watch,
        function (error) {
            console.log(error);
            sparkfun.telemetry.addAlert(error.message);
            sparkfun.telemetry.stopSending();
        },
        {
            enableHighAccuracy: true
        });
};


/**
 * Stops sending the telemetry data.
 */
sparkfun.telemetry.stopSending = function () {
    navigator.geolocation.clearWatch(sparkfun.telemetry.watchId);
    sparkfun.telemetry._noSleep.disable();

    // Enable no sleep next time we touch anything
    // I'd like to make it this only enable when we touch 'send' again, but
    // running this code inside of the 'send' handler would mean we need to
    // click twice to make it work, and I would rather have the failure
    // condition of "on but should be off" than the reverse
    document.addEventListener('touchstart', sparkfun.telemetry.enableNoSleep, false);
};


/**
 * @param {string} message
 */
sparkfun.telemetry.addAlert = function (message) {
    $('#alerts').append(
        '<div class="alert alert-danger">' +
            '<button type="button" class="close" data-dismiss="alert">' +
            '&times;</button>' + message + '</div>');
};


sparkfun.telemetry.enableNoSleep = function() {
    sparkfun.telemetry._noSleep.enable();
    document.removeEventListener('touchstart', sparkfun.telemetry.enableNoSleep, false);
};
