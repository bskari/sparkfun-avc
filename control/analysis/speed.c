// Waits for a start, and then times how long until the car breaks the plane of
// a range sensor

const int pingPin = 7;

float microsecondsToInches(const long microseconds);
float microsecondsToCentimeters(const long microseconds);


void setup() {
    Serial.begin(9600);
}


int readLine(char* line) {
    int byteCount = 0;
    while ((line[byteCount++] = Serial.read()) != '\n');
    line[byteCount - 1] = '\0';
}


void loop() {
    // Trigger ping by pulsing pingPin HIGH for 2 microseconds
    pinMode(pingPin, OUTPUT);
    digitalWrite(pingPin, LOW);
    delayMicroseconds(2);
    digitalWrite(pingPin, HIGH);
    delayMicroseconds(5);
    digitalWrite(pingPin, LOW);

    while (1) {
        // Wait for the start option
        char line[20] = "";
        while (strcmp(line, "start") != 0) {
            readLine(line);
        }
        const unsigned long start = millis();

        pinMode(pingPin, INPUT);
        long durationUs = 1000000;
        float cm = microsecondsToCentimeters(durationUs);
        // Wait for the car to cross the threshold
        while (cm > 50) {
            durationUs = pulseIn(pingPin, HIGH);
            cm = microsecondsToCentimeters(durationUs);
        }

        const unsigned long end = millis();

        // Print out the results
        Serial.print("Seconds: ");
        Serial.println(end - start);

        delay(100);
    }
}


float microsecondsToInches(const long microseconds) {
    // According to Parallax's datasheet for the PING))), there are
    // 73.746 microseconds per inch (i.e. sound travels at 1130 feet per
    // second).    This gives the distance travelled by the ping, outbound
    // and return, so we divide by 2 to get the distance of the obstacle.
    // See: <a href="http://www.parallax.com/dl/docs/prod/acc/28015-PING-v1.3.pdf"> <a href="http://www.parallax.com/dl/docs/prod/acc/28015-PI...</a"> <a href="http://www.parallax.com/dl/docs/prod/acc/28015-PI...</a"> http://www.parallax.com/dl/docs/prod/acc/28015-PI...</a>>>
    return float(microseconds) / 74.0f * 0.5f;
}


float microsecondsToCentimeters(const long microseconds) {
    // The speed of sound is 340 m/s or 29 microseconds per centimeter.
    // The ping travels out and back, so to find the distance of the
    // object we take half of the distance travelled.
    return float(microseconds) / 29.0f * 0.5f;
}
