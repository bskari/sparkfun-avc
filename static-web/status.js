// TODO(2015-02-04): Use goog.provide
var sparkfun = sparkfun || {};
sparkfun.status = sparkfun.status || {};

/**
 * @param {
 *  run: Object,
 *  calibrateCompass: Object,
 *  reset: Object,
 *  stop: Object,
 * } buttons
 * @param {Object} throttle
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
 *  compassCalibrated: Object,
 * } telemetryFields
 * @param {Object} logs
 * @param {string} webSocketAddress
 */
sparkfun.status.init = function(
        buttons,
        throttle,
        carFields,
        telemetryFields,
        logs,
        webSocketAddress
) {
    'use strict';
    buttons.run.click(sparkfun.status.run);
    buttons.stop.click(sparkfun.status.stop);
    buttons.reset.click(sparkfun.status.reset);
    buttons.calibrateCompass.click(sparkfun.status.calibrateCompass);
    throttle.change(sparkfun.status.setThrottle);

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
    sparkfun.status.compassCalibrated = telemetryFields.compassCalibrated;

    sparkfun.status.logs = logs;

    sparkfun.status.heading = null;
    // Safari only?
    window.addEventListener('deviceorientation', function(e) {
        sparkfun.status.heading = e.webkitCompassHeading;
    }, false);
    sparkfun.status.followInterval = null;

    sparkfun.status.webSocket = null;
    webSocketAddress = (window.location.protocol === 'http:' ? 'ws://' : 'wss://') + webSocketAddress;
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
        console.log(evt.data);
        var data = JSON.parse(evt.data);
        if (data.type === 'log') {
            sparkfun.status.logs.text(
                data.message + '\n' + sparkfun.status.logs.text());
        } else if (data.type === 'telemetry') {
            console.log(data.message);
            var telemetry = JSON.parse(data.message);
            // Do some processing here to offload the burden from Python
            telemetry['waypoint_distance'] = Math.sqrt(
                sparkfun.status.square(
                    Math.abs(
                        telemetry['x_m'] - telemetry['waypoint_x_m']))
                + sparkfun.status.square(
                    Math.abs(
                        telemetry['y_m'] - telemetry['waypoint_y_m'])));

            telemetry['waypoint_heading'] = sparkfun.status.relativeDegrees(
                telemetry['x_m'],
                telemetry['y_m'],
                telemetry['waypoint_x_m'],
                telemetry['waypoint_y_m']);

            var typeToField = {
                'x_m': sparkfun.status.carX_m,
                'y_m': sparkfun.status.carY_m,
                'speed_m_s': sparkfun.status.carSpeed,
                'heading_d': sparkfun.status.carHeading,
                'throttle': sparkfun.status.carThrottle,
                'steering': sparkfun.status.carSteering,
                'waypoint_x_m': sparkfun.status.waypointX_m,
                'waypoint_y_m': sparkfun.status.waypointY_m,
                'waypoint_distance': sparkfun.status.waypointDistance,
                'waypoint_heading': sparkfun.status.waypointHeading,
                'satellites': sparkfun.status.satellites,
                'accuracy': sparkfun.status.accuracy,
                'compass': sparkfun.status.compass,
                'gps': sparkfun.status.gps,
                'accelerometer': sparkfun.status.accelerometer,
                'compass_calibrated': sparkfun.status.compassCalibrated};
            for (var key in telemetry) {
                if (telemetry.hasOwnProperty(key)) {
                    if (typeof(telemetry[key]) === 'number') {
                        telemetry[key] = sparkfun.status.round(telemetry[key], 3);
                    }
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


sparkfun.status.reset = function () {
    'use strict';
    sparkfun.status._poke('/reset');
};


sparkfun.status.calibrateCompass = function () {
    'use strict';
    sparkfun.status._poke('/calibrate-compass');
};


sparkfun.status.setThrottle = function (evt) {
    'use strict';
    sparkfun.status._poke('/set-max-throttle', {'throttle': evt.currentTarget.value});
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
sparkfun.status._poke = function(url, params) {
    'use strict';
    if (params === undefined) {
        params = '';
    }
    $.post(url, params, function (data, textStatus, jqXHR) {
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
};


/**
 * @param {number} value
 * @return {number}
 */
sparkfun.status.square = function (value) {
    'use strict';
    return value * value;
};


/**
 * @param {number} value
 * @return {number}
 */
sparkfun.status.round = function (value, exponent) {
    'use strict';
    var power = Math.pow(10, exponent);
    return Math.round(value * power) / power;
};



/**
 * @param {number} x1
 * @param {number} y1
 * @param {number} x2
 * @param {number} y2
 * @return {number}
 */
sparkfun.status.relativeDegrees = function (x1, y1, x2, y2) {
    'use strict';
    var relativeY = y2 - y1;
    var relativeX = x2 - x1;
    if (relativeX === 0.0) {
        if (relativeY > 0.0) {
            return 0.0;
        } else {
            return 180.0;
        }
    }

    var degrees = Math.atan(relativeY / relativeX) * 180.0 / 3.14159265358979;
    if (relativeX > 0.0) {
        return 90.0 - degrees;
    }
    return 270.0 - degrees;
};
