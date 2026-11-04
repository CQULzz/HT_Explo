# Audited Scout rear-deck surface

`rack_rear_deck.npz` contains 536 actual material triangles from the confirmed
`scout_sensor_rack.urdf.xacro` assembly, expressed in `base_link`. It is a subset
of the opaque URDF rack, not an enlarged vehicle box or a filled convex hull.

- URDF SHA256: `f02ef732ada922d587b9e59810f83e382cbc313af4916271072f2d872b600e30`
- Source `frame.STL` SHA256: `828a686c1a0ec7d66e727fc7772600a98f24bb709b566be82d2d5ca43f1e7754`
- Mesh origin in base: `[0.1725, 0, 0.1162] m`, no rotation or scale.
- Selection: all source faces at mesh Z=0.189 m (tolerance1e-7), whose maximum
  mesh X is less than -0.1 m. Base Z is consequently0.3052 m.
- `source_triangle_ids` retains the original STL triangle indices.

Regenerate with `tools/derive_scout_rack_surface.py --stl <frame.STL> --output <new.npz>`.
The generator checks the source hash and refuses to overwrite an existing asset.
Runtime input diagnostics include both occlusion-module and asset hashes.
