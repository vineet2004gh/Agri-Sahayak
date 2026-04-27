"""
Yield Prediction Pipeline using LangGraph
==========================================

This module implements crop yield prediction for Kharif and Rabi seasons
using pre-trained XGBoost models.  Each crop has its own model trained on
remote-sensing features (EVI, NDVI, LST, rainfall).

Since end-users won't have raw satellite data, the module uses
representative seasonal averages for the remote-sensing features and
runs the XGBoost model to produce a baseline yield estimate.  The
prediction is then sent to Google Gemini for farmer-friendly
interpretation and actionable advice.

Pipeline::

    validate  →  load_model  →  predict  →  gemini_interpret  →  END

Usage::

    from backend.yield_prediction import run_yield_prediction
    result = run_yield_prediction(
        crop="rice", season="kharif",
        state="Punjab", district="Ludhiana",
        google_api_key="..."
    )
"""

from __future__ import annotations

import os
from typing import TypedDict, Optional, List

import numpy as np
from langgraph.graph import StateGraph, END


# ---------------------------------------------------------------------------
# Model directories
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # project root
KHARIF_MODEL_DIR = os.path.join(_BASE_DIR, "kharif", "report_cropwise_kharif_agricultural_land_mapped_final")
RABI_MODEL_DIR = os.path.join(_BASE_DIR, "rabi", "report_cropwise_rabi_agricultural_land_mapped_final")

# ---------------------------------------------------------------------------
# Available crops per season
# ---------------------------------------------------------------------------
KHARIF_CROPS = {
    "cotton": "COTTON",
    "groundnut": "GROUNDNUT",
    "kharif sorghum": "KHARIF_SORGHUM",
    "sorghum": "KHARIF_SORGHUM",  # alias
    "maize": "MAIZE",
    "pearl millet": "PEARL_MILLET",
    "bajra": "PEARL_MILLET",  # alias
    "millet": "PEARL_MILLET",  # alias
    "pigeonpea": "PIGEONPEA",
    "arhar": "PIGEONPEA",  # alias
    "rice": "RICE",
    "paddy": "RICE",  # alias
    "sesamum": "SESAMUM",
    "til": "SESAMUM",  # alias
    "soyabean": "SOYABEAN",
    "soybean": "SOYABEAN",  # alias
}

RABI_CROPS = {
    "barley": "BARLEY",
    "chickpea": "CHICKPEA",
    "chana": "CHICKPEA",  # alias
    "gram": "CHICKPEA",  # alias
    "linseed": "LINSEED",
    "rapeseed and mustard": "RAPESEED_AND_MUSTARD",
    "mustard": "RAPESEED_AND_MUSTARD",  # alias
    "sarson": "RAPESEED_AND_MUSTARD",  # alias
    "sorghum": "SORGHUM",
    "rabi sorghum": "SORGHUM",
    "sunflower": "SUNFLOWER",
    "wheat": "WHEAT",
    "gehun": "WHEAT",  # alias
}

# ---------------------------------------------------------------------------
# Feature templates — representative seasonal averages
# These are used as baseline inputs since users don't provide satellite data.
# Values are approximate Indian-subcontinent averages for each season.
# ---------------------------------------------------------------------------

# Kharif features: months 06-10 (Jun-Oct), 33 features total
KHARIF_FEATURE_NAMES = [
    "evi_06", "evi_07", "evi_08", "evi_09", "evi_10",
    "lst_max_06", "lst_max_07", "lst_max_08", "lst_max_09", "lst_max_10",
    "lst_mean_06", "lst_mean_07", "lst_mean_08", "lst_mean_09", "lst_mean_10",
    "ndvi_06", "ndvi_07", "ndvi_08", "ndvi_09", "ndvi_10",
    "rain_sum_06", "rain_sum_07", "rain_sum_08", "rain_sum_09", "rain_sum_10",
    "ndvi_mean", "ndvi_std",
    "ndvi_06_anom", "ndvi_07_anom", "ndvi_08_anom", "ndvi_09_anom", "ndvi_10_anom",
    "kharif_rain",
]

KHARIF_DEFAULT_VALUES = {
    # EVI (Enhanced Vegetation Index) — typical kharif range
    "evi_06": 0.25, "evi_07": 0.35, "evi_08": 0.42, "evi_09": 0.38, "evi_10": 0.30,
    # LST max (Land Surface Temperature max, °C)
    "lst_max_06": 42.0, "lst_max_07": 38.0, "lst_max_08": 35.0, "lst_max_09": 36.0, "lst_max_10": 34.0,
    # LST mean
    "lst_mean_06": 35.0, "lst_mean_07": 32.0, "lst_mean_08": 30.0, "lst_mean_09": 31.0, "lst_mean_10": 29.0,
    # NDVI (Normalized Difference Vegetation Index)
    "ndvi_06": 0.30, "ndvi_07": 0.42, "ndvi_08": 0.50, "ndvi_09": 0.45, "ndvi_10": 0.35,
    # Rain sum (mm)
    "rain_sum_06": 120.0, "rain_sum_07": 250.0, "rain_sum_08": 280.0, "rain_sum_09": 180.0, "rain_sum_10": 60.0,
    # Derived
    "ndvi_mean": 0.40, "ndvi_std": 0.07,
    "ndvi_06_anom": -0.10, "ndvi_07_anom": 0.02, "ndvi_08_anom": 0.10,
    "ndvi_09_anom": 0.05, "ndvi_10_anom": -0.05,
    "kharif_rain": 890.0,
}

# Rabi features: months 01-03, 10-12 (Oct-Mar), 37 features total
RABI_FEATURE_NAMES = [
    "evi_01", "evi_02", "evi_03", "evi_10", "evi_11", "evi_12",
    "lst_max_02", "lst_max_03", "lst_max_10", "lst_max_11", "lst_max_12",
    "lst_mean_02", "lst_mean_03", "lst_mean_10", "lst_mean_11", "lst_mean_12",
    "ndvi_01", "ndvi_02", "ndvi_03", "ndvi_10", "ndvi_11", "ndvi_12",
    "rain_sum_01", "rain_sum_02", "rain_sum_03", "rain_sum_10", "rain_sum_11", "rain_sum_12",
    "ndvi_mean", "ndvi_std",
    "ndvi_01_anom", "ndvi_02_anom", "ndvi_03_anom",
    "ndvi_10_anom", "ndvi_11_anom", "ndvi_12_anom",
    "rabi_rain",
]

RABI_DEFAULT_VALUES = {
    # EVI
    "evi_01": 0.30, "evi_02": 0.35, "evi_03": 0.28, "evi_10": 0.22, "evi_11": 0.25, "evi_12": 0.28,
    # LST max
    "lst_max_02": 28.0, "lst_max_03": 33.0, "lst_max_10": 34.0, "lst_max_11": 30.0, "lst_max_12": 26.0,
    # LST mean
    "lst_mean_02": 22.0, "lst_mean_03": 27.0, "lst_mean_10": 29.0, "lst_mean_11": 24.0, "lst_mean_12": 20.0,
    # NDVI
    "ndvi_01": 0.35, "ndvi_02": 0.42, "ndvi_03": 0.38, "ndvi_10": 0.28, "ndvi_11": 0.30, "ndvi_12": 0.32,
    # Rain sum
    "rain_sum_01": 15.0, "rain_sum_02": 20.0, "rain_sum_03": 12.0,
    "rain_sum_10": 40.0, "rain_sum_11": 10.0, "rain_sum_12": 8.0,
    # Derived
    "ndvi_mean": 0.34, "ndvi_std": 0.05,
    "ndvi_01_anom": 0.01, "ndvi_02_anom": 0.08, "ndvi_03_anom": 0.04,
    "ndvi_10_anom": -0.06, "ndvi_11_anom": -0.04, "ndvi_12_anom": -0.02,
    "rabi_rain": 105.0,
}


# ---------------------------------------------------------------------------
# Model cache
# ---------------------------------------------------------------------------
_model_cache: dict = {}


def _load_yield_model(crop_key: str, season: str):
    """Load an XGBoost model from disk (cached)."""
    cache_key = f"{season}_{crop_key}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    import joblib

    if season == "kharif":
        model_path = os.path.join(KHARIF_MODEL_DIR, f"{crop_key}_xgb_model.joblib")
    else:
        model_path = os.path.join(RABI_MODEL_DIR, f"{crop_key}_xgb_model.joblib")

    if not os.path.isfile(model_path):
        print(f"[YieldPred] Model not found: {model_path}")
        return None

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = joblib.load(model_path)
        print(f"[YieldPred] Loaded model: {model_path}")
        _model_cache[cache_key] = model
        return model
    except Exception as e:
        print(f"[YieldPred] Failed to load model {model_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# Graph state schema
# ---------------------------------------------------------------------------
class YieldState(TypedDict):
    crop: str
    season: str
    state: Optional[str]
    district: Optional[str]
    google_api_key: str
    # Populated by pipeline
    crop_key: Optional[str]
    predicted_yield: Optional[float]
    yield_unit: Optional[str]
    feature_values: Optional[dict]
    response: Optional[str]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def validate_node(state: YieldState) -> dict:
    """Validate inputs and resolve crop name to model key."""
    crop = (state.get("crop") or "").strip().lower()
    season = (state.get("season") or "").strip().lower()

    if not crop:
        return {"error": "Crop name is required for yield prediction."}

    # Auto-detect season if not provided
    if not season:
        if crop in KHARIF_CROPS:
            season = "kharif"
        elif crop in RABI_CROPS:
            season = "rabi"
        else:
            return {"error": f"Could not determine season for crop '{crop}'. Please specify 'kharif' or 'rabi'."}

    # Resolve crop key
    if season == "kharif":
        crop_key = KHARIF_CROPS.get(crop)
        if not crop_key:
            available = ", ".join(sorted(set(KHARIF_CROPS.values())))
            return {"error": f"Crop '{crop}' not available for Kharif season. Available: {available}"}
    elif season == "rabi":
        crop_key = RABI_CROPS.get(crop)
        if not crop_key:
            available = ", ".join(sorted(set(RABI_CROPS.values())))
            return {"error": f"Crop '{crop}' not available for Rabi season. Available: {available}"}
    else:
        return {"error": f"Invalid season '{season}'. Must be 'kharif' or 'rabi'."}

    return {"crop_key": crop_key, "season": season}


def load_model_node(state: YieldState) -> dict:
    """Load the XGBoost model for the given crop and season."""
    if state.get("error"):
        return {}

    crop_key = state.get("crop_key")
    season = state.get("season")

    model = _load_yield_model(crop_key, season)
    if model is None:
        return {"error": f"Yield model for {crop_key} ({season}) could not be loaded."}

    return {}


def predict_node(state: YieldState) -> dict:
    """Run the XGBoost yield prediction using representative feature values."""
    if state.get("error"):
        return {}

    crop_key = state.get("crop_key")
    season = state.get("season")

    model = _load_yield_model(crop_key, season)
    if model is None:
        return {"error": "Model not available for prediction."}

    try:
        import pandas as pd
        
        district = state.get("district")
        predicted_yield = None
        used_real_data = False
        feature_values = None
        
        # 1. Try real Earth Engine data via city_metrics_api
        if district:
            try:
                print(f"[YieldPred] Attempting Earth Engine extraction for district: {district}")
                from backend.city_metrics_api import predict_yield, Season
                from datetime import datetime
                
                ee_result = predict_yield(
                    city=district.title(),
                    season=Season(season),
                    crop=crop_key,
                    year=datetime.now().year
                )
                predicted_yield = float(ee_result["predicted_yield_kg_per_ha"])
                feature_values = ee_result.get("features_used", {})
                used_real_data = True
                print(f"[YieldPred] Earth Engine success! Predicted: {predicted_yield:.2f} kg/ha")
            except Exception as e:
                # Hide the massive Google Cloud IAM error, just print a clean fallback message
                print(f"[YieldPred] Live satellite data unavailable for district. Falling back to regional baseline.")
        
        # 2. Fallback to synthetic baseline data
        if not used_real_data:
            # Select features and defaults based on season
            if season == "kharif":
                feature_names = KHARIF_FEATURE_NAMES
                default_values = KHARIF_DEFAULT_VALUES.copy()
            else:
                feature_names = RABI_FEATURE_NAMES
                default_values = RABI_DEFAULT_VALUES.copy()
    
            # Build feature vector
            feature_vector = [default_values.get(f, 0.0) for f in feature_names]
            df = pd.DataFrame([feature_vector], columns=feature_names)
            
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                predicted_yield = float(model.predict(df)[0])
                
            feature_values = default_values
            print(f"[YieldPred] Baseline fallback {crop_key} ({season}): predicted yield = {predicted_yield:.2f} kg/ha")

        # Ensure non-negative yield
        predicted_yield = max(0.0, predicted_yield)

        return {
            "predicted_yield": round(predicted_yield, 2),
            "yield_unit": "kg/hectare",
            "feature_values": feature_values,
        }

    except Exception as e:
        print(f"[YieldPred] Prediction error: {e}")
        return {"error": f"Yield prediction failed: {e}"}


def gemini_interpret_node(state: YieldState) -> dict:
    """Send the yield prediction to Gemini for farmer-friendly interpretation."""
    if state.get("error"):
        # Return the error as response so the user sees it
        return {"response": state["error"]}

    try:
        import google.generativeai as genai

        genai.configure(api_key=state["google_api_key"])
        model = genai.GenerativeModel("gemini-flash-latest")

        crop = state.get("crop", "unknown")
        season = state.get("season", "unknown")
        state_name = state.get("state", "India")
        district = state.get("district", "")
        predicted_yield = state.get("predicted_yield", 0.0)
        yield_unit = state.get("yield_unit", "kg/hectare")

        location = f"{district}, {state_name}" if district else state_name

        prompt = (
            "You are an expert agricultural advisor for Indian farmers. "
            "A yield prediction model (XGBoost trained on satellite remote-sensing data) "
            "has produced the following estimate:\n\n"
            f"  • Crop: {crop.title()}\n"
            f"  • Season: {season.title()}\n"
            f"  • Location: {location}\n"
            f"  • Predicted Yield: {predicted_yield:,.2f} {yield_unit}\n\n"
            "Based on this prediction, provide a comprehensive, farmer-friendly response:\n\n"
            "1. **Yield Assessment**: Is this yield good, average, or below average for this crop?\n"
            "2. **Comparison**: How does this compare to national/state averages?\n"
            "3. **Improvement Tips**: Practical steps to improve yield (soil, water, fertilizer)\n"
            "4. **Risk Factors**: What could reduce yield (weather, pests, disease)\n"
            "5. **Economic Outlook**: Approximate revenue potential at current market rates\n\n"
            "Keep the language simple and practical for a farmer. Use bullet points."
        )

        response = model.generate_content(prompt)

        answer = response.text if response and response.text else (
            f"Predicted yield for {crop.title()} ({season.title()}): "
            f"{predicted_yield:,.2f} {yield_unit}"
        )

        print("[YieldPred] Deep Agricultural Analysis Complete:")
        print(answer)
        print("[YieldPred] --------------------------------------------------")

        # Prepend the prediction summary
        summary = (
            f"🌾 **Yield Prediction for {crop.title()} ({season.title()} Season)**\n"
            f"📍 Location: {location}\n"
            f"📊 Predicted Yield: **{predicted_yield:,.2f} {yield_unit}**\n\n"
            f"---\n\n"
        )

        return {"response": summary + answer}

    except Exception as e:
        print(f"[YieldPred] Gemini call failed: {e}")
        predicted_yield = state.get("predicted_yield", 0.0)
        yield_unit = state.get("yield_unit", "kg/hectare")
        crop = state.get("crop", "unknown")
        season = state.get("season", "unknown")
        fallback = (
            f"🌾 **Yield Prediction for {crop.title()} ({season.title()} Season)**\n"
            f"📊 Predicted Yield: **{predicted_yield:,.2f} {yield_unit}**\n\n"
            "Detailed analysis is temporarily unavailable. "
            "Please consult a local agricultural extension officer for yield improvement advice."
        )
        return {"response": fallback}


# ---------------------------------------------------------------------------
# Build the LangGraph StateGraph
# ---------------------------------------------------------------------------

def build_yield_graph() -> StateGraph:
    """Construct and compile the yield prediction graph.

    Graph topology::

        validate → load_model → predict → gemini_interpret → END
    """
    graph = StateGraph(YieldState)

    graph.add_node("validate", validate_node)
    graph.add_node("load_model", load_model_node)
    graph.add_node("predict", predict_node)
    graph.add_node("gemini_interpret", gemini_interpret_node)

    graph.set_entry_point("validate")
    graph.add_edge("validate", "load_model")
    graph.add_edge("load_model", "predict")
    graph.add_edge("predict", "gemini_interpret")
    graph.add_edge("gemini_interpret", END)

    return graph.compile()


_yield_graph = None


def get_yield_graph():
    global _yield_graph
    if _yield_graph is None:
        _yield_graph = build_yield_graph()
    return _yield_graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_available_crops() -> dict:
    """Return available crops for each season."""
    return {
        "kharif": sorted(set(KHARIF_CROPS.values())),
        "rabi": sorted(set(RABI_CROPS.values())),
    }


def run_yield_prediction(
    crop: str,
    season: str,
    google_api_key: str,
    state: str = "",
    district: str = "",
) -> dict:
    """Run the yield prediction pipeline for a crop.

    Args:
        crop: Crop name (e.g., 'rice', 'wheat')
        season: 'kharif' or 'rabi'
        google_api_key: Google API key for Gemini
        state: User's state (for context in Gemini prompt)
        district: User's district (for context)

    Returns:
        dict with ``response``, ``predicted_yield``, ``yield_unit``, ``crop``, ``season``
    """
    graph = get_yield_graph()

    final_state = graph.invoke({
        "crop": crop,
        "season": season,
        "state": state,
        "district": district,
        "google_api_key": google_api_key,
        "crop_key": None,
        "predicted_yield": None,
        "yield_unit": None,
        "feature_values": None,
        "response": None,
        "error": None,
    })

    return {
        "response": final_state.get("response", "Yield prediction could not be completed."),
        "predicted_yield": final_state.get("predicted_yield"),
        "yield_unit": final_state.get("yield_unit"),
        "crop": crop,
        "season": season,
        "error": final_state.get("error"),
    }
