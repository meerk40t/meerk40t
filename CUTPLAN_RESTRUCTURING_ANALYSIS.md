## Analysis: CutPlan Module Architecture & Proposed Restructuring

### Current State

The `cutplan.py` module (3870 lines) has evolved into a complex system with the following key components:

#### Current Flow (Simplified):
```
CutPlan.blob() 
  ↓ [Convert operations to CutCode]
CutPlan.preopt()
  ↓ [Add optimization commands]
CutPlan.optimize_cuts() or optimize_travel()
  ├→ inner_first_ident() 
  │  └─ Identifies closed groups and their contents (lines 2356-2440)
  │  └─ Sets .contains and .inside attributes
  │  └─ Returns context with constrained=True if hierarchy found
  │
  └→ short_travel_cutcode()
     └─ short_travel_cutcode_optimized() (lines 2719-2870)
        └─ Selects algorithm based on dataset_size
        └─ Calls _group_aware_selection or _group_preserving_selection
        └─ Or calls _simple_greedy / _improved_greedy / _spatial_optimized
```

#### Current Hierarchy Handling:
- `inner_first_ident()` detects which groups are inside others
- Sets `.contains` (groups this group contains) and `.inside` (outer groups)
- But applies this **after** creating CutCode objects
- Hierarchy is treated as a **constraint** during travel optimization, not as a **primary organizing principle**

---

### The Problem With Current Approach

Your Priority 1 requirement states:
> "If we have cut inner first established, look for closed shapes inside 'op cut' operations. If we find any other shapes that lie inside/cover part of that shape, these should be done BEFORE the closed cut finishes."

**Current implementation issues:**
1. Hierarchy detection (`inner_first_ident`) happens AFTER cutting sequence is largely established
2. Travel optimization doesn't properly account for: "shape A is inside shape B which is inside shape C"
3. No explicit "hierarchical selection phase" - just constraints passed to travel algorithms
4. When selecting cuts, algorithm doesn't consider: "burning this cut will shift the material, affecting inner cuts"

---

### Proposed Restructuring

#### Phase 1: **Hierarchical Organization** (NEW - Before Travel Optimization)
```
Purpose: Build complete containment hierarchy
Inputs: CutCode with all groups identified
Output: Hierarchical structure with:
  - Level 0: Outermost closed shapes
  - Level N: Shapes inside Level N-1 shapes
  - Constraints: Inner shapes must complete before outer shapes

Algorithm:
1. Identify ALL closed CutGroups
2. For each closed group, find ALL shapes it contains (recursive)
3. Build multi-level hierarchy 
4. Mark which groups BLOCK others (need to be cut first)
```

**Why this matters:**
- Shape A (closed) contains Shape B (closed) contains Shape C (open path)
- Current: C, B, A could be interleaved
- Proposed: C and B MUST finish before A starts

#### Phase 2: **Hierarchical Selection** (MODIFIED - Primary Optimization)
```
Purpose: Select cut sequence respecting hierarchy
Inputs: Hierarchical organization from Phase 1
Output: Ordered sequence with inner-first constraints

Algorithm:
For each hierarchy level (from innermost to outermost):
  1. Start with innermost uncompleted level
  2. Identify all candidates at this level
  3. Apply travel optimization WITHIN this level
  4. Mark level as complete
  5. Move to next level (whose parent just finished)

Key insight:
- Travel optimization only happens WITHIN hierarchy levels
- Between levels, the decision is made by hierarchy structure
```

**Why this matters:**
- Prevents "nearest neighbor" from linking to a cut in a different hierarchy
- Ensures blocking shapes get handled first

#### Phase 3: **Travel Optimization** (EXISTING - But Constrained by Hierarchy)
```
Purpose: Minimize distance within hierarchy level
Inputs: Candidates at current hierarchy level
Output: Optimized sequence maintaining hierarchy

This can still use existing algorithms:
- nearest_neighbor
- 2-opt
- spatial_indexed
- But operating on pre-filtered set of compatible candidates
```

---

### Code Restructuring Proposal

#### Option A: Minimal Changes (Backward Compatible)
```python
def optimize_cuts(self):
    # ... existing setup code ...
    
    # NEW PHASE 1: Build hierarchical structure
    for i, c in enumerate(self.plan):
        if isinstance(c, CutCode) and c.constrained:
            self.plan[i] = self._build_hierarchy(c)
    
    # MODIFIED PHASE 2: Use hierarchy for sequencing
    for i, c in enumerate(self.plan):
        if isinstance(c, CutCode) and c.constrained:
            self.plan[i] = self._hierarchical_selection(c, ...)

def _build_hierarchy(self, context: CutCode) -> CutCode:
    """
    Build explicit hierarchy levels from containment relationships.
    Returns context with new .hierarchy attribute containing
    ordered list of levels.
    """
    # 1. Run existing inner_first_ident
    context = inner_first_ident(context, ...)
    
    # 2. Convert to explicit hierarchy levels
    hierarchy = _build_hierarchy_levels(context)
    context.hierarchy = hierarchy
    
    return context

def _hierarchical_selection(self, context: CutCode, ...) -> CutCode:
    """
    Process hierarchy level by level, applying travel optimization
    at each level.
    """
    if not hasattr(context, 'hierarchy'):
        return short_travel_cutcode_optimized(context, ...)
    
    # Process each level respecting hierarchy
    ordered = CutCode()
    for level in context.hierarchy:
        # Create temporary CutCode with just this level
        level_context = CutCode()
        level_context.extend(level.cuts)
        
        # Apply travel optimization to this level
        optimized = short_travel_cutcode_optimized(
            level_context,
            ...
            grouped_inner=False  # Already at same hierarchy level
        )
        
        ordered.extend(optimized)
    
    return ordered
```

#### Option B: Major Redesign (Better Architecture)
```python
class HierarchyLevel:
    """Represents one level in the containment hierarchy"""
    def __init__(self):
        self.cuts = []           # CutGroups at this level
        self.parent_level = None # Which level contains this one
        self.child_levels = []   # Which levels are inside this one

class HierarchyProcessor:
    """Handles hierarchical structure and sequencing"""
    
    def build_hierarchy(self, context: CutCode) -> list[HierarchyLevel]:
        """Convert containment attributes into explicit levels"""
        pass
    
    def validate_hierarchy(self, levels: list[HierarchyLevel]) -> bool:
        """Ensure hierarchy is consistent"""
        pass
    
    def select_with_hierarchy(self, levels: list[HierarchyLevel], 
                              optimizer) -> CutCode:
        """Process levels in order, applying optimizer to each"""
        pass

def optimize_cuts(self):
    # ... setup ...
    processor = HierarchyProcessor()
    for i, c in enumerate(self.plan):
        if isinstance(c, CutCode) and c.constrained:
            # Run inner_first_ident as before
            c = inner_first_ident(c, ...)
            
            # Build hierarchy structure
            hierarchy = processor.build_hierarchy(c)
            processor.validate_hierarchy(hierarchy)
            
            # Process with hierarchy
            self.plan[i] = processor.select_with_hierarchy(
                hierarchy,
                optimizer=short_travel_cutcode_optimized
            )
```

---

### Benefits of Proposed Restructuring

| Aspect | Current | Proposed |
|--------|---------|----------|
| **Hierarchy awareness** | Constraint passed to optimizer | Primary organizing principle |
| **Level sequencing** | Travel algo decides order | Hierarchy decides; travel optimizes within |
| **Blocking prevention** | Implicit via constraints | Explicit; can't link across levels |
| **Nested hierarchy** | Flattened approach | Multi-level support (A→B→C) |
| **Material shift handling** | Not considered | Explicit: inner completes before outer |
| **Code clarity** | Mixed concerns | Clear separation of phases |
| **Testing** | Hard to verify logic | Each phase independently testable |

---

### Recommended Approach

**Start with Option A (Minimal Changes):**
1. Add `_build_hierarchy()` method to make levels explicit
2. Add `_hierarchical_selection()` method to process levels
3. Keep existing `short_travel_cutcode_optimized()` unchanged
4. Gradual transition allows testing and validation

**Then move to Option B:**
1. Create `HierarchyProcessor` class
2. Move hierarchy logic into dedicated class
3. Improve testability and modularity
4. Cleaner separation of concerns

---

### Implementation Priority

**Phase 1 (Immediate):**
- [x] Build hierarchy levels from `.contains`/`.inside` attributes
- [x] Validate that hierarchy is acyclic and consistent

**Phase 2 (Short term):**
- [ ] Implement level-by-level processing
- [ ] Test with existing test cases
- [ ] Verify no regression

**Phase 3 (Medium term):**
- [ ] Extract to `HierarchyProcessor` class
- [ ] Improve documentation with examples
- [ ] Performance optimization if needed

---

### Key Questions to Address

1. **What about non-closed shapes?**
   - Currently only closed shapes form hierarchy
   - Open paths need to be handled - hierarchy level or independent?

2. **What about overlapping hierarchies?**
   - Shape A inside both B and C (not inside each other)?
   - Need clear rules for membership

3. **Performance implications?**
   - Current: O(N²) for all groups against all closed groups
   - Proposed: Still O(N²) but explicit structure
   - No significant change expected

4. **Backward compatibility?**
   - Proposed keeps existing functions
   - New logic adds feature, doesn't remove
   - Safe transition possible

