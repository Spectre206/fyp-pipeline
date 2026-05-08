"""
Django Channels SSE Consumer — Real-Time Queue Updates

This module implements the Server-Sent Events (SSE) consumer that pushes new
incident arrivals and decision updates to connected dashboard clients in real time.
It uses Django Channels with an in-memory channel layer.

When a new incident arrives in the hitl.queue RabbitMQ queue, a signal is sent
to the SSE channel group, and all connected browser clients receive a push event
containing the new incident summary. The queue page updates without a full page
reload. Decision outcomes (approve/reject/modify) also push update events so
multiple operators see the same queue state without polling.
"""
