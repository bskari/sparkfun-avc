// TODO(2016-04-27): Use goog.provide
var sparkfun = sparkfun || {};
sparkfun.telemetry = sparkfun.telemetry || {};

/**
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
sparkfun.telemetry.Telemetry = function(
        telemetryFields,
        webSocketAddress,
        postAddress
) {
    'use strict';
    this.latitude = telemetryFields.latitude;
    this.longitude = telemetryFields.longitude;
    this.altitude = telemetryFields.altitude;
    this.accuracy = telemetryFields.accuracy;
    this.heading = telemetryFields.heading;
    this.speed = telemetryFields.speed;
    this.timestamp = telemetryFields.timestamp;

    this._noSleep = new NoSleep();
    document.addEventListener('touchstart', this.enableNoSleep, false);

    var parens = /\([^)]*\)/.exec(navigator.userAgent);
    // I think this is supposed to return null if there's no match, but just to
    // be safe, I'm going to test both
    if (parens !== null && parens.length > 0) {
        this.deviceId =
            parens[0].slice(0, -1)
            .split(';')
            .sort(function(a, b) { return b.length - a.length; })[0];
    } else {
        this.deviceId = 'web-telemetry';
    }
    this.deviceId += '-' + String(Math.round(Math.random() * 10000));
    this.postEndPoint = postAddress;
    this.webSocket = null;
    webSocketAddress = (window.location.protocol === 'http:' ? 'ws://' : 'wss://') + webSocketAddress;
    this.webSocket = sparkfun.telemetry.openWebSocket(webSocketAddress);
    if (this.webSocket === null) {
        sparkfun.telemetry.addAlert(
            'Your browser does not support websockets, falling back to POST',
            'alert-info'
        );
    }

    window.onbeforeunload = function(e) {
        this.webSocket.close(1000);
        if (!e) {
            e = window.event;
        }
        e.stopPropogation();
        e.preventDefault();
    }.bind(this);

    if (this.webSocket) {
        this.webSocket.onmessage = function (evt) {
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

        this.webSocket.onclose = function (evt) {
            sparkfun.telemetry.addAlert('Connection closed by server');
        };
    }
    this.watchId = null;
};


/**
 * Binds the buttons to the actions. I was having trouble getting this to work
 * in the constructor, so just do it here instead.
 * @param {
 *  run: Object,
 *  stop: Object,
 *  send: Object,
 *  stopSending: Object
 * } buttons
 */
sparkfun.telemetry.Telemetry.prototype.bindButtons = function(buttons) {
    // iPad treats single clicks as a hover, we need to bind to a different
    // event
    var eventType;
    if (navigator.userAgent.match('iPad')) {
        eventType = 'touchstart';
    } else {
        eventType = 'click';
    }
    buttons.run.bind(eventType, this.run.bind(this));
    buttons.stop.click(eventType, this.stop.bind(this));
    buttons.send.click(eventType, this.send.bind(this));
    buttons.stopSending.click(eventType, this.stopSending.bind(this));
};


sparkfun.telemetry.Telemetry.prototype.run = function () {
    'use strict';
    sparkfun.telemetry.poke('/run');
};


sparkfun.telemetry.Telemetry.prototype.stop = function () {
    'use strict';
    if (this.followInterval !== null) {
        clearInterval(this.followInterval);
    }
    sparkfun.telemetry.poke('/stop');
};


/**
 * Sends position changes to the server.
 * @param {Position} position
 */
sparkfun.telemetry.Telemetry.prototype.watch = function(position) {
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
            '"device_id":"' + this.deviceId + '"' +
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
            device_id: this.deviceId});
    }

    if (this.webSocket) {
        this.webSocket.send(data);
    } else {
        sparkfun.telemetry.poke(
            this.postEndPoint,
            {'message': data}
        );
    }
    this.latitude.text(position.coords.latitude);
    this.longitude.text(position.coords.longitude);
    this.speed.text(position.coords.speed);
    this.heading.text(position.coords.heading);
    this.accuracy.text(position.coords.accuracy);
    this.altitude.text(position.coords.altitude);
    this.timestamp.text(timestamp);
};


/**
 * Sends a POST request to the url.
 * @param {string} url
 * @param {object} data
 */
sparkfun.telemetry.poke = function(url, data) {
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
sparkfun.telemetry.Telemetry.prototype.send = function () {
    document.addEventListener('touchstart', this.enableNoSleep, false);
    this.watchId = sparkfun.telemetry.watchPositionDelegate(
        this.watch.bind(this),
        function (error) {
            console.log(error);
            sparkfun.telemetry.addAlert(error.message);
            this.stopSending();
        }.bind(this),
        {
            enableHighAccuracy: true
        });
};


/**
 * Stops sending the telemetry data.
 */
sparkfun.telemetry.Telemetry.prototype.stopSending = function () {
    if (sparkfun.telemetry.isMobile()) {
        navigator.geolocation.clearWatch(this.watchId);
    } else {
        window.clearInterval(this.watchId);
    }
    this._noSleep.disable();

    // Enable no sleep next time we touch anything
    // I'd like to make it this only enable when we touch 'send' again, but
    // running this code inside of the 'send' handler would mean we need to
    // click twice to make it work, and I would rather have the failure
    // condition of "on but should be off" than the reverse
    document.addEventListener('touchstart', this.enableNoSleep, false);
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


sparkfun.telemetry.Telemetry.prototype.enableNoSleep = function() {
    this._noSleep.enable();
    document.removeEventListener('touchstart', this.enableNoSleep, false);
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
        return new window.WebSocket(webSocketAddress);
    }
    if (window.MozWebSocket) {
        return new window.MozWebSocket(webSocketAddress);
    }
    return null;
};
