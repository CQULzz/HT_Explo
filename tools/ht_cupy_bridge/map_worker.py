"""One event-driven inference owner, retaining LatestInput source ordering."""
from threading import Condition,Thread,current_thread

class MapWorker:
    def __init__(self,pending,callback):
        self.pending=pending;self.callback=callback;self.failure=None
        self._condition=Condition();self._stopping=False
        self.thread=Thread(target=self._run,name='HT-map-worker',daemon=False)
        self.thread.start()

    def submit(self,msg):
        with self._condition:
            if self._stopping:return False
            accepted=self.pending.put(msg)
            if accepted:self._condition.notify()
            return accepted

    def _run(self):
        try:
            while True:
                with self._condition:
                    while True:
                        if self._stopping:return
                        item=self.pending.take_with_metadata()
                        if item is not None:break
                        self._condition.wait()
                # Never hold the condition during inference or ROS publication.
                self.callback(item[0],received_monotonic=item[1])
        except BaseException as error:
            # The owning main loop propagates this as a process failure.
            self.failure=error

    def close(self):
        with self._condition:
            self._stopping=True;self.pending.clear_for_shutdown()
            self._condition.notify_all()
        if current_thread() is not self.thread:self.thread.join()
