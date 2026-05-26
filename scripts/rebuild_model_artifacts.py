#!/usr/bin/env python3
"""Rebuild saved scikit-learn model artifacts from packaged data and splits.

This uses the best hyperparameters recovered from the original notebook outputs.
It writes both:
- best models fitted on the saved training split
- final models refitted on all labeled rows

LightGBM is intentionally not rebuilt here because it requires the optional
`lightgbm` dependency and is handled by `notebooks/04_lightgbm.ipynb`.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

try:
    from lightgbm import LGBMRegressor
except ImportError:
    LGBMRegressor = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_COLS = ["Density", "PV", "GSA", "VSA", "VF", "PLD", "LCD"]
RANDOM_STATE = 42

TASKS = {
    "PS_UG": ("data/processed/ps_cleaned_canonical.csv", "UG at PS"),
    "PS_UV": ("data/processed/ps_cleaned_canonical.csv", "UV at PS"),
    "TPS_UG": ("data/processed/tps_cleaned_canonical.csv", "ug_at_tps"),
    "TPS_UV": ("data/processed/tps_cleaned_canonical.csv", "uv_at_tps"),
}

MODEL_SLUGS = [
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
    "lightgbm",
    "knn",
    "support_vector_regressor",
]


def load_dataset(task: str) -> tuple[np.ndarray, np.ndarray]:
    rel_path, target = TASKS[task]
    df = pd.read_csv(PROJECT_ROOT / rel_path)
    dfw = df.dropna(subset=FEATURE_COLS + [target]).reset_index(drop=True)
    y = pd.to_numeric(dfw[target], errors="coerce").values
    mask = ~np.isnan(y)
    return dfw.loc[mask, FEATURE_COLS].values, y[mask]


def load_train_indices(slug: str, suffix: str, task: str) -> np.ndarray:
    split_path = PROJECT_ROOT / "splits" / slug / f"{task}_{suffix}_split_indices.csv"
    split = pd.read_csv(split_path)
    return split.loc[split["split"] == "train", "model_matrix_index"].to_numpy(dtype=int)


def make_model(slug: str, params: dict):
    params = dict(params)
    if slug == "random_forest":
        params.update({"random_state": RANDOM_STATE, "n_jobs": -1})
        return RandomForestRegressor(**params)
    if slug == "extra_trees":
        params.update({"random_state": RANDOM_STATE, "n_jobs": -1})
        return ExtraTreesRegressor(**params)
    if slug == "hist_gradient_boosting":
        params.pop("scoring", None)
        params.update({"random_state": RANDOM_STATE})
        return HistGradientBoostingRegressor(**params)
    if slug == "lightgbm":
        if LGBMRegressor is None:
            raise ImportError("Install lightgbm before rebuilding LightGBM artifacts.")
        params.update({"random_state": RANDOM_STATE, "n_jobs": -1, "verbosity": -1})
        return LGBMRegressor(**params)
    if slug == "knn":
        model = Pipeline([("scaler", StandardScaler()), ("knn", KNeighborsRegressor(n_jobs=-1))])
        model.set_params(**params)
        return model
    if slug == "support_vector_regressor":
        model = Pipeline([("scaler", StandardScaler()), ("svr", SVR(kernel="rbf"))])
        model.set_params(**params)
        return model
    raise ValueError(f"Unsupported model slug: {slug}")


def main() -> None:
    manifest: list[dict] = []
    recovered_params = json.loads((PROJECT_ROOT / "models" / "recovered_best_params.json").read_text(encoding="utf-8"))
    for slug in MODEL_SLUGS:
        model_info = recovered_params[slug]
        label = model_info["model_label"]
        suffix = model_info["suffix"]
        params_by_task = model_info["tasks"]
        outdir = PROJECT_ROOT / "models" / slug
        outdir.mkdir(parents=True, exist_ok=True)
        for task in ["PS_UG", "PS_UV", "TPS_UG", "TPS_UV"]:
            params = params_by_task[task]
            X, y = load_dataset(task)
            train_idx = load_train_indices(slug, suffix, task)

            best = make_model(slug, params)
            best.fit(X[train_idx], y[train_idx])
            best_path = outdir / f"best_{suffix}_{task}.joblib"
            joblib.dump(best, best_path, compress=3)

            final = make_model(slug, params)
            final.fit(X, y)
            final_path = outdir / f"final_{suffix}_{task}.joblib"
            joblib.dump(final, final_path, compress=3)

            for kind, path in [("best", best_path), ("final", final_path)]:
                manifest.append(
                    {
                        "model": label,
                        "task": task,
                        "kind": kind,
                        "path": path.relative_to(PROJECT_ROOT).as_posix(),
                        "exists": True,
                        "size_bytes": path.stat().st_size,
                        "params": params,
                    }
                )

    (PROJECT_ROOT / "models" / "model_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
