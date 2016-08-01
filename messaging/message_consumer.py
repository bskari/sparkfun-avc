"""Message broker that receives from RabbitMQ."""

import pika


def consume_messages(message_type, callback, host=None):
    """Starts consuming messages."""
    if host is None:
        host = 'localhost'

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=host)
    )
    channel = connection.channel()
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=message_type, queue=queue_name)
    consumer_tag = None

    def inner_callback(channel, method, properties, body):
        """Callback that intercepts quit messages."""
        if body == b'QUIT':
            channel.basic_cancel(consumer_tag)
            return
        callback(body.decode('utf-8'))

    consumer_tag = channel.basic_consume(
        inner_callback,
        queue=queue_name,
        no_ack=True
    )

    channel.start_consuming()
