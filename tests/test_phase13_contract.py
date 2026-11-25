import unittest
from src.explainability.contracts import validate

class ExplanationContractTests(unittest.TestCase):
    def test_identity_schema_background_and_shap_guard(self):
        m=dict(model_id='archived-v1',features=['x'],method='exact_linear',output_space='log-odds',background_role='training_reference')
        self.assertTrue(validate(m,'archived-v1',['x']))
        for change in (dict(model_id='other'),dict(features=['y']),dict(background_role='evaluation'),dict(method='tree_shap',output_space='probability')):
            with self.assertRaises(ValueError):validate(m|change,'archived-v1',['x'])
        self.assertTrue(validate(m|dict(method='tree_shap',output_space='probability',prediction_parity_verified=True),'archived-v1',['x']))
