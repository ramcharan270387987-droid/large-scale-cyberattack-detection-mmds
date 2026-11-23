"""Map fitted coefficients or split importances to the exact vector order."""


def explain(estimator, model_name, active):
    if model_name == "logistic_regression":
        method, values = "scaled_lr_coefficient", model_values(estimator.coefficients)
    else:
        method, values = "impurity_split_importance", model_values(estimator.featureImportances)
    if len(values) != len(active):
        raise ValueError("Fitted vector and registry dimensions disagree")
    return [{"feature": feature, "method": method, "value": value}
            for feature, value in sorted(zip(active, values), key=lambda item: (-abs(item[1]), item[0]))]


def model_values(vector):
    return [float(value) for value in vector.toArray()]
