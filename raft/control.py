# control.py
#
# Implementation of the Raft state machine controller.  All system-level
# functions such as networking, persistence, and other details get implemented
# here.

import queue
import logging
import threading
import time

from .machine import RaftMachine
from . import config

class RaftControl:
    def __init__(self, net):
        self.net = net
        self.machine = RaftMachine(self)
        self._events = queue.Queue()
        self._debuglog = logging.getLogger(f'{self.net.address}.control')


    def start(self):
        self._stopped = False

        # Start the networking layer
        self.net.start()

        # Launch the event loop
        threading.Thread(target=self._event_loop, daemon=True).start()

        # Launch the message receiver
        threading.Thread(target=self._message_receiver, daemon=True).start()
        # Launch the heartbeat timer
        threading.Thread(target=self._heartbeat_timer, daemon=True).start()
        # Launch the election timer
        threading.Thread(target=self._election_timer, daemon=True).start()

    def _message_receiver(self):
        while True:
            msg = self.net.recv()
            self._events.put(('message', msg))

    def _heartbeat_timer(self):
        while True:
            time.sleep(config.LEADER_HEARTBEAT)
            self._events.put(('heartbeat',))

    def _election_timer(self):
        pass

    def _event_loop(self):
        while True:
            evt, *args = self._events.get()
            if self._stopped:
                continue

            self._debuglog.debug("Event %r %r", evt, args)

            # Process the event on the underlying machine.  This is the only place where it is safe
            # to do things on the underlying raft state machine.  Basically, all operations occur
            # within a single thread.   There's no chance of concurrent operation. 
            if evt == 'message':
                self.machine.handle_message(*args)
            elif evt == 'election_timeout':
                self.machine.handle_election_timeout()
            elif evt == 'heartbeat':
                self.machine.send_append_entries()
            else:
                raise RuntimeError("Unknown event")


    def suspend(self):
        self._stopped = True

    def resume(self):
        self._stopped = False

    def append_entry(self, entry):
        # Fake client function
        ...


    