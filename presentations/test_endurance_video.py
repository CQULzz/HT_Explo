"""Delayed camera callbacks must not backfill future images into earlier video time."""
from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

from endurance_probe import EnduranceProbe


class VideoTimelineTest(unittest.TestCase):
    def test_future_camera_is_not_used_for_an_earlier_output_frame(self):
        frames=[]
        with TemporaryDirectory() as directory:
            node=SimpleNamespace(
                video_fps=2,created=0.,created_wall=1000.,last_video=0.,
                camera_buffer=deque([(.75,np.full((540,960,3),200,np.uint8))]),
                encoded_camera=None,encoded_camera_time=None,
                output=Path(directory),scenario='campus',command=(.2,.1),status={},
                writer=SimpleNamespace(write=lambda frame:frames.append(frame.copy())),video_frames=0)
            with patch('endurance_probe.time.monotonic',return_value=1.):
                EnduranceProbe.video(node)
        self.assertEqual(len(frames),2)
        self.assertTrue(np.all(frames[0][:540]==0))
        self.assertTrue(np.all(frames[1][:540]==200))


if __name__=='__main__':unittest.main()
