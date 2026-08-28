(function initRacewayProjectionCore(globalScope) {
  function warn(message, detail) {
    if (detail === undefined) console.warn(message);
    else console.warn(message, detail);
  }

  function sourcePointFromGraphWarning(warning) {
    const point = warning?.source_point_m || warning?.sourcePointM || null;
    const x = Number(point?.x);
    const y = Number(point?.y);
    const z = Number(point?.z);
    if (![x, y, z].every(Number.isFinite)) return null;
    return { x, y, z };
  }

  function validateGraphProjectionContract(graph) {
    if (!graph) {
      warn('Raceway graph projection missing from response.');
      return;
    }
    if (!Array.isArray(graph.nodes)) {
      warn('Raceway graph projection contract warning: nodes must be an array.');
    }
    if (!Array.isArray(graph.edges)) {
      warn('Raceway graph projection contract warning: edges must be an array.');
    }
    if (!Array.isArray(graph.warnings)) {
      warn('Raceway graph projection contract warning: warnings must be an array.');
    }
    (Array.isArray(graph.edges) ? graph.edges : []).forEach(edge => {
      if (!edge.key) warn('Raceway graph edge missing key.', edge);
      if (!edge.run_key && !edge.run_id) warn('Raceway graph edge missing run identity.', edge);
      if (!Number.isInteger(Number(edge.start_sequence))) warn('Raceway graph edge missing start_sequence.', edge);
      if (!Number.isInteger(Number(edge.end_sequence))) warn('Raceway graph edge missing end_sequence.', edge);
      if (!edge.start_point_m || typeof edge.start_point_m !== 'object') warn('Raceway graph edge missing start_point_m.', edge);
      if (!edge.end_point_m || typeof edge.end_point_m !== 'object') warn('Raceway graph edge missing end_point_m.', edge);
    });
    (Array.isArray(graph.warnings) ? graph.warnings : [])
      .filter(warning => warning?.code === 'raceway.graph.unconnected_crossing')
      .forEach(warning => {
        if (!Array.isArray(warning.edge_keys) || warning.edge_keys.length < 2) {
          warn('Raceway unconnected-crossing warning missing edge_keys.', warning);
        }
        if (!sourcePointFromGraphWarning(warning)) {
          warn('Raceway unconnected-crossing warning missing source_point_m.', warning);
        }
      });
  }

  function warningSummaryText(warnings = {}) {
    if (!Number(warnings.total || 0)) return '';
    return `${warnings.total} validation notice(s) affect this schedule`
      + (warnings.by_severity ? ` (${warnings.warning || 0} warning, ${warnings.info || 0} info).` : '.');
  }

  function buildScheduleSummaryViewModel(schedule) {
    const totals = schedule?.totals || {};
    const fittingCounts = schedule?.fitting_placeholders?.counts || {};
    const warnings = schedule?.warning_summary || schedule?.graph_warnings || {};
    const assumptions = Array.isArray(schedule?.assumptions) ? schedule.assumptions : [];
    const groups = Array.isArray(schedule?.groups) ? schedule.groups : [];
    return {
      runCount: Number(totals.run_count || 0),
      lengthM: Number(totals.length_m || 0),
      pieceCountEstimate: Number(totals.piece_count_estimate || 0),
      offcutM: Number(totals.offcut_m_estimate || 0),
      planBendCount: Number(totals.plan_bend_count || 0),
      riserCount: Number(totals.riser_count || 0),
      teeCount: Number(fittingCounts.tee_total ?? totals.tee_count ?? 0),
      crossCount: Number(fittingCounts.cross_total ?? totals.cross_count ?? 0),
      supportPlaceholderCount: Number(totals.support_placeholders || 0),
      branchProjectionOnlyCount: Number(fittingCounts.branch_accessory_unresolved_total || 0),
      warningText: warningSummaryText(warnings),
      assumptionCount: assumptions.length,
      groupRows: groups.slice(0, 3).map(group => ({
        familyCode: String(group.family_code || ''),
        sizeLabel: String(group.size_label || ''),
        serviceClass: String(group.service_class || ''),
        lengthM: Number(group.length_m || 0),
        pieceCountEstimate: Number(group.piece_count_estimate || 0),
      })),
      hiddenGroupCount: Math.max(groups.length - 3, 0),
    };
  }

  function buildFittingSummaryViewModel(projection) {
    const counts = projection?.counts || {};
    const byKind = counts.by_kind || {};
    const byCategory = counts.by_category || {};
    const graph = projection?.graph_summary || {};
    return {
      totalCount: Number(counts.total || 0),
      syntheticProxyCount: Number(counts.synthetic_proxy_total || 0),
      planBendCount: Number(byKind.plan_bend || 0),
      riserCount: Number(byKind.riser || 0),
      teeCount: Number(byKind.tee || 0),
      crossCount: Number(byKind.cross || 0),
      reducerCandidateCount: Number(byKind.reducer_candidate || 0),
      reducerProxyCount: Number(counts.reducer_proxy_total || 0),
      requiresFaceAlignmentCount: Number(counts.requires_face_alignment || 0),
      requiresCatalogueValidationCount: Number(counts.requires_catalogue_validation || 0),
      nonStandardPlanBendCount: Number(counts.non_standard_plan_bends || 0),
      edgeMatchCandidateCount: Number(counts.one_edge_alignment_candidates || 0),
      faceOffsetStepCount: Number(counts.face_offset_steps || 0),
      faceAlignmentResolvedCount: Number(counts.face_alignment_resolved_by_offset || 0),
      junctionNodeCount: Number(graph.junction_node_count || 0),
      branchNodeCount: Number(graph.branch_node_count || 0),
      assumptionCount: Array.isArray(projection?.assumptions) ? projection.assumptions.length : 0,
      categoryRows: Object.entries(byCategory).slice(0, 4).map(([category, count]) => ({
        category: String(category),
        count: Number(count || 0),
      })),
    };
  }

  function commandState(disabled, reason = '') {
    return {
      disabled: Boolean(disabled),
      reason: disabled ? reason : '',
    };
  }

  function computeRacewayCommandStates(snapshot = {}) {
    const layerId = snapshot.layerId || null;
    const persistenceLoading = Boolean(snapshot.persistenceLoading);
    const fittingsLoading = Boolean(snapshot.fittingsLoading);
    const graphLoading = Boolean(snapshot.graphLoading);
    const scheduleLoading = Boolean(snapshot.scheduleLoading);
    const edgeMatchCandidateCount = Number(snapshot.edgeMatchCandidateCount || 0);
    const reducerCandidateCount = Number(snapshot.reducerCandidateCount || 0);
    const targetSegmentCount = Number(snapshot.targetSegmentCount || 0);
    const splitPercent = Number(snapshot.splitPercent || 0);
    const segmentLengthM = Number(snapshot.segmentLengthM || 0);
    const hasUnsavedSavableChanges = Boolean(snapshot.hasUnsavedSavableChanges);
    const fittingsLoaded = Boolean(snapshot.fittingsLoaded);
    const edgeMatchDisabled = persistenceLoading
      || fittingsLoading
      || !layerId
      || hasUnsavedSavableChanges
      || (fittingsLoaded && edgeMatchCandidateCount <= 0 && reducerCandidateCount <= 0);
    let edgeMatchReason = '';
    if (!layerId) edgeMatchReason = 'Save a raceway layer before applying reducer edge-match suggestions.';
    else if (persistenceLoading || fittingsLoading) edgeMatchReason = 'Raceway persistence or fittings are busy.';
    else if (hasUnsavedSavableChanges) edgeMatchReason = 'Save Draft before applying reducer suggestions from the saved fitting projection.';
    else if (fittingsLoaded && edgeMatchCandidateCount <= 0 && reducerCandidateCount <= 0) edgeMatchReason = 'Refresh fittings after creating unresolved unequal-size reducer candidates.';
    return {
      start: commandState(!(Number(snapshot.catalogCount || 0) > 0), 'Raceway catalogue is still loading.'),
      'continue-run': commandState(!snapshot.hasRun, 'Select a run before continuing it.'),
      finish: commandState(!snapshot.hasRun || Number(snapshot.runNodeCount || 0) < 2, 'Add at least two nodes before finishing.'),
      undo: commandState(!(Number(snapshot.undoCount || 0) > 0), 'Nothing to undo.'),
      redo: commandState(!(Number(snapshot.redoCount || 0) > 0), 'Nothing to redo.'),
      cancel: commandState(!snapshot.hasRun && snapshot.mode === 'idle', 'No active raceway command.'),
      'select-node-mode': commandState(!snapshot.hasRun, 'Select a run before selecting nodes on canvas.'),
      'move-node': commandState(!snapshot.hasNode, 'Select a node before moving it.'),
      'delete-node': commandState(!snapshot.hasNode, 'Select a node before deleting it.'),
      'connect-node': commandState(!snapshot.canConnectEndpoint, 'Select the first or last node of a run before connecting it.'),
      'make-tee': commandState(
        !snapshot.canConnectEndpoint || targetSegmentCount <= 0,
        !snapshot.canConnectEndpoint
          ? 'Select the first or last node of a branch run before making a tee.'
          : 'Create another horizontal raceway segment before making a tee.'
      ),
      'make-cross': commandState(
        persistenceLoading || graphLoading || hasUnsavedSavableChanges || !snapshot.hasSelectedGraphCrossingWarning,
        persistenceLoading || graphLoading
          ? 'Raceway persistence or graph refresh is busy.'
          : hasUnsavedSavableChanges
            ? 'Save Draft before making a cross from saved graph warnings.'
            : 'Refresh graph and select an unconnected crossing warning.'
      ),
      'anchor-node': commandState(!snapshot.hasRun, 'Start or select a run before anchoring.'),
      'clear-anchor': commandState(!snapshot.hasAnchoredNode, 'Select an anchored node first.'),
      save: commandState(
        persistenceLoading || (!Number(snapshot.savableRunCount || 0) && !Number(snapshot.pendingDraftDeleteCount || 0)),
        'Add at least one two-node run or remove a saved run before saving.'
      ),
      reload: commandState(persistenceLoading, persistenceLoading ? 'Raceway persistence is busy.' : ''),
      'refresh-graph': commandState(
        persistenceLoading || graphLoading || !layerId,
        layerId ? 'Raceway persistence or graph refresh is busy.' : 'Save a raceway layer before refreshing graph warnings.'
      ),
      'refresh-schedule': commandState(
        persistenceLoading || scheduleLoading || !layerId,
        layerId ? 'Raceway persistence or schedule refresh is busy.' : 'Save a raceway layer before refreshing the schedule.'
      ),
      'refresh-fittings': commandState(
        persistenceLoading || fittingsLoading || !layerId,
        layerId ? 'Raceway persistence or fittings refresh is busy.' : 'Save a raceway layer before refreshing fittings.'
      ),
      'apply-reducer-offsets': commandState(edgeMatchDisabled, edgeMatchReason),
      'open-warning-details': commandState(
        persistenceLoading || !layerId,
        layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before opening warning details.'
      ),
      'open-schedule-csv': commandState(
        persistenceLoading || !layerId,
        layerId ? 'Raceway persistence is busy.' : 'Save a raceway layer before downloading CSV.'
      ),
      'delete-run': commandState(persistenceLoading || !snapshot.hasRun, 'Select a run before deleting it.'),
      'add-segment': commandState(
        !Number(snapshot.runNodeCount || 0) || !(segmentLengthM > 0),
        'Add at least one node and enter a positive segment length.'
      ),
      'split-segment': commandState(
        !snapshot.hasSelectedSegment || splitPercent <= 0 || splitPercent >= 100,
        'Select a segment and enter a split percentage between 1 and 99.'
      ),
      'toggle-surfaces': commandState(false),
    };
  }

  globalScope.racewayProjectionCore = Object.freeze({
    validateGraphProjectionContract,
    warningSummaryText,
    buildScheduleSummaryViewModel,
    buildFittingSummaryViewModel,
    computeRacewayCommandStates,
  });
})(typeof window !== 'undefined' ? window : globalThis);
