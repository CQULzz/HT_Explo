"""One pending observation, with monotonic source stamps and bounded memory."""
from threading import Lock
import time

class LatestInput:
    def __init__(self,clock=time.monotonic):
        self._lock=Lock();self._pending=None;self._newest=None;self.replaced=0;self.out_of_order=0
        self._clock=clock;self._received_at=None
        self.received=0;self.accepted=0;self.taken=0
        self.dropped_on_shutdown=0
        self.last_received_at=None;self.receive_interval_s=None
    def put(self,msg):
        key=(msg.header.stamp.sec,msg.header.stamp.nanosec)
        with self._lock:
            now=self._clock();self.received+=1
            self.receive_interval_s=None if self.last_received_at is None else now-self.last_received_at
            self.last_received_at=now
            if self._newest is not None and key<=self._newest:
                self.out_of_order+=1;return False
            if self._pending is not None:self.replaced+=1
            self._pending=msg;self._newest=key;self._received_at=now;self.accepted+=1;return True
    def take(self):
        item=self.take_with_metadata()
        return None if item is None else item[0]
    def take_with_metadata(self):
        with self._lock:
            if self._pending is None:return None
            item=(self._pending,self._received_at);self._pending=None;self._received_at=None;self.taken+=1
            return item
    def status(self):
        with self._lock:
            return {'received':self.received,'accepted':self.accepted,'taken':self.taken,
                    'replaced':self.replaced,'out_of_order':self.out_of_order,
                    'dropped_on_shutdown':self.dropped_on_shutdown,
                    'pending':self._pending is not None,'receive_interval_s':self.receive_interval_s}
    def clear_for_shutdown(self):
        with self._lock:
            if self._pending is not None:self.dropped_on_shutdown+=1
            self._pending=None;self._received_at=None
