"""Information availability and unit declarations for Phase 11 signals."""
SIGNALS={
 'synthetic_signal':{'unit':'observation','labels_required':False},
 'released_error':{'unit':'released observation','labels_required':True},
 'rf_score_histogram':{'unit':'historical replay window','labels_required':False},
 'feature_js':{'unit':'historical replay window','labels_required':False},
 'historical_error_rate':{'unit':'released historical replay window','labels_required':True},
}
