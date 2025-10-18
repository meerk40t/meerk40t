# Integration Guide: Hierarchical CutPlan into Main CutPlan

## Overview

This guide shows how to integrate the new `cutplan_hierarchical.py` module into the existing `cutplan.py` to use hierarchical optimization.

## Integration Options

### Option 1: Feature Flag (Recommended for Initial Integration)

Add a feature flag to enable hierarchical optimization without modifying existing behavior.

#### Step 1: Add Feature Flag to CutPlan Class

```python
# In meerk40t/core/cutplan.py, in CutPlan.__init__():

class CutPlan:
    def __init__(self, name, planner):
        self.name = name
        self.context = planner
        self.plan = []
        self.spool_commands = []
        self.commands = []
        self.channel = self.context.channel("optimize", timestamp=True)
        self.outline = None
        self._previous_bounds = None
        
        # NEW: Add feature flag for hierarchical optimization
        self.use_hierarchical_selection = (
            self.context.kernel.settings.get(
                "optimize/use_hierarchical_selection",
                False  # Default to False initially
            )
        )
```

#### Step 2: Modify optimize_cuts() Method

```python
# In CutPlan.optimize_cuts(), modify the constrained optimization path:

def optimize_cuts(self):
    """..."""
    busy = self.context.kernel.busyinfo
    _ = self.context.kernel.translation
    
    if busy.shown:
        busy.change(msg=_("Optimize cuts"), keep=1)
        busy.show()
    
    tolerance = self._calculate_tolerance()
    channel = self.context.channel("optimize", timestamp=True)
    
    for i, c in enumerate(self.plan):
        if not isinstance(c, CutCode):
            continue
        
        if c.constrained:
            if self.use_hierarchical_selection:
                # NEW: Use hierarchical optimization
                c = self._optimize_with_hierarchy(
                    c,
                    tolerance=tolerance,
                    channel=channel
                )
            else:
                # Existing path (unchanged)
                c = inner_first_ident(
                    c,
                    kernel=self.context.kernel,
                    channel=channel,
                    tolerance=tolerance,
                )
                c = short_travel_cutcode(
                    c,
                    channel=channel,
                    grouped_inner=True,
                )
        else:
            # No hierarchy
            c = short_travel_cutcode(
                c,
                channel=channel,
                grouped_inner=False,
            )
        
        self.plan[i] = c
```

#### Step 3: Add Hierarchical Optimization Method

```python
# In CutPlan class, add new method:

def _optimize_with_hierarchy(self, context, tolerance=None, channel=None):
    """
    Optimize using hierarchical selection.
    
    Args:
        context: CutCode to optimize
        tolerance: Tolerance for geometry operations
        channel: Channel for logging
        
    Returns:
        Optimized CutCode
    """
    from .cutplan_hierarchical import HierarchicalCutPlan
    
    optimizer = HierarchicalCutPlan(
        kernel=self.context.kernel,
        channel=channel
    )
    
    try:
        result = optimizer.optimize_with_hierarchy(
            context,
            use_inner_first=True,
            optimizer_func=short_travel_cutcode_optimized,
            tolerance=tolerance
        )
        if channel:
            channel("Hierarchical optimization completed successfully")
        return result
    except Exception as e:
        if channel:
            channel(f"Hierarchical optimization failed: {e}")
            channel("Falling back to standard optimization")
        # Fallback to existing approach
        context = inner_first_ident(
            context,
            kernel=self.context.kernel,
            channel=channel,
            tolerance=tolerance,
        )
        return short_travel_cutcode(
            context,
            channel=channel,
            grouped_inner=True,
        )
```

#### Step 4: Add Setting to Kernel Configuration

Add a new setting that users can configure:

```python
# In appropriate kernel initialization code:

# Register setting for hierarchical optimization
kernel.settings.register(
    "optimize/use_hierarchical_selection",
    type_=bool,
    default=False,
    label=_("Use Hierarchical Optimization"),
    help=_("When enabled, uses the new hierarchical cut planning algorithm "
           "which better handles inner-first constraints and material shift. "
           "Experimental feature.")
)
```

#### Step 5: Add GUI Setting (Optional)

```python
# In appropriate GUI preference panel:

def register_preferences(self, pref_panel):
    """Register preference controls."""
    
    # Add checkbox for hierarchical optimization
    pref_panel.append({
        "attr": "use_hierarchical_selection",
        "object": self.kernel.settings,
        "default": False,
        "type": bool,
        "label": _("Use Hierarchical Optimization"),
        "section": "_60_Optimization",
        "help": _("When enabled, uses the new hierarchical cut planning algorithm "
                  "which better handles inner-first constraints and material shift. "
                  "Experimental feature.")
    })
```

---

### Option 2: Direct Replacement (After Testing)

After thoroughly testing and validating the hierarchical approach, replace the entire optimization path.

```python
# In CutPlan.optimize_cuts(), replace entire constrained block:

if c.constrained:
    from .cutplan_hierarchical import HierarchicalCutPlan
    
    optimizer = HierarchicalCutPlan(
        kernel=self.context.kernel,
        channel=channel
    )
    
    c = optimizer.optimize_with_hierarchy(
        c,
        use_inner_first=True,
        optimizer_func=short_travel_cutcode_optimized,
        tolerance=tolerance
    )
else:
    # Non-constrained path unchanged
    c = short_travel_cutcode(
        c,
        channel=channel,
        grouped_inner=False,
    )
```

---

### Option 3: Gradual Migration (Recommended for Production)

Run both approaches and validate they produce compatible results before full migration.

```python
# In CutPlan.optimize_cuts():

if c.constrained:
    # Run standard optimization
    result_standard = inner_first_ident(c, ...)
    result_standard = short_travel_cutcode(result_standard, ...)
    
    # Run hierarchical optimization if enabled
    if self.use_hierarchical_selection:
        from .cutplan_hierarchical import HierarchicalCutPlan
        optimizer = HierarchicalCutPlan(kernel=self.context.kernel, channel=channel)
        result_hierarchical = optimizer.optimize_with_hierarchy(c, use_inner_first=True)
        
        # Compare results
        if self._validate_optimization_equivalence(result_standard, result_hierarchical):
            c = result_hierarchical
            if channel:
                channel("Using hierarchical optimization (validated)")
        else:
            c = result_standard
            if channel:
                channel("Validation failed, using standard optimization")
    else:
        c = result_standard
```

---

## Testing Integration

### Unit Tests

```python
# In test/test_cutplan_integration.py (new file):

import unittest
from unittest.mock import MagicMock, patch
from meerk40t.core.cutplan import CutPlan
from meerk40t.core.cutcode.cutcode import CutCode

class TestHierarchicalIntegration(unittest.TestCase):
    """Test hierarchical optimization integration into CutPlan."""
    
    def setUp(self):
        self.mock_kernel = MagicMock()
        self.mock_kernel.busyinfo.shown = False
        self.mock_kernel.channel = lambda *args, **kwargs: lambda msg: None
        self.mock_kernel.settings.get = lambda key, default: default
        self.mock_context = MagicMock()
        self.mock_context.kernel = self.mock_kernel
        
    def test_hierarchical_flag_disabled_by_default(self):
        """Test that hierarchical optimization is disabled by default."""
        plan = CutPlan("test", self.mock_context)
        self.assertFalse(plan.use_hierarchical_selection)
    
    def test_hierarchical_flag_can_be_enabled(self):
        """Test that hierarchical optimization can be enabled via settings."""
        self.mock_kernel.settings.get = lambda key, default: (
            True if key == "optimize/use_hierarchical_selection" else default
        )
        plan = CutPlan("test", self.mock_context)
        self.assertTrue(plan.use_hierarchical_selection)
    
    def test_optimize_with_hierarchy_method_exists(self):
        """Test that _optimize_with_hierarchy method exists."""
        plan = CutPlan("test", self.mock_context)
        self.assertTrue(hasattr(plan, '_optimize_with_hierarchy'))
        self.assertTrue(callable(getattr(plan, '_optimize_with_hierarchy')))
```

### Integration Tests

```bash
# Run existing tests to ensure no regression
python -m pytest test/test_drivers_grbl.py test/test_drivers_lihuiyu.py -v

# Run hierarchical tests
python -m pytest test/test_cutplan_hierarchical.py -v

# Run new integration tests
python -m pytest test/test_cutplan_integration.py -v
```

---

## Enabling in User Settings

Once integrated, users can enable hierarchical optimization in several ways:

### Via Settings File

```python
# In user settings or configuration:
kernel.settings["optimize/use_hierarchical_selection"] = True
```

### Via Console Command

```
!optimize use_hierarchical_selection true
```

### Via GUI

1. Open Preferences/Settings
2. Navigate to Optimization section
3. Check "Use Hierarchical Optimization"
4. Restart application (if needed)

---

## Rollout Strategy

### Phase 1: Initial Integration (Weeks 1-2)
- Add to main branch with feature flag disabled
- Developers test and validate
- Collect feedback

### Phase 2: Limited Testing (Weeks 3-4)
- Enable for specific test users
- Gather real-world feedback
- Monitor for issues

### Phase 3: Beta Release (Weeks 5-6)
- Make available as opt-in feature in beta branch
- Broader user testing
- Refinement based on feedback

### Phase 4: Full Release (Weeks 7-8)
- Enable by default in stable release
- Keep fallback in place for safety
- Update documentation

---

## Monitoring & Metrics

### Performance Metrics to Track

1. **Execution Time**
   - Time to build hierarchy
   - Time for travel optimization
   - Total optimization time

2. **Cut Quality**
   - Total travel distance
   - Number of moves
   - Job completion time

3. **Reliability**
   - Error rates
   - Fallback usage frequency
   - User-reported issues

### Logging

Add detailed logging for monitoring:

```python
def _optimize_with_hierarchy(self, context, tolerance=None, channel=None):
    start = time.perf_counter()
    
    if channel:
        channel("Starting hierarchical optimization...")
    
    # ... optimization code ...
    
    elapsed = time.perf_counter() - start
    if channel:
        channel(f"Hierarchical optimization completed in {elapsed:.3f}s")
```

---

## Fallback Plan

If issues are discovered, quick fallback is possible:

### Quick Disable
```python
# Set feature flag to False in code or settings
kernel.settings["optimize/use_hierarchical_selection"] = False
```

### Rollback
```bash
# Revert to previous commit before integration
git revert <commit_hash>
```

### Hybrid Mode (Safety Net)
```python
# Always run both and use standard result if hierarchical fails
try:
    result = _optimize_with_hierarchy(c, ...)
except Exception:
    result = standard_optimize(c, ...)
```

---

## Success Criteria

- ✅ All existing tests continue to pass
- ✅ No performance regression
- ✅ New tests achieve 100% pass rate
- ✅ Material shift scenario handled correctly
- ✅ Backward compatibility maintained
- ✅ User documentation updated
- ✅ Feature flag working as expected

---

## Implementation Checklist

- [ ] Add feature flag to CutPlan.__init__()
- [ ] Add use_hierarchical_selection setting
- [ ] Modify optimize_cuts() method
- [ ] Add _optimize_with_hierarchy() method
- [ ] Create integration tests
- [ ] Update documentation
- [ ] Test with real laser jobs
- [ ] Gather user feedback
- [ ] Monitor performance metrics
- [ ] Release in beta
- [ ] Final production release

---

## Questions & Support

For questions about the integration:

1. **Architecture Questions**: See CUTPLAN_RESTRUCTURING_ANALYSIS.md
2. **Implementation Details**: See CUTPLAN_IMPLEMENTATION_PROPOSAL.md
3. **Visual Explanations**: See CUTPLAN_VISUAL_COMPARISON.md
4. **API Reference**: See CUTPLAN_HIERARCHICAL_GUIDE.md
5. **Test Examples**: See test/test_cutplan_hierarchical.py

---

## Conclusion

The hierarchical cutplan module is designed to integrate smoothly into the existing cutplan.py using a feature flag approach. This allows for safe, gradual adoption while maintaining backward compatibility and providing a clear fallback path if issues arise.

The modular design means the hierarchical optimization can be tested independently, integrated gradually, and rolled back quickly if needed. All while providing better handling of material shift scenarios and clearer code architecture.
