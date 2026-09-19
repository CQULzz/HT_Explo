"""Fixed world-grid surface-hit metrics; no free-space/ray-volume inference."""
import numpy as np


def voxel_keys(xyz, resolution=0.5):
    xyz = np.asarray(xyz)
    xyz = xyz[np.all(np.isfinite(xyz), axis=1)]
    indices = np.floor(xyz/resolution).astype(np.int64)
    if np.any(indices < -(1 << 20)) or np.any(indices >= (1 << 20)):
        raise ValueError('Point outside the supported world grid')
    indices += 1 << 20
    return np.unique((indices[:, 0] << 42) | (indices[:, 1] << 21) | indices[:, 2])


def decode_keys(keys, resolution=0.5):
    keys = np.asarray(keys, dtype=np.int64)
    mask = (1 << 21)-1
    indices = np.column_stack((keys >> 42, (keys >> 21) & mask, keys & mask)) - (1 << 20)
    return (indices+0.5)*resolution


def read_reference_ply(path):
    # The official CMU preview PLY is binary little endian, with float x/y/z.
    with open(path, 'rb') as stream:
        header = []
        while True:
            line = stream.readline().decode('ascii').strip()
            header.append(line)
            if line == 'end_header':
                break
            if len(header) > 100:
                raise ValueError('Unexpected PLY header')
        if header[1] != 'format binary_little_endian 1.0':
            raise ValueError('Unsupported PLY format')
        properties = [line for line in header if line.startswith('property ')]
        if properties != ['property float x', 'property float y', 'property float z']:
            raise ValueError('Unsupported PLY vertex layout')
        count = int(next(line for line in header if line.startswith('element vertex ')).split()[-1])
        xyz = np.fromfile(stream, dtype='<f4', count=count*3).reshape(-1, 3)
        if len(xyz) != count:
            raise ValueError('Truncated PLY')
        return xyz


if __name__ == '__main__':
    # Independently specified expected cells, including negative boundaries.
    points = [[0.01, 0.01, 0.01], [0.49, 0.1, 0.1], [-0.01, 0, 0],
              [0.5, 0, 0], [float('nan'), 0, 0], [0, float('inf'), 0]]
    keys = voxel_keys(points)
    assert len(keys) == 3
    assert set(map(tuple, decode_keys(keys))) == {
        (0.25, 0.25, 0.25), (-0.25, 0.25, 0.25), (0.75, 0.25, 0.25)}
    assert len(set(keys) & set(voxel_keys([[0.2, 0.2, 0.2], [10, 10, 10]]))) == 1
    assert len(voxel_keys(np.zeros((0, 3)))) == 0
    print('Coverage quantization, deduplication, finite filtering and reference matching: PASS')
