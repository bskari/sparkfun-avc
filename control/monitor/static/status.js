// TODO: Use goog.provide
var sparkfun = sparkfun || {};
sparkfun.status = sparkfun.status || {};

/**
 * @param {
 *  start: Object,
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
sparkfun.status.init = function(buttons, carFields, telemetryFields) {
    'use strict';
    buttons.start.click(sparkfun.status.start);
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

    setInterval(sparkfun.status.pollData, 250);
};


sparkfun.status.pollData = function () {
    // TODO Implement this
};


sparkfun.status.start = function () {
    sparkfun.status._poke('/run');
};


sparkfun.status.stop = function () {
    sparkfun.status._poke('/stop');
};


sparkfun.status.calibrateCompass = function () {
    sparkfun.status._poke('/calibrate_compass');
};


sparkfun.status.lineUp = function () {
    sparkfun.status._poke('/line_up');
};


sparkfun.status.countDown = function () {
    sparkfun.status._poke('/count_down');
};


/**
 * @param {url: string}
 */
sparkfun.status._poke = function (url) {
    $.post(
        url,
        '',
        function (data, textStatus, jqXHR) {
            if (data.success !== true) {
                alert('Failed: ' + data.message);
            }
        }
    ).fail(function () {
        alert('Unable to contact server');
    });
};
