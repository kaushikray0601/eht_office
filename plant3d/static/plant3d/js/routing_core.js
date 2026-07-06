function normalizePoint(point) {
  if (Array.isArray(point) && point.length >= 3) {
    const x = Number(point[0]);
    const y = Number(point[1]);
    const z = Number(point[2]);
    return [x, y, z].every(Number.isFinite) ? { x, y, z } : null;
  }
  if (point && typeof point === 'object') {
    const x = Number(point.x);
    const y = Number(point.y);
    const z = Number(point.z);
    return [x, y, z].every(Number.isFinite) ? { x, y, z } : null;
  }
  return null;
}

function samePoint(a, b, tolerance = 0.001) {
  if (!a || !b) return false;
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  const dz = a.z - b.z;
  return (dx * dx) + (dy * dy) + (dz * dz) <= tolerance * tolerance;
}

function pushDistinct(points, point, tolerance = 0.001) {
  if (!point) return;
  if (samePoint(points[points.length - 1], point, tolerance)) return;
  points.push({ x: point.x, y: point.y, z: point.z });
}

export function manhattanSegmentPoints(startPoint, endPoint, options = {}) {
  const start = normalizePoint(startPoint);
  const end = normalizePoint(endPoint);
  if (!start || !end) return [];
  const order = Array.isArray(options.axisOrder) && options.axisOrder.length
    ? options.axisOrder
    : ['x', 'z', 'y'];
  const current = { x: start.x, y: start.y, z: start.z };
  const points = [{ ...current }];
  for (const axis of order) {
    if (!['x', 'y', 'z'].includes(axis)) continue;
    current[axis] = end[axis];
    pushDistinct(points, current, options.tolerance);
  }
  pushDistinct(points, end, options.tolerance);
  return points;
}

export function suggestManhattanRoute(guidePoints, options = {}) {
  const guides = (guidePoints || []).map(normalizePoint).filter(Boolean);
  if (guides.length <= 1) return guides.map(point => ({ ...point }));
  const route = [];
  for (let index = 1; index < guides.length; index += 1) {
    const segment = manhattanSegmentPoints(guides[index - 1], guides[index], options);
    segment.forEach(point => pushDistinct(route, point, options.tolerance));
  }
  return route;
}

export function routeLength(points) {
  const route = (points || []).map(normalizePoint).filter(Boolean);
  let total = 0;
  for (let index = 1; index < route.length; index += 1) {
    const a = route[index - 1];
    const b = route[index];
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    const dz = a.z - b.z;
    total += Math.sqrt((dx * dx) + (dy * dy) + (dz * dz));
  }
  return total;
}

export function routeDiagnostics(points) {
  const route = (points || []).map(normalizePoint).filter(Boolean);
  return {
    point_count: route.length,
    segment_count: Math.max(route.length - 1, 0),
    length_m: routeLength(route),
    bend_count: Math.max(route.length - 2, 0),
  };
}

function routeWarning(code, severity, message) {
  return { code, severity, message };
}

function directionBetween(a, b) {
  const dx = Math.abs(a.x - b.x);
  const dy = Math.abs(a.y - b.y);
  const dz = Math.abs(a.z - b.z);
  const max = Math.max(dx, dy, dz);
  if (max <= 0.001) return '';
  if (max === dx) return 'x';
  if (max === dy) return 'y';
  return 'z';
}

export function validateRoute(points, options = {}) {
  const route = (points || []).map(normalizePoint).filter(Boolean);
  const warnings = [];
  const diagnostics = routeDiagnostics(route);
  const minSegmentLength = Number(options.minSegmentLengthM || 0.1);
  const maxBendCount = Number(options.maxBendCount || 24);
  if (route.length < 2) {
    warnings.push(routeWarning('route_too_short', 'block', 'Route needs at least two points.'));
  }
  if (options.sourceId && options.destinationId && options.sourceId === options.destinationId) {
    warnings.push(routeWarning('same_source_destination', 'block', 'Source and destination must be different components.'));
  }
  let shortSegments = 0;
  let nonOrthogonalSegments = 0;
  for (let index = 1; index < route.length; index += 1) {
    const a = route[index - 1];
    const b = route[index];
    const length = routeLength([a, b]);
    if (length > 0 && length < minSegmentLength) shortSegments += 1;
    const changedAxes = ['x', 'y', 'z'].filter(axis => Math.abs(a[axis] - b[axis]) > 0.001);
    if (changedAxes.length > 1) nonOrthogonalSegments += 1;
  }
  if (shortSegments) {
    warnings.push(routeWarning('short_segments', 'warn', `${shortSegments} very short segment${shortSegments === 1 ? '' : 's'} may be hard to fabricate or review.`));
  }
  if (nonOrthogonalSegments) {
    warnings.push(routeWarning('non_orthogonal_segments', 'warn', `${nonOrthogonalSegments} segment${nonOrthogonalSegments === 1 ? '' : 's'} are not orthogonal.`));
  }
  if (diagnostics.bend_count > maxBendCount) {
    warnings.push(routeWarning('many_bends', 'warn', `Route has ${diagnostics.bend_count} bends; consider using fewer guide points or a raceway path.`));
  }
  for (let index = 2; index < route.length; index += 1) {
    const previousDirection = directionBetween(route[index - 2], route[index - 1]);
    const nextDirection = directionBetween(route[index - 1], route[index]);
    if (previousDirection && previousDirection === nextDirection) {
      warnings.push(routeWarning('collinear_node', 'info', 'One or more intermediate nodes are collinear and may be simplified later.'));
      break;
    }
  }
  return {
    valid: !warnings.some(warning => warning.severity === 'block'),
    diagnostics,
    warnings,
  };
}
