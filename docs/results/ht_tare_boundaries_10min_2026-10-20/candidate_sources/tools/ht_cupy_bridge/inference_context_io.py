"""Immutable diagnostic snapshots and deferred graceful-stop requests."""
import os
from pathlib import Path
import uuid
import zipfile

import numpy as np


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
