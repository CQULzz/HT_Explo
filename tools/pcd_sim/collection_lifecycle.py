"""Collection completion is published only after durable local cleanup."""
from pathlib import Path
import json
import subprocess


def write_completion(output, completion):
    if completion is None:
        return
    output = Path(output)
    final = output / 'DONE.json'
    if final.exists():
        raise FileExistsError('Refuse to overwrite completed collection')
    temporary = output / 'DONE.json.tmp'
    with temporary.open('x') as stream:
        json.dump(completion, stream)
        stream.flush()
    temporary.replace(final)


def await_observer_exit(processes, timeout=8.0):
    """Let the already-completed observer finish naturally before signals.

    A timeout or nonzero result is a real lifecycle failure, never normalized.
    Other owned processes are still torn down by the caller's finally block.
    """
    observer = next((process for label, process in processes if label == 'observer'), None)
    if observer is None:
        raise RuntimeError('Completed run has no observer process')
    try:
        code = observer.wait(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('Observer did not exit after completion') from error
    if code != 0:
        raise RuntimeError(f'Observer exited {code} after completion')
