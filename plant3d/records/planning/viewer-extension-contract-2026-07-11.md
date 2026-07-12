# Plant3D Viewer Extension Contract

Date: 2026-07-11

This note records the stable-enough browser runtime surface used by consumer
overlays such as `raceway`. The goal is a small contract, not a plugin
framework.

## Runtime Helpers

Extensions should prefer these helpers over raw viewer internals:

- `registerInteraction(config)`: register a named canvas interaction.
- `deactivateActiveInteraction(options)`: deactivate the current interaction.
- `pointOnSourceElevationFromViewerEvent(event, sourceElevationM)`: cursor to
  source-frame point on a horizontal working plane.
- `modelAnchorFromViewerEvent(event)`: cursor to a Plant3D model anchor at the
  actual clicked source-frame model point, when a visible model object is hit.
- `getSelectedModelAnchor()`: current selected model object as an anchor
  snapshot.
- `raycastObjectsFromViewerEvent(event, objects, recursive)`: raycast
  extension-owned handles or overlays using the host camera/raycaster.
- `sourcePointToRenderPoint(point)` / `renderPointToSourcePoint(point)`:
  source/render coordinate conversion for the active package.
- `frameSourcePoints(points, options)`: frame one or more source-frame points in
  the host camera. Current options: `paddingM` and `minRadiusM`.
- `worldUnitsForScreenPixels(point, pixels, minValue, maxValue)`: stable handle
  sizing across camera distance.
- `currentSourceElevationM()`: current viewer target elevation in source-frame
  metres.
- `getPackage()` / `getPackageBounds()`: active render package context.
- `renderNow()`: request an immediate host render.

## Interaction Config

`registerInteraction` currently recognizes:

- `id`: stable extension interaction id.
- `cursor`: cursor while active.
- `onCanvasClick(event)`: commit click. The host suppresses calls after
  navigation drags.
- `onNavigationClick(event)`: optional callback when a navigation gesture was
  intentionally ignored as a commit.
- `onCancel()`: Escape/cancel callback.
- `onDeactivate(options)`: called when another viewer tool replaces the
  interaction.

Only one canvas tool should be active at a time. Activating Measure, EHT, or an
extension interaction deactivates the others.

## Layer Snap Providers

Viewer layers registered through `plant3dViewerLayers.register()` may optionally
provide:

- `getMeasurementSnapObjects()`: returns visible `Object3D` instances that the
  Plant3D Measure tool may use when `Snap Vertex On` is active.

Use this for consumer-owned overlay geometry such as Raceway tray rails, lower
edges, depth ticks, rungs, and cross-members. The Measure tool should depend on
this generic layer contract, not on a specific consumer app.

Line-like provider objects are selected by closest screen-space segment within a
tight pixel radius before selected-model vertex snapping is attempted. This keeps
thin overlay edge picking tied to the visual cursor target instead of ordinary
raycaster depth order.

## Provisional Internals

`scene`, `camera`, `controls`, `renderer`, `canvas`, and `raycaster` are still
exposed for migration convenience. Treat them as provisional. New consumer
tools should ask for a helper instead of depending on these directly.

## Reserved Future Additions

- `modelSurfaceHitFromViewerEvent(event)`: model hit with source point, source
  normal, object summary, and anchor. Needed by lighting fittings and support
  placement.
- pointer-move routing on interactions, for ghost previews and true drag
  handles. Build this with the first real consumer.
