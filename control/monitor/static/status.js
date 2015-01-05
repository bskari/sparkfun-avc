// TODO: Use goog.provide
var sparkfun = sparkfun || {};
sparkfun.status = sparkfun.status || {};

/**
 * @param {
 *  run: Object,
 *  stop: Object,
 *  calibrateCompass: Object,
 *  line: Object,
 *  count: Object
 * } buttons
 * @param {
 *  latitude: Object,
 *  longitude: Object,
 *  speed: Object,
 *  heading: Object,
 *  throttle: Object,
 *  steering: Object
 * } carFields
 * @param {
 *  latitude: Object,
 *  longitude: Object,
 *  speed: Object,
 *  heading: Object,
 *  throttle: Object,
 *  steering: Object
 * }
 * @param {
 *  waypointLatitude: Object,
 *  waypointLongitude: Object,
 *  waypointDistance: Object,
 *  waypointHeading: Object,
 *  satellites: Object,
 *  accuracy: Object,
 *  compass: Object,
 *  gps: Object,
 *  accelerometer: Object,
 * } telemetryFields
 */
sparkfun.status.init = function(buttons, carFields, telemetryFields, webSocketAddress) {
    'use strict';
    buttons.run.click(sparkfun.status.run);
    buttons.stop.click(sparkfun.status.stop);
    buttons.calibrateCompass.click(sparkfun.status.calibrateCompass);
    buttons.lineUp.click(sparkfun.status.lineUp);
    buttons.countDown.click(sparkfun.status.countDown);

    sparkfun.status.carLatitude = carFields.latitude;
    sparkfun.status.carLongitude = carFields.longitude;
    sparkfun.status.carSpeed = carFields.speed;
    sparkfun.status.carHeading = carFields.heading;
    sparkfun.status.carThrottle = carFields.throttle;
    sparkfun.status.carSteering = carFields.steering;

    sparkfun.status.waypointLatitude = telemetryFields.waypointLatitude;
    sparkfun.status.waypointLongitude = telemetryFields.waypointLongitude;
    sparkfun.status.waypointDistance = telemetryFields.waypointDistance;
    sparkfun.status.waypointHeading = telemetryFields.waypointHeading;
    sparkfun.status.satellites = telemetryFields.satellites;
    sparkfun.status.accuracy = telemetryFields.accuracy;
    sparkfun.status.compass = telemetryFields.compass;
    sparkfun.status.gps = telemetryFields.gps;
    sparkfun.status.accelerometer = telemetryFields.accelerometer;

    var webSocket = null;
    if (window.WebSocket) {
        webSocket = new WebSocket(webSocketAddress);
    } else if (window.MozWebSocket) {
        webSocket = new MozWebSocket(webSocketAddress);
    }
    if (webSocket === null) {
        alert('Your browser does not support websockets, monitoring disabled');
        return;
    }

    window.onbeforeunload = function(e) {
         webSocket.close(1000);
         if (!e) {
             e = window.event;
         }
         e.stopPropogation();
         e.preventDefault();
    };

    webSocket.onmessage = function (evt) {
        var data = JSON.parse(evt.data);
        // TODO: Parse the message and do stuff with it
        if (data.type === 'log') {
            alert('Log: ' + data.message);
        } else {
            alert('Type: ' + data.type);
        }
    };

    webSocket.onopen = function (evt) {
        alert("Look at me! I'm using websockets!");
        webSocket.send('Test');
    };

    webSocket.onclose = function (evt) {
        alert('Connection closed by server');
    };
};


sparkfun.status.run = function () {
    'use strict';
    sparkfun.status._poke('/run');
};


sparkfun.status.stop = function () {
    'use strict';
    sparkfun.status._poke('/stop');
};


sparkfun.status.calibrateCompass = function () {
    'use strict';
    sparkfun.status._poke('/calibrate-compass');
};


sparkfun.status.lineUp = function () {
    'use strict';
    sparkfun.status._poke('/line-up');
};


sparkfun.status.countDown = function () {
    'use strict';
    sparkfun.status._poke('/count-down');
};


/**
 * @param {string} url
 */
sparkfun.status._poke= function(url) {
    'use strict';
    $.post(url, '', function (data, textStatus, jqXHR) {
        if (data.success !== true) {
            if (data.message) {
                alert('Failed: ' + data.message);
            } else {
                alert('Failed due to unknown server-side reason');
            }
        }
    }).fail(function () {
        alert('Failed to contact server');
    });
};
