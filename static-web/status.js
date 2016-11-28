// TODO(2015-02-04): Use goog.provide
var sparkfun = sparkfun || {};
sparkfun.status = sparkfun.status || {};

/**
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
sparkfun.status.Status = function(
    carFields,
    telemetryFields,
    logs,
    webSocketAddress
) {
    'use strict';

    this.carX_m = carFields.x_m;
    this.carY_m = carFields.y_m;
    this.carSpeed = carFields.speed;
    this.carHeading = carFields.heading;
    this.carThrottle = carFields.throttle;
    this.carSteering = carFields.steering;

    this.waypointX_m = telemetryFields.waypointX_m;
    this.waypointY_m = telemetryFields.waypointY_m;
    this.waypointDistance = telemetryFields.waypointDistance;
    this.waypointHeading = telemetryFields.waypointHeading;
    this.satellites = telemetryFields.satellites;
    this.accuracy = telemetryFields.accuracy;
    this.compass = telemetryFields.compass;
    this.gps = telemetryFields.gps;
    this.accelerometer = telemetryFields.accelerometer;
    this.compassCalibrated = telemetryFields.compassCalibrated;

    this.logs = logs;

    this.heading = null;

    this.webSocket = null;
    webSocketAddress = (window.location.protocol === 'http:' ? 'ws://' : 'wss://') + webSocketAddress;
    if (!navigator.userAgent.match('Mac OS X') && window.WebSocket) {
        this.webSocket = new WebSocket(webSocketAddress);
    } else if (!navigator.userAgent.match('Mac OS X') && window.MozWebSocket) {
        this.webSocket = new MozWebSocket(webSocketAddress);
    }
    if (this.webSocket === null) {
        sparkfun.status.addAlert(
            'Your browser does not support websockets, disabling logging and reverting to GET'
        );
    }

    window.onbeforeunload = function(e) {
        if (this.webSocket) {
            this.webSocket.close(1000);
        }
        if (!e) {
            e = window.event;
        }
        e.stopPropogation();
        e.preventDefault();
    }.bind(this);

    if (this.webSocket) {
        this.webSocket.onmessage = function(evt) {
            var data = JSON.parse(evt.data);
            if (data.type === 'log') {
                this.logs.text(
                    data.message + '\n' + this.logs.text());
            } else if (data.type === 'telemetry') {
                this.handleTelemetryMessage(JSON.parse(data.message));
            } else {
                sparkfun.status.addAlert('Unknown message type: ' + data.type);
            }
        }.bind(this);

        this.webSocket.onclose = function (evt) {
            sparkfun.status.addAlert('Connection closed by server');
        };
    } else {
        var url = document.location + '/telemetry-json';
        window.setInterval(function () {
            $.getJSON(url, function(data) {
                this.handleTelemetryMessage(data);
            }.bind(this));
        }.bind(this), 1000);
    }
};


/**
 * @param {
 *  run: Object,
 *  calibrateCompass: Object,
 *  reset: Object,
 *  stop: Object,
 *  shutDown: Object,
 * } buttons
 * @param {Object} throttle
 * @param {Array<String>} waypointFiles
 */
sparkfun.status.Status.prototype.bindButtons = function(buttons, throttle, waypointFiles) {
    // iPad treats single clicks as a hover, we need to bind to a different
    // event
    var eventType;
    if (navigator.userAgent.match('iPad')) {
        eventType = 'touchstart';
    } else {
        eventType = 'click';
    }
    buttons.run.bind(eventType, this.run.bind(this));
    buttons.stop.bind(eventType, this.stop.bind(this));
    buttons.reset.bind(eventType, this.reset.bind(this));
    buttons.calibrateCompass.bind(eventType, this.calibrateCompass.bind(this));
    buttons.shutDown.bind(eventType, this.confirmShutDown.bind(this));
    throttle.change(this.setThrottle.bind(this));
    waypointFiles.change(this.setWaypoints.bind(this));
};


sparkfun.status.Status.prototype.handleTelemetryMessage = function(telemetry) {
    'use strict';
    // Do some processing here to offload the burden from Python
    var xSquare = sparkfun.status.square(
        Math.abs(
            telemetry.x_m - telemetry.waypoint_x_m));
    var ySquare = sparkfun.status.square(
        Math.abs(
            telemetry.y_m - telemetry.waypoint_y_m));
    telemetry.waypoint_distance_m = Math.sqrt(xSquare + ySquare);

    telemetry.waypoint_heading_d = sparkfun.status.relativeDegrees(
        telemetry.x_m,
        telemetry.y_m,
        telemetry.waypoint_x_m,
        telemetry.waypoint_y_m);

    var typeToField = {
        'x_m': this.carX_m,
        'y_m': this.carY_m,
        'speed_m_s': this.carSpeed,
        'heading_d': this.carHeading,
        'throttle': this.carThrottle,
        'steering': this.carSteering,
        'waypoint_x_m': this.waypointX_m,
        'waypoint_y_m': this.waypointY_m,
        'waypoint_distance_m': this.waypointDistance,
        'waypoint_heading_d': this.waypointHeading,
        'satellites': this.satellites,
        'accuracy': this.accuracy,
        'compass': this.compass,
        'gps': this.gps,
        'accelerometer': this.accelerometer,
        'compass_calibrated': this.compassCalibrated};
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
};


sparkfun.status.Status.prototype.run = function () {
    'use strict';
    this._poke('/run');
};


sparkfun.status.Status.prototype.stop = function () {
    'use strict';
    this._poke('/stop');
};


sparkfun.status.Status.prototype.reset = function () {
    'use strict';
    this._poke('/reset');
};


sparkfun.status.Status.prototype.calibrateCompass = function () {
    'use strict';
    this._poke('/calibrate-compass');
};


sparkfun.status.Status.prototype.setThrottle = function (evt) {
    'use strict';
    this._poke('/set-max-throttle', {'throttle': evt.currentTarget.value});
};


sparkfun.status.Status.prototype.setWaypoints = function (evt) {
    'use strict';
    this._poke('/set-waypoints', {'kml_file_name': evt.currentTarget.value});
};


sparkfun.status.Status.prototype.confirmShutDown = function (evt) {
    'use strict';
    if (confirm('Shut down?')) {
        this._poke('/shut-down');
    }
};


/**
 * @param {string} url
 */
sparkfun.status.Status.prototype.sendPosition = function() {
    'use strict';
    navigator.geolocation.getCurrentPosition(
        function (position) {
            this.webSocket.send(
                JSON.stringify({
                    "latitude_d": position.coords.latitude,
                    "longitude_d": position.coords.longitude,
                    "speed_m_s": position.coords.speed,
                    "heading_d": this.heading}));
        }.bind(this),
        function (error) {
            alert(JSON.stringify(error));
        }
    );
};


/**
 * @param {string} url
 */
sparkfun.status.Status.prototype._poke = function(url, params) {
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
