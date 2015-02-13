"""Drive the Grasshopper using a joypad or keyboard."""
import argparse
import json
import pygame
import socket
import time


def make_parser():
    """Builds and returns an argument parser."""
    parser = argparse.ArgumentParser(
        description='Manual control of the Tamiya Grasshopper.'
    )

    parser.add_argument(
        '-q',
        '--quiet',
        dest='quiet',
        help='Silence output.',
        action='store_true'
    )

    parser.add_argument(
        '-s',
        '--server',
        dest='server',
        help='The IP address of the Tamiya server.',
        default='10.1',
        type=str,
    )

    parser.add_argument(
        '-p',
        '--port',
        dest='port',
        help='The por that the Tamiya server is listening on.',
        default=12345,
        type=int,
    )

    return parser


def get_throttle_and_steering_keyboard():  # pylint: disable=invalid-name
    """Returns the throttle and and steering values from the keyboard."""
    keys = pygame.key.get_pressed()

    direction = 0.0
    power = 0.0
    if keys[pygame.K_UP]:
        direction = 1.0
        power = 0.25
    elif keys[pygame.K_DOWN]:
        direction = -1.0
        power = 0.25

    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
        power = 1.0

    steering = 0.0
    if keys[pygame.K_LEFT]:
        steering = -0.5
    if keys[pygame.K_RIGHT]:
        steering = 0.5

    throttle = direction * power
    if throttle < -0.5:
        throttle = -0.5

    return (throttle, steering)


def get_throttle_and_steering_joystick(joystick):  # pylint: disable=invalid-name
    """Returns the throttle and steering values from the joystick."""
    throttle = 0.0
    throttle = throttle or joystick.get_button(8) * -0.25 # Select
    throttle = throttle or joystick.get_button(3) * 0.25
    throttle = throttle or joystick.get_button(2) * 0.5
    throttle = throttle or joystick.get_button(1) * 0.75
    throttle = throttle or joystick.get_button(0) * 1.0

    steering = 0.0
    steering = steering or joystick.get_axis(0) * 0.5
    steering = steering or joystick.get_button(4) * -1.0 # Left shoulder button
    steering = steering or joystick.get_button(5) * 1.0 # Right shoulder button

    return (throttle, steering)


def main():
    """Send commands to the car."""
    parser = make_parser()
    args = parser.parse_args()

    pygame.init()
    _ = pygame.display.set_mode((640, 480))
    pygame.display.set_caption('Pygame Caption')
    try:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
    except Exception as joystick_exception:  # pylint: disable=broad-except
        print('No joystick: {}'.format(joystick_exception))
        joystick = None

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    last_send_time = time.time()
    while True:
        time.sleep(0.1)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            # Possible joystick actions: JOYAXISMOTION JOYBALLMOTION
            # JOYBUTTONDOWN JOYBUTTONUP JOYHATMOTION
            if event.type in (
                pygame.JOYBUTTONUP,
                pygame.JOYBUTTONDOWN,
                pygame.JOYAXISMOTION,
                pygame.KEYDOWN,
                pygame.KEYUP,
            ):
                if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                    throttle, steering = get_throttle_and_steering_keyboard()
                else:
                    throttle, steering = get_throttle_and_steering_joystick(
                        joystick
                    )
                command = json.dumps({
                    'throttle': throttle,
                    'steering': steering,
                })
                if not args.quiet:
                    print(command)
                sock.sendto(
                    command,
                    (args.server, args.port)
                )
                last_send_time = time.time()

        # Send a keep-alive request at least once per second
        if time.time() - last_send_time > 1.0:
            if not args.quiet:
                print('Sending keep alive')
            sock.sendto('{"keep_alive": true}', (args.server, args.port))
            last_send_time = time.time()


if __name__ == '__main__':
    try:
        main()
    finally:
        pygame.quit()
