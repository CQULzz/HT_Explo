"""Bounded online history; optional full experiment journal on an I/O worker."""
from collections import deque
import json
from pathlib import Path
from queue import Full, Queue
from threading import Thread


class DiagnosticHistory:
    def __init__(self, capacity=600, archive_path=None, queue_capacity=2048, metadata=None):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity<=0:
            raise ValueError('diagnostic capacity must be a positive integer')
        if isinstance(queue_capacity, bool) or not isinstance(queue_capacity, int) or queue_capacity<=0:
            raise ValueError('diagnostic queue capacity must be a positive integer')
        self.capacity=capacity
        self._rows=deque(maxlen=capacity)
        self.seen=0;self.written=0;self.dropped=0;self.error=None;self.closed=False
        self.archive_path=Path(archive_path) if archive_path else None
        self._queue=None;self._thread=None
        if self.archive_path is not None:
            if self.archive_path.exists():
                raise FileExistsError(self.archive_path)
            self.journal_path=Path(str(self.archive_path)+'.jsonl')
            self._file=self.journal_path.open('x',encoding='utf-8')
            try:
                if metadata is not None:
                    with Path(str(self.archive_path)+'.runtime.json').open('x',encoding='utf-8') as stream:
                        json.dump(metadata,stream,indent=2);stream.write('\n')
            except Exception:
                self._file.close();raise
            self._queue=Queue(maxsize=queue_capacity)
            self._thread=Thread(target=self._write,name='ht_diagnostic_writer')
            self._thread.start()

    def __len__(self):return len(self._rows)
    def __getitem__(self,index):return self._rows[index]
    def __iter__(self):return iter(self._rows)

    def append(self,row):
        if self.closed:raise RuntimeError('diagnostic history is closed')
        self._rows.append(row);self.seen+=1
        if self._queue is not None:
            try:
                # Freeze the record before handing it to another thread. The
                # callback does bounded serialization, never file I/O or waits.
                encoded=json.dumps(row,separators=(',',':'))
                self._queue.put_nowait(encoded)
            except (Full,TypeError,ValueError) as exc:
                self.dropped+=1
                self.error=type(exc).__name__

    def _write(self):
        try:
            while True:
                item=self._queue.get()
                try:
                    if item is None:break
                    try:
                        self._file.write(item+'\n')
                        self._file.flush()
                        self.written+=1
                    except (OSError,ValueError) as exc:
                        self.dropped+=1;self.error=type(exc).__name__
                finally:self._queue.task_done()
        finally:
            try:self._file.close()
            except OSError as exc:self.error=type(exc).__name__

    def status(self):
        return {'capacity':self.capacity,'retained':len(self),'seen':self.seen,
                'evicted_from_memory':self.seen-len(self),
                'archive_enabled':self.archive_path is not None,
                'archive_written':self.written,'archive_dropped':self.dropped,
                'archive_error':self.error,'closed':self.closed}

    def close(self):
        if self.closed:return
        self.closed=True
        if self._thread is not None:
            # Called only after callbacks drain, never from the map callback.
            self._queue.put(None)
            self._thread.join()

    def finalize(self):
        """Stream the full journal to the legacy JSON array without loading it."""
        self.close()
        if self.archive_path is None:return
        status=self.status()
        status_path=Path(str(self.archive_path)+'.status.json')
        with status_path.open('x',encoding='utf-8') as stream:
            json.dump(status,stream,indent=2);stream.write('\n')
        if self.error is not None or self.dropped or self.written!=self.seen:
            raise RuntimeError('Incomplete diagnostic archive; see journal and status; no complete JSON emitted')
        # Exclusive creation preserves earlier experiments. The journal is
        # retained as crash evidence and avoids shutdown RAM proportional to N.
        with self.archive_path.open('x',encoding='utf-8') as stream, self.journal_path.open() as journal:
            stream.write('[\n')
            first=True
            for line in journal:
                if not first:stream.write(',\n')
                stream.write(line.rstrip('\n'));first=False
            stream.write('\n]\n')
