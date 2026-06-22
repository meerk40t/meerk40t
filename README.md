# MeerK40t — Andre van der Westhuizen fork

**GitHub:** https://github.com/Andre6553/meerk40t

**Workspace (hardware, EEPROM, workflow):** [meerk40t_Makerbase_DLC32](https://github.com/Andre6553/meerk40t_Makerbase_DLC32)

**Current version:** `0.9.9040` · **Upstream:** [meerk40t/meerk40t](https://github.com/meerk40t/meerk40t)

Personal fork for a **Makerbase MKS DLC32** GRBL controller on a **30×40 cm, 60 W CO2** laser. Active local development — not the upstream maintenance branch.

**On this page:** [Fork changelog](#fork-changelog-meerk40t) · [Upstream README](#welcome-to-meerk40t)

---

## Fork changelog (MeerK40t)

**Latest entry:** **v0.9.9040**. Canonical copy also lives in the workspace repo at [`docs/meerk40t/15-meerkat-local-changes.md`](https://github.com/Andre6553/meerk40t_Makerbase_DLC32/blob/main/docs/meerk40t/15-meerkat-local-changes.md) (keep in sync when editing).

All entries are **fork-style edits** in this repository, not upstream MeerK40t releases.

## 2026-06 — Rotary: Fit uses native units → mm correctly (v0.9.9040)

**Files:** `meerk40t/meerk40t/rotary/rotary.py`

**Problem:** Fit treated scene bounds as mm but MeerK40t stores them in **native units** (~2580 per mm). It also stripped the normal text matrix `scale(UNITS_PER_PIXEL)`, which blew up font size and triggered false “bounds look wrong” errors on **new** text.

**Fix:** Convert selection size with `UNITS_PER_MM`; only remove **extra** matrix scale (old bugs), always keep `UNITS_PER_PIXEL` on text; use standard `selected_area()` for bounds.

## 2026-06 — Rotary: Fit selection fixes text (v0.9.9038)

**Files:** `meerk40t/meerk40t/rotary/rotary.py`

**Problem:** **Fit selection to rotary** scaled text by multiplying its matrix. wxPython draws text with `DrawText` + matrix, so scaled text looked like a shattered round blob.

**Fix:** Text is scaled via **font size** (and position nudge), not matrix scale.

## 2026-06 — Rotary Pro: diameter, steps calibration, GRBL hooks (v0.9.9035)

**Files:** `meerk40t/meerk40t/rotary/rotary.py`, `meerk40t/meerk40t/rotary/rotary_cam.py`, `meerk40t/meerk40t/grbl/driver.py`, `meerk40t/meerk40t/rotary/gui/rotarysettings.py`

**Feature:** Y-motor-swap chuck rotary for GRBL/DLC32 — diameter, usable length, Y steps compensation, homing guards, **Fit selection to rotary**, console `rotary` / `rotaryfit` / `rotarycal` / `rotarysuggest`.

## 2026-06 — Living Hinges: Apply to scene button visible (v0.9.9034)

**File:** `meerk40t/meerk40t/tools/livinghinges.py`

**Problem:** **Generate** sat below the left-column sliders and was often off-screen; users saw preview only with no obvious way to commit the pattern.

**Fix:** Renamed **Generate** → **Apply to scene**; moved it (with **Close**) under the **Preview** panel so it stays visible. Default window height 480 px.

## 2026-06 — Kerf-Test Create Pattern crash fix (v0.9.9033)

**File:** `meerk40t/meerk40t/tools/kerftest.py`

**Problem:** **Kerf-Test** → **Create Pattern** crashed with `AttributeError: 'Context' object has no attribute 'signal_refresh'`.

**Fix:** After generating the test pattern, refresh the scene with `refresh_scene` (same as **Parameter-Test**), not the non-existent `context.signal_refresh()`.

## 2026-06 — Line tool: click on existing geometry + precise preview (v0.9.9032)

**Files:** `meerk40t/meerk40t/gui/scenewidgets/selectionwidget.py`, `meerk40t/meerk40t/gui/scenewidgets/rectselectwidget.py`, `meerk40t/meerk40t/gui/toolwidgets/toolpointlistbuilder.py`

**Problem:** With the line tool active, clicks on top of an existing (selected) line were intercepted by selection/rect-select widgets, so a new line could not start on existing geometry unless the cursor moved away. While placing the second point, snap preview pulled the rubber-band endpoint away from the cursor (felt like overshoot when zoomed in).

**Fix:**
- Selection handles and rectangular selection now defer mouse events whenever `active_tool != "none"`.
- Point-list tools (line/polyline) follow the raw cursor for preview (`move`/`hover`/`leftdown`); snap is applied only on `leftclick` when placing a point.

## 2026-06 — Start new line directly on existing line (v0.9.9031)

**File:** `meerk40t/meerk40t/gui/scenewidgets/elementswidget.py`

**Problem:** After finishing a line, clicking directly on top of an existing line could be consumed as element selection first, so the first point of the next line did not start unless the cursor moved off the line.

**Fix:** `ElementsWidget` no longer consumes `leftclick` for selection while any non-`none` tool is active. This lets line/polyline and other creation tools start exactly on existing geometry.

## 2026-06 — Middle-mouse pan while drawing point tools (v0.9.9030)

**File:** `meerk40t/meerk40t/gui/toolwidgets/toolpointlistbuilder.py`

**Problem:** While drawing with point-based tools (Line/Polyline and related), pressing and dragging the middle mouse button did not pan the scene because move events were consumed by the active tool.

**Fix:** Point-list tools now pass through `move` events when the middle button is held (`m_middle` modifier), so scene panning can work during active drawing without ending the tool.

## 2026-06 — Camera Calibration Enter-key crash fix (v0.9.9029)

**Files:** `meerk40t/meerk40t/camera/gui/cameracal.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`

**Problem:** Opening **Camera Calibration** crashed: `wxTE_PROCESS_ENTER` required for Enter-key connect on the URI text box.

**Fix:** Camera URI fields created with `wx.TE_PROCESS_ENTER`.

## 2026-06 — Camera paste URL / IP connect (v0.9.9028)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`, `meerk40t/meerk40t/camera/gui/cameracal.py`

**Feature:** Users can paste a **USB index**, **full `rtsp://` URL**, **`user:pass@IP`**, or **bare IP** — `normalize_camera_uri()` builds the OpenCV address. **Connect** in **Camera URI** manager and **Camera Calibration** applies it to `camera0` (or chosen index) and saves it in the URI list.

**Andre's setup unchanged:** full URL `rtsp://admin:***@192.168.10.133:8554/stream1` still works as-is; shorthand `admin:***@192.168.10.133:8554/stream1` also works.

## 2026-06 — Camera align offset crash fix (v0.9.9027)

**File:** `meerk40t/meerk40t/camera/camera.py`

**Problem:** Crash on scene refresh after Update image: `AttributeError: 'Context' object has no attribute 'align_offset_scene_units'` — `camera_align_offsets_for_context` used `kernel.get_context("camera/N")` which can return a plain Context stub, not the Camera service.

**Fix:** `_camera_service_for_index()` resolves the real Camera service from `kernel.services("camera")` by path; skips non-Camera contexts. Composite path wraps offset lookup in try/except.

## 2026-06 — Camera bed photo MemoryDC composite (v0.9.9026)

**Files:** `meerk40t/meerk40t/gui/scene/scene.py`, `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`

**Problem:** Console still reported success with 1 bed widget but main scene stayed grey — `GraphicsContext.DrawBitmap` inside the scene layer cache does not paint reliably on Windows.

**Fix:** After the background layer is drawn, `composite_bed_photo_on_device_dc()` blits the bed photo with `MemoryDC.DrawBitmap` in device pixels. Bed widget skips the GC bitmap path. Console logs center-pixel RGB to confirm the frame has real image data.

## 2026-06 — Camera bed photo draw fix (v0.9.9025)

**Files:** `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`, `meerk40t/meerk40t/camera/camera.py`

**Problem:** Console reported `Bed background applied` but main scene stayed **grey** — camera bitmap was stored but not painted (Hide Background draw mode and/or `GraphicsContext.DrawBitmap` failing on Windows).

**Fix:** Bed widget **always draws** a stored camera bitmap (not gated by Hide Background). Pre-scales bitmap to screen pixels before draw; falls back to `CreateBitmapFromImage`. Clears Hide Background on root + scene contexts; `wx.CallAfter` refresh. Console shows bed widget count.

## 2026-06 — Camera bed apply crash fix (v0.9.9024)

**Files:** `meerk40t/meerk40t/camera/camera.py`

**Problem:** **Update image** crashed with `NameError: name '_' is not defined` in `push_bed_background_bitmap` right after the bed bitmap was built (v0.9.9023).

**Fix:** Module-level messages use `kernel.translation`; `Camera.background()` uses `self._()`.

## 2026-06 — Camera Update Image console messages fix (v0.9.9023)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`

**Problem:** **Update image** appeared to do nothing — messages used `self.channel("the message")` (wrong API) or the **camera** channel only, so nothing showed in the **Console** pane. `CameraInterface` passed the wrong context to `CameraPanel`.

**Fix:** `camera_user_log()` writes to **console** and **camera** channels. **Update image** calls `camera.background()` (same as right-click **Update Background**). Clear errors when the camera is **stopped**. `CameraInterface` uses **root** context like the docked camera pane.

## 2026-06 — Camera bed background direct widget apply (v0.9.9022)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`, `meerk40t/meerk40t/gui/wxmscene.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`

**Problem:** On v0.9.9021 the bed stayed **grey** after **Update image** — background signal did not reliably land on the bed widget; large full-res bitmaps could fail to draw on Windows.

**Fix:** `_apply_bed_background_to_scene()` sets the bitmap on every `BedWidget` directly (simulation-style path). Perspective warp capped at **1280 px** long edge. Bed draw tries `CreateBitmapFromImage` fallback. Console reports `Bed background applied (W x H px)` or a clear error.

## 2026-06 — Camera bed background direct scene push (v0.9.9021)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`, `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`

**Problem:** **Update image** still left a **grey** bed — background signal did not always reach the bed widget; bitmap build via `FromBuffer` was unreliable on Windows.

**Fix:** `push_bed_background_bitmap()` builds the bitmap with `wx.Image.SetData`, pushes it **directly** to the main scene bed widget (not only via kernel signal), clears **Hide Background** draw mode, and refreshes. Bed image stored under device label and `__default__` fallback.

## 2026-06 — Camera bed background grey regression fix (v0.9.9020)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`, `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`, `meerk40t/meerk40t/gui/wxmscene.py`

**Problem:** After v0.9.9019, **Update image** showed a **solid grey** bed again. v0.9.9019 bed pre-scaling used scene units (mm) as pixel sizes; shallow bitmap copies could be invalidated when the camera thread refreshed the live frame.

**Fix:** Reverted bed pre-scaling — `DrawBitmap` scales the photo to the bed rect. New `make_bed_bitmap_from_frame()` builds an **owned** wx bitmap from RGB bytes. Camera stream size is synced into `width`/`height` each frame so perspective warp stays at full resolution without the broken scale step.

## 2026-06 — Camera bed background full resolution (v0.9.9019)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`, `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`

**Problem:** Bed overlay looked **grainy / black-and-white** — perspective warp output was forced to **640×480** then stretched across the full bed.

**Fix:** Perspective correction now keeps the **live camera resolution** (e.g. 1920×1080). Bed draw uses **high-quality scaling** when fitting the photo to the bed.

## 2026-06 — Camera Update Image uses live bitmap (v0.9.9018)

**Files:** `meerk40t/meerk40t/camera/gui/camerapanel.py`, `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/gui/wxmscene.py`, `meerk40t/meerk40t/gui/simulation.py`

**Problem:** **Update image** still filled the bed with **solid grey** — frame buffer conversion failed (non-uint8 / wrong buffer type).

**Fix:** **Update image** now copies the **same wx bitmap** already shown in the camera window to the main scene. `camera background` console path forces **uint8 RGB** before `FromBuffer`. Console confirms `Bed background updated (W x H px).`

## 2026-06 — Camera Update Image grey bed fix (v0.9.9017)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/gui/wxmscene.py`, `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`

**Problem:** **Update image** on the camera window left the main scene **grey** (no bed photo).

**Fix:** Safer RGB buffer for `wx.Bitmap.FromBuffer`; bed draw handles **negative height** (top-left / Flip Y); background stored even if device label was missing; **Show Background** draw mode turned on when updating; console message if no camera frame yet.

## 2026-06 — Camera Calibration window shows Fine alignment (v0.9.9016)

**Files:** `meerk40t/meerk40t/camera/gui/cameracal.py`

**Fix:** **Fine alignment (mm)** was hidden when the window kept an old saved size. Window now auto-grows to fit; section lives inside **Actions**. Close and reopen **Camera Calibration** after update.

## 2026-06 — Camera fine alignment offset (v0.9.9015)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/cameracal.py`, `meerk40t/meerk40t/gui/scenewidgets/bedwidget.py`

**Feature:** **Fine alignment (mm)** in **Camera Calibration** — `align_offset_x` / `align_offset_y` per camera shift the bed photo on the main scene without changing GRBL steps/mm. **Overlay ←/→/↑/↓** nudges 1 mm; spinners for exact values; **Apply offset** / **Reset offset**.

## 2026-06 — Camera flip crash fix (v0.9.9014)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`

**Problem:** **Flip 180°** / flip toggles crashed with `TypeError: 'NoneType' object is not subscriptable` — `reset_perspective()` cleared corners before the UI redrew.

**Fix:** `ensure_perspective()` re-initializes default TL/TR/BR/BL corners from the live (oriented) frame size immediately after flip or reset.

## 2026-06 — Camera flip horizontal / vertical / 180° (v0.9.9013)

**Files:** `meerk40t/meerk40t/camera/camera.py`, `meerk40t/meerk40t/camera/gui/camerapanel.py`, `meerk40t/meerk40t/camera/gui/cameracal.py`

**Change:** IP camera feed can be **flipped** so on-screen TL/TR/BR/BL match the physical bed (e.g. upside-down mount where TL appeared at BR). Settings: `flip_x`, `flip_y` on each camera. **Camera right-click** → Flip horizontal / Flip vertical / **Flip 180°**. **Camera Calibration** window → **Flip camera 180°** (resets perspective corners). Toggling flip resets perspective so corners are re-dragged on the corrected image.

## 2026-06 — Camera perspective corner markers easier to see (v0.9.9012)

**Files:** `meerk40t/meerk40t/camera/gui/camerapanel.py`, `meerk40t/meerk40t/camera/gui/cameracal.py`

**Change:** Perspective calibration handles are now **large filled circles** (56 px hit area) with **white outline**, **TL/TR/BR/BL labels**, and a **yellow dashed** bed outline. Markers stay visible even when camera **Aspect** is on (only hidden when **Correct Perspective** is on).

## 2026-06 — Camera Calibration startup recursion fix (v0.9.9011)

**Files:** `meerk40t/meerk40t/camera/gui/cameracal.py`, `meerk40t/meerk40t/camera/gui/gui.py`, `meerk40t/meerk40t/main.py`

**Problem:** Startup **RecursionError** — `sub_register` called `kernel.register("window/CameraCalib", …)` which called `sub_register` again in a loop.

**Fix:** Register the window once in `gui.py` (like `BatchRun` in `wxmeerk40t.py`); `sub_register` only registers the ribbon button.

## 2026-06 — Camera Calibration startup crash fix (v0.9.9010)

**Files:** `meerk40t/meerk40t/camera/gui/cameracal.py`, `meerk40t/meerk40t/main.py`

**Problem:** MeerK40t crashed on startup with `ImportError: cannot import name 'wxSpinCtrl' from meerk40t.gui.wxutils`.

**Fix:** Use `wx.SpinCtrl` directly (same as CSV Batch Run and other panels).

## 2026-06 — Camera Calibration helper (v0.9.9009)

**Files:** `meerk40t/meerk40t/camera/gui/cameracal.py` (new), `meerk40t/meerk40t/camera/gui/gui.py`, `meerk40t/meerk40t/gui/wxmmain.py`, `meerk40t/meerk40t/main.py`

**Feature:** Guided **camera bed calibration** — perspective corners, background overlay, corner test marks.

**Open:** **Settings → Camera Calibration**, ribbon **Preparation → Camera Calib**, or `window open CameraCalib`.

**Workflow:** Home machine → open camera → drag four corner markers (perspective OFF) → Correct Perspective ON → link DLC32 device (camera right-click) → **Update background** → **Add corner test marks** → low-power cut test.

## 2026-06 — Abort button crash after async estop (v0.9.9008)

**Files:** `meerk40t/meerk40t/gui/wxutils.py`, `meerk40t/meerk40t/gui/spoolerpanel.py`, `meerk40t/meerk40t/gui/laserpanel.py`, `meerk40t/meerk40t/main.py`

**Problem:** After **Abort**, crash: `RuntimeError: wrapped C/C++ object of type HoverButton has been deleted` when re-enabling the Stop button via `wx.CallAfter`.

**Fix:** `safe_enable_control()` ignores deleted widgets; `HoverButton.Enable()` catches `RuntimeError`.

## 2026-06 — Spooler Abort freeze fix v2 (v0.9.9007)

**Files:** `meerk40t/meerk40t/grbl/driver.py`, `meerk40t/meerk40t/core/spoolers.py`, `meerk40t/meerk40t/gui/spoolerpanel.py`, `meerk40t/meerk40t/gui/laserpanel.py`, `meerk40t/meerk40t/main.py`

**Problem:** Job Spooler still froze on **Abort** — especially during **raster** jobs.

**Root cause (v2):** `plot_start()` raster / PlotCut loops only checked `hold_work()` (pause/buffer), **not** abort. A stopped job could keep queuing millions of G-code points on the spooler thread while the UI ran `estop` synchronously.

**Fix:**

- Abort check on **every raster / PlotCut point**; skip `wait_finish()` when aborted.
- `clear_queue()` sets **`_user_aborted` immediately**, stops jobs under lock, logs **after** releasing lock.
- **Abort** on Job Spooler + Laser tab runs **`estop` on a worker thread** (UI stays responsive).
- Job Spooler list no longer calls **`calc_steps()`** on **Running** jobs (was blocking the UI).

## 2026-06 — Spooler Abort freeze fix (v0.9.9006)

**Files:** `meerk40t/meerk40t/grbl/controller.py`, `meerk40t/meerk40t/grbl/driver.py`, `meerk40t/meerk40t/core/spoolers.py`, `meerk40t/meerk40t/gui/batchrun.py`, `meerk40t/meerk40t/main.py`

**Problem:** **Abort** / **Stop** often left MeerK40t “Not responding” — especially on GRBL/Wi‑Fi and during **CSV Batch Run**.

**Causes:**

1. Soft reset (`0x18`) cleared the send queue but **not** the forward buffer waiting for `ok` — spooler thread could spin in `wait_finish()` / `plot_start()`.
2. **clear_queue** fired **`spooler;completed` once per queued job**, flooding UI updates.
3. **CSV Batch Run** treated abort as “job finished” and could **spool the next CSV row** immediately.

**Fix:**

- On estop reset: send **`0x18` first**, clear forward buffer, stop jobs, exit plot loops when aborted.
- New signal **`spooler;aborted`**; one **`spooler;completed`** after clear (not N times).
- Batch window listens for **`spooler;aborted`** and stops the chain.

## 2026-06 — CSV Batch Run open crash fix (v0.9.9005)

**Files:** `meerk40t/meerk40t/gui/batchrun.py`, `meerk40t/meerk40t/main.py`

**Problem:** Opening **CSV Batch Run** crashed with `RuntimeError: wrapped C/C++ object of type BoxSizer has been deleted` in `restore_aspect()`.

**Fix:** Build UI on `self.sizer` from `MWindow` (same as Wordlist Editor) instead of calling `SetSizer()` with a new box sizer.

## 2026-06 — CSV Batch Run (v0.9.9004)

**Files:** `meerk40t/meerk40t/gui/batchrun.py` (new), `meerk40t/meerk40t/gui/wxmeerk40t.py`, `meerk40t/meerk40t/gui/wxmmain.py`, `meerk40t/meerk40t/main.py`

**Feature:** LightBurn-style **batch personalization** from CSV wordlist data — no camera required.

**Open:** **Settings → CSV Batch Run**, ribbon **Preparation → CSV Batch**, or console `window open BatchRun`.

**Workflow:**

1. Design text with `{column}` placeholders (CSV header names, lowercased).
2. **Import** a CSV (Auto / Data / Headers first row).
3. **Prev / Next** or spin control to preview each row; scene text updates via wordlist.
4. **Run current row** — spools one job for the active row.
5. **Run all rows** — runs row 1, then auto-advances after each **`spooler;completed`** until done or **Stop batch**.

**Notes:** Arm the laser before batch run if your device profile requires it. Uses existing wordlist CSV engine (`wordlist load` compatible). For camera overlay see **Camera Calibration** (v0.9.9009).

## 2026-06 — Plan Export: no UI freeze on large jobs (v0.9.9003)

**Files:** `meerk40t/meerk40t/gui/laserpanel.py`, `meerk40t/meerk40t/grbl/device.py`, `meerk40t/meerk40t/grbl/esp3d_upload.py`, `meerk40t/meerk40t/main.py`

**Problem:** **Plan → Export** ran on the UI thread. Huge rasters froze MeerK40t (“Not responding”). SD patch then loaded the **entire file into RAM** (second long freeze).

**Fix:**

- Export runs **`threaded plan… save_job`** — UI stays usable; **Thread Info** window can show the task
- Console: `Exporting to …`, `Patching for MKS SD card…`, then success/fail, then `Finished command … after N sec`
- **`prepare_sd_gcode_file`** streams line-by-line (no 300 MB load into memory)

## 2026-06 — Plan → Export SD-ready for MKS DLC32 (v0.9.9002)

**Files:** `meerk40t/meerk40t/grbl/device.py`, `meerk40t/meerk40t/grbl/esp3d_upload.py`, `meerk40t/meerk40t/main.py`

**Problem:** **Laser → Plan → Export** wrote **CR-only** G-code with trailing **`G28`**. MKS SD firmware reads lines on **`\\n` only**, so uploaded files often **Execute with no motion** (same as old `tree.gcode` / `sq2.gc` failures).

**Fix:**

- After every successful **Export**, when **Prepare Plan exports for SD card** is on (default): **LF** line endings, **M3** (if **Use M3** is on), **`G28` removed**
- Default **Line Ending** for new GRBL configs changed from **CR** → **LF**
- Console confirms: `Export succeeded (SD-ready): …` and homing reminder (**$HY** / **$HX** before Execute)

**Setting:** **Configuration → Device → ESP3D Upload → Prepare Plan exports for SD card** (disable only if you need raw CR exports for another host).

**Note:** Huge raster jobs (e.g. photo engraves **100+ MB**) may still fail **web upload** — use **ESP3D Upload** (right-click = upload only) or stream over **:8080**.

## 2026-06 — ESP3D upload: choose SD filename (v0.9.9001)

**Files:** `meerk40t/meerk40t/grbl/gui/esp3dupload.py`, `meerk40t/meerk40t/grbl/gui/gui.py`, `meerk40t/meerk40t/grbl/esp3d_upload.py`, `meerk40t/meerk40t/grbl/plugin.py`, `meerk40t/meerk40t/main.py`

**Problem:** **ESP3D Upload+Run** auto-named SD files (`file3a7f.gc`, etc.), so **ESP3D Files** was hard to use for reruns.

**Fix:** Toolbar button now opens a **filename dialog** before upload:

- Default from **project name** (window title label, trimmed to **8.3** — e.g. `example edit` → `example.gc`) or **last upload** this session
- You can edit the name; **same name overwrites** on the SD card (repeat jobs easily)
- **Left click:** upload + run; **right click:** upload only (unchanged)
- Console **`esp3d_upload_run`** without **`-f`** still auto-generates a name

**8.3 rule:** max **8** characters before **`.gc`** (MKS SD convention).

## 2026-06 — Scene right-click: Move laser head here

**Files:** `meerk40t/meerk40t/gui/wxmscene.py`, `meerk40t/meerk40t/gui/scenewidgets/elementswidget.py`

**Behavior:** Right-click on the main scene grid (empty area, no tool active) → **Move laser head here** sends `move_absolute` to the click position (same coordinate path as **Tools → Relocate**). Position is clamped to the device bed in scene space.

**Use:** Connect GRBL first; spooler must be idle (not mid-job). Homed machine recommended before relying on coordinates.

## 2026-06 — CO2 jobs: Use M3 (laser fires on touch panel but not in jobs)

**Files:** `MeerK40t.cfg`, `meerk40t/meerk40t/grbl/plugin.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`

**Symptom:** Head moves during a MeerK40t job but the tube does not fire; touch-panel laser test still works.

**Cause:** Touch panel sends **`M3`** (constant PWM). MeerK40t had **`use_m3 = False`** → jobs used **`M4`**, which with **`$32=1`** scales power by speed — often too weak to strike on CO2, especially at low **S** or high **F**.

**Fix:** **`use_m3 = True`** for **GRBL-DLC32-400** (config + DLC32 device profile default). Workflow doc §5 troubleshooting table added.

## 2026-06 — GRBL false “connected” / jog & settings dead (sync mode)

**Files:** `meerk40t/meerk40t/grbl/controller.py`

**Symptom:** GRBL Controller shows green **Connected** (USB or Wi‑Fi) but the log stays empty, **Status** / **Read settings** / jog do nothing.

**Cause:** In **sync** mode, realtime commands (`?`, `!`, `~`, soft reset) were queued in the **forward buffer** and waited forever for `ok` — GRBL answers those with status reports, not `ok`. Boot validation sends `?` at the end; one stuck `?` blocked all later G-code. With **`require_validator = True`** and **`reset_on_connect = False`**, USB attach often never sends a welcome string, so validation never started.

**Fix:** `_expects_ok()` / `_send_realtime()` — status and pause/resume bytes bypass the forward buffer. `_connect_validation_fallback()` starts the `$` boot sequence if no welcome arrives within ~0.5 s.

**Use:** Restart MeerK40t → **Device-Control → GRBL Controller → Connect** → **Status** should show `<--` / `-->` traffic; jog and **Read settings** should work. Console **`grbl_validate`** still forces ready if needed.

## 2026-06 — ESP3D SD jobs: Execute “started” but machine idle

**Files:** `meerk40t/meerk40t/grbl/esp3d_upload.py`, `meerk40t/meerk40t/grbl/gui/esp3dfilemgr.py`, `meerk40t/meerk40t/grbl/plugin.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`

**Symptom:** ESP3D Files **Execute** reports success; head/laser do nothing even after homing.

**Cause:** MKS firmware `readFileLine()` splits on `\n` only. Old MeerK40t exports used **CR** line endings → SD file unreadable (silent no-op). Old files also had **M4** instead of **M3** for CO2.

**Fix:** `prepare_sd_gcode_file()` on upload (LF + M3). `execute_file()` uses `PAGEID=0`, parses Alarm/Busy, polls GRBL `?` after ESP220. ESP3D Files pane uses dropdown + clear failure messages. Re-upload via **`esp3d_upload_run -e`**.


**Files:** `docs/meerk40t/19-dlc32-eeprom-settings.md`, `meerk40t/meerk40t/grbl/plugin.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`, `docs/meerk40t/16-mks-dlc32-board.md`

**Saved (Andre, homing verified):** **`$3=0`** (jog + touch screen), **`$23=1`** (homing — Y correct like `$23=0`, X homing inverted), **`$5=0`**, **`$27=5`**, **`$HY`** then **`$HX`**. Full snapshot: **`19-dlc32-eeprom-settings.md`**.

**Bed:** **`$130=405`**, **`$131=285`** — full `$$` snapshot in **`19-dlc32-eeprom-settings.md`** and Cursor rule **`.cursor/rules/dlc32-eeprom-settings.mdc`** (always apply).

## 2026-05 — Scene startup crash (0×0 window / null background bitmap)

**Files:** `meerk40t/meerk40t/gui/scene/scene.py`

**Problem:** MeerK40t could crash on start with `MemoryDC.SelectObject(): argument 1 has unexpected type 'NoneType'` in `_update_buffer_ui_thread` when `ClientSize` was **0×0** before the window laid out.

**Fix:** `LayerCache.ensure_size` allocates at least **1×1** bitmaps when size is zero and does not skip allocation when `_size` is already `(0,0)` but bitmaps were never created. `_update_buffer_ui_thread` returns early for zero client size and before using a missing background bitmap.

## 2026-05 — Queue warning when shapes are unassigned

**Files:** `meerk40t/meerk40t/gui/laserpanel.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md` (§9)

**Problem:** Jobs could run with only the **outer border** cutting because inner geometry was never assigned to a Cut op (common with **fill-only** SVG art).

**Fix:** **`queue_cutplan_to_spooler()`** warns if **`have_unassigned_elements()`** before spooling (cancel or queue anyway). Workflow doc §9 lists classification fixes (stroke vs fill, Re-Classify, Outline vs full job).

## 2026-05 — Parameter-Test → spooler queue + Hold fix

**Files:** `meerk40t/meerk40t/gui/materialtest.py`, `meerk40t/meerk40t/gui/laserpanel.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`

**Problem:** **Parameter-Test** only runs **Create Pattern** (scene ops); **Arm → Start** often left the **Job Spooler** empty — especially with **Hold** on (re-spool old plan without blob), **threaded** planning still running, or no burnable ops after a failed create.

**Fix:** Shared **`queue_cutplan_to_spooler()`** in `laserpanel.py` (checks device connected, burnable ops; **Hold** only re-spools when the held plan already has a **blob** stage). **Parameter-Test** adds **Queue to Spooler** (always rebuilds from scene). Clearer workflow doc steps.

## 2026-06 — Laser-Control job progress bar fix

**Files:** `meerk40t/meerk40t/gui/laserpanel.py`

**Problem:** **Job progress** stayed at **“No job running”** (or froze at 0%) during burns. The panel listened for `spooler;update`, but that signal is only relayed inside the status-bar widget — it is **never** emitted on the kernel signal bus. During a job, only `spooler;queue` (at enqueue) and `spooler;completed` fired, so the gauge rarely refreshed. Progress also used top-level `item_index` / `len(items)`; typical jobs have one `CutCode` item, so the bar stayed at **0%** even when updates did run.

**Fix:** Listen to **`driver;position`** and **`emulator;position`** (same as **Job Spooler**). Compute **%** from **`steps_done` / `steps_total`** when available, with fallback to item index. Throttled ~1 s. Idle: “No job running”.

## 2026-05 — Laser-Control job progress bar

**Files:** `meerk40t/meerk40t/gui/laserpanel.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`

**Behavior:** On the **Laser** tab of **Laser-Control**, a **Job progress** gauge shows **0–100%** while a `LaserJob` is running (spooler steps). A detail line shows step counts, rough time remaining, optional GRBL send-buffer counts (`current/total` from the driver), and queue position when multiple jobs are queued. Updates on `spooler;queue`, `spooler;completed`, and position signals (throttled ~1 s). Idle: “No job running”.

**Note:** Progress reflects **planner/spooler steps**, not “% of drawn geometry on screen.” If Wi‑Fi drops, the bar may freeze and the job stops — use USB for long cuts until the link is stable (see workflow doc §8).

## 2026-06 — Sequential homing ($HY / $HX) for DLC32

**Files:** `meerk40t/meerk40t/grbl/driver.py`, `device.py`, `gui/navigationpanels.py`, `grbl/plugin.py`, `MeerK40t.cfg`

**Problem:** MeerK40t **Home** sent **`$H`** or **`G28`**; homing stopped **~50 mm** before **X− / Y+** switches with **ALARM:1**.

**Fix:** Device setting **Sequential homing** — **`physical_home`** sends **`$HY`** then **`$HX`**. **Home** toolbar button calls **`physical_home`** when **Has endstops** is on. DLC32 profile defaults: endstops on, sequential on; macros **Home Y** / **Home X**.

## 2026-06 — GRBL MPos sync + ALARM:1 hard limit notes

**Files:** `meerk40t/meerk40t/grbl/controller.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`

**MPos sync:** After connect, `declare_position()` now runs on every status **`MPos:`** update so MeerK40t confined jogs match the board (avoids commanding extra travel when the head was moved on the touch panel).

**ALARM:1:** Documented recovery and safe Y travel (home → jog down in steps toward **−300**, stop before ramming the switch). See workflow doc §5.

## 2026-06 — GRBL ALARM:2 on Y jog (Flip Y must be on)

**Files:** `MeerK40t.cfg`, `meerk40t/meerk40t/grbl/controller.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`

**Symptom:** **ALARM:2 Soft limit** when jogging Y in MeerK40t; X OK.

**Cause:** Board **MPos Y** is **0 at top**, **negative into bed**. With **Flip Y off**, MeerK40t’s down jog sends **G91 Y+** → past soft limit. Saved config had **`flip_y = False`**.

**Fix:** **`flip_y = True`**, **`home_corner = top-left`**. One-time console warning if MPos Y &lt; 0 and Flip Y is off.

## 2026-06 — GRBL Y jog in MeerK40t (confined + home corner)

**Files:** `meerk40t/meerk40t/grbl/driver.py`, `MeerK40t.cfg` (`[grbl1]`), `meerk40t/meerk40t/grbl/plugin.py`

**Problem:** X jog worked; **Y jog did nothing** in Navigation (down arrow) while the touch panel moved Y fine. Board uses **MPos Y 0 at top** and **negative Y into the bed** (e.g. **−300**).

**Cause:** `move_rel(confined=True)` compared **native** `native_y` with **UI** jog deltas (`0…300`). That mixed coordinate systems and often zeroed `dy` (e.g. at home, or when `native_y` was already negative). **`home_corner=auto`** also left the bed origin wrong for top-left homing with **`flip_y=True`**.

**Fix:** Confined clamping now uses **`device.current`** (bed/UI coords), same as the Navigation panel. Saved device: **`home_corner=top-left`**, **`bedwidth=405mm`**. DLC32 profile defaults: **405×300**, **`swap_xy=False`**, **`flip_y=True`**, **`home_corner=top-left`**.

**User:** Restart MeerK40t after pulling this change. In **Configuration → Device**, confirm **Home corner = top-left**, **Flip Y = on**, bed **405×300 mm**. Jog **down** should move into the bed; **up** toward home.

## 2026-06 — DLC32 X steps/mm calibrated (`$100=158`)

**Board EEPROM (Andre):** **`$100=158`** so **`G0 X100`** moves **100 mm** real (was **80** — display reached **400** while X only traveled ~half). **`$101=160`** unchanged (Y full travel to **−300**). Homing: **`$HY`** then **`$HX`**, **`$23=1`**, **`$5=0`**, **`$27=3`**, probe/Z/unused limits **GND–S** jumpers. Doc: `16-mks-dlc32-board.md`, `17-meerkat-dlc32-workflow.md`.

## 2026-06 — DLC32 GRBL TCP port 8080 (not 23)

**Files:** `meerk40t/meerk40t/grbl/tcp_connection.py`, `meerk40t/meerk40t/grbl/plugin.py`, `scripts/wake-mks-dlc32.ps1`, `docs/meerk40t/17-meerkat-dlc32-workflow.md` (§8)

**Cause:** MKS DLC32 V2.2.6 reports **Data port: 8080** in `[ESP420]`; port **23** is refused even when `http://192.168.10.90/` works.

**Behavior:** On connect, after HTTP wake, `resolve_grbl_tcp_port()` tries configured port, then **8080**, then **23**. Device profile and saved config use **8080**. Wake script checks TCP **8080** after HTTP.

## 2026 — DLC32 Wi‑Fi wake (script + TCP connect)

**Files:** `meerk40t/meerk40t/grbl/tcp_connection.py`, `scripts/wake-mks-dlc32.ps1`, `run-meerk40t-dev.bat`, `docs/meerk40t/17-meerkat-dlc32-workflow.md` (§8)

**Behavior:** Before GRBL TCP connect, MeerK40t HTTP-wakes the board (same as opening the phone browser), retries TCP up to 4×. Launcher script retries wake 8×. Doc covers DHCP reservation, Post Connection Delay 500 ms.

**Fix (same file):** Removed 8 s read timeout on the live TCP socket — it had caused connect-then-disconnect ~8 s later during `$$` validation over Wi-Fi. Connect still uses 8 s timeout; reads are blocking again.

## 2026 — Backup-before-edit rule + DLC32 400×300 device profile

**Rules:** `.cursor/rules/meerkat-backup-before-edit.mdc` — agent must rotate `.bak.1`–`.bak.3` before any edit under `meerk40t/`, `docs/meerk40t/`, or `.cursor/rules/`.

**Files:** `meerk40t/meerk40t/grbl/plugin.py`, `meerk40t/meerk40t/grbl/device.py`, `docs/meerk40t/17-meerkat-dlc32-workflow.md`

**Behavior:**

- New device type **K40 CO2 — MKS DLC32 (400×300 mm)** (`dev_info/grbl-dlc32-k40-400`): bed 400×300, Swap XY, TCP `192.168.10.90:8080`, reset on connect, five GRBL macros.
- `dev_info` choices can set `macro_0` … `macro_title_4`; persisted when the device is created.
- Workflow doc covers Material Test, Material Manager presets (manual), macros, safety — camera/LBRN deferred.

## 2026 — Bed movement limit on by default + disable warning

**Files:** `meerk40t/meerk40t/gui/navigationpanels.py`, `meerk40t/meerk40t/gui/plugin.py`, `meerk40t/meerk40t/core/spoolers.py`

**Behavior:**

- **Limit laser movement to bed size** (confined) is turned **on** when MeerK40t starts and when the Jog panel opens.
- Clicking the fence button to **turn it off** shows a **warning** (Yes/No, default No) about GRBL max travel, alarms, and driver stress before allowing unconfined jogs.
- Console/spooler `move_relative` uses confined **True** by default if the setting is missing.

## 2026 — GRBL confined jog crash (bed size strings)

**Files:** `meerk40t/meerk40t/grbl/driver.py`

**Problem:** Jogging to the bed edge (e.g. **Y to max** with **Confined** on) could crash MeerK40t with `TypeError: unsupported operand type(s) for -: 'str' and 'float'` because `view.width` / `view.height` are stored as length strings (e.g. `"400mm"`) but `move_rel(confined=True)` compared and subtracted them as raw values.

**Fix:** Convert `dx`, `dy`, and bed limits with `float(Length(...))` before confined clamping.

**Backups:** `driver.py.bak.1` … `.bak.3` beside the file.

## 2026 — Simulation preview cache

**Files:** `meerk40t/meerk40t/gui/simulation.py`

**Behavior:** While the simulation panel rebuilds raster/plot preview caches, the **Send to Laser** button label becomes **Calculating**. A **Stop calculating** button appears below it so you can abort that phase without closing the app.

**Mechanism:** Cooperative cancel (`wx.YieldIfNeeded()` between cuts, cancel flag). UI cleanup runs in a `finally` block so the spool button is restored.

**Limit:** Cancellation applies **between** cuts. A single very large raster can still block inside one `list(plot…)` until that call finishes.

**Backups:** Rotating snapshots `simulation.py.bak.1` … `.bak.3` beside the file (see workspace Cursor rule §4).

## 2026 — Tips at startup preference

**Files:** `meerk40t/meerk40t/gui/tips.py`

**Behavior:** Toggling **Show tips at startup** now calls `context.write_persistent("show_tips", state)` so the choice is saved immediately instead of only on shutdown.

## 2026 — Ribbon toolbar: delayed description tooltip

**Files:** `meerk40t/meerk40t/gui/ribbon.py`, `meerk40t/meerk40t/gui/plugin.py`

**Behavior:** The ribbon bar uses its own hover timer (default **2000 ms**). After you pause on a toolbar button that long, the tooltip shows the **short tip** and, when defined, the **extended help** text in one popup (two paragraphs separated by a blank line).

**Preference:** **Gui → Tooltips → Ribbon: hover before description** (`ribbon_tooltip_delay_ms`). **Gui → Tooltips → Long ribbon hover descriptions** (`ribbon_verbose_hover_help`) and **Panes → Help → Long hover descriptions on ribbon toolbars** (same setting). The global **ToolTip delay** still applies to other controls only (via `wx.ToolTip.SetDelay`).

**Scope:** Only the **custom ribbon strips** at the top (`wxmribbon.py`: primary, tools, edit/modify). Other panes (scene, tree, etc.) use normal wx tooltips, not this delayed ribbon job.

**Tree / scene context menus:** The same **`ribbon_verbose_hover_help`** flag controls **`create_menu_for_node`** in `wxutils.py`: when it is on, each menu item’s status-bar help uses formatted `help=` text from `element_treeops.py`, and if that is empty, the first paragraph of the operation’s docstring (when present). **Look at the status bar** while moving through a right-click menu (not a floating tooltip). When the flag is off, only explicit `help=` strings are used (no docstring fallback).

## 2026-06 — Laser-Control override: 5% steps, typed Set, power direction fix

**Files:** `meerk40t/meerk40t/gui/laserpanel.py`, `meerk40t/meerk40t/grbl/driver.py`

**Problem:** Override sliders moved in **10%** steps only. No way to type a value. **Power slider felt reversed** on GRBL/DLC32: moving right (+70%) reduced burn because `0x9A`/`0x9B` spindle commands were swapped vs GRBL 1.1 (increase/decrease).

**Fix:** Sliders use **5%** steps (center = 0%, range about −100% to +100%). Small **text + Set** beside Power and Speed for typed percent (e.g. `70`, `-30`). GRBL driver resets to 100% then steps in **5%** with correct **0x9A** increase / **0x9B** decrease.

**Use:** Enable **Override**, adjust while engraving; **right = more power**, **left = less**.

## 2026-06 — Material Manager delete-by-category crash fix

**Files:** `meerk40t/meerk40t/gui/materialmanager.py`

**Problem:** Right-click **Delete category** (e.g. under **&lt;All Lasertypes&gt; → New material**) crashed with `AttributeError: 'int' object has no attribute 'replace'` because `laser` is stored as an integer index, not a string.

**Fix:** `_entry_category_label()` maps laser indices to the same labels as the library tree; delete matching uses that helper. Also fixed secondary-key comparison in the delete loop (`sec_key == secondary`).

## 2026-06 — Tree panel material preset dropdown

**Files:** `meerk40t/meerk40t/gui/wxmtree.py`

**Behavior:** On the **Tree → Details** tab, a **Material:** dropdown lists all **Material Manager** library entries (e.g. `Acrylic — 3mm — …`). Choosing one runs `material load` — the **Operations** branch is replaced with that preset’s cut/engrave/raster speeds and powers (same as right-click **Operations → Load → …**). Optionally updates the status-bar operation buttons when **Update Statusbar on load** is checked (right-click **Operations** menu).

**Use:** Create presets in **Edit → Material Manager**, restart MeerK40t if the list was open during edits, then pick from the dropdown.

## 2026-06 — Keyboard Delete matches ribbon Delete

**Files:** `meerk40t/meerk40t/gui/scene/scenepanel.py`, `meerk40t/meerk40t/gui/wxmtree.py`, `meerk40t/meerk40t/gui/wxutils.py`, `meerk40t/meerk40t/core/bindalias.py`

**Problem:** Ribbon **Delete** worked (`tree selected delete`) but **Delete** / numpad **Del** on the canvas often did nothing (key-up vs key-down on Windows; numpad not in the default keymap).

**Fix:** Default keymap adds **`numpad_delete` → `tree selected delete`**. Scene panel runs the same command on **key-up** when the keymap did not already fire on key-down (mirrors the tree widget). Tree **key-up** handles numpad Delete too.

**Use:** Select shape(s) on the scene, press **Delete** or numpad **Del** — same as the ribbon button. While a draw/edit tool is active (`tool_active`), tools keep priority. Console **Window → Keymap** can still remap `delete` / `numpad_delete`.

## 2026-06 — Tree double-click on operations opens Parameter-Test

**Files:** `meerk40t/meerk40t/gui/wxmmain.py`, `meerk40t/meerk40t/gui/materialtest.py`

**Problem:** Double-clicking a **Cut / Engrave / Raster / Image / Dots** operation in the **Tree** opened the standalone **Properties** window (or element PathNode for mis-clicks) instead of **Parameter-Test** with the operation’s speed/power tabs.

**Fix:** `open_property_window_for_node()` routes laser operation types to **`window/Templatetool`** (title **Parameter-Test**), syncs the **Generator** operation combo via `select_operation_for_node()`, and embeds the real operation node in the notebook **Properties** tab (`focus_properties=True`). **Elements** (paths, text, images) still open **Properties** as before.

**Use:** Restart MeerK40t after pulling. Double-click **Cut** or **Engrave** under **Operations** in the tree — expect **Parameter-Test**, **Properties** tab selected. Double-click geometry under **Elements** — still the normal **Properties** editor.

## Workspace rules (Cursor)

**File:** `.cursor/rules/meerk40t-knowledge-base.mdc`

- **§4:** Rotate three `.bak.N` backups before substantive edits under `meerk40t/`.
- **§5:** When code behavior changes, update `docs/meerk40t/README.md` and the relevant topic note (such as this file) in the same batch; update the workspace root `README.md` if one exists and should mention the change.

---

# Welcome to MeerK40t!
MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed open-source laser cutting software.

The primary goals of this software is simple:


* Provide users with high quality laser control software.
* Provide developers with a highly extensible platform to help further their own ideas, and provide novel work to the laser community at large.

## Getting started
To get up and running, simply download Meerk40t from [here](https://github.com/meerk40t/meerk40t/releases) for your specific platform. (Windows, Mac OSX, Linux, and by extension, Raspberry Pi).

## 🛠 Project Status: Maintenance Mode
**MeerK40t is currently in a low-maintenance phase.** The original maintainers have limited bandwidth for active development. What this means for users and contributors:
* **Response Times:** Issues and Pull Requests may not receive immediate feedback. Silence is not a lack of interest, but a lack of time.
* **Weekly Builds:** These are automated experimental snapshots. They **will** contain bugs and regressions. If you require a stable experience, please stick to the [latest stable Release](https://github.com/meerk40t/meerk40t/releases).
* **Contributions Welcome:** This project survives on community involvement. If you find a bug in a weekly build, the fastest way to get it fixed is to submit a Pull Request. 
* **Support:** Please use the [Discussions] tab or community forums for general help, as the Issue tracker is reserved for actionable bug reports and development tasks.

<details>
<summary>Release Versions (Just use the latest)</summary>


> * 0.9 - Active - New features and some underlying architectural changes. Try the latest released version: [0.9.9000](https://github.com/meerk40t/meerk40t/releases/tag/0.9.9000) (Jan 17, 2026) or try a prerelease even: [release list](https://github.com/meerk40t/meerk40t/releases)
> * 0.8 - Maintenance - may receive critical bugfixes but no more new features, latest version: [0.8.12](https://github.com/meerk40t/meerk40t/releases/tag/0.8.12000) (Oct 17, 2023)
> * 0.7 - Discontinued - K40 support only (including ruidacontrol emulator for 3rd party lasersoftware integration), latest version [0.7.10](https://github.com/meerk40t/meerk40t/releases/tag/0.7.10000) (June 13, 2023)
> * 0.6 - Discontinued - K40 support only, latest version: [0.6.24](https://github.com/meerk40t/meerk40t/releases/tag/0.6.24) (Oct 11, 2021)


</details>

### Command Line Interface

Meerk40t has an advanced internal console system allowing access to most parts of the code with various commands. It also provides a command line interface which should allow you to automate any processes. To learn more, download a version of Meerk40t for your platform, and execute it in a terminal with the ``--help`` argument to get a list of options.

## Compiling from source

Alternatively you can run MeerK40t directly from Python. `pip install meerk40t[all]` with python installed will usually be sufficient. Then merely run `meerk40t` at the command line.

See [Install: Source wiki page](https://github.com/meerk40t/meerk40t/wiki/Install:-Source)

The wxMeerK40t is the GUI and is written in wxPython. We use AUI to allow to have a very highly configurable UI. We can easily add panes and tools and there are quite a few available already.

## Screenshots
![grafik](https://github.com/user-attachments/assets/e56135a2-7b1f-44be-9761-b92931e300f6)

## Drivers

Meerk40t provides a variety of drivers with an extensible framework to provide support for other new laser devices. The code was written with the myriad of possibilities for different software in mind. For example, it may be essential that GRBL be able to reset an alarm or notify the user of particular error codes. The configuration for GRBL is not the same for the configuration of other laser control drivers. With this in mind, MeerK40t can radically change how and when it works


### Supported devices
*   Lihuiyu M2/M3-Nano (aka K40 lasers)
*   Any GRBL device (Atomstack, Creality, Longer, Ortur etc...)
*   Ezcad2-compatible JCZ controllers galvo lasers
*   Moshiboard
*   NewlyDraw System 8.1 Lasers
*   Devices with Ruida-controller
*   Ruida-Emulation (Middleman between Lightburn and K40)
