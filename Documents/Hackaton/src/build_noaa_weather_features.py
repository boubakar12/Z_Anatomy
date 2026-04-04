from __future__ import annotations

import argparse
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


ISD_LITE_BASE = "https://www.ncei.noaa.gov/pub/data/noaa/isd-lite"
ISD_HISTORY_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
YEARS = list(range(2011, 2016))

DEFAULT_NEIGHBORS = 3
DEFAULT_BUFFER_DEG = 2.0


# ISD-Lite fixed-width positions are 1-based in the official format doc.
ISD_LITE_SPECS = {
    "air_temp": (13, 19, 10.0),
    "dew_point": (19, 25, 10.0),
    "sea_level_pressure": (25, 31, 10.0),
    "wind_dir": (31, 37, 1.0),
    "wind_speed": (37, 43, 10.0),
    "cloud_code": (43, 49, 1.0),
    "precip_1h": (49, 55, 10.0),
    "precip_6h": (55, 61, 10.0),
}


@dataclass
class Station:
    usaf: str
    wban: str
    lat: float
    lon: float
    station_id: str


def _download_bytes(url: str, timeout: int = 30) -> bytes | None:
    try:
        request = Request(url, headers={"User-Agent": "EY-challenge-weather-ingest"})
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (HTTPError, URLError):
        return None


def _parse_float(token: str, scale: float = 1.0) -> float:
    token = token.strip()
    if not token:
        return np.nan
    try:
        value = float(token)
    except ValueError:
        return np.nan
    if value == -9999.0:
        return np.nan
    value /= scale
    if value == -0.1:
        return 0.0
    return value


def parse_isd_lite_line(line: str, station_id: str) -> dict | None:
    if len(line) < 61:
        return None

    try:
        year = int(line[0:4].strip())
        month = int(line[5:7].strip())
        day = int(line[8:10].strip())
        hour = int(line[11:13].strip())
    except ValueError:
        return None

    if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23):
        return None

    row = {
        "station_id": station_id,
        "sample_datetime": pd.Timestamp(year=year, month=month, day=day, hour=hour),
    }

    for name, (start, end, scale) in ISD_LITE_SPECS.items():
        row[name] = _parse_float(line[start:end], scale)

    if pd.notna(row["wind_dir"]):
        radians = np.deg2rad(row["wind_dir"])
        row["wind_dir_sin"] = np.sin(radians)
        row["wind_dir_cos"] = np.cos(radians)
    else:
        row["wind_dir_sin"] = np.nan
        row["wind_dir_cos"] = np.nan

    return row


def parse_isd_station_file(content: bytes, station_id: str) -> pd.DataFrame:
    lines = gzip.decompress(content).splitlines()
    rows = []
    for raw in lines:
        parsed = parse_isd_lite_line(raw.decode("ascii", errors="ignore"), station_id)
        if parsed is not None:
            rows.append(parsed)

    if not rows:
        cols = [
            "station_id",
            "sample_datetime",
            "air_temp",
            "dew_point",
            "sea_level_pressure",
            "wind_speed",
            "cloud_code",
            "precip_1h",
            "precip_6h",
            "wind_dir_sin",
            "wind_dir_cos",
        ]
        return pd.DataFrame(columns=cols)

    return pd.DataFrame(rows)


def load_station_history() -> pd.DataFrame:
    content = _download_bytes(ISD_HISTORY_URL)
    if content is None:
        raise RuntimeError("Unable to download NOAA station history from NCEI")

    history = pd.read_csv(pd.io.common.BytesIO(content))
    history = history.rename(
        columns={
            "USAF": "usaf",
            "WBAN": "wban",
            "LAT": "lat",
            "LON": "lon",
            "BEGIN": "begin",
            "END": "end",
        }
    )

    needed = ["usaf", "wban", "lat", "lon", "begin", "end"]
    missing = [c for c in needed if c not in history.columns]
    if missing:
        raise RuntimeError(f"Missing columns from station history: {missing}")

    history = history[needed].copy()
    history["lat"] = pd.to_numeric(history["lat"], errors="coerce")
    history["lon"] = pd.to_numeric(history["lon"], errors="coerce")
    history["begin"] = pd.to_datetime(history["begin"].astype(str), format="%Y%m%d", errors="coerce")
    history["end"] = pd.to_datetime(history["end"].astype(str), format="%Y%m%d", errors="coerce")

    history = history.dropna(subset=["lat", "lon", "begin", "end", "usaf", "wban"])
    history = history[(history["lat"] != 0.0) | (history["lon"] != 0.0)]
    history["usaf"] = history["usaf"].astype(str).str.zfill(6)
    history["wban"] = history["wban"].astype(str).str.zfill(5)

    history = history.copy()
    history["station_id"] = history["usaf"] + "-" + history["wban"]
    return history


def select_stations(history: pd.DataFrame, sample_points: pd.DataFrame, min_date: pd.Timestamp, max_date: pd.Timestamp, buffer_deg: float) -> List[Station]:
    lat_min = sample_points["Latitude"].min() - buffer_deg
    lat_max = sample_points["Latitude"].max() + buffer_deg
    lon_min = sample_points["Longitude"].min() - buffer_deg
    lon_max = sample_points["Longitude"].max() + buffer_deg

    candidates = history[
        (history["lat"].between(lat_min, lat_max))
        & (history["lon"].between(lon_min, lon_max))
        & (history["begin"] <= max_date)
        & (history["end"] >= min_date)
    ]

    stations: List[Station] = []
    for _, row in candidates.iterrows():
        stations.append(
            Station(
                usaf=row["usaf"],
                wban=row["wban"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                station_id=row["station_id"],
            )
        )
    return stations


def _station_year_filename(station: Station, year: int) -> str:
    return f"{station.usaf}-{station.wban}-{year}.gz"


def _download_or_load_station_year(station: Station, year: int, cache_dir: Path, force_redownload: bool) -> bytes | None:
    filename = _station_year_filename(station, year)
    path = cache_dir / station.station_id / filename

    if path.exists() and not force_redownload:
        return path.read_bytes()

    url = f"{ISD_LITE_BASE}/{year}/{filename}"
    content = _download_bytes(url)
    if content is None:
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def station_hourly_to_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    if hourly.empty:
        return pd.DataFrame()

    hourly = hourly.copy()
    hourly["sample_date"] = pd.to_datetime(hourly["sample_datetime"]).dt.floor("D")

    daily = hourly.groupby(["station_id", "sample_date"], as_index=False).agg(
        air_temp=("air_temp", "mean"),
        dew_point=("dew_point", "mean"),
        sea_level_pressure=("sea_level_pressure", "mean"),
        wind_speed=("wind_speed", "mean"),
        cloud_code=("cloud_code", "mean"),
        precip_1h=("precip_1h", "sum"),
        precip_6h=("precip_6h", "sum"),
        wind_dir_sin=("wind_dir_sin", "mean"),
        wind_dir_cos=("wind_dir_cos", "mean"),
    )

    daily["wind_dir_deg"] = (np.degrees(np.arctan2(daily["wind_dir_sin"], daily["wind_dir_cos"])) + 360) % 360

    base_cols = ["air_temp", "dew_point", "sea_level_pressure", "wind_speed", "precip_1h", "precip_6h", "wind_dir_deg"]

    rows = []
    for _, g in daily.groupby("station_id"):
        g = g.sort_values("sample_date").reset_index(drop=True)
        for col in base_cols:
            g[f"{col}_roll3"] = g[col].rolling(3, min_periods=1).mean()
            g[f"{col}_roll7"] = g[col].rolling(7, min_periods=1).mean()
            g[f"{col}_roll14"] = g[col].rolling(14, min_periods=1).mean()
            g[f"{col}_roll30"] = g[col].rolling(30, min_periods=1).mean()
        rows.append(g)

    return pd.concat(rows, ignore_index=True)


def _haversine_matrix(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    lat1 = np.deg2rad(lat1)[:, None]
    lon1 = np.deg2rad(lon1)[:, None]
    lat2 = np.deg2rad(lat2)[None, :]
    lon2 = np.deg2rad(lon2)[None, :]

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def build_noaa_point_features(
    points: pd.DataFrame,
    station_daily: pd.DataFrame,
    station_coords: pd.DataFrame,
    neighbors: int,
) -> pd.DataFrame:
    points = points.copy()
    points["Sample Date"] = pd.to_datetime(points["Sample Date"]).dt.floor("D")
    station_daily = station_daily.copy()
    station_daily["sample_date"] = pd.to_datetime(station_daily["sample_date"]).dt.floor("D")

    feature_cols = [c for c in station_daily.columns if c not in {"station_id", "sample_date"}]
    station_index = station_daily.set_index(["station_id", "sample_date"])

    global_by_date = station_daily.groupby("sample_date")[feature_cols].mean()
    global_overall = station_daily[feature_cols].mean()

    station_ids = station_coords["station_id"].to_numpy()
    station_lat = station_coords["lat"].to_numpy()
    station_lon = station_coords["lon"].to_numpy()

    k = min(neighbors, len(station_ids))
    distances = _haversine_matrix(points["Latitude"].to_numpy(), points["Longitude"].to_numpy(), station_lat, station_lon)
    nearest_idx = np.argsort(distances, axis=1)[:, :k]

    generated: List[Dict[str, float | str]] = []

    for i, point in enumerate(points.to_dict("records")):
        p_date = point["Sample Date"]
        nn_ids = station_ids[nearest_idx[i]]
        nn_dist = distances[i, nearest_idx[i]]
        weights = 1.0 / (nn_dist + 1e-3)

        stack = np.full((len(nn_ids), len(feature_cols)), np.nan)
        for j, sid in enumerate(nn_ids):
            try:
                row = station_index.loc[(sid, p_date), feature_cols]
                stack[j, :] = np.asarray(row, dtype=float)
            except KeyError:
                continue

        valid = np.isfinite(stack)
        feat = np.full(len(feature_cols), np.nan)

        for col_idx in range(len(feature_cols)):
            col_valid = valid[:, col_idx]
            if col_valid.any():
                w = weights[col_valid]
                v = stack[col_valid, col_idx]
                feat[col_idx] = np.sum(w * v) / np.sum(w)

        # fallback 1: date-level mean across all stations
        if np.isnan(feat).any():
            if p_date in global_by_date.index:
                by_date_vals = global_by_date.loc[p_date].to_numpy(dtype=float)
                fill_mask = ~np.isfinite(feat)
                feat[fill_mask] = by_date_vals[fill_mask]

        # fallback 2: global mean
        fill_mask = ~np.isfinite(feat)
        if fill_mask.any():
            feat[fill_mask] = global_overall.to_numpy(dtype=float)[fill_mask]

        record = {
            "Latitude": point["Latitude"],
            "Longitude": point["Longitude"],
            "Sample Date": point["Sample Date"].strftime("%d-%m-%Y"),
        }
        record.update({col: value for col, value in zip(feature_cols, feat)})
        generated.append(record)

    return pd.DataFrame.from_records(generated)


def prepare_noaa_features(
    base_dir: Path,
    out_dir: Path,
    neighbors: int,
    buffer_deg: float,
    force_redownload: bool,
) -> Tuple[Path, Path]:
    train = pd.read_csv(base_dir / "water_quality_training_dataset.csv")
    submission = pd.read_csv(base_dir / "submission_template.csv")

    all_points = pd.concat(
        [
            train[["Latitude", "Longitude", "Sample Date"]],
            submission[["Latitude", "Longitude", "Sample Date"]],
        ],
        ignore_index=True,
    )
    all_points["Sample Date"] = pd.to_datetime(all_points["Sample Date"], dayfirst=True)

    min_date = all_points["Sample Date"].min()
    max_date = all_points["Sample Date"].max()

    history = load_station_history()
    stations = select_stations(history, all_points, min_date, max_date, buffer_deg)
    if not stations:
        raise RuntimeError("No NOAA stations found for your coordinates/date span.")

    station_coords = pd.DataFrame({
        "station_id": [s.station_id for s in stations],
        "usaf": [s.usaf for s in stations],
        "wban": [s.wban for s in stations],
        "lat": [s.lat for s in stations],
        "lon": [s.lon for s in stations],
    })

    tasks = [(s, year) for s in stations for year in YEARS]
    cache_dir = out_dir / "cache"

    payloads: List[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(tasks)))) as executor:
        futures = {
            executor.submit(_download_or_load_station_year, station, year, cache_dir, force_redownload): (station, year)
            for station, year in tasks
        }
        for future in as_completed(futures):
            content = future.result()
            if content is None:
                continue
            station, year = futures[future]
            station_id = station.station_id
            hourly = parse_isd_station_file(content, station_id)
            if not hourly.empty:
                payloads.append(hourly)

    if not payloads:
        raise RuntimeError("No NOAA observation records were downloaded.")

    hourly_all = pd.concat(payloads, ignore_index=True)
    daily = station_hourly_to_daily(hourly_all)
    if daily.empty:
        raise RuntimeError("Unable to build daily NOAA features from downloaded data.")

    all_points_featured = build_noaa_point_features(
        all_points[["Latitude", "Longitude", "Sample Date"]],
        daily,
        station_coords,
        neighbors,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "noaa_features_training.csv"
    sub_path = out_dir / "noaa_features_validation.csv"

    feature_cols = [c for c in all_points_featured.columns if c not in {"Latitude", "Longitude", "Sample Date"}]

    train_featured = train[["Latitude", "Longitude", "Sample Date"]].merge(
        all_points_featured,
        on=["Latitude", "Longitude", "Sample Date"],
        how="left",
    )

    sub_featured = submission[["Latitude", "Longitude", "Sample Date"]].merge(
        all_points_featured,
        on=["Latitude", "Longitude", "Sample Date"],
        how="left",
    )

    train_featured.to_csv(train_path, index=False)
    sub_featured.to_csv(sub_path, index=False)

    return train_path, sub_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download NOAA ISD-Lite and generate challenge weather features")
    parser.add_argument(
        "--base-dir",
        default="/Users/boubakardiallo/Documents/Hackaton/Snowflake Notebooks Package",
        help="Directory that contains water_quality_training_dataset.csv and submission_template.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="/Users/boubakardiallo/Documents/Hackaton/data/noaa_features",
        help="Output directory for generated NOAA feature CSVs",
    )
    parser.add_argument("--neighbors", type=int, default=DEFAULT_NEIGHBORS)
    parser.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)
    parser.add_argument("--force-redownload", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_path, sub_path = prepare_noaa_features(
        base_dir=Path(args.base_dir),
        out_dir=Path(args.out_dir),
        neighbors=args.neighbors,
        buffer_deg=args.buffer_deg,
        force_redownload=args.force_redownload,
    )
    print(f"Saved NOAA training features: {train_path}")
    print(f"Saved NOAA validation features: {sub_path}")


if __name__ == "__main__":
    main()
