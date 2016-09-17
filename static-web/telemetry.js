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
 * @param {string} postAddress
 */
sparkfun.telemetry.init = function(
        buttons,
        telemetryFields,
        webSocketAddress,
        postAddress
) {
    'use strict';
    $(document).ready(function () {
        // iPad treats single clicks as a hover, we need to bind to a different
        // event
        var eventType;
        if (navigator.userAgent.match('iPad')) {
            eventType = 'touchstart';
        } else {
            eventType = 'click';
        }
        buttons.run.bind(eventType, sparkfun.telemetry.run);
        buttons.stop.click(eventType, sparkfun.telemetry.stop);
        buttons.send.click(eventType, sparkfun.telemetry.send);
        buttons.stopSending.click(eventType, sparkfun.telemetry.stopSending);
    });

    sparkfun.telemetry.latitude = telemetryFields.latitude;
    sparkfun.telemetry.longitude = telemetryFields.longitude;
    sparkfun.telemetry.altitude = telemetryFields.altitude;
    sparkfun.telemetry.accuracy = telemetryFields.accuracy;
    sparkfun.telemetry.heading = telemetryFields.heading;
    sparkfun.telemetry.speed = telemetryFields.speed;
    sparkfun.telemetry.timestamp = telemetryFields.timestamp;

    sparkfun.telemetry._noSleep = new NoSleep();
    document.addEventListener('touchstart', sparkfun.telemetry.enableNoSleep, false);

    var parens = /\([^)]*\)/.exec(navigator.userAgent);
    // I think this is supposed to return null if there's no match, but just to
    // be safe, I'm going to test both
    if (parens !== null && parens.length > 0) {
        sparkfun.telemetry.deviceId =
            parens[0].slice(0, -1)
            .split(';')
            .sort(function(a, b) { return b.length - a.length; })[0];
    } else {
        sparkfun.telemetry.deviceId = 'web-telemetry';
    }
    sparkfun.telemetry.deviceId += '-' + String(Math.round(Math.random() * 10000));
    sparkfun.telemetry.postEndPoint = postAddress;
    sparkfun.telemetry.webSocket = null;
    webSocketAddress = (window.location.protocol === 'http:' ? 'ws://' : 'wss://') + webSocketAddress;
    sparkfun.telemetry.webSocket = sparkfun.telemetry.openWebSocket(webSocketAddress);
    if (sparkfun.telemetry.webSocket === null) {
        sparkfun.telemetry.addAlert(
            'Your browser does not support websockets, falling back to POST',
            'alert-info'
        );
    }

    window.onbeforeunload = function(e) {
        sparkfun.telemetry.webSocket.close(1000);
        if (!e) {
            e = window.event;
        }
        e.stopPropogation();
        e.preventDefault();
    };

    if (sparkfun.telemetry.webSocket) {
        sparkfun.telemetry.webSocket.onmessage = function (evt) {
            // TODO(2016-04-27) Figure out where this message is coming from and
            // prevent it from sending
            if (evt.isTrusted !== undefined) {
                return;
            }
            // I don't know why Galaxy S4 is getting messages, but ignore them
            if (navigator.userAgent.match('Android 4.4.4; en-us; SAMSUNG SGH-M919 Build/KTU84P')) {
                return;
            }
            sparkfun.telemetry.addAlert('Unknown message: ' + JSON.stringify(evt));
        };

        sparkfun.telemetry.webSocket.onclose = function (evt) {
            sparkfun.telemetry.addAlert('Connection closed by server');
        };
    }
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
    // Support for old phones that don't follow the spec. They should have
    // position.timestamp as instance of DOMTimeStamp.
    var timestamp;
    if (typeof(position.timestamp) === 'object') {
        timestamp = new Date(String(position.timestamp)).getTime();
    } else {
        timestamp = String(position.timestamp);
    }

    // iPhone 1 doesn't have JSON object. Supporting 8 year old phones!
    var data;
    if (navigator.userAgent.match('iPhone OS 3')) {
        data = (
            '{' +
            '"latitude_d":' + position.coords.latitude + "," +
            '"longitude_d":' + position.coords.longitude + "," +
            '"speed_m_s":' + position.coords.speed + "," +
            '"heading_d":' + position.coords.heading + "," +
            '"accuracy_m":' + position.coords.accuracy + "," +
            '"altitude_m":' + position.coords.altitude + "," +
            '"timestamp_s":' + timestamp + "," +
            '"device_id":"' + sparkfun.telemetry.deviceId + '"' +
            '}'
        );
    } else {
        data = JSON.stringify({
            latitude_d: position.coords.latitude,
            longitude_d: position.coords.longitude,
            speed_m_s: position.coords.speed,
            heading_d: position.coords.heading,
            accuracy_m: position.coords.accuracy,
            altitude_m: position.coords.altitude,
            timestamp_s: timestamp,
            device_id: sparkfun.telemetry.deviceId});
    }

    if (sparkfun.telemetry.webSocket) {
        sparkfun.telemetry.webSocket.send(data);
    } else {
        sparkfun.telemetry._poke(
            sparkfun.telemetry.postEndPoint,
            {'message': data}
        );
    }
    sparkfun.telemetry.latitude.text(position.coords.latitude);
    sparkfun.telemetry.longitude.text(position.coords.longitude);
    sparkfun.telemetry.speed.text(position.coords.speed);
    sparkfun.telemetry.heading.text(position.coords.heading);
    sparkfun.telemetry.accuracy.text(position.coords.accuracy);
    sparkfun.telemetry.altitude.text(position.coords.altitude);
    sparkfun.telemetry.timestamp.text(timestamp);
};


/**
 * @param {string} url
 */
sparkfun.telemetry._poke = function(url, data) {
    'use strict';
    if (data === undefined) {
        data = '';
    }
    $.post(url, data, function (data, textStatus, jqXHR) {
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
 * Returns true if running on a mobile device.
 */
sparkfun.telemetry.isMobile = function() {
    return navigator.userAgent.match(/(iPad)|(iPhone)|(iPod)|(android)|(webOS)/i);
};


/**
 * Delegate for navigator.geolocation. On mobile, this uses GPS, but on desktop,
 * it uses a fake position generator, because Google's geolocation API that uses
 * WiFi rejects websites that are using self-signed certificates.
 */
sparkfun.telemetry.watchPositionDelegate = function(callback, error, options) {
    if (sparkfun.telemetry.isMobile()) {
        return navigator.geolocation.watchPosition(callback, error, options);
    }
    sparkfun.telemetry.addAlert(
        'Desktop browser detected, providing fake data',
        'alert-warning');
    return window.setInterval(function() {
        callback({
            coords: {
                // SSD
                latitude: 40.021405 + ((Math.random() - 0.5) / 1000),
                longitude: -105.250020 + ((Math.random() - 0.5) / 1000),
                speed: 0,
                heading: 90,
                accuracy: 5,
                altitude: 1655
            },
            timestamp: new Date().getTime()
        });
    }, 1000);
};


/**
 * Start sending the telemetry data.
 */
sparkfun.telemetry.send = function () {
    document.addEventListener('touchstart', sparkfun.telemetry.enableNoSleep, false);
    sparkfun.telemetry.watchId = sparkfun.telemetry.watchPositionDelegate(
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
    if (sparkfun.telemetry.isMobile()) {
        navigator.geolocation.clearWatch(sparkfun.telemetry.watchId);
    } else {
        window.clearInterval(sparkfun.telemetry.watchId);
    }
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
sparkfun.telemetry.addAlert = function (message, level) {
    if (level === undefined) {
        level = 'alert-danger';
    }
    if ($('#alerts').children().length > 3) {
        // Delete the oldest one
        $('#alerts').children().first().remove();
    }
    $('#alerts').append(
        '<div class="alert ' + level + '">' +
            '<button type="button" class="close" data-dismiss="alert">' +
            '&times;</button>' + message + '</div>');
};


sparkfun.telemetry.enableNoSleep = function() {
    sparkfun.telemetry._noSleep.enable();
    document.removeEventListener('touchstart', sparkfun.telemetry.enableNoSleep, false);
};


/** Opens a websocket if supported by the platform */
sparkfun.telemetry.openWebSocket = function(webSocketAddress) {
    // Safari won't connect websockets over secure self-signed connections
    if (navigator.userAgent.match('Mac OS X')) {
        return null;
    }
    // And Galaxy S4 doesn't seem to support websockets
    if (navigator.userAgent.match('SAMSUNG SGH-M919 Build/KTU84P')) {
        return null;
    }

    if (window.WebSocket) {
        return new WebSocket(webSocketAddress);
    }
    if (window.MozWebSocket) {
        return new MozWebSocket(webSocketAddress);
    }
    return null;
};
