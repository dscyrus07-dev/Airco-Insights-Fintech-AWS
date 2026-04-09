"""
RabbitMQ message queue client for event-driven architecture.
"""

import asyncio
import inspect
import json
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import pika

from ..core.config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class MessageQueue:
    """RabbitMQ message queue client built on pika BlockingConnection."""

    def __init__(self):
        self.connection_url = settings.RABBITMQ_URL
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self._publisher_connection: Optional[pika.BlockingConnection] = None
        self._publisher_channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self._consumers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._connected = False
        self._consumer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def _create_connection(self) -> None:
        parameters = pika.URLParameters(self.connection_url)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        self._declare_topology()
        self._connected = True

    def _probe_connection(self) -> None:
        parameters = pika.URLParameters(self.connection_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.basic_qos(prefetch_count=1)
        for exchange in ["file_processing", "pdf_processing", "ai_processing", "report_processing"]:
            channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        connection.close()
        self._connected = True

    def _declare_topology(self) -> None:
        assert self.channel is not None

        exchanges = ["file_processing", "pdf_processing", "ai_processing", "report_processing"]
        for exchange in exchanges:
            self.channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)

        queues = [
            ("file_upload_queue", "file_processing", "file.uploaded"),
            ("pdf_processing_queue", "pdf_processing", "pdf.process"),
            ("ai_analysis_queue", "ai_processing", "ai.analyze"),
            ("report_generation_queue", "report_processing", "report.generate"),
        ]

        for queue_name, exchange, routing_key in queues:
            self.channel.queue_declare(queue=queue_name, durable=True)
            self.channel.queue_bind(queue=queue_name, exchange=exchange, routing_key=routing_key)

    def _declare_topology_on_channel(self, channel) -> None:
        exchanges = ["file_processing", "pdf_processing", "ai_processing", "report_processing"]
        for exchange in exchanges:
            channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)

        queues = [
            ("file_upload_queue", "file_processing", "file.uploaded"),
            ("pdf_processing_queue", "pdf_processing", "pdf.process"),
            ("ai_analysis_queue", "ai_processing", "ai.analyze"),
            ("report_generation_queue", "report_processing", "report.generate"),
        ]

        for queue_name, exchange, routing_key in queues:
            channel.queue_declare(queue=queue_name, durable=True)
            channel.queue_bind(queue=queue_name, exchange=exchange, routing_key=routing_key)

    def _ensure_publisher_channel(self):
        if (
            self._publisher_connection
            and self._publisher_connection.is_open
            and self._publisher_channel
            and self._publisher_channel.is_open
        ):
            return self._publisher_channel

        parameters = pika.URLParameters(self.connection_url)
        self._publisher_connection = pika.BlockingConnection(parameters)
        self._publisher_channel = self._publisher_connection.channel()
        self._publisher_channel.basic_qos(prefetch_count=1)
        self._declare_topology_on_channel(self._publisher_channel)
        return self._publisher_channel

    def _close_publisher_connection(self) -> None:
        with self._lock:
            try:
                if self._publisher_connection and self._publisher_connection.is_open:
                    self._publisher_connection.close()
            except Exception:
                pass
            self._publisher_connection = None
            self._publisher_channel = None

    async def connect(self):
        """Connect to RabbitMQ without blocking the event loop."""
        try:
            await asyncio.to_thread(self._probe_connection)
            logger.info("Connected to RabbitMQ", url=self.connection_url)
        except Exception as e:
            self._connected = False
            logger.warning("RabbitMQ unavailable; continuing without queue", error=str(e))

    def register_consumer(self, queue_name: str, callback: Callable[[Dict[str, Any]], Any]):
        """Register a consumer for a queue."""
        self._consumers[queue_name] = callback
        logger.info("Consumer registered", queue=queue_name)

    def _message_callback(self, queue_name: str, user_callback: Callable[[Dict[str, Any]], Any]):
        def _callback(ch, method, properties, body):
            try:
                payload = json.loads(body.decode("utf-8"))
                logger.info("Consumed message", queue=queue_name, payload_keys=list(payload.keys()))

                if inspect.iscoroutinefunction(user_callback):
                    result = asyncio.run(user_callback(payload))
                else:
                    result = user_callback(payload)

                if result is False:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                else:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error("Consumer failed", queue=queue_name, error=str(e))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        return _callback

    def _start_consumer_loop(self):
        while not self._stop_event.is_set():
            connection = None
            channel = None
            try:
                parameters = pika.URLParameters(self.connection_url)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.basic_qos(prefetch_count=1)
                self._connected = True
                self.connection = connection
                self.channel = channel

                for exchange in ["file_processing", "pdf_processing", "ai_processing", "report_processing"]:
                    channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)

                for queue_name, callback in self._consumers.items():
                    channel.queue_declare(queue=queue_name, durable=True)
                    if queue_name == "file_upload_queue":
                        channel.queue_bind(queue=queue_name, exchange="file_processing", routing_key="file.uploaded")
                    elif queue_name == "pdf_processing_queue":
                        channel.queue_bind(queue=queue_name, exchange="pdf_processing", routing_key="pdf.process")
                    elif queue_name == "ai_analysis_queue":
                        channel.queue_bind(queue=queue_name, exchange="ai_processing", routing_key="ai.analyze")
                    elif queue_name == "report_generation_queue":
                        channel.queue_bind(queue=queue_name, exchange="report_processing", routing_key="report.generate")

                    channel.basic_consume(
                        queue=queue_name,
                        on_message_callback=self._message_callback(queue_name, callback),
                        auto_ack=False,
                    )

                logger.info("RabbitMQ consumer loop starting", queues=list(self._consumers.keys()))
                channel.start_consuming()
            except pika.exceptions.ConnectionClosedByBroker:
                logger.warning("RabbitMQ broker closed consumer connection; retrying")
            except Exception as e:
                logger.error("RabbitMQ consumer initialization failed", error=str(e))
            finally:
                try:
                    if connection and connection.is_open:
                        connection.close()
                except Exception:
                    pass
                self._connected = False

            if not self._stop_event.is_set():
                time.sleep(5)

    async def start_consuming(self):
        """Start consuming messages in a background thread."""
        if self._consumer_thread and self._consumer_thread.is_alive():
            return

        self._stop_event.clear()
        self._consumer_thread = threading.Thread(target=self._start_consumer_loop, daemon=True)
        self._consumer_thread.start()
        logger.info("RabbitMQ consumer thread started")

    def _publish_sync(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            with self._lock:
                channel = self._ensure_publisher_channel()
                body = json.dumps(message).encode("utf-8")
                channel.basic_publish(
                    exchange=exchange,
                    routing_key=routing_key,
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type="application/json",
                        headers=headers or {},
                        timestamp=int(datetime.utcnow().timestamp()),
                    ),
                )
            return True
        except Exception as e:
            self._close_publisher_connection()
            logger.warning("RabbitMQ publish connection failed", error=str(e))
            return False

    async def publish_message(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ):
        """Publish a message to RabbitMQ."""
        try:
            success = await asyncio.to_thread(self._publish_sync, exchange, routing_key, message, headers)
            if not success:
                logger.warning("RabbitMQ not connected; message not published", exchange=exchange, routing_key=routing_key)
                return False

            logger.info("Message published", exchange=exchange, routing_key=routing_key)
            return True
        except Exception as e:
            logger.error("Failed to publish message", exchange=exchange, routing_key=routing_key, error=str(e))
            return False

    async def close(self):
        """Close the connection and stop consumers."""
        self._stop_event.set()
        self._close_publisher_connection()
        if self.connection and self.connection.is_open:
            try:
                self.connection.add_callback_threadsafe(lambda: self.channel and self.channel.stop_consuming())
            except Exception:
                pass

        if self.connection and self.connection.is_open:
            try:
                await asyncio.to_thread(self.connection.close)
            except Exception:
                pass

        self._connected = False
        logger.info("RabbitMQ connection closed")


# Global message queue instance
message_queue = MessageQueue()
