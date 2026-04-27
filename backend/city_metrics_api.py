"""
City Crop Metrics API
=====================
Fetches remote sensing metrics from Google Earth Engine for a given
district/city and year, applies the full preprocessing pipeline
(seasonal filtering, feature engineering), and returns a model-ready
feature vector that can be fed directly to the trained XGBoost models.

Usage:
    python3 city_metrics_api.py
    # Then visit http://127.0.0.1:8000/docs for Swagger UI

Endpoints:
    GET /metrics?city=Agra&season=kharif&year=2026
    GET /predict?city=Agra&season=kharif&crop=RICE&year=2026
"""

import ee
import json
import os
import glob
import numpy as np
import joblib
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from enum import Enum

# ---------------------------------------------------------------------------
# App & Earth Engine initialisation
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Crop Yield Metrics API",
    description="Fetch model-ready remote sensing features for crop yield prediction",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    ee.Initialize(project="gen-lang-client-0111974159")
except Exception as e:
    print("Earth Engine init error:", e)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DISTRICT_ASSET_PATH = "projects/gen-lang-client-0111974159/assets/districts"
DISTRICT_ID_PROPERTY = "shapeName"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NDVI_MEANS_PATH = os.path.join(SCRIPT_DIR, "district_ndvi_means.json")
TREND_COEFFS_PATH = os.path.join(SCRIPT_DIR, "crop_trend_coefficients.json")

# Model directories
KHARIF_MODEL_DIR = os.path.join(
    SCRIPT_DIR, os.pardir, "kharif",
    "report_cropwise_kharif_agricultural_land_mapped_final",
)
RABI_MODEL_DIR = os.path.join(
    SCRIPT_DIR, os.pardir, "rabi",
    "report_cropwise_rabi_agricultural_land_mapped_final",
)

# Months relevant to each season
KHARIF_MONTHS = [6, 7, 8, 9, 10]
RABI_MONTHS   = [1, 2, 3, 10, 11, 12]

# The exact feature lists the trained XGBoost models expect (order matters)
KHARIF_FEATURES = [
    'evi_06', 'evi_07', 'evi_08', 'evi_09', 'evi_10',
    'lst_max_06', 'lst_max_07', 'lst_max_08', 'lst_max_09', 'lst_max_10',
    'lst_mean_06', 'lst_mean_07', 'lst_mean_08', 'lst_mean_09', 'lst_mean_10',
    'ndvi_06', 'ndvi_07', 'ndvi_08', 'ndvi_09', 'ndvi_10',
    'rain_sum_06', 'rain_sum_07', 'rain_sum_08', 'rain_sum_09', 'rain_sum_10',
    'ndvi_mean', 'ndvi_std',
    'ndvi_06_anom', 'ndvi_07_anom', 'ndvi_08_anom', 'ndvi_09_anom', 'ndvi_10_anom',
    'kharif_rain',
]

RABI_FEATURES = [
    'evi_01', 'evi_02', 'evi_03', 'evi_10', 'evi_11', 'evi_12',
    'lst_max_02', 'lst_max_03', 'lst_max_10', 'lst_max_11', 'lst_max_12',
    'lst_mean_02', 'lst_mean_03', 'lst_mean_10', 'lst_mean_11', 'lst_mean_12',
    'ndvi_01', 'ndvi_02', 'ndvi_03', 'ndvi_10', 'ndvi_11', 'ndvi_12',
    'rain_sum_01', 'rain_sum_02', 'rain_sum_03', 'rain_sum_10', 'rain_sum_11', 'rain_sum_12',
    'ndvi_mean', 'ndvi_std',
    'ndvi_01_anom', 'ndvi_02_anom', 'ndvi_03_anom', 'ndvi_10_anom', 'ndvi_11_anom', 'ndvi_12_anom',
    'rabi_rain',
]

# ---------------------------------------------------------------------------
# Load precomputed historical NDVI means
# ---------------------------------------------------------------------------
_ndvi_means: dict = {}
if os.path.exists(NDVI_MEANS_PATH):
    with open(NDVI_MEANS_PATH) as f:
        _ndvi_means = json.load(f)
    print(f"Loaded NDVI historical means from {NDVI_MEANS_PATH}")
else:
    print(f"WARNING: {NDVI_MEANS_PATH} not found. NDVI anomalies will default to 0.")

# ---------------------------------------------------------------------------
# Load trend coefficients (for reversing yield detrending)
# ---------------------------------------------------------------------------
_trend_coeffs: dict = {}
if os.path.exists(TREND_COEFFS_PATH):
    with open(TREND_COEFFS_PATH) as f:
        _trend_coeffs = json.load(f)
    print(f"Loaded trend coefficients from {TREND_COEFFS_PATH}")
else:
    print(f"WARNING: {TREND_COEFFS_PATH} not found. Predictions will be detrended values only.")

# ---------------------------------------------------------------------------
# Load trained XGBoost models at startup
# ---------------------------------------------------------------------------
_models: dict = {"kharif": {}, "rabi": {}}

def _load_models_from_dir(model_dir: str, season_key: str):
    """Scan a directory for .joblib model files and load them."""
    if not os.path.isdir(model_dir):
        print(f"WARNING: Model directory not found: {model_dir}")
        return
    for path in sorted(glob.glob(os.path.join(model_dir, "*_xgb_model.joblib"))):
        # Filename e.g. RICE_xgb_model.joblib -> crop key = "RICE"
        basename = os.path.basename(path)
        crop_key = basename.replace("_xgb_model.joblib", "").replace("_", " ")
        try:
            _models[season_key][crop_key] = joblib.load(path)
            print(f"  Loaded {season_key} model: {crop_key}")
        except Exception as exc:
            print(f"  FAILED to load {path}: {exc}")

print("Loading Kharif models...")
_load_models_from_dir(KHARIF_MODEL_DIR, "kharif")
print("Loading Rabi models...")
_load_models_from_dir(RABI_MODEL_DIR, "rabi")
print(f"Models loaded — Kharif: {list(_models['kharif'].keys())}, Rabi: {list(_models['rabi'].keys())}")


class Season(str, Enum):
    kharif = "kharif"
    rabi = "rabi"


# ---------------------------------------------------------------------------
# Earth Engine: fetch raw monthly metrics for specific months only
# ---------------------------------------------------------------------------
def _fetch_ee_metrics(city_name: str, year: int, months: list[int]) -> dict:
    """
    Query Earth Engine for the given district, year, and month list.
    Returns a flat dict like {'ndvi_06': 0.27, 'evi_06': 0.19, ...}.
    Only fetches NDVI, EVI, LST (mean & max), and precipitation (no ET).
    """
    districts_fc = ee.FeatureCollection(DISTRICT_ASSET_PATH)
    districts_filtered = districts_fc.filter(
        ee.Filter.eq(DISTRICT_ID_PROPERTY, city_name)
    )

    if districts_filtered.size().getInfo() == 0:
        raise ValueError(
            f"City '{city_name}' not found in the Earth Engine asset. "
            f"Check the exact district name (case-sensitive)."
        )

    geom = districts_filtered.first().geometry()

    # MODIS Land Cover mask — cropland only (class 12)
    lc_year = min(max(year, 2001), 2022)
    lc_img = (
        ee.ImageCollection("MODIS/061/MCD12Q1")
        .filter(ee.Filter.calendarRange(lc_year, lc_year, "year"))
        .first()
    )
    cropland_mask = lc_img.select("LC_Type1").eq(12)

    ee_months = ee.List([int(m) for m in months])

    def get_monthly_metrics(month):
        month = ee.Number(month)
        start_date = ee.Date.fromYMD(year, month, 1)
        end_date = start_date.advance(1, "month")
        month_str = month.format("%02d")

        # ---- NDVI & EVI ----
        modis_veg = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select(["NDVI", "EVI"])
            .map(lambda img: img.multiply(0.0001))
        )
        veg_size = modis_veg.size()

        def compute_veg():
            veg_mean = modis_veg.mean()
            return ee.Image.cat([
                veg_mean.select("NDVI"),
                veg_mean.select("EVI"),
            ])

        def empty_veg():
            return ee.Image.constant([-9999, -9999]).rename(["NDVI", "EVI"])

        veg_img = ee.Image(
            ee.Algorithms.If(veg_size.gt(0), compute_veg(), empty_veg())
        )

        ndvi = veg_img.select("NDVI")
        evi = veg_img.select("EVI")

        # ---- LST ----
        lst_col = (
            ee.ImageCollection("MODIS/061/MOD11A2")
            .filterDate(start_date, end_date)
            .select("LST_Day_1km")
            .map(lambda img: img.multiply(0.02).subtract(273.15))
        )
        lst_mean = lst_col.mean()
        lst_max = lst_col.max()

        # ---- Precipitation ----
        rain_col = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterDate(start_date, end_date)
            .select("precipitation")
        )
        rain_sum = rain_col.sum()

        # Combine and mask to cropland
        monthly_img = ee.Image.cat([
            ndvi.rename(ee.String("ndvi_").cat(month_str)),
            evi.rename(ee.String("evi_").cat(month_str)),
            lst_mean.rename(ee.String("lst_mean_").cat(month_str)),
            lst_max.rename(ee.String("lst_max_").cat(month_str)),
            rain_sum.rename(ee.String("rain_sum_").cat(month_str)),
        ])
        monthly_img = monthly_img.updateMask(cropland_mask)

        stats = monthly_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom,
            scale=500,
            maxPixels=1e10,
        )
        return stats

    monthly_dicts = ee_months.map(get_monthly_metrics)

    def merge_dict(current, prev):
        return ee.Dictionary(prev).combine(ee.Dictionary(current), overwrite=True)

    final_dict = ee.Dictionary(
        monthly_dicts.iterate(merge_dict, ee.Dictionary({}))
    )

    return final_dict.getInfo()


# ---------------------------------------------------------------------------
# Feature engineering (replicates crop_train.py preprocessing)
# ---------------------------------------------------------------------------
def _engineer_features(
    raw_metrics: dict,
    season: str,
    city_name: str,
) -> dict:
    """
    Takes the raw Earth Engine metrics dict and applies the same
    preprocessing steps as crop_train.py:

    1. Replace -9999 sentinel values with None
    2. Compute ndvi_mean  (mean of season NDVI values)
    3. Compute ndvi_std   (std of season NDVI values)
    4. Compute ndvi_XX_anom (ndvi_XX - historical district mean)
    5. Compute kharif_rain / rabi_rain (sum of rain_sum_* columns)
    6. Select and order features to match model expectations
    """
    season_lower = season.lower()
    if season_lower == "kharif":
        months = KHARIF_MONTHS
        feature_order = KHARIF_FEATURES
    else:
        months = RABI_MONTHS
        feature_order = RABI_FEATURES

    # Step 1: replace -9999 sentinels
    for key, val in raw_metrics.items():
        if val is not None and val == -9999:
            raw_metrics[key] = None

    # Collect season NDVI values for aggregate stats
    ndvi_cols = [f"ndvi_{m:02d}" for m in months]
    ndvi_values = []
    for col in ndvi_cols:
        v = raw_metrics.get(col)
        if v is not None:
            ndvi_values.append(v)

    # Step 2–3: ndvi_mean and ndvi_std
    if ndvi_values:
        raw_metrics["ndvi_mean"] = float(np.mean(ndvi_values))
        raw_metrics["ndvi_std"] = float(np.std(ndvi_values, ddof=0))
    else:
        raw_metrics["ndvi_mean"] = None
        raw_metrics["ndvi_std"] = None

    # Step 4: NDVI anomalies
    hist_means = _ndvi_means.get(season_lower, {}).get(city_name, {})
    for col in ndvi_cols:
        anom_key = f"{col}_anom"
        current_val = raw_metrics.get(col)
        hist_val = hist_means.get(col)
        if current_val is not None and hist_val is not None:
            raw_metrics[anom_key] = current_val - hist_val
        else:
            # Fall back to 0 if no historical data available
            raw_metrics[anom_key] = 0.0

    # Step 5: seasonal total rainfall
    rain_cols = [f"rain_sum_{m:02d}" for m in months]
    rain_values = [raw_metrics.get(c, 0) or 0 for c in rain_cols]
    rain_key = f"{season_lower}_rain"
    raw_metrics[rain_key] = float(sum(rain_values))

    # Step 6: select and order features
    ordered = {}
    for feat in feature_order:
        ordered[feat] = raw_metrics.get(feat)

    return ordered


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------
@app.get("/metrics")
def get_metrics(
    city: str = Query(
        ..., description="District/city name exactly as stored in EE asset (e.g. 'Agra')"
    ),
    season: Season = Query(
        ..., description="Crop season: 'kharif' or 'rabi'"
    ),
    year: int = Query(
        None, description="Year to fetch metrics for (defaults to current year)"
    ),
):
    """
    Fetch model-ready remote sensing features for a district.

    Returns the **exact** feature vector (with correct column order) that
    the trained XGBoost crop-yield models expect, so the consumer can
    feed it directly into the model for prediction.
    """
    if year is None:
        year = datetime.now().year

    season_val = season.value  # "kharif" or "rabi"
    months = KHARIF_MONTHS if season_val == "kharif" else RABI_MONTHS
    feature_list = KHARIF_FEATURES if season_val == "kharif" else RABI_FEATURES

    try:
        # 1. Fetch raw metrics from Earth Engine
        raw = _fetch_ee_metrics(city, year, months)

        # 2. Apply feature engineering pipeline
        features = _engineer_features(raw, season_val, city)

        # 3. Check for any null features
        nulls = [k for k, v in features.items() if v is None]

        return {
            "city": city,
            "year": year,
            "season": season_val,
            "features": features,
            "feature_order": feature_list,
            "warnings": (
                f"The following features are null (model may not handle nulls): {nulls}"
                if nulls else None
            ),
        }

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Earth Engine error: {str(e)}")


# ---------------------------------------------------------------------------
# /predict endpoint
# ---------------------------------------------------------------------------
@app.get("/predict")
def predict_yield(
    city: str = Query(
        ..., description="District/city name exactly as stored in EE asset (e.g. 'Agra')"
    ),
    season: Season = Query(
        ..., description="Crop season: 'kharif' or 'rabi'"
    ),
    crop: str = Query(
        ..., description="Crop name in UPPERCASE (e.g. 'RICE', 'WHEAT', 'MAIZE')"
    ),
    year: int = Query(
        None, description="Year to predict for (defaults to current year)"
    ),
):
    """
    End-to-end crop yield prediction.

    1. Fetches remote sensing data from Earth Engine for the given district.
    2. Applies the full preprocessing / feature engineering pipeline.
    3. Runs the trained XGBoost model for the specified crop.
    4. Reverses yield detrending to return the **actual predicted yield (Kg/ha)**.
    """
    if year is None:
        year = datetime.now().year

    season_val = season.value
    crop_upper = crop.upper().strip()
    months = KHARIF_MONTHS if season_val == "kharif" else RABI_MONTHS
    feature_list = KHARIF_FEATURES if season_val == "kharif" else RABI_FEATURES

    # --- Validate model exists ---
    model = _models.get(season_val, {}).get(crop_upper)
    if model is None:
        available = list(_models.get(season_val, {}).keys())
        raise HTTPException(
            status_code=404,
            detail=(
                f"No trained model found for crop '{crop_upper}' in season '{season_val}'. "
                f"Available crops: {available}"
            ),
        )

    try:
        # 1. Fetch raw metrics from Earth Engine
        raw = _fetch_ee_metrics(city, year, months)

        # 2. Apply feature engineering pipeline
        features = _engineer_features(raw, season_val, city)

        # 3. Check for nulls
        nulls = [k for k, v in features.items() if v is None]
        if nulls:
            raise ValueError(
                f"Cannot predict — the following features are null: {nulls}. "
                f"Earth Engine may not have data for this city/year combination."
            )

        # 4. Build the feature array in the correct order
        X = np.array([[features[f] for f in feature_list]])

        # 5. Run model prediction (returns detrended yield)
        yield_detrended = float(model.predict(X)[0])

        # 6. Reverse detrending: predicted_yield = detrended + trend(year)
        trend_info = _trend_coeffs.get(season_val, {}).get(crop_upper)
        if trend_info:
            slope = trend_info["slope"]
            intercept = trend_info["intercept"]
            trend_value = slope * year + intercept
            predicted_yield = yield_detrended + trend_value
        else:
            trend_value = None
            predicted_yield = yield_detrended  # fallback: no detrending reversal

        return {
            "city": city,
            "year": year,
            "season": season_val,
            "crop": crop_upper,
            "predicted_yield_kg_per_ha": round(predicted_yield, 2),
            "yield_detrended": round(yield_detrended, 2),
            "trend_value": round(trend_value, 2) if trend_value is not None else None,
            "features_used": features,
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/crops")
def list_available_crops():
    """List all crops that have trained models available, grouped by season."""
    return {
        "kharif": sorted(_models.get("kharif", {}).keys()),
        "rabi": sorted(_models.get("rabi", {}).keys()),
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting API Server... Visit http://127.0.0.1:8000/docs for Swagger UI")
    uvicorn.run("city_metrics_api:app", host="127.0.0.1", port=8000, reload=True)
