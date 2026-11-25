"""Fail-closed explanation metadata and archived-model compatibility checks."""
METHOD_SPACES={'exact_linear':'log-odds','native_tree_importance':'global split importance','centroid_deviation':'squared distance','hybrid_policy':'registered hybrid score','linear_shap':'log-odds','tree_shap':'probability'}


def validate(metadata, model_id, features):
    if metadata.get('model_id')!=model_id or metadata.get('features')!=list(features):
        raise ValueError('Explanation model or feature order differs')
    method=metadata.get('method')
    if method not in METHOD_SPACES or metadata.get('output_space')!=METHOD_SPACES[method]:
        raise ValueError('Explanation method and output space differ')
    if metadata.get('background_role') not in (None,'training_reference'):
        raise ValueError('Explanation background must come from permitted reference observations')
    if method.endswith('shap') and not metadata.get('prediction_parity_verified'):
        raise ValueError('SHAP compatibility requires verified archived prediction parity')
    return True
