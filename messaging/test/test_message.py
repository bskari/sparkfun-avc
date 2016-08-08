"""Tests the message framework."""

import threading
import time
import unittest

from messaging.message_consumer import consume_messages
from messaging.message_producer import MessageProducer


class TestMessage(unittest.TestCase):
    """Tests the message framework."""

    EXCHANGE = 'test'

    def setUp(self):
        self.message = None

    def test_1_producer_1_consumer(self):
        """Test single producer single consumer."""
        def save_message(x):
            self.message = x

        def consume():
            """Function to consume messages."""
            consume_messages(self.EXCHANGE, save_message)

        consumer = threading.Thread(target=consume)
        consumer.name = '{}:consume_messages'.format(self.__class__.__name__)
        consumer.start()

        # Give the receiver some time to set up, see comment below
        time.sleep(0.05)
        self.assertIs(self.message, None)
        sent_message = 'banana'
        producer = MessageProducer(self.EXCHANGE)
        producer.publish(sent_message)
        producer.publish('QUIT')
        for _ in range(10):
            # Because of a race condition, if the message is sent before the
            # receiver has set up, the messages are never queued or something.
            # Keep resending until the thread exits.
            consumer.join(0.05)
            if consumer.is_alive():
                producer.publish(sent_message)
                producer.publish('QUIT')

        consumer.join(0.05)
        self.assertFalse(consumer.is_alive())
        producer.kill()
        self.assertEqual(self.message, sent_message)


if __name__ == '__main__':
    unittest.main()
