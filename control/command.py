"""Class to control the RC car."""

import threading
import time


class Command(threading.Thread):
    """Processes telemetry data and controls the RC car."""

    def __init__(self, telemetry, fake_socket, commands, sleep_time_milliseconds=None):
        """Create the Command thread. fake_socket is just a wrapper around
        some other kind of socket that has a simple "send" method.
        """
        super(Command, self).__init__()

        self._valid_commands = {'start', 'stop'}
        self._telemetry = telemetry
        if sleep_time_milliseconds is None:
            self._sleep_time_milliseconds = 20 
        else:
            self._sleep_time_milliseconds = sleep_time_milliseconds
        self._fake_socket = fake_socket
        self._commands = commands
        self._run = True

    def handle_message(self, message):
        """Handles command messages, e.g. 'start' or 'stop'."""
        # TODO: Process the message and stop using test data
        if 'command' not in message:
            print('No command in command message')
            return
        
        if message['command'] not in self._valid_commands:
            print(
                'Unknown command: "{command}"'.format(
                    command=message['command']
                )
            )
            return

        if message['command'] == 'start':
            self.run()
        elif message['command'] == 'stop':
            self.stop()

    def run(self):
        """Run in a thread, controls the RC car."""
        start_time = 0.0  # Force the car to start driving right away
        command_to_next_command = {
            'forward-left': 'forward',
            'forward': 'forward-left'
        }
        last_command = 'forward-left'

        while self._run:
            # Just drive in circles for now
            now = time.time()
            if now + 1.0 < start_time:
                new_command = command_to_next_command[last_command]
                socket.send(self._commands[new_command])
                start_time = time.time()
                self._telemetry.process_drive_command(new_command)
                last_command = new_command

            try:
                time.sleep(self._sleep_time_milliseconds / 1000.0)
            except:
                pass

    def stop(self):
        self._run = False
