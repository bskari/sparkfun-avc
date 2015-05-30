"""Handles physical button presses."""

#import RPIO
import threading
import time


BUTTON_GPIO_PIN = 23
BUTTON_DOWN = 1
BUTTON_UP = 0


class Button(threading.Thread):  # pylint: disable=too-few-public-methods
    """Listens for physical button presses and controls the car."""

    def __init__(self, command, logger):
        super(Button, self).__init__()
        self._command = command
        self._logger = logger

        self._button_press_time = None
        self._run = True

        #RPIO.add_interrupt_callback(
        #    BUTTON_GPIO_PIN,
        #    self.gpio_callback,
        #    debounce_timeout_ms=50
        #)

    def run(self):
        """Run in a thread, waits for button presses."""
        while self._run:
            #RPIO.wait_for_interrupts()
            time.sleep(1)

    def kill(self):
        """Stops the thread."""
        self._run = False
        #RPIO.stop_waiting_for_interrupts()

    def gpio_callback(self, gpio_id, value):
        """Called when the button is pressed."""
        if value == BUTTON_UP:
            return

        self._logger.info('Button pressed: GPIO pin {pin}'.format(pin=gpio_id))

        # One press to start, two within a second to stop
        if self._command.is_running_course():
            if time.time() - self._button_press_time < 1.0:
                self._command.handle_message({'command': 'stop'})
        else:
            self._command.handle_message({'command': 'start'})

        self._button_press_time = time.time()
