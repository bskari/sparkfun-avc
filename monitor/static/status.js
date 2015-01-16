// TODO(2015-02-04): Use goog.provide
var sparkfun = sparkfun || {};
sparkfun.status = sparkfun.status || {};

/**
 * @param {
 *  run: Object,
 *  stop: Object,
 *  follow: Object,
 *  calibrateCompass: Object,
 *  line: Object,
 *  count: Object
 * } buttons
 * @param {
 *  x_m: Object,
 *  y_m: Object,
 *  speed: Object,
 *  heading: Object,
 *  throttle: Object,
 *  steering: Object
 * } carFields
 * @param {
 *  waypointX_m: Object,
 *  waypointY_m: Object,
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
    buttons.follow.click(sparkfun.status.follow);
    buttons.calibrateCompass.click(sparkfun.status.calibrateCompass);
    buttons.lineUp.click(sparkfun.status.lineUp);
    buttons.countDown.click(sparkfun.status.countDown);

    sparkfun.status.carX_m = carFields.x_m;
    sparkfun.status.carY_m = carFields.y_m;
    sparkfun.status.carSpeed = carFields.speed;
    sparkfun.status.carHeading = carFields.heading;
    sparkfun.status.carThrottle = carFields.throttle;
    sparkfun.status.carSteering = carFields.steering;

    sparkfun.status.waypointX_m = telemetryFields.waypointX_m;
    sparkfun.status.waypointY_m = telemetryFields.waypointY_m;
    sparkfun.status.waypointDistance = telemetryFields.waypointDistance;
    sparkfun.status.waypointHeading = telemetryFields.waypointHeading;
    sparkfun.status.satellites = telemetryFields.satellites;
    sparkfun.status.accuracy = telemetryFields.accuracy;
    sparkfun.status.compass = telemetryFields.compass;
    sparkfun.status.gps = telemetryFields.gps;
    sparkfun.status.accelerometer = telemetryFields.accelerometer;

    sparkfun.status.logs = logs;

    sparkfun.status.heading = null;
    // Safari only?
    window.addEventListener('deviceorientation', function(e) {
        sparkfun.status.heading = e.webkitCompassHeading;
    }, false);
    sparkfun.status.followInterval = null;

    sparkfun.status.webSocket = null;
    if (window.WebSocket) {
        sparkfun.status.webSocket = new WebSocket(webSocketAddress);
    } else if (window.MozWebSocket) {
        sparkfun.status.webSocket = new MozWebSocket(webSocketAddress);
    }
    if (sparkfun.status.webSocket === null) {
        sparkfun.status.addAlert('Your browser does not support websockets, monitoring disabled');
        return;
    }

    window.onbeforeunload = function(e) {
         sparkfun.status.webSocket.close(1000);
         if (!e) {
             e = window.event;
         }
         e.stopPropogation();
         e.preventDefault();
    };

    sparkfun.status.webSocket.onmessage = function (evt) {
        var data = JSON.parse(evt.data);
        if (data.type === 'log') {
            sparkfun.status.logs.text(
                data.message + '\n' + sparkfun.status.logs.text()
            );
        } else if (data.type === 'telemetry') {
            console.log(data.message);
            var telemetry = JSON.parse(data.message);
            var typeToField = {
                'x_m': sparkfun.status.carX_m,
                'y_m': sparkfun.status.carY_m,
                'speed': sparkfun.status.carSpeed,
                'heading': sparkfun.status.carHeading,
                'throttle': sparkfun.status.carThrottle,
                'steering': sparkfun.status.carSteering,
                'waypoint-x-m': sparkfun.status.waypointX_m,
                'waypoint-y-m': sparkfun.status.waypointY_m,
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

    sparkfun.status.webSocket.onclose = function (evt) {
        sparkfun.status.addAlert('Connection closed by server');
    };
};


sparkfun.status.run = function () {
    'use strict';
    sparkfun.status._poke('/run');
};


sparkfun.status.stop = function () {
    'use strict';
    if (sparkfun.status.followInterval !== null) {
        clearInterval(sparkfun.status.followInterval);
    }
    sparkfun.status._poke('/stop');
};


sparkfun.status.follow = function () {
    'use strict';
    // Do this once to set up the geo permissions
    navigator.geolocation.getCurrentPosition(
        function () {
            sparkfun.status.followInterval = window.setInterval(sparkfun.status.sendPosition, 250);
        });
    sparkfun.status._poke('/follow');
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
sparkfun.status.sendPosition = function() {
    'use strict';
    navigator.geolocation.getCurrentPosition(
        function (position) {
            sparkfun.status.webSocket.send(
                JSON.stringify({
                    "latitude_d": position.coords.latitude,
                    "longitude_d": position.coords.longitude,
                    "speed_m_s": position.coords.speed,
                    "heading_d": sparkfun.status.heading}));
        },
        function (error) {
            alert(JSON.stringify(error));
        }
    );
};


/**
 * @param {string} url
 */
sparkfun.status._poke = function(url) {
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
