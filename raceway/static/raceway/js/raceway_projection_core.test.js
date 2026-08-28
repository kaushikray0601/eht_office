const assert = require('node:assert/strict');
const test = require('node:test');

delete globalThis.racewayProjectionCore;
require('./raceway_projection_core.js');

const core = globalThis.racewayProjectionCore;

test('raceway projection core exports a frozen pure helper surface', () => {
  assert.equal(Object.isFrozen(core), true);
  assert.equal(typeof core.validateGraphProjectionContract, 'function');
  assert.equal(typeof core.buildScheduleSummaryViewModel, 'function');
  assert.equal(typeof core.buildFittingSummaryViewModel, 'function');
  assert.equal(typeof core.computeRacewayCommandStates, 'function');
});

test('computeRacewayCommandStates explains reducer edge-match disabled states', () => {
  const dirty = core.computeRacewayCommandStates({
    layerId: 3,
    hasUnsavedSavableChanges: true,
    fittingsLoaded: true,
    edgeMatchCandidateCount: 1,
  });

  assert.equal(dirty['apply-reducer-offsets'].disabled, true);
  assert.match(dirty['apply-reducer-offsets'].reason, /Save Draft/);

  const ready = core.computeRacewayCommandStates({
    layerId: 3,
    fittingsLoaded: true,
    edgeMatchCandidateCount: 1,
  });

  assert.equal(ready['apply-reducer-offsets'].disabled, false);
  assert.equal(ready['apply-reducer-offsets'].reason, '');
});

test('buildScheduleSummaryViewModel keeps Phase-H schedule fields stable', () => {
  const summary = core.buildScheduleSummaryViewModel({
    totals: {
      run_count: 2,
      length_m: 12.5,
      piece_count_estimate: 5,
      offcut_m_estimate: 2.5,
      plan_bend_count: 1,
      riser_count: 2,
      support_placeholders: 4,
    },
    fitting_placeholders: {
      counts: {
        tee_total: 1,
        cross_total: 1,
        branch_accessory_unresolved_total: 2,
      },
    },
    warning_summary: {
      total: 3,
      by_severity: { warning: 2, info: 1 },
      warning: 2,
      info: 1,
    },
    assumptions: [{ code: 'one' }],
    groups: [
      { family_code: 'LADDER', size_label: '300 x 100 mm', service_class: 'power', length_m: 8, piece_count_estimate: 3 },
      { family_code: 'PERF', size_label: '150 x 75 mm', service_class: 'control', length_m: 4.5, piece_count_estimate: 2 },
      { family_code: 'WIRE', size_label: '100 x 50 mm', service_class: 'lighting', length_m: 1, piece_count_estimate: 1 },
      { family_code: 'HIDDEN', size_label: '50 x 50 mm', service_class: 'spare', length_m: 1, piece_count_estimate: 1 },
    ],
  });

  assert.equal(summary.runCount, 2);
  assert.equal(summary.lengthM, 12.5);
  assert.equal(summary.teeCount, 1);
  assert.equal(summary.crossCount, 1);
  assert.equal(summary.branchProjectionOnlyCount, 2);
  assert.match(summary.warningText, /3 validation notice/);
  assert.equal(summary.groupRows.length, 3);
  assert.equal(summary.hiddenGroupCount, 1);
});

test('buildFittingSummaryViewModel keeps viewer-consumed fitting counts stable', () => {
  const summary = core.buildFittingSummaryViewModel({
    counts: {
      total: 7,
      synthetic_proxy_total: 4,
      requires_face_alignment: 1,
      requires_catalogue_validation: 3,
      non_standard_plan_bends: 1,
      one_edge_alignment_candidates: 2,
      face_offset_steps: 1,
      face_alignment_resolved_by_offset: 2,
      reducer_proxy_total: 1,
      by_kind: {
        plan_bend: 1,
        riser: 1,
        tee: 1,
        cross: 1,
        reducer_candidate: 2,
      },
      by_category: {
        plan_bend_46_90: 1,
        riser_up: 1,
      },
    },
    graph_summary: {
      junction_node_count: 2,
      branch_node_count: 1,
    },
    assumptions: [{ code: 'one' }, { code: 'two' }],
  });

  assert.equal(summary.totalCount, 7);
  assert.equal(summary.syntheticProxyCount, 4);
  assert.equal(summary.reducerProxyCount, 1);
  assert.equal(summary.edgeMatchCandidateCount, 2);
  assert.equal(summary.junctionNodeCount, 2);
  assert.equal(summary.branchNodeCount, 1);
  assert.equal(summary.assumptionCount, 2);
  assert.equal(summary.categoryRows.length, 2);
});

test('validateGraphProjectionContract warns loudly for malformed graph payloads', () => {
  const messages = [];
  const originalWarn = console.warn;
  console.warn = (message, detail) => messages.push([String(message), detail]);
  try {
    core.validateGraphProjectionContract({
      nodes: {},
      edges: [
        {
          key: '',
          run_key: '',
          start_sequence: null,
          end_sequence: null,
        },
      ],
      warnings: [
        {
          code: 'raceway.graph.unconnected_crossing',
          edge_keys: ['E001'],
          source_point_m: { x: 'bad', y: 0, z: 0 },
        },
      ],
    });
  } finally {
    console.warn = originalWarn;
  }

  const text = messages.map(([message]) => message).join('\n');
  assert.match(text, /nodes must be an array/);
  assert.match(text, /Raceway graph edge missing run identity/);
  assert.match(text, /unconnected-crossing warning missing edge_keys/);
  assert.match(text, /unconnected-crossing warning missing source_point_m/);
});
