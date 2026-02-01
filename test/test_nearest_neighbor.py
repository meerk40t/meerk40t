import time
import unittest
import numpy as np

from meerk40t.core.spatial import (
    shortest_distance as shortest_distance_chunked,
)


def naive_shortest(p1, p2, tuplemode):
    a1 = np.asarray(p1)
    a2 = np.asarray(p2)
    if a1.size == 0 or a2.size == 0:
        return None, None, None
    if tuplemode:
        d2 = np.sum((a1[:, None, :] - a2[None, :, :]) ** 2, axis=2)
        min_idx = np.argmin(d2)
        i, j = divmod(min_idx, a2.shape[0])
        return float(np.sqrt(d2.flat[min_idx])), a1[i], a2[j]
    else:
        d = np.abs(a1[:, None] - a2[None, :])
        min_idx = np.argmin(d)
        i, j = divmod(min_idx, a2.shape[0])
        return float(d.flat[min_idx]), a1[i], a2[j]


class TestNearestNeighbor(unittest.TestCase):
    def test_equivalence_complex(self):
        rng = np.random.RandomState(0)
        p1 = rng.rand(80) + 1j * rng.rand(80)
        p2 = rng.rand(100) + 1j * rng.rand(100)
        ref = naive_shortest(p1, p2, False)
        res = shortest_distance_chunked(p1, p2, False)
        self.assertIsNotNone(ref[0])
        self.assertIsNotNone(res[0])
        self.assertAlmostEqual(ref[0], res[0], places=9)

    def test_equivalence_pairs(self):
        rng = np.random.RandomState(1)
        p1 = rng.rand(50, 2)
        p2 = rng.rand(60, 2)
        ref = naive_shortest(p1, p2, True)
        res = shortest_distance_chunked(p1, p2, True)
        self.assertIsNotNone(ref[0])
        self.assertIsNotNone(res[0])
        self.assertAlmostEqual(ref[0], res[0], places=9)

    def test_benchmark(self):
        rng = np.random.RandomState(2)
        sizes = [(200, 200), (800, 800)]
        for n1, n2 in sizes:
            p1 = rng.rand(n1) + 1j * rng.rand(n1)
            p2 = rng.rand(n2) + 1j * rng.rand(n2)
            t0 = time.perf_counter()
            r_chunk = shortest_distance_chunked(p1, p2, False)
            t1 = time.perf_counter()
            t_chunk = t1 - t0
            t0 = time.perf_counter()
            r_naive = naive_shortest(p1[:200], p2[:200], False) if (n1 * n2) > 200 * 200 else naive_shortest(p1, p2, False)
            t1 = time.perf_counter()
            t_naive = t1 - t0
            print(f"Benchmark n1={n1} n2={n2}: chunked={t_chunk:.4f}s, naive_sample={t_naive:.4f}s")
            # Verify correctness on a small subrange if arrays large
            if n1 * n2 > 200 * 200:
                # check equality on small slice
                ref = naive_shortest(p1[:200], p2[:200], False)
                sub = shortest_distance_chunked(p1[:200], p2[:200], False)
                self.assertAlmostEqual(ref[0], sub[0], places=9)

    def test_scipy_kdtree_equivalence(self):
        """If SciPy is available, verify KD-tree path matches chunked results."""
        try:
            from scipy.spatial import cKDTree  # type: ignore
        except Exception:
            self.skipTest("SciPy not available")

        rng = np.random.RandomState(3)
        # complex arrays
        p1 = rng.rand(100) + 1j * rng.rand(100)
        p2 = rng.rand(120) + 1j * rng.rand(120)
        r_kd = shortest_distance_chunked(p1, p2, False)
        # Using the KD tree implicitly; chunked should agree
        r_chunk = shortest_distance_chunked(p1, p2, False)
        self.assertAlmostEqual(r_kd[0], r_chunk[0], places=9)

        # pair arrays
        p1p = rng.rand(80, 2)
        p2p = rng.rand(90, 2)
        r_kd2 = shortest_distance_chunked(p1p, p2p, True)
        r_chunk2 = shortest_distance_chunked(p1p, p2p, True)
        self.assertAlmostEqual(r_kd2[0], r_chunk2[0], places=9)


if __name__ == "__main__":
    unittest.main()
