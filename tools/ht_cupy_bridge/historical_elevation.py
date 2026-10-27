"""Sparse, surface-aware elevation history on a fixed map-frame XY grid.

Each XY cell can retain several distinct observed heights. The local crop
selects one compatible surface; it never averages floor/ceiling observations.
Unknown cells stay NaN rather than being filled from neighbouring cells.
"""

import numpy as np


class HistoricalElevation:
    def __init__(self, resolution, tile_size=64, max_tiles=1024, max_age_s=600.0,
                 max_layers=4, association_gap_m=0.6, reference_tolerance_m=1.0):
        self.resolution = float(resolution)
        self.tile_size = int(tile_size)
        self.max_tiles = int(max_tiles)
        self.max_age_s = float(max_age_s)
        self.max_layers = int(max_layers)
        self.association_gap_m = float(association_gap_m)
        self.reference_tolerance_m = float(reference_tolerance_m)
        if (self.resolution <= 0 or self.tile_size <= 0 or self.max_tiles <= 0
                or self.max_layers <= 0 or self.max_age_s < 0
                or self.association_gap_m <= 0 or self.reference_tolerance_m <= 0):
            raise ValueError("invalid historical elevation configuration")
        self.tiles = {}
        self.rejections = {}
        self.rejected_heights = {}
        self.frames = 0
        # A known height rejected during surface/age selection must not be
        # reconstructed as free ground by downstream nearest-value padding.
        self.last_window_incompatible_mask = None
        self.last_window_obstacle_elevation = None

    def _tile(self, tx, ty):
        key = (int(tx), int(ty))
        if key not in self.tiles:
            if len(self.tiles) >= self.max_tiles:
                raise MemoryError("historical elevation tile limit reached")
            shape = (self.max_layers, self.tile_size, self.tile_size)
            self.tiles[key] = (np.full(shape, np.nan, np.float32),
                               np.full(shape, np.inf, np.float32),
                               np.full(shape, -np.inf, np.float64))
        return self.tiles[key]

    def fuse(self, elevation, variance, center_x, center_y, stamp_s, outer_start=0,
             inner_start=0, *, observation_time=None):
        """Fuse physical-buffer arrays, returning the number of updated cells.

        ``observation_time`` is the actual measurement time of each cell, as a
        scalar or an array with the same physical-buffer layout. A retained
        CuPy cell whose measurement time has not changed is not fused again or
        made younger. Without this input, the map publication stamp is used
        for compatibility with maps that lack a per-cell observation layer.
        """
        elevation, variance = np.asarray(elevation), np.asarray(variance)
        if elevation.shape != variance.shape or elevation.ndim != 2:
            raise ValueError("elevation/variance shape mismatch")
        nx, ny = elevation.shape
        offset = (-int(outer_start), -int(inner_start))
        # GridMap logical (0, 0) is the cell at the positive X/Y corner.
        elevation = np.roll(elevation, offset, (0, 1))
        variance = np.roll(variance, offset, (0, 1))
        if observation_time is None:
            observed = np.full(elevation.shape, float(stamp_s), np.float64)
        elif np.ndim(observation_time) == 0:
            observed = np.full(elevation.shape, float(observation_time), np.float64)
        else:
            observed = np.asarray(observation_time, np.float64)
            if observed.shape != elevation.shape:
                raise ValueError("observation_time shape mismatch")
            observed = np.roll(observed, offset, (0, 1))
        valid = (np.isfinite(elevation) & np.isfinite(variance)
                 & (variance >= 0) & (variance < 1) & np.isfinite(observed)
                 & (observed <= float(stamp_s) + 1e-3))
        ii, jj = np.nonzero(valid)
        self.frames += 1
        if not ii.size:
            return 0
        source_gx, source_gy = self._source_indices(center_x, center_y, (nx, ny))
        gx, gy = source_gx[ii], source_gy[jj]
        tx, ty = gx // self.tile_size, gy // self.tile_size
        inverse = self._tile_groups(tx,ty)
        updates = 0
        for group in range(int(inverse.max()) + 1):
            selected = np.flatnonzero(inverse == group)
            mean, var, last = self._tile(tx[selected[0]], ty[selected[0]])
            lx, ly = gx[selected] % self.tile_size, gy[selected] % self.tile_size
            z = elevation[ii[selected], jj[selected]]
            v = variance[ii[selected], jj[selected]]
            obs = observed[ii[selected], jj[selected]]
            values = mean[:, lx, ly]
            distance = np.where(np.isfinite(values), np.abs(values-z[None, :]), np.inf)
            mode = np.argmin(distance, axis=0)
            matched = np.min(distance, axis=0) <= self.association_gap_m
            empty = ~np.isfinite(values)
            free = np.argmax(empty, axis=0)
            # If a cell sees more than max_layers surfaces, replace its oldest
            # mode; never merge two separated heights to make room.
            replacement = np.where(np.any(empty, axis=0), free,
                                   np.argmin(last[:, lx, ly], axis=0))
            mode = np.where(matched, mode, replacement)
            # A retained source cell or out-of-order message is not a new
            # observation of any surface at this XY. In particular, reusing
            # one old timestamp cannot create a second apparent floor.
            latest_observation = np.max(last[:, lx, ly], axis=0)
            rejected_time=self.rejections.get((int(tx[selected[0]]),int(ty[selected[0]])))
            if rejected_time is not None:
                latest_observation=np.maximum(latest_observation,rejected_time[lx,ly])
            # Source ages commonly use float32 seconds. Reconstructing an
            # old timestamp from header-age introduces sub-millisecond jitter;
            # that is not a new scan (the sensor cadence is tens of ms).
            fresh = obs > latest_observation + 1e-3
            if not np.any(fresh):
                continue
            lx, ly, z, v, obs, mode, matched = (
                a[fresh] for a in (lx, ly, z, v, obs, mode, matched))
            old_mean, old_var = mean[mode, lx, ly], var[mode, lx, ly]
            new_mean, new_var = z.copy(), v.copy()
            # CuPy windows overlap heavily. Within a surface, cap the gain
            # rather than interpreting snapshots as independent measurements.
            gain = np.clip(old_var[matched] /
                           (old_var[matched] + v[matched] + 1e-5), .05, .5)
            new_mean[matched] = (old_mean[matched] + gain *
                                 (z[matched] - old_mean[matched]))
            new_var[matched] = np.maximum(.0001,
                (1-gain)*old_var[matched] + gain*v[matched])
            mean[mode, lx, ly], var[mode, lx, ly] = new_mean, new_var
            last[mode, lx, ly] = obs
            updates += len(lx)
        return updates

    def record_rejections(self, rejected, center_x, center_y, stamp_s, observation_time,
                          *, elevation=None):
        """Record genuinely new rejected measurements, not variance aging.

        Retained source cells may gain process variance without a new return.
        They cannot retroactively invalidate the same observation already
        accepted into history. A new bad return remains forbidden until a newer
        accepted observation clears it; simply waiting does not fill a hole.
        A finite rejected height is retained only as occupied context. It is
        never fused as ground and the bridge forces its eight HT scores to zero.
        Inputs use decoded logical GridMap order, as in the production bridge.
        """
        rejected=np.asarray(rejected,bool);observed=np.asarray(observation_time,np.float64)
        if observed.shape!=rejected.shape or rejected.ndim!=2:raise ValueError('rejection shape mismatch')
        height=np.full(rejected.shape,np.nan,np.float32) if elevation is None else np.asarray(elevation,np.float32)
        if height.shape!=rejected.shape:raise ValueError('rejected elevation shape mismatch')
        ii,jj=np.nonzero(rejected & np.isfinite(observed) & (observed<=stamp_s+1e-3)
                         & (stamp_s-observed<=self.max_age_s))
        if not len(ii):return 0
        gx,gy=self._source_indices(center_x,center_y,rejected.shape);gx,gy=gx[ii],gy[jj]
        tx,ty=gx//self.tile_size,gy//self.tile_size
        groups=self._tile_groups(tx,ty)
        count=0
        for group in range(int(groups.max())+1):
            ids=np.flatnonzero(groups==group);key=(int(tx[ids[0]]),int(ty[ids[0]]))
            _,_,last=self._tile(*key);lx,ly=gx[ids]%self.tile_size,gy[ids]%self.tile_size
            stored=self.rejections.setdefault(key,np.full((self.tile_size,self.tile_size),-np.inf,np.float64))
            stored_height=self.rejected_heights.setdefault(key,np.full((self.tile_size,self.tile_size),np.nan,np.float32))
            times=observed[ii[ids],jj[ids]]
            fresh=times>np.maximum(np.max(last[:,lx,ly],axis=0),stored[lx,ly])+1e-3
            stored[lx[fresh],ly[fresh]]=times[fresh];count+=int(fresh.sum())
            stored_height[lx[fresh],ly[fresh]]=height[ii[ids[fresh]],jj[ids[fresh]]]
        return count

    def window(self, center_x, center_y, side, stamp_s, *, reference_height=None,
               preferred_elevation=None):
        """Return (elevation, variance, exact_x, exact_y) in GridMap order.

        ``preferred_elevation`` is a current-source map already aligned to the
        returned fixed-world crop, shape (side, side). A finite preferred value
        selects the matching mode within association_gap_m; if none matches,
        this cell stays unknown. It cannot fall back to a different floor.

        Else ``reference_height`` (scalar or aligned array) selects a mode no
        more than reference_tolerance_m away. The caller should provide the
        vehicle's current ground height or a local surface reference, not the
        sensor mounting height. A ramp is associated per XY cell, without
        global height buckets. Without either hint, the newest mode is chosen
        for legacy callers; production planning should supply surface hints.
        """
        side = int(side)
        if side <= 0 or side % 2 != 1:
            raise ValueError("window side must be positive and odd")
        preferred = self._reference_array(preferred_elevation, side, "preferred_elevation")
        reference = self._reference_array(reference_height, side, "reference_height")
        center_gx = self._nearest_index(center_x)
        center_gy = self._nearest_index(center_y)
        exact_x = center_gx * self.resolution
        exact_y = center_gy * self.resolution
        indices = np.arange(side, dtype=np.int64)
        gx = center_gx + side//2 - indices
        gy = center_gy + side//2 - indices
        elevation = np.full((side, side), np.nan, np.float32)
        variance = np.full((side, side), np.inf, np.float32)
        self.last_window_incompatible_mask = np.zeros((side, side), dtype=bool)
        self.last_window_obstacle_elevation = np.full((side, side), np.nan, np.float32)
        for tx in np.unique(gx // self.tile_size):
            ix = np.flatnonzero(gx // self.tile_size == tx)
            for ty in np.unique(gy // self.tile_size):
                tile = self.tiles.get((int(tx), int(ty)))
                if tile is None:
                    continue
                iy = np.flatnonzero(gy // self.tile_size == ty)
                lx, ly = gx[ix] % self.tile_size, gy[iy] % self.tile_size
                z, v, last = (a[:, lx[:, None], ly[None, :]] for a in tile)
                usable = (np.isfinite(z) & (stamp_s-last <= self.max_age_s)
                          & (last <= stamp_s + 1e-3))
                # A current-source elevation is stronger evidence than a
                # robot-height fallback, including observed obstacle tops.
                output_index=np.ix_(ix,iy)
                p, r = preferred[output_index], reference[output_index]
                has_preferred, has_reference = np.isfinite(p), np.isfinite(r)
                target = np.where(has_preferred, p, r)
                has_target = has_preferred | has_reference
                distance = np.abs(z-target[None, :, :])
                tolerance = np.where(has_preferred, self.association_gap_m,
                                     self.reference_tolerance_m)
                usable &= ~has_target[None, :, :] | (distance <= tolerance[None, :, :])
                # A ground reference chooses the current compatible surface,
                # not whichever height happens to lie closest to ideal ground.
                # Otherwise a 0.8m obstacle and older ground both inside the
                # 1m reference gate would silently revert to free ground.
                score = np.where(has_preferred[None, :, :], -distance, last)
                mode = np.argmax(np.where(usable, score, -np.inf), axis=0)
                chosen_z = np.take_along_axis(z, mode[None, :, :], axis=0)[0]
                chosen_v = np.take_along_axis(v, mode[None, :, :], axis=0)[0]
                chosen_time = np.take_along_axis(last, mode[None, :, :], axis=0)[0]
                found = np.any(usable, axis=0)
                newest_mode = np.argmax(np.where(np.isfinite(z), last, -np.inf), axis=0)
                newest_z = np.take_along_axis(z, newest_mode[None, :, :], axis=0)[0]
                newest_time = np.take_along_axis(last, newest_mode[None, :, :], axis=0)[0]
                # A later observed post/other floor cannot be discarded in
                # favour of older ground solely because a ground-height hint
                # prefers it. Expiry does not prove that the post disappeared.
                # Fresh direct source evidence can select ground again.
                newer_incompatible = (~has_preferred & has_reference
                    & (newest_time > chosen_time + 1e-3)
                    & (abs(newest_z-r) > self.reference_tolerance_m))
                found &= ~newer_incompatible
                rejected_time=self.rejections.get((int(tx),int(ty)))
                newer_rejection=np.zeros(found.shape,bool)
                if rejected_time is not None:
                    rejected_time=rejected_time[lx[:,None],ly[None,:]]
                    newer_rejection=(rejected_time>np.max(last,axis=0)+1e-3)&(
                        rejected_time<=stamp_s+1e-3)&(stamp_s-rejected_time<=self.max_age_s)
                    found &= ~newer_rejection
                # Explicit surface selection with a nonfinite reference and
                # no current observation is not permission to choose a floor.
                if reference_height is not None or preferred_elevation is not None:
                    found &= has_target
                # Keep evidence that a real observed height was discarded.
                # Include expired modes: a stale post is unknown occupancy,
                # not proof that the obstacle disappeared. An inactive floor
                # with no compatible current-floor height has the same rule.
                self.last_window_incompatible_mask[output_index] = (
                    (np.any(np.isfinite(z), axis=0) & ~found) | newer_rejection)
                # An observed incompatible surface is occupied/unsafe evidence,
                # not an observation of traversable ground. Preserve its actual
                # height separately for network context and an explicit hard
                # obstacle mask. Never promote expired or unreferenced layers.
                obstacle = (~found & ~newer_rejection & has_reference & np.isfinite(newest_z)
                    & (newest_time <= stamp_s+1e-3)
                    & (stamp_s-newest_time <= self.max_age_s)
                    & (abs(newest_z-r) > self.reference_tolerance_m))
                obstacle_height=np.where(obstacle,newest_z,np.nan)
                rejected_height=self.rejected_heights.get((int(tx),int(ty)))
                if rejected_height is not None:
                    rejected_height=rejected_height[lx[:,None],ly[None,:]]
                    obstacle_height=np.where(newer_rejection & np.isfinite(rejected_height),
                                             rejected_height,obstacle_height)
                self.last_window_obstacle_elevation[output_index] = obstacle_height
                elevation[output_index] = np.where(found, chosen_z, np.nan)
                variance[output_index] = np.where(found, chosen_v, np.inf)
        return elevation, variance, exact_x, exact_y

    @staticmethod
    def _tile_groups(tx,ty):
        # Dense local tile coordinates encode the same lexicographic order as
        # unique(stack((tx,ty)),axis=0), without the structured 2D sort.
        width=int(ty.max()-ty.min())+1
        keys=(tx-tx.min())*width+(ty-ty.min())
        return np.unique(keys,return_inverse=True)[1]

    def _nearest_index(self, coordinate):
        # Fixed grid cell centres are at integer multiples of resolution.
        # Choose one translation for the entire input lattice, so ties and
        # float32 accumulation in CuPy's centre cannot duplicate or skip cells.
        return int(np.floor(float(coordinate) / self.resolution + .5))

    def _source_indices(self, center_x, center_y, shape):
        nx, ny = shape
        first_x = self._nearest_index(center_x + (nx-1)*.5*self.resolution)
        first_y = self._nearest_index(center_y + (ny-1)*.5*self.resolution)
        return (first_x - np.arange(nx, dtype=np.int64),
                first_y - np.arange(ny, dtype=np.int64))

    def aligned_source_window(self, source, center_x, center_y, side,
                              outer_start=0, inner_start=0, *, fill_value=np.nan):
        """Align a current source array to ``window``'s exact fixed-world crop.

        The source uses its physical circular-buffer layout. This helper is
        intended for preferred elevations, surface references and measurement
        timestamps. It copies observed cells; it does not interpolate or fill
        unknown cells. The grid origin matches schema-2 history, at (0, 0).
        """
        source = np.asarray(source)
        if source.ndim != 2:
            raise ValueError("source must be a 2D array")
        side = int(side)
        if side <= 0 or side % 2 != 1:
            raise ValueError("window side must be positive and odd")
        source = np.roll(source, (-int(outer_start), -int(inner_start)), (0, 1))
        gx, gy = self._source_indices(center_x, center_y, source.shape)
        row = self._nearest_index(center_x) + side//2 - gx
        col = self._nearest_index(center_y) + side//2 - gy
        ix = np.flatnonzero((row >= 0) & (row < side))
        iy = np.flatnonzero((col >= 0) & (col < side))
        dtype = np.result_type(source.dtype, np.float32)
        result = np.full((side, side), fill_value, dtype=dtype)
        result[np.ix_(row[ix], col[iy])] = source[np.ix_(ix, iy)]
        return result

    @staticmethod
    def _reference_array(value, side, name):
        if value is None:
            return np.full((side, side), np.nan, np.float32)
        result = np.asarray(value, np.float32)
        if result.ndim == 0:
            return np.full((side, side), result, np.float32)
        if result.shape != (side, side):
            raise ValueError(f"{name} must match the requested window")
        return result

    @property
    def allocated_cells(self):
        """Number of allocated XY cells (each has up to max_layers modes)."""
        return len(self.tiles) * self.tile_size**2

    def save(self, path):
        """Persist every height mode and latest-mode compatibility views."""
        keys = sorted(self.tiles)
        shape = (0, self.max_layers, self.tile_size, self.tile_size)
        layers = [np.stack([self.tiles[k][i] for k in keys]) if keys else
                  np.empty(shape, dtype) for i, dtype in
                  enumerate((np.float32, np.float32, np.float64))]
        z, v, last = layers
        newest = np.argmax(last, axis=1, keepdims=True)
        latest = [np.take_along_axis(a, newest, axis=1)[:, 0] for a in layers]
        np.savez_compressed(
            path, schema_version=2, resolution=self.resolution,
            tile_size=self.tile_size, max_layers=self.max_layers,
            world_origin=np.asarray([0., 0.]),
            association_gap_m=self.association_gap_m,
            reference_tolerance_m=self.reference_tolerance_m,
            keys=np.asarray(keys, dtype=np.int32).reshape(-1, 2),
            elevation=latest[0], variance=latest[1], last_seen=latest[2],
            elevation_modes=z, variance_modes=v, last_seen_modes=last,
            rejected_observation_time=np.stack([self.rejections.get(k,np.full((self.tile_size,self.tile_size),-np.inf)) for k in keys]) if keys else np.empty((0,self.tile_size,self.tile_size)),
            rejected_height=np.stack([self.rejected_heights.get(k,np.full((self.tile_size,self.tile_size),np.nan,np.float32)) for k in keys]) if keys else np.empty((0,self.tile_size,self.tile_size),np.float32),
            frames=self.frames)
