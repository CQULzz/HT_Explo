"""ROS-independent checks of channel layout and the FCN evaluation geometry."""
import sys,unittest
from pathlib import Path
import numpy as np,torch
sys.path.insert(0,'/home/lzz/my test/eletranskit_scout/src/ht_traversability_ros2')
from ht_traversability_ros2.model import load_student_model

class BridgeTest(unittest.TestCase):
 def test_image_rotation_matches_world_grid(self):
  x,y=np.meshgrid(np.arange(-2,3),np.arange(2,-3,-1))
  h=x+2*y
  # Training yaw=0 rotates image CCW: input rows point -X, columns -Y.
  rotated=np.rot90(h)
  np.testing.assert_array_equal(np.diff(rotated,axis=0),-np.ones((4,5)))
  np.testing.assert_array_equal(np.diff(rotated,axis=1),-2*np.ones((5,4)))
 def test_dense_output_matches_center_patch(self):
  torch.set_num_threads(2);torch.manual_seed(7)
  p='/home/lzz/下载/original_scout/mini_25_training/runs/formal/student/best_epoch_weights.pth'
  m=load_student_model(p,torch.device('cpu'));x=torch.randn(1,1,61,61)*.05
  with torch.inference_mode():
   dense=m(x);single=m(x[:,:,5:56,5:56])
  self.assertEqual(tuple(dense.shape),(1,8,2,11,11));torch.testing.assert_close(dense[:,:,:,5,5],single[:,:,:,0,0],atol=1e-4,rtol=1e-4)
 def test_column_major_roundtrip(self):
  a=np.arange(35).reshape(5,7);np.testing.assert_array_equal(a,np.array(a.flatten(order='F')).reshape(5,7,order='F'))
if __name__=='__main__':unittest.main()
