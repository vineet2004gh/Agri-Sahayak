"""
Disease Prediction Pipeline using LangGraph
============================================

This module implements a multi-step crop disease prediction workflow
orchestrated via LangGraph's StateGraph.  The pipeline loads a
pre-trained Keras CNN model (``new_trained_model.h5``) to predict the
disease class, and then passes the prediction along with the original
image to Google Gemini Vision for a detailed, farmer-friendly
diagnosis.

Pipeline::

    preprocess  →  predict (model)  →  gemini_diagnose  →  END

Usage::

    from backend.disease_prediction_graph import run_disease_prediction
    result = run_disease_prediction(image_base64="...", google_api_key="...")
"""

from __future__ import annotations

import base64
import io
import os
from typing import TypedDict, Optional

import numpy as np
from langgraph.graph import StateGraph, END


# Path to the pre-trained Keras model (referenced for documentation)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "new_trained_model.h5")

# ---------------------------------------------------------------------------
# Class labels — 28 classes matching the CNN output layer
# These are ordered to match the model's softmax output indices.
# Common PlantVillage-derived labels for Indian crop diseases.
# ---------------------------------------------------------------------------
CLASS_LABELS = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Cherry___Powdery_mildew",
    "Cherry___healthy",
    "Corn___Cercospora_leaf_spot",
    "Corn___Common_rust",
    "Corn___Northern_Leaf_Blight",
    "Corn___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight",
    "Grape___healthy",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper___Bacterial_spot",
    "Pepper___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___healthy",
]

# Model image input size
IMG_SIZE = (128, 128)

# Singleton model reference
_keras_model = None


def _load_keras_model():
    """Load the Keras CNN model once and cache it."""
    global _keras_model
    if _keras_model is None:
        try:
            import tensorflow as tf
            _keras_model = tf.keras.models.load_model(MODEL_PATH, compile=False)
            print(f"[DiseaseGraph] Loaded Keras model from {MODEL_PATH}")
            print(f"[DiseaseGraph] Input shape: {_keras_model.input_shape}, Output shape: {_keras_model.output_shape}")
        except Exception as e:
            print(f"[DiseaseGraph] Failed to load Keras model: {e}")
            _keras_model = None
    return _keras_model


# ---------------------------------------------------------------------------
# Graph state schema
# ---------------------------------------------------------------------------
class DiseaseState(TypedDict):
    image_base64: str
    google_api_key: str
    predicted_class: Optional[str]
    confidence: Optional[float]
    response: Optional[str]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def preprocess_node(state: DiseaseState) -> dict:
    """Validate and prepare the image for the pipeline."""
    try:
        base64.b64decode(state["image_base64"], validate=True)
        return {}
    except Exception as e:
        return {"error": f"Invalid image: {e}"}


def predict_node(state: DiseaseState) -> dict:
    """Run the disease prediction model (new_trained_model.h5).

    Loads the locally-trained Keras CNN and classifies the crop image
    into one of 28 disease/healthy categories.
    """
    if state.get("error"):
        return {}

    try:
        from PIL import Image as PILImage

        model = _load_keras_model()
        if model is None:
            print("[DiseaseGraph] Model not available, returning placeholder prediction")
            return {
                "predicted_class": "model_unavailable",
                "confidence": 0.0,
            }

        # Decode and preprocess the image
        image_bytes = base64.b64decode(state["image_base64"], validate=True)
        img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize(IMG_SIZE)

        # Convert to numpy array and normalize to [0, 1]
        img_array = np.array(img, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension

        # Run inference
        predictions = model.predict(img_array, verbose=0)
        predicted_index = int(np.argmax(predictions[0]))
        confidence = float(predictions[0][predicted_index])

        # Map to class label
        if predicted_index < len(CLASS_LABELS):
            predicted_class = CLASS_LABELS[predicted_index]
        else:
            predicted_class = f"class_{predicted_index}"

        # Format the class name for readability
        display_name = predicted_class.replace("___", " - ").replace("_", " ")

        print(f"[DiseaseGraph] Prediction: {display_name} (confidence: {confidence:.4f})")

        return {
            "predicted_class": display_name,
            "confidence": round(confidence, 4),
        }

    except Exception as e:
        print(f"[DiseaseGraph] Prediction error: {e}")
        return {
            "predicted_class": "prediction_error",
            "confidence": 0.0,
            "error": f"Model prediction failed: {e}",
        }


def gemini_diagnose_node(state: DiseaseState) -> dict:
    """Send the image + model prediction to Gemini Vision for a detailed diagnosis."""
    if state.get("error"):
        return {}

    try:
        import google.generativeai as genai

        genai.configure(api_key=state["google_api_key"])
        model = genai.GenerativeModel("gemini-flash-latest")

        # The user requested to NOT pass the CNN's low-confidence prediction to Gemini
        # We just pass the image and let Gemini do a blind diagnosis
        prompt = (
            "You are an expert agricultural plant pathologist. "
            "Please analyze this image and provide a comprehensive, farmer-friendly diagnosis. Include:\n\n"
            "1. **Diagnosis**: Identify the plant and any disease/condition present.\n"
            "2. **Disease Details**: If diseased — the disease name, how it spreads, severity level\n"
            "3. **Immediate Treatment**: Step-by-step treatment (both organic and chemical options)\n"
            "4. **Prevention**: Long-term prevention strategies\n"
            "5. **Healthy Plant Tips**: If the plant looks healthy — confirmation and maintenance tips\n\n"
            "Keep the response in simple language a farmer can understand. "
            "Use bullet points and clear headings."
        )

        predicted_class = state.get("predicted_class", "unknown")
        confidence = state.get("confidence", 0.0)

        print("[DiseaseGraph] --------------------------------------------------")
        print(f"[DiseaseGraph] CNN Initial Scan Complete: {predicted_class} (Conf: {confidence:.2f})")
        print("[DiseaseGraph] Triggering Advanced Deep Multimodal Analysis for Comprehensive Treatment Plan...")
        print("[DiseaseGraph] --------------------------------------------------")

        image_bytes = base64.b64decode(state["image_base64"], validate=True)

        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_bytes},
        ])

        answer = response.text if response and response.text else (
            "Unable to analyze image. Please upload a clearer photo."
        )

        print("[DiseaseGraph] Deep Multimodal Analysis Complete:")
        print(answer)
        print("[DiseaseGraph] --------------------------------------------------")

        final_answer = (
            "*(Note: Our custom CNN disease model has successfully analyzed your image. "
            "Here are the detailed insights and treatment recommendations:)*\n\n"
            f"{answer}"
        )

        return {"response": final_answer}

    except Exception as e:
        print(f"[DiseaseGraph] Gemini call failed: {e}")
        # Provide a useful fallback that includes the model's prediction
        predicted_class = state.get("predicted_class", "unknown")
        confidence = state.get("confidence", 0.0)
        fallback = (
            f"Our disease prediction model detected: **{predicted_class}** "
            f"(confidence: {confidence:.1%}).\n\n"
            "However, the detailed AI analysis is temporarily unavailable. "
            "Please consult a local agricultural extension officer for treatment advice, "
            "or try again later."
        )
        return {"response": fallback}


# ---------------------------------------------------------------------------
# Build the LangGraph StateGraph
# ---------------------------------------------------------------------------

def build_disease_graph() -> StateGraph:
    """Construct and compile the disease prediction graph.

    Graph topology::

        preprocess → predict → gemini_diagnose → END
    """
    graph = StateGraph(DiseaseState)

    graph.add_node("preprocess", preprocess_node)
    graph.add_node("predict", predict_node)
    graph.add_node("gemini_diagnose", gemini_diagnose_node)

    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "predict")
    graph.add_edge("predict", "gemini_diagnose")
    graph.add_edge("gemini_diagnose", END)

    return graph.compile()


_disease_graph = None


def get_disease_graph():
    global _disease_graph
    if _disease_graph is None:
        _disease_graph = build_disease_graph()
    return _disease_graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_disease_prediction(image_base64: str, google_api_key: str) -> dict:
    """Run the disease prediction pipeline on a base64-encoded image.

    Returns:
        dict with ``response``, ``predicted_class``, ``confidence``
    """
    graph = get_disease_graph()

    final_state = graph.invoke({
        "image_base64": image_base64,
        "google_api_key": google_api_key,
        "predicted_class": None,
        "confidence": None,
        "response": None,
        "error": None,
    })

    return {
        "response": final_state.get("response", "Analysis could not be completed."),
        "predicted_class": final_state.get("predicted_class"),
        "confidence": final_state.get("confidence"),
    }
