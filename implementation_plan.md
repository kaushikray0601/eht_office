# IDFViewer Upgrades and EHT Integration

This plan details the upgrade path for the `idfviewer` application. It includes proper robust database design for PostgreSQL, deeper Hexagon IDF metadata extraction, a unified 3D coordinate mapping for multiple files, and styling to match the rest of the application. 

## Proposed Changes

### 1. Database Model (PostgreSQL)
We will introduce models in `idfviewer/models.py` to securely store IDF files and their parsed components as a permanent representation of the physical pipeline routing, linking them to your main `eht` projects.

- **`IDFUpload`**: A model to track a batch upload session or folder, tied to a Django project instance (can import `ProjectData` from `eht.models`).
- **`IDFFile`**: Tracks individual files processed (e.g. `A10U-POW6029-01-Rev00C.idf`), file state, and bounding box.
- **`IDFComponent`**: Represents every node (Pipe, Weld, Support, Valve, Marker) extracted from the file.
  - Core fields: `component_type` (Enum: pipe, weld, fitting...), `line_id` (Pipeline ref), `uid` (for 3js mapping).
  - Geometry fields: `start_x, start_y, start_z`, `end_x, end_y, end_z` (using PostgreSQL `FloatField`).
  - `properties`: A PostgreSQL `JSONField` (built-in to Django) storing all the complex metadata like materials, insulation types, tags, and unmapped properties. 

*Rationale*: PostgreSQL JSONField excels here as IDF files have diverse metadata structures that don't need fixed columns, yet can be queried if necessary.

---

### 2. Deep Metadata Extraction
We analyzed the `.idf` formats in the workspace. Currently, `parser.py` drops a lot of data. We'll update the parser to capture and categorize these Hexagon-specific records, putting unknown ones in a dedicated section:
- `-20` & `-21`: Material Code and Description (Already partial support)
- `-22`: Instrument Tag (e.g., `PDT 2018`, `FO 8012`)
- `-26`: Insulation Spec / Code (e.g., `T1A2N`)
- `-30`: Pipeline ID (e.g., `A10U-POW6029`)
- `-31`: Spool/Weld Ref (e.g., `T-1019/I02`)
- `-37`: Descriptive Notes (e.g., `PIPE SLEEVE E`, `PASSING THROUGH`)
- `-39`: Component Tag (e.g., `17401/7583`)
- `-40` & `-46`: Location/Directional (e.g., `S 35 W`, `N`)
- `-70`: Support Type (e.g., `SG2-20`)
- **Unknown items**: E.g., `-250` (DATE?), `-245` (DOWN), `-300` (SHOP MATERIAL). All unmapped negative IDs will be grouped under `Unmapped Metadata` in the properties side panel so piping engineers can provide clarity.

---

### 3. Multiple File/Directory Support & 3JS Scene Unification
**Frontend**: 
- We will update the HTML input to accept multiple files `multiple` and directory selection `webkitdirectory`, allowing batch uploads.
- The `Upload & View` button click will be removed: JS will submit the form automatically `onchange`.

**Backend / 3D Visualization**:
- `views.py` will process a list of files rather than a single file.
- **CRITICAL**: In the current code, `_normalize_points()` shifts coordinates to `(0,0,0)` based on a single file's bounding box. If we do this for multiple files individually, their spatial relationships are destroyed! 
- *Fix*: The parser will act on a *combined scene*, calculating a single global bounding box and shifting all pipelines relative to the center of the entire plant. This ensures `A10U` correctly sits relative to `A80U` in 3D space.

---

### 4. Added Structural Details for Reference Context
While IDF files themselves do not natively contain civil structural steel beams (they are isometric piping files), they *do* contain markers referencing building grids and column locations (often Record 149 mapped to textual notes like "COL A-4"). 
- We will configure Three.js to render a prominent Ground Plane with Grid lines. 
- We can parse text markers representing structural coordinates and render them as semi-transparent reference pillars or vertical flags in the 3JS space to give you directional awareness.

---

### 5. UI and Performant Coding Improvements
- Improve `upload.html` with basic "glassmorphic" Tailwind/Custom CSS similar to the Elecsense UI styling.
- `viewer.html`: The side panel layout will be improved to elegantly handle large volumes of newly extracted metadata via collapsible sections.
- **Performance**: We will shift away from single meshes if the component count exceeds 10,000 to use `InstancedMesh` for pipes and fittings, which drastically boosts 3D rendering performance.

---

## EHT Design Perspective Ideas 

Leveraging this real plant coordinate geometry space gives a massive advantage to your application:

1. **Automated Cold Lead / Power Cable Lengths**: If you mark your DB (Distribution Board) and JB (Junction Box) positions within the 3JS viewer, distance logic can automatically map the routing distance (e.g. Manhattan distance) from the JB to the heating circuit start-points on the pipe, eliminating manual cable length estimation currently done in Excel.
2. **Thermal Heat Map Visualization**: We can link the `HeatTracingInput` model to the `IDFComponent` pipeline ID. When an engineer clicks "View Heat Loss Map", pipes can be automatically color-coded in the viewer (Red = high heat loss, Blue = low), visually flagging critical points.
3. **Clash & Accessibility Check**: Render a bounding volume (clearance zone) around where Junction Boxes or Thermolyptic sensors need to be installed on the pipes to visually verify if they clash with valves or crowded pipe-racks.
4. **BOQ Accuracy**: The IDF counts exactly how many valves, flanges, and supports are on the line. Rather than trusting the Excel input, we can cross-verify your `xlid` counts against the physical `IDF` parsing and alert the user to discrepancies.

## User Review Required

> [!WARNING]
> Storing the 3D geometries for 32+ pipelines as JSON fields and Float fields will expand the database considerably. We will implement bulk creation logic for this data to prevent timeouts on the initial folder upload. Are you comfortable with the unified `IDFFile` / `ProjectData` relation structure?

## Open Questions
1. Should the uploaded files immediately execute their Heat Tracing Design steps as part of the view generation, or should this purely populate the database + 3D viewer for now, keeping calculation as a separate step?
2. Which Django project ID (`proj_id` in `ProjectData`) should be assigned by default when uploading IDF files? Should we present a dropdown of active projects in the upload screen?
