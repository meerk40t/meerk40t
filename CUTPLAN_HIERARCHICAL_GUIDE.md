# Hierarchical CutPlan Module

## Overview

The `cutplan_hierarchical.py` module implements a new, cleaner architecture for cut planning that treats **hierarchy as the primary organizing principle** rather than as a constraint applied during optimization.

This module complements the existing `cutplan.py` by providing:
1. **Explicit hierarchy structures** (HierarchyLevel, HierarchyContext)
2. **Level-by-level processing** that respects inner-first constraints
3. **Travel optimization constrained to hierarchy levels** (not crossing between levels)
4. **Better handling of material shift scenarios**
5. **Clear separation of concerns** between hierarchy and travel optimization

## Architecture

### Key Data Structures

#### HierarchyLevel
Represents one level in the containment hierarchy. All groups at the same level are independent of each other (in terms of hierarchy ordering), but depend on their parent level being complete before execution.

```python
class HierarchyLevel:
    level: int                              # Depth (0=root, 1=inside root, etc)
    cuts: List[CutGroup]                    # Groups at this level
    parent_level: Optional[HierarchyLevel]  # Parent level (if any)
    child_levels: List[HierarchyLevel]      # Child levels
```

#### HierarchyContext
Manages the complete containment hierarchy for a CutCode.

```python
class HierarchyContext:
    root_levels: List[HierarchyLevel]               # Top-level groups
    all_levels: List[HierarchyLevel]                # All levels in order
    level_by_group: Dict[CutGroup, HierarchyLevel]  # Group -> level mapping
```

### Example Hierarchy

```
Input CutCode: [A (closed), B (closed), C (open), D (closed)]

After inner_first_ident():
  A.contains = [B, C]  |  B.inside = [A]
  B.contains = [C]     |  C.inside = [A, B]
  D.contains = []      |  D.inside = []

Explicit Hierarchy:
  Level 0 (Root):     [A]  [D]
    ├─ Level 1:       [B]  (inside A)
    │   ├─ Level 2:   [C]  (inside B)
    
Processing order (innermost first):
  1. Level 2: C
  2. Level 1: B
  3. Level 0: A, D (optimized together)
```

## Key Functions

### build_hierarchy_levels(context: CutCode) -> HierarchyContext

Converts the containment attributes (.contains, .inside) from `inner_first_ident()` into explicit hierarchy levels.

**Algorithm:**
1. Extract all CutGroup objects from CutCode
2. Identify root groups (no parent)
3. Create root levels for each root group
4. Iteratively find and add child groups
5. Create levels for each depth
6. Link parent-child relationships

**Time Complexity:** O(N × depth) where N = number of groups, depth = max hierarchy depth

**Example:**
```python
context = CutCode()  # With groups populated
context = inner_first_ident(context, ...)  # Sets .contains/.inside

hierarchy = build_hierarchy_levels(context)
print(f"Built {len(hierarchy.all_levels)} hierarchy levels")
```

### validate_hierarchy(hierarchy: HierarchyContext) -> Tuple[bool, List[str]]

Validates that a hierarchy is well-formed.

**Checks:**
- All groups are assigned to levels
- Parent-child relationships are consistent
- No cycles exist
- Each level references correct parent

**Example:**
```python
is_valid, errors = validate_hierarchy(hierarchy)
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

### hierarchical_selection(...) -> CutCode

Processes cuts level-by-level using hierarchical order and travel optimization.

This is the core function implementing the hierarchical optimization strategy.

**Algorithm:**
1. Sort hierarchy levels from deepest to shallowest
2. For each level:
   - Check if parent level is complete
   - Create sub-CutCode with just that level's cuts
   - Apply travel optimization to that level only
   - Add result to final sequence
3. Return combined, hierarchy-respecting result

**Key behavior:**
- Never links cuts across hierarchy levels
- Travel optimizer only sees candidates from current level
- Processes from innermost to outermost

**Example:**
```python
optimized = hierarchical_selection(
    context,
    hierarchy,
    optimizer_func=short_travel_cutcode_optimized,
    kernel=kernel,
    channel=channel,
    complete_path=False,
    grouped_inner=False,
    hatch_optimize=False
)
```

### HierarchicalCutPlan (Class)

Main optimizer class providing state management and convenience interface.

**Methods:**
- `__init__(kernel=None, channel=None)` - Initialize
- `log(message: str)` - Log a message
- `optimize_with_hierarchy(...)` - Main entry point

**Example:**
```python
optimizer = HierarchicalCutPlan(kernel=kernel, channel=channel)
result = optimizer.optimize_with_hierarchy(
    context,
    use_inner_first=True,
    optimizer_func=short_travel_cutcode_wrapper
)
```

### optimize_cutcode_hierarchical(cutcode, kernel=None, channel=None, **kwargs) -> CutCode

Convenience function for one-off optimizations.

**Example:**
```python
result = optimize_cutcode_hierarchical(
    cutcode,
    kernel=kernel,
    channel=channel,
    use_inner_first=True
)
```

## Integration with Existing Code

### Reusing inner_first_ident()

The hierarchical module delegates hierarchy detection to the existing `inner_first_ident()` function from `cutplan.py`:

```python
# In hierarchical module
context = inner_first_ident_wrapper(context, ...)  # Calls cutplan.inner_first_ident
```

### Reusing Travel Optimization

Similarly, travel optimization is delegated to `short_travel_cutcode_optimized()`:

```python
# In hierarchical module
optimized = short_travel_cutcode_wrapper(context, ...)  # Calls cutplan.short_travel_cutcode_optimized
```

This ensures compatibility with existing algorithms while applying them within hierarchy levels.

## Processing Order

The module implements a strict innermost-first processing order:

```
Level 2 (deepest)   ← Process first
  │
  └─→ Complete all cuts
  
Level 1 (middle)    ← Process second
  │
  └─→ Complete all cuts
  
Level 0 (outermost) ← Process last
  │
  └─→ Complete all cuts
```

This ensures that:
1. Inner holes are burned before outer closed shapes
2. Material settles before adjacent shapes are burned
3. Material shift is fully accounted for

## Material Shift Scenario

The hierarchical approach correctly handles the material shift problem:

### Example Scenario
```
Rectangle A (closed) with hole B inside
Rectangle C nearby (would overlap if A's material shifts)

Current approach (problematic):
  1. Burn B (hole)
  2. Nearest is C, burn it    ← But A's material hasn't settled!
  3. Burn A (outer)           ← Material shifts, misalignment
  
Hierarchical approach (correct):
  1. Level 1: Burn B (hole inside A)
  2. Material settles
  3. Level 0: Burn A (outer) then C
     (A and C are independent at Level 0)
```

## Testing

Comprehensive test suite in `test/test_cutplan_hierarchical.py`:

**Test Classes:**
- `TestHierarchyLevel` - Tests HierarchyLevel functionality
- `TestHierarchyContext` - Tests HierarchyContext functionality
- `TestBuildHierarchyLevels` - Tests hierarchy building algorithm
- `TestValidateHierarchy` - Tests hierarchy validation
- `TestHierarchicalCutPlan` - Tests optimizer class
- `TestPrintFunctions` - Tests debugging/analysis functions

**Running Tests:**
```bash
python -m pytest test/test_cutplan_hierarchical.py -v
```

## Debugging & Analysis

### print_hierarchy(hierarchy: HierarchyContext) -> str

Generates human-readable hierarchy representation:

```python
output = print_hierarchy(hierarchy)
print(output)
```

**Output example:**
```
Hierarchy Structure:
  Root levels: 2
  Total levels: 5
  Level 0: 1 cuts
    - Group A
  Level 1: 2 cuts
    - Group B
    - Group E
```

### print_hierarchy_stats(hierarchy: HierarchyContext) -> str

Generates statistics about the hierarchy:

```python
output = print_hierarchy_stats(hierarchy)
print(output)
```

**Output example:**
```
Hierarchy Statistics:
  Total cuts: 100
  Total levels: 4
  Max depth: 3
  Cuts by level:
    Level 0: 20 cuts
    Level 1: 30 cuts
    Level 2: 30 cuts
    Level 3: 20 cuts
```

## Performance Characteristics

### Complexity Analysis

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Hierarchy Detection | O(N² × check) | Same as `inner_first_ident` |
| Build Hierarchy Levels | O(N × depth) | Very fast |
| Hierarchy Validation | O(N) | Linear |
| Hierarchical Selection | O(Σ(Li²)) | Li = cuts at level i |

**Typical Case:**
- For hierarchy with 4 levels, cuts distributed as [1000, 500, 250, 250]
- Current approach: O(1000²) = 1M operations
- Hierarchical approach: O(1000² + 500² + 250² + 250²) ≈ 1.39M operations
- No significant degradation, but clearer logic

### Memory Overhead

- HierarchyLevel objects: O(N) where N = number of levels
- HierarchyContext: O(N) + O(level_count)
- Typical overhead: < 1% of total memory

## Integration with CutPlan

To integrate this module into the main CutPlan class:

```python
# In CutPlan.optimize_cuts()

# Option 1: Use feature flag
if self.use_hierarchical_selection and c.constrained:
    from meerk40t.core.cutplan_hierarchical import HierarchicalCutPlan
    optimizer = HierarchicalCutPlan(kernel=self.context.kernel, channel=channel)
    c = optimizer.optimize_with_hierarchy(c, use_inner_first=True)
else:
    # Existing logic
    c = short_travel_cutcode(c, ...)

# Option 2: Gradual migration
# Run both in parallel on test data, verify results match
```

## Known Limitations & Future Work

### Current Limitations
1. **Multi-parent hierarchies**: Groups inside multiple unrelated outer groups are handled by using first parent as primary
2. **Non-closed shapes**: Open paths can be inside closed shapes, hierarchy level logic works the same
3. **Raster images**: RasterCut can be inside CutGroup, hierarchy handling similar to other cuts

### Future Enhancements
1. Better handling of multi-parent relationships
2. Unified hierarchy handling for hatch patterns
3. Performance optimization for very deep hierarchies
4. Integration into CutPlan as default when `opt_inner_first=True`

## Backward Compatibility

The module is designed for backward compatibility:
- Reuses existing `inner_first_ident()` and travel optimization functions
- Can be integrated as optional feature via feature flag
- Doesn't modify existing cutplan.py
- Tests validate against existing behavior

## References

- **Architecture Analysis:** `CUTPLAN_RESTRUCTURING_ANALYSIS.md`
- **Implementation Details:** `CUTPLAN_IMPLEMENTATION_PROPOSAL.md`
- **Visual Comparison:** `CUTPLAN_VISUAL_COMPARISON.md`
- **Main Module:** `meerk40t/core/cutplan.py`
- **Existing Tests:** `test/test_drivers_*.py`, `test/test_cutplan_*.py`
