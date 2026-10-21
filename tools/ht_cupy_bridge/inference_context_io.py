"""Immutable diagnostic snapshots and deferred graceful-stop requests."""
import os
from pathlib import Path
import uuid
import zipfile
import math

import numpy as np


class ContextCaptureSchedule:
    """Capture every startup frame, including delayed TARE startup, then periodically."""
    def __init__(self, warmup_s=45., interval_s=10.):
        self.warmup_s, self.interval_s = warmup_s, interval_s
        self.first_source = self.first_runtime = self.last_saved = None

    def begin_runtime(self, stamp):
        if self.first_runtime is None and math.isfinite(stamp):
            self.first_runtime = stamp

    def due(self, stamp):
        if not math.isfinite(stamp):
            return False
        if self.first_source is None:
            self.first_source = stamp
        if self.last_saved is not None and stamp <= self.last_saved:
            return False
        warm = 0 <= stamp-self.first_source <= self.warmup_s
        if self.first_runtime is not None:
            warm |= -3. <= stamp-self.first_runtime <= self.warmup_s
        return warm or self.last_saved is None or stamp-self.last_saved >= self.interval_s

    def saved(self, stamp):
        self.last_saved = stamp


class GracefulStop:
    """A signal requests exit after the current callback, without raising in it."""
    def __init__(self):
        self.requested = False

    def request(self, signum, frame):
        self.requested = True


def save_immutable_npz(filename, **values):
    """Publish only a closed NPZ; never replace an earlier source-stamped file.

    Interrupted files retain a .partial suffix for diagnosis. Explicit ZipFile
    ownership closes it before the underlying stream even on interruption.
    """
    filename = Path(filename)
    if filename.exists():
        raise FileExistsError(filename)
    temporary = filename.with_name(filename.name + '.' + uuid.uuid4().hex + '.partial')
    with temporary.open('xb') as stream:
        with zipfile.ZipFile(stream, mode='w', compression=zipfile.ZIP_DEFLATED,
                             allowZip64=True) as archive:
            for key, value in values.items():
                with archive.open(key + '.npy', mode='w', force_zip64=True) as target:
                    np.lib.format.write_array(target, np.asanyarray(value), allow_pickle=False)
        stream.flush()
    # Same-directory hardlink publishes atomically and fails if final exists.
    os.link(temporary, filename)
    temporary.unlink()
