# IDF Viewer Architecture Upgrade Walkthrough

The `idfviewer` app has been successfully upgraded from an in-memory prototype to a fully persistent, robust, and beautiful multi-file pipeline integration tool.

## Key Accomplishments

### 1. Database Integration
- Implemented `IDFFile` and `IDFComponent` models that link directly to `eht.ProjectData`.
- Hexagon IDF components are now parsed, structured, and saved into a PostgreSQL database upon upload, taking advantage of `JSONField`s to future-proof meta properties.
- **Performance consideration:** Leveraged `.bulk_create()` in chunks of 5000 to ensure fast writes, even when processing complete plant structures with hundreds of thousands of vertices.

### 2. Multi-File Processing & Uniform Geometry
- The form interface now seamlessly supports uploading single files, multiple files selectively, or entire directory structures using WebKit directory selectors.
- The `parser.py` was rewritten to collect components from **all** selected files into a single unified scene *before* calculating the global origin and scale factors. This eliminates the bounding-box misalignment issue. The unified structure is flawlessly normalized onto a single mathematical stage.

### 3. Detailed Metadata Handling
- Augmented the parser to map standard negative-ID metadata streams derived from PDMS/Isodraft:
  - Material Specifications (`-20`, `-21`)
  - Instrument Identifiers, Insulation Specifications, Component References (`-22`, `-26`, `-39`)
  - Pipeline & Spool designations (`-30`, `-31`)
  - Orientation vectors and Support codes (`-40`, `-46`, `-70`)
- **Unmapped data safety net:** Any remaining negative string descriptors are securely captured in an `unmapped_meta` dictionary instead of being discarded.

### 4. UI/UX Glassmorphic Redesign & Deep 3D Controls
- Fully integrated the visual aesthetics requested: the forms and viewer now use a premium **Glassmorphism** engine implemented via Tailwind CSS (`backdrop-blur`).
- Standardized color branding referencing `eht` requirements (soft green and blue tinted glass interfaces).
- JavaScript dynamically handles user interaction:
  - Form dynamically auto-submits on file drop (if a project is selected).
  - The Viewer side-panel includes active **Display Settings checkboxes** allowing users to instantaneously tailor the complexity of their selected component's properties.
- Added a visual ground plane (`THREE.MeshStandardMaterial`) to visually anchor the floating pipelines in the virtual 3-dimensional space.
- **Enhanced 3D Exploration Tooling (Fix for Long Outliers):**
  - **Unrestricted Zoom:** The camera's minimum viewing distance and clipping planes have been unlocked, allowing you to infinitely zoom into densely packed clusters (blobs).
  - **Dynamic Object Hiding:** Because extremely long outlier pipes heavily skew the bounding box math, you can now click on any outlier and select **Hide Object**. This temporarily removes it from the scene.
  - **Scene Recalibration:** After hiding outliers, click the **Recalibrate Scene Camera** button to instantaneously command the viewing frustum to scale exclusively to the remaining dense sections of your plant structure.
  - **Focus Navigation:** Double-click on any component, or press **Focus Zoom**, to automatically snap the target rotation and zoom depth precisely onto that element.

### 5. Interactive Pipeline Hierarchy (Selective Rendering)
- Built a deeply integrated left-hand **Asset Hierarchy Sidebar**.
- `viewer.js` automatically groups every component by its `File Image` and `pipeline_ref`.
- Generates a nested togglable DOM tree for engineers to quickly filter out complex backgrounds. Disabling files/lines visually culls them from the renderer and instantaneously triggers `fitCameraToObject()` so your 3D view is completely scaled and boxed *exclusively* to the Spools you wish to evaluate for EHT.

### 6. Plot Plan Floor Map Projection
- Incorporated a **Plot Plan Map Overlay** utility inside the left-sidebar.
- The user can instantly load any 2D architectural flat file (`.png`, `.jpg`) without refreshing.
- The 2D image is seamlessly projected as a high-fidelity Albedo texture against the ThreeJS Ground Plane.
- **Dynamic Calibration:** Included three HTML range sliders (Scale, Offset X, Offset Z) allowing the engineer to stretch and slide the floor plan under the disjointed pipelines until the true 3D absolute coordinates perfectly align with the visual 2D foundations of the building.

## Django Backend Progress
- Bootstrapped `MEDIA_ROOT` configuration into `settings.py` for handling Image Uploads.
- Created and successfully migrated the `PlotPlanOverlay` Model in `idfviewer` to facilitate permanent saving of Plot Plan files tied cleanly back to `eht.ProjectData`.
