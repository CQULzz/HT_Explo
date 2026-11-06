"""Shared geometry, navigation bounds and observer coordinates for PCD trials."""
from dataclasses import asdict, dataclass
import json
import hashlib
import math
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SceneConfig:
    bounds_xy_m: tuple = (-15., 15., -15., 15.)
    navigation_inset_m: float = 1.5
    metric_z_m: tuple = (-1.5, 2.5)
    metric_voxel_m: float = .2
    metric_ray_range_m: float = 15.

    def __post_init__(self):
        if len(self.bounds_xy_m) != 4 or len(self.metric_z_m) != 2:
            raise ValueError('Expected xmin,xmax,ymin,ymax and zmin,zmax')
        values = (*self.bounds_xy_m, *self.metric_z_m, self.navigation_inset_m,
                  self.metric_voxel_m, self.metric_ray_range_m)
        if not all(math.isfinite(value) for value in values):
            raise ValueError('Scene configuration must be finite')
        xmin, xmax, ymin, ymax = self.bounds_xy_m
        if min(xmax-xmin, ymax-ymin) <= 2*self.navigation_inset_m:
            raise ValueError('Navigation inset leaves no scene interior')
        if self.navigation_inset_m < 0 or self.metric_z_m[0] >= self.metric_z_m[1]:
            raise ValueError('Invalid navigation inset or vertical metric bounds')
        if self.metric_voxel_m <= 0 or self.metric_ray_range_m <= self.metric_voxel_m:
            raise ValueError('Invalid metric voxel size or ray range')
        if math.prod(self.voxel_shape) > np.iinfo(np.int64).max:
            raise ValueError('Scene voxel keys exceed int64 capacity')

    @property
    def navigation_polygon(self):
        xmin, xmax, ymin, ymax = self.bounds_xy_m
        margin = self.navigation_inset_m
        return ((xmin+margin, ymin+margin), (xmax-margin, ymin+margin),
                (xmax-margin, ymax-margin), (xmin+margin, ymax-margin))

    def contains_xy(self, points):
        xmin, xmax, ymin, ymax = self.bounds_xy_m
        return ((points[..., 0] > xmin) & (points[..., 0] < xmax) &
                (points[..., 1] > ymin) & (points[..., 1] < ymax))

    @property
    def voxel_origin(self):
        lower = np.array([self.bounds_xy_m[0], self.bounds_xy_m[2], self.metric_z_m[0]])
        return np.floor(lower/self.metric_voxel_m)*self.metric_voxel_m

    @property
    def voxel_shape(self):
        xmin, xmax, ymin, ymax = self.bounds_xy_m
        lower = (xmin, ymin, self.metric_z_m[0])
        upper = (xmax, ymax, self.metric_z_m[1])
        return tuple(math.ceil(high/self.metric_voxel_m)-math.floor(low/self.metric_voxel_m)
                     for low, high in zip(lower, upper))

    def voxel_keys(self, points):
        """Pack each in-bounds XYZ voxel without collisions on larger maps."""
        lower = np.rint(self.voxel_origin/self.metric_voxel_m).astype(np.int64)
        voxels = np.floor(points/self.metric_voxel_m).astype(np.int64)-lower
        shape = np.array(self.voxel_shape, dtype=np.int64)
        if np.any(voxels < 0) or np.any(voxels >= shape):
            raise ValueError('Metric points fall outside the configured voxel grid')
        return (voxels[:, 0]*shape[1]+voxels[:, 1])*shape[2]+voxels[:, 2]

    def image_xy(self, x, y):
        xmin, xmax, ymin, ymax = self.bounds_xy_m
        scale = min(560/(xmax-xmin), 560/(ymax-ymin))
        return (round(320+(x-(xmin+xmax)/2)*scale),
                round(340-(y-(ymin+ymax)/2)*scale))

    def to_dict(self):
        return {'schema_version': 1, **asdict(self)}

    def write(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2)+'\n')


def load_scene_config(runtime, explicit=None):
    path = Path(explicit) if explicit else Path(runtime)/'scene_config.json'
    if not path.exists() and explicit is None:
        # Existing 30m runtimes predate the shared file. Their metric settings
        # remain readable, while prepared scenes always carry explicit bounds.
        return SceneConfig()
    data = json.loads(path.read_text())
    if data.pop('schema_version', None) != 1:
        raise ValueError('Unsupported scene configuration version')
    return SceneConfig(**data)


def verify_scene(runtime, config):
    runtime = Path(runtime)
    manifest_path = runtime/'SCENE_MANIFEST.json'
    if not manifest_path.exists():
        if tuple(config.bounds_xy_m) != SceneConfig().bounds_xy_m:
            raise ValueError('Larger scene bounds require a prepared scene manifest')
        return
    manifest = json.loads(manifest_path.read_text())
    if 'scene_config' not in manifest:
        crop = manifest.get('crop_xy_m')
        if crop is None or tuple(config.bounds_xy_m) != tuple(crop+crop):
            raise ValueError('Scene bounds differ from the legacy reconstruction')
        return
    recorded = manifest['scene_config']
    if tuple(recorded['bounds_xy_m']) != tuple(config.bounds_xy_m):
        raise ValueError('Scene bounds differ from the reconstructed geometry')
    expected = {runtime/'scene.sdf': manifest['scene_sha256']}
    expected.update({runtime/'assets'/name: digest
                     for name, digest in manifest['geometry_sha256'].items()})
    for path, digest in expected.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Prepared scene geometry hash mismatch: '+str(path))
