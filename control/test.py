from RPIO import PWM
import socket
import json

THROTTLE_GPIO_PIN = 17
THROTTLE_NEUTRAL_US = 1500
THROTTLE_DIFF = 500
THROTTLE_FORWARD_US = THROTTLE_NEUTRAL_US + THROTTLE_DIFF
THROTTLE_REVERSE_US = THROTTLE_NEUTRAL_US - THROTTLE_DIFF

STEERING_GPIO_PIN = 22
STEERING_NEUTRAL_US = 1650
STEERING_DIFF = 300
STEERING_LEFT_US = STEERING_NEUTRAL_US - STEERING_DIFF
STEERING_RIGHT_US = STEERING_NEUTRAL_US + STEERING_DIFF


def main():
    def get_throttle(percentage):
        # Purposely limit the reverse in case we try to go back while still
        # rolling - prevent damage to the gear box
        if not (-0.25 <= percentage <= 1.0):
            raise ValueError('Bad throttle')
        return int(THROTTLE_NEUTRAL_US + THROTTLE_DIFF * percentage) // 10 * 10

    def get_steering(percentage):
        if not (-1.0 <= percentage <= 1.0):
            raise ValueError('Bad steering')
        return int(STEERING_NEUTRAL_US + STEERING_DIFF * percentage) // 10 * 10

    servo = PWM.Servo(subcycle_time_us=(1000000 // 50))
    # First, shut the damn car up
    throttle_percentage = 0.0
    # And reset the steering
    steering_percentage = 0.0

    socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_.bind(('', 12345))
    socket_.settimeout(2)

    try:
        data = None
        while True:
            print('Throttle: {}, steering: {}'.format(throttle_percentage, steering_percentage))
            servo.set_servo(THROTTLE_GPIO_PIN, get_throttle(throttle_percentage))
            print('Setting steering to {}'.format(steering_percentage))
            servo.set_servo(STEERING_GPIO_PIN, get_steering(steering_percentage))

            try:
                data, address = socket_.recvfrom(1024)
                command = json.loads(data.decode())
            except ValueError as ve:
                print('Unable to parse JSON {}: {}'.format(data, ve))
                continue
            except:
                print('Timed out')
                throttle_percentage = 0.0
                steering_percentage = 0.0
                command = {}

            if 'quit' in command:
                break
            if 'throttle' in command:
                throttle_percentage = float(command['throttle'])
            if 'steering' in command:
                print('Parsing steering')
                steering_percentage = float(command['steering'])
    except Exception as e:
        print('Exception: {}'.format(e))
    finally:
        servo.stop_servo(THROTTLE_GPIO_PIN)
        servo.stop_servo(STEERING_GPIO_PIN)


if __name__ == '__main__':
    for i in range(10):
        main()
