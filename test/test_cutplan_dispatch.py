"""
CutPlan.preopt() chooses which optimizer to schedule from the optimization
settings. These tests pin that choice for the key setting combinations.

The subtle case is effect combining: "Keep effect lines together"
(opt_effect_combine) groups hatch/effect lines so they burn together, but it
must NOT disable optimization for ordinary geometry. combine_effects marks the
effect groups with .skip and short_travel_cutcode sequences those separately,
so inner-first / travel optimization still has to run for everything else even
when effects are combined (which is the default).
"""

import unittest

from test import bootstrap


class TestCutplanDispatch(unittest.TestCase):
    def _preopt_commands(self, **opts):
        """Build a two-rect cut plan and return the names of the commands that
        preopt scheduled for the optimize stage."""
        kernel = bootstrap.bootstrap(profile="MeerK40t_TEST_optdispatch")
        try:
            kernel.console("service device start -i grbl 0\n")
            planner = kernel.planner
            for attr, value in opts.items():
                setattr(planner, attr, value)
            kernel.console("element* delete\noperation* delete\n")
            kernel.console("rect 0cm 0cm 5cm 5cm\n")
            kernel.console("rect 2cm 2cm 1cm 1cm\n")
            kernel.console("element* cut -s 15\n")
            kernel.console(
                "plan clear copy preprocess validate blob preopt\n"
            )
            cutplan = planner.default_plan
            return [
                getattr(c, "__name__", repr(c)) for c in cutplan.commands
            ]
        finally:
            kernel()

    def test_inner_first_runs_with_combined_effects(self):
        # Defaults: opt_effect_combine=True, opt_effect_optimize=False.
        # Inner-first must still optimize ordinary geometry, not fall back to
        # basic sequencing; combine_effects still runs to protect hatch lines.
        commands = self._preopt_commands(opt_inner_first=True)
        self.assertIn("optimize_cuts", commands)
        self.assertNotIn("basic_cutcode_sequencing", commands)
        self.assertIn("combine_effects", commands)

    def test_travel_optimization_runs_with_combined_effects(self):
        # Travel-only optimization (inner-first off) must also survive combined
        # effects.
        commands = self._preopt_commands(
            opt_inner_first=False,
            opt_reduce_travel=True,
            opt_nearest_neighbor=True,
        )
        self.assertIn("optimize_travel", commands)
        self.assertNotIn("basic_cutcode_sequencing", commands)

    def test_no_optimization_uses_basic_sequencing(self):
        # With no optimization requested, basic sequencing is the correct
        # fallback (and no optimizer is scheduled).
        commands = self._preopt_commands(
            opt_inner_first=False,
            opt_reduce_travel=False,
            opt_nearest_neighbor=False,
            opt_2opt=False,
        )
        self.assertIn("basic_cutcode_sequencing", commands)
        self.assertNotIn("optimize_cuts", commands)
        self.assertNotIn("optimize_travel", commands)


if __name__ == "__main__":
    unittest.main()
