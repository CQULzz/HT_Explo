"""One pending observation, with monotonic source stamps and bounded memory."""
from threading import Lock

class LatestInput:
    def __init__(self):
        self._lock=Lock();self._pending=None;self._newest=None;self.replaced=0;self.out_of_order=0
    def put(self,msg):
        key=(msg.header.stamp.sec,msg.header.stamp.nanosec)
        with self._lock:
            if self._newest is not None and key<=self._newest:
                self.out_of_order+=1;return False
            if self._pending is not None:self.replaced+=1
            self._pending=msg;self._newest=key;return True
    def take(self):
        with self._lock:
            msg=self._pending;self._pending=None;return msg
