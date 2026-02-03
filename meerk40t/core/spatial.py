"""
Spatial helper utilities for nearest-neighbour queries.
Provides a memory-safe nearest neighbour implementation with an optional SciPy cKDTree fallback.
"""
from typing import Optional
import numpy as np

# Optional SciPy KD-tree fallback for faster nearest-neighbor queries
try:
    from scipy.spatial import cKDTree as _cKDTree
except Exception:
    _cKDTree = None

# Optional psutil for accurate available memory detection
try:
    import psutil as _psutil
except Exception:
    _psutil = None


def _detect_available_memory():
    """Detect available system memory in bytes.

    Prefer psutil.virtual_memory().available when available. Fall back to
    POSIX sysconf sources; otherwise return None.
    """
    if _psutil is not None:
        try:
            vm = _psutil.virtual_memory()
            return int(vm.available)
        except Exception:
            return None

    # POSIX fallback
    try:
        import os

        if hasattr(os, "sysconf"):
            if "SC_PAGE_SIZE" in os.sysconf_names and "SC_AVPHYS_PAGES" in os.sysconf_names:
                page = os.sysconf("SC_PAGE_SIZE")
                pages = os.sysconf("SC_AVPHYS_PAGES")
                if page is not None and pages is not None:
                    return int(page * pages)
    except Exception:
        pass
    return None


def compute_default_max_mem(fraction: float = 0.1, cap: int = 200_000_000, minimum: int = 5_000_000) -> int:
    """Compute a conservative default max memory in bytes.

    - fraction: fraction of available memory to use for temporary buffers (default 0.1)
    - cap: maximum cap in bytes (default 200 MB)
    - minimum: minimum allowed value in bytes
    """
    avail = _detect_available_memory()
    if avail is None:
        # Fallback conservative default
        return cap
    value = int(avail * float(fraction))
    # Clamp
    if value < minimum:
        value = minimum
    if value > cap:
        value = cap
    return value


# Default max memory used by shortest_distance when no explicit max_mem is provided.
DEFAULT_MAX_MEM = compute_default_max_mem()


def get_default_max_mem() -> int:
    """Return the current default max memory in bytes."""
    return DEFAULT_MAX_MEM


def set_default_max_mem(
    value: Optional[int] = None,
    fraction: Optional[float] = None,
    cap: Optional[int] = None,
    minimum: Optional[int] = None,
) -> int:
    """Set the global default max memory.

    You can set either a fixed `value` in bytes, or recompute from the available memory
    using `fraction` and optional `cap` and `minimum`.

    Returns the new default value.
    """
    global DEFAULT_MAX_MEM
    if value is not None:
        DEFAULT_MAX_MEM = int(value)
    else:
        _fraction = 0.1 if fraction is None else float(fraction)
        _cap = 200_000_000 if cap is None else int(cap)
        _minimum = 5_000_000 if minimum is None else int(minimum)
        DEFAULT_MAX_MEM = compute_default_max_mem(_fraction, _cap, _minimum)
    return DEFAULT_MAX_MEM


def shortest_distance(p1, p2, tuplemode, max_mem: Optional[int] = None):
    """Block-wise nearest neighbor search using pure numpy with optional cKDTree.

    Returns (min_dist, pt_from_p1, pt_from_p2) where the returned points are
    typed as in the original inputs (complex for complex inputs, 2-tuple/array for tuplemode).

    Parameters:
        p1, p2 : array-like
            If tuplemode is False these are 1-D complex arrays. If tuplemode is True these
            are Nx2 float arrays.
        tuplemode : bool
            Whether to treat inputs as tuple pairs (True) or complex numbers (False).
        max_mem : int
            Approximate maximum bytes of temporary memory to use for chunked distance
            computations (default uses DEFAULT_MAX_MEM).
    """
    if max_mem is None or max_mem <= 0:
        max_mem = DEFAULT_MAX_MEM
    try:
        a1 = np.asarray(p1)
        a2 = np.asarray(p2)
    except Exception:
        return None, None, None
    if a1.size == 0 or a2.size == 0:
        return None, None, None

    # Normalize to Nx2 float arrays for distance computation
    def _ensure_xy(arr):
        if arr.ndim == 1:
            if arr.size == 2:
                return arr.reshape(1, 2)
            return None
        if arr.ndim != 2 or arr.shape[1] != 2:
            return None
        return arr

    if not tuplemode:
        p1_xy = np.column_stack((a1.real, a1.imag)) if np.iscomplexobj(a1) else np.asarray(a1)
        p2_xy = np.column_stack((a2.real, a2.imag)) if np.iscomplexobj(a2) else np.asarray(a2)
    else:
        p1_xy = np.asarray(a1)
        if np.iscomplexobj(p1_xy):
            p1_xy = np.column_stack((p1_xy.real, p1_xy.imag))
        p2_xy = np.asarray(a2)
        if np.iscomplexobj(p2_xy):
            p2_xy = np.column_stack((p2_xy.real, p2_xy.imag))

    p1_xy = _ensure_xy(p1_xy)
    p2_xy = _ensure_xy(p2_xy)
    if p1_xy is None or p2_xy is None:
        return None, None, None

    n1 = p1_xy.shape[0]
    n2 = p2_xy.shape[0]

    swapped = False
    if n1 > n2:
        p1_xy, p2_xy = p2_xy, p1_xy
        n1, n2 = n2, n1
        swapped = True

    # Try KD-tree first if available
    if _cKDTree is not None:
        try:
            tree = _cKDTree(p2_xy)
            dists, idxs = tree.query(p1_xy, k=1)
            min_i = int(np.argmin(dists))
            min_j = int(idxs[min_i])
            min_dist = float(dists[min_i])
            if not swapped:
                idx1 = min_i
                idx2 = min_j
            else:
                idx1 = min_j
                idx2 = min_i
            try:
                pt1 = a1[idx1]
                pt2 = a2[idx2]
            except Exception:
                pt1 = p1_xy[min_i] if not swapped else p2_xy[min_j]
                pt2 = p2_xy[min_j] if not swapped else p1_xy[min_i]
            return min_dist, pt1, pt2
        except Exception:
            # Fall back to chunked approach on error
            pass

    # Compute chunk size to keep memory usage bounded: 3 temporaries (dx, dy, d2)
    bytes_per_val = max(getattr(p1_xy.dtype, "itemsize", 8), getattr(p2_xy.dtype, "itemsize", 8), 8)
    bytes_per_val *= 3
    max_cells = max(1, int(max_mem / bytes_per_val))
    chunk_size = max(1, min(n1, int(max_cells / max(1, n2))))

    min_sq = np.inf
    min_i = -1
    min_j = -1
    for start in range(0, n1, chunk_size):
        chunk = p1_xy[start : start + chunk_size]
        dx = chunk[:, None, 0] - p2_xy[None, :, 0]
        dy = chunk[:, None, 1] - p2_xy[None, :, 1]
        d2 = dx * dx + dy * dy
        local_idx = np.argmin(d2)
        local_min = d2.flat[local_idx]
        if local_min < min_sq:
            min_sq = local_min
            local_row, local_col = divmod(local_idx, n2)
            min_i = start + local_row
            min_j = local_col

    if min_i == -1 or np.isnan(min_sq):
        return None, None, None

    min_dist = float(np.sqrt(min_sq))
    if not swapped:
        idx1 = min_i
        idx2 = min_j
    else:
        idx1 = min_j
        idx2 = min_i

    try:
        pt1 = a1[idx1]
        pt2 = a2[idx2]
    except Exception:
        pt1 = p1_xy[min_i] if not swapped else p2_xy[min_j]
        pt2 = p2_xy[min_j] if not swapped else p1_xy[min_i]

    return min_dist, pt1, pt2


# Backwards-compatible alias
shortest_distance_chunked = shortest_distance
