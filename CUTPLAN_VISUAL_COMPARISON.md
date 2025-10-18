## CutPlan Module: Visual Comparison

### CURRENT ARCHITECTURE (Implicit Hierarchy)

```
┌─────────────────────────────────────────────────────────────┐
│ CutCode: [A (closed), B (closed), C (open), D (closed)]    │
├─────────────────────────────────────────────────────────────┤
│ After inner_first_ident():                                  │
│  A.contains = [B, C]  |  B.inside = [A]                   │
│  B.contains = [C]     |  C.inside = [A, B]                │
│  D.contains = []      |  D.inside = []                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────────┐
        │ short_travel_cutcode_optimized()          │
        │                                           │
        │ candidates = context.candidate(...)       │
        │ while candidates:                         │
        │   next = pick_nearest(current_pos,       │
        │          candidates,                      │
        │          constraints=.contains/.inside)  │
        │   append(next)                            │
        │   mark_done(next)                         │
        │   candidates = context.candidate(...)     │
        └───────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────────┐
        │ Execution Sequence:                       │
        │ (Determined by travel optimizer)          │
        │                                           │
        │ Could be: A → B → C → D                  │
        │       or: C → B → A → D                  │
        │       or: D → C → B → A                  │
        │       or: ...any valid combination        │
        │                                           │
        │ ⚠️ Risk: Crosses hierarchy levels!        │
        │         "nearest" can link across levels  │
        └───────────────────────────────────────────┘

PROBLEM: Travel optimizer doesn't "know" about hierarchy levels
         It just sees constraints
```

---

### PROPOSED ARCHITECTURE (Explicit Hierarchy)

```
┌─────────────────────────────────────────────────────────────┐
│ CutCode: [A (closed), B (closed), C (open), D (closed)]    │
├─────────────────────────────────────────────────────────────┤
│ After inner_first_ident():                                  │
│  A.contains = [B, C]  |  B.inside = [A]                   │
│  B.contains = [C]     |  C.inside = [A, B]                │
│  D.contains = []      |  D.inside = []                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────────┐
        │ build_hierarchy_levels()                  │
        │                                           │
        │ Creates explicit hierarchy structure:     │
        └───────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ HierarchyContext:                                           │
│                                                             │
│ Level 0 (Root):     [A]  [D]                              │
│   ├─ Level 1:       [B]  (inside A)                        │
│   │   ├─ Level 2:   [C]  (inside B)                        │
│                                                             │
│ Processing order:  Level 2 → Level 1 → Level 0            │
│                    (innermost first)                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────────┐
        │ hierarchical_selection()                  │
        │                                           │
        │ for level in levels (innermost first):   │
        │   candidates = cuts_at_level             │
        │   optimized = travel_optimizer(          │
        │      candidates)  ← LIMITED SET!         │
        │   append(optimized)                      │
        └───────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────────┐
        │ Execution Sequence:                       │
        │ (Determined by hierarchy first,           │
        │  then travel optimizer within level)      │
        │                                           │
        │ MUST be: C (inside B)                    │
        │       → B (inside A)                      │
        │       → A (root) AND/OR D (root)         │
        │                                           │
        │ ✓ Hierarchy levels respected!             │
        │ ✓ Material shift handled!                 │
        │ ✓ Travel optimized within level!         │
        └───────────────────────────────────────────┘

BENEFIT: Explicit hierarchy prevents crossing between levels
         Travel optimizer can't "accidentally" link across
```

---

### SCENARIO: Material Shift Problem

#### Current Approach (Can Fail)

```
SETUP: Rectangle A (closed) with hole B inside
       Rectangle C nearby, but would overlap if material shifts
       Line D crossing both

Geometry:
    ┌──────────────────┐
    │  A (Rectangle)   │
    │  ┌────────────┐  │
    │  │   Hole B   │  │
    │  └────────────┘  │
    └──────────────────┘
           C (Rectangle)  ← Would overlap after A is cut
        ─────────D────────  ← Line crossing both

Naive nearest-neighbor (current risk):
1. Start at hole B        ← burn
2. Go to nearest: C       ← burn (but material hasn't settled!)
3. Go to nearest: D       ← misaligned!
4. Go to A                ← burn outer

PROBLEM: C was burned while material still floating
         D gets burned at wrong position
         Result: Misaligned cuts
```

#### Proposed Approach (Handles Correctly)

```
Explicit hierarchy:
  Level 0: [A]
    └─ Level 1: [B]
  Level 0: [C, D]  ← Separate from A's hierarchy

Processing:
1. Process Level 1: Burn B    ← hole first
2. Process Level 0 (A): Burn A ← outer last (material settled)
3. Process Level 0 (C,D): Burn C, D in optimized order

BENEFIT: B completes, material settles, THEN C is burned
         Proper position ensured
```

---

### ALGORITHM COMPARISON

#### Candidate Selection

**Current (Travel-first):**
```
get_all_candidates():
    return [A, B, C, D, E, F, ...]  ← ALL possible cuts

travel_optimizer picks from this set:
    nearest_neighbor(position, [A, B, C, D, E, F, ...])
    might link A → F → D → B  ← Crosses multiple hierarchy levels!
```

**Proposed (Hierarchy-first):**
```
get_candidates_at_current_level():
    if current_level == 2:
        return [B, C]             ← Only Level 2
    if current_level == 1:
        return [A, D]             ← Only Level 1 (2 is done)
    if current_level == 0:
        return [X, Y, Z]          ← Only Level 0

travel_optimizer picks from FILTERED set:
    nearest_neighbor(position, [B, C])      ← Within level
    links B → C                             ← Both at same level
```

---

### CODE FLOW VISUALIZATION

#### Current Flow

```
optimize_cuts()
  │
  ├─→ inner_first_ident(context)
  │   └─ Sets: context.contains, context.inside
  │
  ├─→ short_travel_cutcode_optimized(context)
  │   ├─ if dataset_size < 50:
  │   │  └─ _simple_greedy_selection()
  │   ├─ elif dataset_size < 100:
  │   │  └─ _improved_greedy_selection()
  │   ├─ elif dataset_size <= 500:
  │   │  └─ _spatial_optimized_selection()
  │   └─ else:
  │      └─ short_travel_cutcode_legacy()
  │
  └─→ RESULT: CutCode with optimized sequence
      (based on travel distance only)
```

#### Proposed Flow

```
optimize_cuts()
  │
  ├─→ inner_first_ident(context)
  │   └─ Sets: context.contains, context.inside
  │
  ├─→ build_hierarchy_levels(context)  ← NEW
  │   └─ Creates: HierarchyContext with Levels
  │
  ├─→ hierarchical_selection(context, hierarchy)  ← NEW
  │   ├─ for level in hierarchy.levels:
  │   │   ├─ level_candidates = get_cuts_at_level(level)
  │   │   └─ optimized_level = travel_optimizer(level_candidates)
  │   │       (optimizer can be simple, improved, spatial, or legacy)
  │   │
  │   └─ RESULT: CutCode with:
  │       - Hierarchy levels respected
  │       - Travel optimized within each level
  │
  └─→ RESULT: CutCode with optimized sequence
      (respecting hierarchy AND travel distance)
```

---

### HIERARCHY LEVEL STRUCTURE

#### Visual Representation

```
Tree View of Containment:
────────────────────────────────────────

Level 0 (Roots):
│
├─ Group A (closed)
│  ├─ Level 1:
│  │  ├─ Group B (closed)
│  │  │  ├─ Level 2:
│  │  │  │  ├─ Group C (open path)
│  │  │  │  └─ Group E (closed)
│  │  │  └─
│  │  └─
│  │
│  └─ (More Level 1 groups)
│
└─ Group D (closed)
   ├─ (No children)
   └─

Processing Order (Innermost First):
  1. Level 2: C, E (children of B)
  2. Level 1: B (child of A)
  3. Level 0: A, D (roots)
```

#### Data Structure

```python
HierarchyContext:
  .root_levels = [Level_0_a, Level_0_d]
  .all_levels = [
    Level_0_a,      # A
    Level_1_b,      # B (inside A)
    Level_2_c,      # C (inside B)
    Level_2_e,      # E (inside B)
    Level_0_d,      # D
  ]
  .level_by_group = {
    A: Level_0_a,
    B: Level_1_b,
    C: Level_2_c,
    E: Level_2_e,
    D: Level_0_d,
  }

HierarchyLevel:
  .level = 0  (depth: 0=root, 1=inside root, 2=inside level 1, etc)
  .cuts = [Group_A]
  .parent_level = None
  .child_levels = [Level_1_b]
```

---

### DECISION TREE: Which Algorithm to Use?

#### Current Decision

```
optimize_cuts()
  ├─ if opt_inner_first:
  │  ├─ inner_first_ident()
  │  └─ short_travel_cutcode_optimized()
  │     └─ dataset_size determines algorithm
  │
  └─ else:
     ├─ short_travel_cutcode_optimized()
     │  └─ dataset_size determines algorithm
     │
     └─ (constraints ignored if opt_inner_first=False)

ISSUE: opt_inner_first is a boolean flag
       Either uses hierarchy or doesn't
```

#### Proposed Decision

```
optimize_cuts()
  ├─ if opt_inner_first:
  │  ├─ inner_first_ident()
  │  ├─ if use_hierarchical_selection:
  │  │  ├─ build_hierarchy_levels()
  │  │  └─ hierarchical_selection()
  │  │     └─ travel_optimizer per level
  │  │
  │  └─ else (legacy):
  │     └─ short_travel_cutcode_optimized()
  │        └─ dataset_size determines algorithm
  │
  └─ else (no inner-first):
     └─ short_travel_cutcode_optimized()
        └─ dataset_size determines algorithm

IMPROVEMENT: Explicit hierarchy + travel optimization
             as separate concerns
```

---

### PERFORMANCE COMPARISON

#### Complexity Analysis

```
Operation               Current         Proposed        Notes
────────────────────────────────────────────────────────────
Hierarchy Detection     O(N² × check)   O(N² × check)   Same
Build Hierarchy Levels  —               O(N × depth)    New, fast
Candidate Filtering     O(K)            O(K / levels)   Reduced
Travel Optimization     O(K²)           O(Σ(Li²))       Typically better
Total per CutCode       O(N²)           O(N²) avg       No worse
────────────────────────────────────────────────────────────

Where:
  N = total cuts
  K = typical number of candidates (usually ≈ N)
  Li = cuts at hierarchy level i
  depth = max hierarchy depth

Typical: If 4 levels with cuts distributed as [1000, 500, 250, 250]:
  Current: O(1000²) = 1M operations
  Proposed: O(1000² + 500² + 250² + 250²) = 1.39M ≈ Same
           (But reduces cross-level linking overhead)
```

---

### SUMMARY TABLE

| Aspect | Current | Proposed | Impact |
|--------|---------|----------|--------|
| **Hierarchy** | Implicit (.contains) | Explicit (HierarchyLevel) | Clearer code |
| **Levels** | Flattened | Structured | Better organization |
| **Selection** | Global optimization | Level-by-level | Respects hierarchy |
| **Material Shift** | Not handled | Explicit awareness | Fixes your Priority 1 |
| **Travel Optimization** | Global | Within-level | Maintains quality |
| **Code Clarity** | Mixed concerns | Separated concerns | More maintainable |
| **Performance** | O(N²) | O(N²) average | No degradation |
| **Backward Compat** | — | Supported | Safe transition |

