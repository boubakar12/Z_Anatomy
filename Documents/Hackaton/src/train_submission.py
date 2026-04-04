from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import os
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor, GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge


TARGETS = [
    "Total Alkalinity",
    "Electrical Conductance",
    "Dissolved Reactive Phosphorus",
]

KEYS = ["Latitude", "Longitude", "Sample Date"]


@dataclass
class CVResult:
    target: str
    model_name: str
    mean_r2: float
    fold_scores: List[float]


def load_data(base_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    project_root = base_dir.parent
    train = pd.read_csv(base_dir / "water_quality_training_dataset.csv")
    submission = pd.read_csv(base_dir / "submission_template.csv")

    landsat_train = pd.read_csv(base_dir / "landsat_features_training.csv")
    landsat_val = pd.read_csv(base_dir / "landsat_features_validation.csv")
    terra_train = pd.read_csv(base_dir / "terraclimate_features_training.csv")
    terra_val = pd.read_csv(base_dir / "terraclimate_features_validation.csv")

    full_train = train.merge(landsat_train, on=KEYS, how="left").merge(terra_train, on=KEYS, how="left")
    full_submission = submission.merge(landsat_val, on=KEYS, how="left").merge(terra_val, on=KEYS, how="left")

    noaa_train_candidates = [
        base_dir / "data" / "noaa_features" / "noaa_features_training.csv",
        base_dir / "noaa_features_training.csv",
        project_root / "data" / "noaa_features" / "noaa_features_training.csv",
    ]
    noaa_sub_candidates = [
        base_dir / "data" / "noaa_features" / "noaa_features_validation.csv",
        base_dir / "noaa_features_validation.csv",
        project_root / "data" / "noaa_features" / "noaa_features_validation.csv",
    ]

    for path in noaa_train_candidates:
        if path.exists():
            noaa_train = pd.read_csv(path)
            full_train = full_train.merge(noaa_train, on=KEYS, how="left")
            break

    for path in noaa_sub_candidates:
        if path.exists():
            noaa_val = pd.read_csv(path)
            full_submission = full_submission.merge(noaa_val, on=KEYS, how="left")
            break

    return full_train, full_submission


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dt = pd.to_datetime(out["Sample Date"], dayfirst=True, errors="coerce")
    out["year"] = dt.dt.year
    out["month"] = dt.dt.month
    out["day"] = dt.dt.day
    out["dayofyear"] = dt.dt.dayofyear

    # Cyclical time encoding for seasonality.
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12.0)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12.0)
    out["doy_sin"] = np.sin(2 * np.pi * out["dayofyear"] / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * out["dayofyear"] / 365.25)

    # Spatial interactions.
    out["lat_lon_interaction"] = out["Latitude"] * out["Longitude"]
    out["abs_lat"] = out["Latitude"].abs()
    out["abs_lon"] = out["Longitude"].abs()

    if {"nir", "green"}.issubset(out.columns):
        out["nir_green_ratio"] = out["nir"] / (out["green"] + 1e-6)
    if {"swir22", "swir16"}.issubset(out.columns):
        out["swir_ratio"] = out["swir22"] / (out["swir16"] + 1e-6)

    return out


def build_models(safe: bool = False) -> Dict[str, Pipeline]:
    if safe:
        return {
            "extra_trees": Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        ExtraTreesRegressor(
                            n_estimators=400,
                            min_samples_leaf=2,
                            max_features="sqrt",
                            random_state=42,
                            n_jobs=1,
                        ),
                    ),
                ]
            ),
            "random_forest": Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        RandomForestRegressor(
                            n_estimators=300,
                            min_samples_leaf=2,
                            max_features="sqrt",
                            random_state=42,
                            n_jobs=1,
                        ),
                    ),
                ]
            ),
            "ridge": Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("model", Ridge(alpha=3.0)),
                ]
            ),
        }

    return {
        "extra_trees": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=700,
                        min_samples_leaf=2,
                        max_features="sqrt",
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=500,
                        min_samples_leaf=2,
                        max_features="sqrt",
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
        "hist_gb": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_depth=8,
                        learning_rate=0.05,
                        max_iter=800,
                        min_samples_leaf=20,
                        max_leaf_nodes=64,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "gbr": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=800,
                        learning_rate=0.03,
                        max_depth=3,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "ridge": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=3.0)),
            ]
        ),
    }


def evaluate_models(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    models: Dict[str, Pipeline],
    n_splits: int = 5,
) -> List[CVResult]:
    gkf = GroupKFold(n_splits=n_splits)
    results: List[CVResult] = []

    for model_name, model in models.items():
        start_model = time.time()
        fold_scores: List[float] = []
        for train_idx, val_idx in gkf.split(X, y, groups=groups):
            X_tr, X_va = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_va = y.iloc[train_idx], y.iloc[val_idx]

            fitted = clone(model)
            fitted.fit(X_tr, y_tr)
            pred = fitted.predict(X_va)
            fold_scores.append(r2_score(y_va, pred))
        duration = time.time() - start_model

        results.append(
            CVResult(
                target=y.name,
                model_name=model_name,
                mean_r2=float(np.mean(fold_scores)),
                fold_scores=fold_scores,
            )
        )

        print(f"[{y.name}] {model_name}: mean_r2={results[-1].mean_r2:.5f}, elapsed={duration:.1f}s")
    return results


def choose_best(results: List[CVResult]) -> CVResult:
    return sorted(results, key=lambda r: r.mean_r2, reverse=True)[0]


def choose_top(results: List[CVResult], top_n: int = 2) -> List[CVResult]:
    return sorted(results, key=lambda r: r.mean_r2, reverse=True)[:top_n]


def blend_weights_for_results(top_results: List[CVResult], epsilon: float = 1e-6) -> List[float]:
    if not top_results:
        return []
    scores = np.array([max(r.mean_r2, 0.0) for r in top_results], dtype=float)
    if scores.sum() <= 0:
        return [1.0 / len(top_results)] * len(top_results)
    scores = scores + epsilon
    return (scores / scores.sum()).tolist()


def maybe_log_target(y: pd.Series, target_name: str) -> bool:
    if target_name in {"Electrical Conductance", "Dissolved Reactive Phosphorus"}:
        return True
    return y.skew() > 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train EY water quality models")
    parser.add_argument(
        "--use-noaa",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to include NOAA weather features if available.",
    )
    parser.add_argument(
        "--blend-top",
        type=int,
        default=2,
        help="Number of top models to blend for final prediction.",
    )
    parser.add_argument(
        "--n-splits",
        type=int,
        default=5,
        help="GroupKFold splits for CV.",
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Use safer models to avoid threaded OpenMP runtime issues.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    base_dir = project_root / "Snowflake Notebooks Package"
    out_dir = project_root / "submissions"
    report_dir = project_root / "reports"
    out_dir.mkdir(exist_ok=True)
    report_dir.mkdir(exist_ok=True)

    train_df, sub_df = load_data(base_dir)
    # Optionally disable NOAA features by dropping any columns that were only derived
    # from the NOAA integration when use_noaa=False.
    if not args.use_noaa:
        noaa_prefixes = [
            "air_temp",
            "dew_point",
            "sea_level_pressure",
            "wind_speed",
            "cloud_code",
            "precip_",
            "wind_dir",
        ]
        drop_cols = [
            c
            for c in train_df.columns
            if any(c.startswith(prefix) for prefix in noaa_prefixes)
        ]
        train_df = train_df.drop(columns=drop_cols, errors="ignore")
        sub_df = sub_df.drop(columns=drop_cols, errors="ignore")

    train_df = add_features(train_df)
    sub_df = add_features(sub_df)

    feature_cols = [c for c in train_df.columns if c not in TARGETS + ["Sample Date"]]
    X_train = train_df[feature_cols]
    X_sub = sub_df[feature_cols]

    groups = train_df["Latitude"].round(4).astype(str) + "_" + train_df["Longitude"].round(4).astype(str)
    models = build_models(safe=args.safe)

    cv_rows = []
    submission = sub_df[KEYS].copy()

    for target in TARGETS:
        y = train_df[target]
        cv_results = evaluate_models(X_train, y, groups, models=models, n_splits=args.n_splits)
        top_models = choose_top(cv_results, top_n=max(1, args.blend_top))
        weights = blend_weights_for_results(top_models)

        for r in cv_results:
            cv_rows.append(
                {
                    "target": target,
                    "model": r.model_name,
                    "mean_r2": r.mean_r2,
                    "fold_scores": ", ".join(f"{s:.4f}" for s in r.fold_scores),
                }
            )

        preds = []
        for r, w in zip(top_models, weights):
            final_model = clone(models[r.model_name])
            if maybe_log_target(y, target):
                final_model = TransformedTargetRegressor(
                    regressor=final_model,
                    func=np.log1p,
                    inverse_func=np.expm1,
                )
            final_model.fit(X_train, y)
            preds.append((final_model.predict(X_sub), w))

        if len(preds) == 1:
            pred = preds[0][0]
        else:
            pred = np.zeros(len(X_sub))
            for model_pred, weight in preds:
                pred += weight * np.where(np.isfinite(model_pred), model_pred, np.nan)

        pred = np.where(np.isfinite(pred), pred, np.nan)
        pred = np.maximum(pred, 0)
        submission[target] = pred

    avg_best = (
        pd.DataFrame(cv_rows)
        .sort_values(["target", "mean_r2"], ascending=[True, False])
        .groupby("target", as_index=False)
        .first()["mean_r2"]
        .mean()
    )

    submission = submission[["Latitude", "Longitude", "Sample Date"] + TARGETS]
    submission_path = out_dir / "submission_enhanced.csv"
    submission.to_csv(submission_path, index=False)

    cv_df = pd.DataFrame(cv_rows).sort_values(["target", "mean_r2"], ascending=[True, False])
    cv_path = report_dir / "cv_results.csv"
    cv_df.to_csv(cv_path, index=False)

    summary_path = report_dir / "training_summary.txt"
    with summary_path.open("w") as f:
        f.write("Enhanced training run summary\n")
        f.write("=============================\n")
        f.write(f"Rows (train): {len(train_df)}\n")
        f.write(f"Rows (submission): {len(sub_df)}\n")
        f.write(f"Feature count: {len(feature_cols)}\n")
        f.write(f"Mean of best CV R2 across 3 targets: {avg_best:.5f}\n\n")
        f.write("Top model by target:\n")
        for target, group in cv_df.groupby("target"):
            top = group.iloc[0]
            f.write(f"- {target}: {top['model']} (mean_r2={top['mean_r2']:.5f})\n")

    print(f"Saved submission: {submission_path}")
    print(f"Saved CV report: {cv_path}")
    print(f"Saved summary: {summary_path}")


if __name__ == "__main__":
    main()
