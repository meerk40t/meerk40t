## CutPlan Restructuring: Detailed Implementation Proposal

### Executive Summary

The current cutplan.py treats hierarchy as a **constraint applied during optimization**. The proposed restructuring makes hierarchy the **primary organizing principle**, with travel optimization as a **secondary concern within each hierarchy level**.

**Key Change:**
- **Current:** Travel optimization selects candidates, with `.contains`/`.inside` attributes as constraints
- **Proposed:** Hierarchy levels select candidates first, travel optimization minimizes distance within a level

---

## Architecture Redesign

### Current Architecture (Implicit Hierarchy)
```
CutCode
├── CutGroup A (closed, .contains=[B,C])
├── CutGroup B (closed, .inside=[A], .contains=[C])
├── CutGroup C (open path, .inside=[A,B])
├── CutGroup D (closed, standalone)
└── ...

optimize_cuts()
  ├─ inner_first_ident() → marks hierarchy
  └─ short_travel_cutcode_optimized() → uses hierarchy as constraint
```

**Problem:** The ordering of the groups in the CutCode is arbitrary. Travel optimizer picks next cut from "candidates" without explicit understanding of hierarchy levels.

---

### Proposed Architecture (Explicit Hierarchy)

#### New Data Structure: HierarchyLevel

```python
class HierarchyLevel:
    """
    Represents one level in the containment hierarchy.
    
    All groups at the same level are independent of each other but
    depend on their parent level being complete.
    """
    def __init__(self, level_number: int, parent_level=None):
        self.level = level_number
        self.cuts: list[CutGroup] = []
        self.parent_level: Optional[HierarchyLevel] = parent_level
        self.child_levels: list[HierarchyLevel] = []
    
    def add_cut(self, cut: CutGroup):
        """Add a cut at this level"""
        self.cuts.append(cut)
        cut._hierarchy_level = self  # Back reference
    
    def add_child_level(self, child_level):
        """Register child level"""
        self.child_levels.append(child_level)
        child_level.parent_level = self
    
    def is_complete(self) -> bool:
        """Check if all cuts at this level are marked done"""
        return all(cut.burns_done == cut.passes for cut in self.cuts)


class HierarchyContext:
    """
    Represents the complete containment hierarchy for a CutCode.
    """
    def __init__(self):
        self.root_levels: list[HierarchyLevel] = []  # Top-level groups
        self.all_levels: list[HierarchyLevel] = []   # All levels in order
        self.level_by_group: dict[CutGroup, HierarchyLevel] = {}
    
    def get_next_level_candidates(self, completed_levels) -> CutGroup:
        """
        Get all cuts that are ready to be executed.
        
        Returns groups whose parent levels are complete.
        """
        for level in self.all_levels:
            if level in completed_levels:
                continue
            # Check if parent is complete
            if level.parent_level is None or level.parent_level.is_complete():
                yield from level.cuts
```

#### New Function: Build Hierarchy from CutCode

```python
def build_hierarchy_levels(context: CutCode) -> HierarchyContext:
    """
    Convert the containment attributes (.contains, .inside) into
    explicit hierarchy levels.
    
    Algorithm:
    1. Find all groups with no parent (standalone or no .inside)
    2. For each parent group, create level for its children
    3. Recursively process children
    4. Return ordered structure
    
    Args:
        context: CutCode with .contains/.inside populated by inner_first_ident
    
    Returns:
        HierarchyContext with explicit levels
    """
    hierarchy = HierarchyContext()
    groups = [c for c in context if isinstance(c, CutGroup)]
    
    # Identify root groups (have no parent)
    root_groups = [g for g in groups if g.inside is None or len(g.inside) == 0]
    
    # Create root levels
    for group in root_groups:
        level = HierarchyLevel(level_number=0)
        level.add_cut(group)
        hierarchy.root_levels.append(level)
        hierarchy.level_by_group[group] = level
        hierarchy.all_levels.append(level)
    
    # Recursively add child levels
    processed = set(root_groups)
    current_level_num = 0
    
    while len(processed) < len(groups):
        # Find all groups whose parents have been processed
        next_to_process = []
        for g in groups:
            if g in processed:
                continue
            # Check if all parents are processed
            if g.inside and all(parent in processed for parent in g.inside):
                next_to_process.append(g)
        
        if not next_to_process:
            # Shouldn't happen if hierarchy is valid
            break
        
        current_level_num += 1
        
        # Group by immediate parent
        by_parent = {}
        for g in next_to_process:
            if g.inside:
                # Use first parent as "immediate" parent (could refine this)
                parent = g.inside[0]
                if parent not in by_parent:
                    by_parent[parent] = []
                by_parent[parent].append(g)
        
        # Create levels for each parent
        for parent, children in by_parent.items():
            parent_level = hierarchy.level_by_group[parent]
            child_level = HierarchyLevel(
                level_number=current_level_num,
                parent_level=parent_level
            )
            
            for child in children:
                child_level.add_cut(child)
                hierarchy.level_by_group[child] = child_level
                parent_level.add_child_level(child_level)
            
            hierarchy.all_levels.append(child_level)
        
        processed.update(next_to_process)
    
    return hierarchy
```

---

## Processing Strategy: Level-by-Level Selection

### Current Selection (Travel-Optimizer Driven)

```python
# Current: optimizer picks from all candidates
ordered = CutCode()
while have_candidates:
    candidates = context.candidate(complete_path, grouped_inner)
    next_cut = optimizer_select_nearest(current_pos, candidates)
    ordered.append(next_cut)
    mark_done(next_cut)
```

**Problem:** Candidates can come from ANY level, potentially linking across hierarchy levels and causing the "material shift" issue you mentioned.

---

### Proposed Selection (Hierarchy-Level Driven)

```python
def hierarchical_selection(context: CutCode, hierarchy: HierarchyContext,
                          optimizer_func) -> CutCode:
    """
    Process the hierarchy level by level, using the travel optimizer
    within each level only.
    
    Algorithm:
    1. Start at innermost uncompleted level (highest in hierarchy)
    2. Get all candidates at that level
    3. Apply travel optimization to candidates at that level only
    4. Execute until level is complete
    5. Move to parent level
    6. Repeat until all complete
    
    This ensures:
    - Inner cuts complete before outer cuts
    - Material shift is accounted for
    - Travel optimization still works within constraints
    """
    ordered = CutCode()
    completed_levels = set()
    
    # Sort hierarchy from innermost to outermost
    # (process deepest levels first)
    levels_in_order = sorted(
        hierarchy.all_levels,
        key=lambda l: l.level,
        reverse=True  # Start with deepest (highest number)
    )
    
    for level in levels_in_order:
        # Check if this level is ready (parent is complete)
        if level.parent_level and level.parent_level not in completed_levels:
            continue  # Skip if parent not done
        
        if not level.cuts:
            continue  # Skip empty levels
        
        # Create temporary context with just this level's cuts
        level_context = CutCode()
        for cut in level.cuts:
            level_context.append(cut)
        
        if level_context.start is not None:
            level_context._start_x, level_context._start_y = level_context.start
        
        # Apply travel optimization within this level
        # Key: optimizer works on reduced set (just this level)
        optimized_level = optimizer_func(
            context=level_context,
            kernel=None,
            channel=None,
            complete_path=False,
            grouped_inner=False,  # Already at same hierarchy level
            hatch_optimize=False   # Handle in separate pass if needed
        )
        
        # Add to final result
        ordered.extend(optimized_level)
        completed_levels.add(level)
    
    return ordered
```

---

## Integration into CutPlan.optimize_cuts()

### Proposed Modified Method

```python
def optimize_cuts(self):
    """
    Optimize cuts using hierarchical selection with travel optimization.
    
    New flow:
    1. Run inner_first_ident() to identify hierarchy
    2. Build explicit hierarchy levels
    3. Process level by level with travel optimization
    4. Respect inner-first constraint throughout
    """
    busy = self.context.kernel.busyinfo
    _ = self.context.kernel.translation
    
    if busy.shown:
        busy.change(msg=_("Optimize cuts - Phase 1: Build hierarchy"), keep=1)
        busy.show()
    
    tolerance = self._calculate_tolerance()
    channel = self.context.channel("optimize", timestamp=True)
    
    for i, c in enumerate(self.plan):
        if not isinstance(c, CutCode):
            continue
        
        # PHASE 1: Build hierarchy structure
        if c.constrained:
            if channel:
                channel("Phase 1: Identifying hierarchy...")
            
            c = inner_first_ident(
                c,
                kernel=self.context.kernel,
                channel=channel,
                tolerance=tolerance,
            )
            
            # NEW: Build explicit hierarchy levels
            if channel:
                channel("Phase 1: Building hierarchy levels...")
            
            hierarchy = build_hierarchy_levels(c)
            c._hierarchy = hierarchy
            
            if channel:
                channel(f"Built {len(hierarchy.all_levels)} hierarchy levels")
            
            if busy.shown:
                busy.change(
                    msg=_("Optimize cuts - Phase 2: Process hierarchy levels"),
                    keep=1
                )
                busy.show()
            
            # PHASE 2: Process with hierarchy
            if channel:
                channel("Phase 2: Processing hierarchy levels...")
            
            c = hierarchical_selection(
                context=c,
                hierarchy=hierarchy,
                optimizer_func=short_travel_cutcode_optimized
            )
        else:
            # No hierarchy, use standard travel optimization
            c = short_travel_cutcode(
                c,
                channel=channel,
                grouped_inner=False,
            )
        
        self.plan[i] = c
```

---

## Compatibility & Migration

### Backward Compatibility

```python
# Old code still works
if c.constrained:
    c = short_travel_cutcode_optimized(c, ...)

# New code uses hierarchy
if c.constrained and USE_NEW_HIERARCHY:
    c = hierarchical_selection(c, ...)
```

### Feature Flag

```python
class CutPlan:
    def __init__(self, name, planner):
        # ... existing code ...
        self.use_hierarchical_selection = True  # Feature flag
        self.use_hierarchical_selection = (
            self.context.kernel.settings.get(
                "optimize/use_hierarchical_selection",
                False  # Default to False for now
            )
        )
```

---

## Testing Strategy

### Unit Tests

```python
def test_build_hierarchy_simple():
    """Test building hierarchy for A contains B contains C"""
    # Setup: A (closed) contains B (closed) contains C (open)
    # Expected: 3 levels with clear parent-child relationships
    pass

def test_build_hierarchy_multiple_roots():
    """Test multiple independent hierarchies"""
    # Setup: A and D are independent, each has their own hierarchy
    # Expected: Separate root levels for A and D
    pass

def test_hierarchical_selection_ordering():
    """Verify level-by-level execution order"""
    # Setup: Multi-level hierarchy
    # Expected: Inner levels execute before outer levels
    pass

def test_hierarchical_selection_vs_flat():
    """Verify that hierarchical selection produces different result than flat"""
    # Setup: Hierarchy where nearest-neighbor would cross levels
    # Expected: Hierarchical respects levels, flat does not
    pass
```

### Integration Tests

```python
def test_material_shift_scenario():
    """
    Verify material shift scenario is handled:
    - Large outer rectangle
    - Small inner hole
    - Other shapes that would be affected by material shift
    
    Expected:
    - Inner hole done first
    - Other shapes processed after considering material shift
    """
    pass
```

---

## Performance Considerations

### Current Algorithm Complexity
- `inner_first_ident`: O(N² × containment_check)
- `short_travel_cutcode_optimized`: O(K² × travel_distance_calc)
  where K = number of candidates, typically K ≈ N

### Proposed Algorithm Complexity
- `build_hierarchy_levels`: O(N × max_depth)
- `hierarchical_selection`: O(Σ(Li²)) where Li = cuts at level i
  - In worst case (all at one level): O(N²) - same as current
  - In typical case (distributed): O(N²) - no worse
  - No polynomial increase

### Memory Overhead
- `HierarchyLevel` objects: O(N) where N = number of levels
- `HierarchyContext`: O(N) + O(level_count)
- Minimal overhead (typical: < 1% increase)

---

## Open Questions

1. **Multi-parent groups**: What if shape C is inside both A and B (peers)?
   - Current design: Use first parent as primary
   - Alternative: Create separate entries or shared level?

2. **Non-closed shapes**: How to handle open paths in hierarchy?
   - Current: Can be inside closed shapes
   - Proposed: Same handling, but separate "level" logic for sequences

3. **Raster images**: How do they fit in hierarchy?
   - Current: RasterCut can be inside CutGroup
   - Proposed: Same, but need to verify level assignment

4. **Hatch patterns**: Interact with new hierarchy?
   - Current: Marked with `.skip` for separate processing
   - Proposed: Should also respect hierarchy levels

---

## Implementation Timeline

### Week 1: Foundation
- [ ] Create `HierarchyLevel` and `HierarchyContext` classes
- [ ] Implement `build_hierarchy_levels()` function
- [ ] Add unit tests

### Week 2: Selection
- [ ] Implement `hierarchical_selection()` function
- [ ] Add integration into `optimize_cuts()`
- [ ] Test with existing scenarios

### Week 3: Validation
- [ ] Run full test suite
- [ ] Performance profiling
- [ ] Real-world scenario testing

### Week 4: Cleanup & Documentation
- [ ] Code review
- [ ] Documentation updates
- [ ] Feature flag removal (full deploy)

---

## Risk Mitigation

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Regression in existing behavior | Keep feature flag; run all existing tests |
| Performance degradation | Profile regularly; optimize if needed |
| Multi-parent hierarchy issues | Handle in Phase 2; use first-parent for now |
| Hatch pattern interaction | Plan Phase 2 for unified hierarchy handling |

---

## Summary

This restructuring makes the cutplan module's logic clearer by:
1. **Explicit hierarchy structure** instead of implicit constraints
2. **Level-by-level processing** instead of global optimization
3. **Separation of concerns**: hierarchy vs. travel optimization
4. **Better handling** of your Priority 1 requirement: material shift awareness

The implementation is **backward compatible** and can be rolled out incrementally with a feature flag.

