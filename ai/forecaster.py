import joblib


class LoadForecaster:
    def __init__(self, model_path):
        self.model = joblib.load(model_path)

    def predict_next(self, history_df, hours_ahead=6):
        """
        Predict load for the next N hours.

        history_df contains:
        - timestamp (int timestep)
        - load_kw
        """

        df = history_df.copy()

        # Time features (same as training)
        df["hour"] = df["timestamp"] % 24
        df["dayofweek"] = (df["timestamp"] // 24) % 7

        # REQUIRED third feature (last known load)
        df["prev_load_kw"] = df["load_kw"]

        X = df[["hour", "dayofweek", "prev_load_kw"]].tail(hours_ahead)

        predictions = self.model.predict(X)
        return predictions.tolist()



