// TODO(2015-02-04): Use goog.provide
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
 * @param {Object} logs
 * @param {string} webSocketAddress
 */
sparkfun.status.init = function(
        buttons,
        carFields,
        telemetryFields,
        logs,
        webSocketAddress
) {
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

    sparkfun.status.logs = logs;

    var webSocket = null;
    if (window.WebSocket) {
        webSocket = new WebSocket(webSocketAddress);
    } else if (window.MozWebSocket) {
        webSocket = new MozWebSocket(webSocketAddress);
    }
    if (webSocket === null) {
        sparkfun.status.addAlert('Your browser does not support websockets, monitoring disabled');
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
        if (data.type === 'log') {
            sparkfun.status.logs.text(
                data.message + '\n' + sparkfun.status.logs.text()
            );
        } else if (data.type === 'telemetry') {
            console.log(data.message);
            var telemetry = JSON.parse(data.message);
            var typeToField = {
                'latitude': sparkfun.status.carLatitude,
                'longitude': sparkfun.status.carLongitude,
                'speed': sparkfun.status.carSpeed,
                'heading': sparkfun.status.carHeading,
                'throttle': sparkfun.status.carThrottle,
                'steering': sparkfun.status.carSteering,
                'waypoint-latitude': sparkfun.status.waypointLatitude,
                'waypoint-longitude': sparkfun.status.waypointLongitude,
                'waypoint-distance': sparkfun.status.waypointDistance,
                'waypoint-heading': sparkfun.status.waypointHeading,
                'satellites': sparkfun.status.satellites,
                'accuracy': sparkfun.status.accuracy,
                'compass': sparkfun.status.compass,
                'gps': sparkfun.status.gps,
                'accelerometer': sparkfun.status.accelerometer
            };
            for (var key in telemetry) {
                if (telemetry.hasOwnProperty(key)) {
                    if (typeToField[key] !== undefined) {
                        typeToField[key].text(telemetry[key]);
                    }
                }
            }
        } else {
            sparkfun.status.addAlert('Unknown message type: ' + data.type);
        }
    };

    webSocket.onclose = function (evt) {
        sparkfun.status.addAlert('Connection closed by server');
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
                sparkfun.status.addAlert('Failed: ' + data.message);
            } else {
                sparkfun.status.addAlert('Failed due to unknown server-side reason');
            }
        }
    }).fail(function () {
        sparkfun.status.addAlert('Failed to contact server');
    });
};


/**
 * @param {string} message
 */
sparkfun.status.addAlert = function (message) {
    $('#alerts').append(
        '<div class="alert alert-danger">' +
            '<button type="button" class="close" data-dismiss="alert">' +
            '&times;</button>' + message + '</div>');
}
