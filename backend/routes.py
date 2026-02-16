from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.prompts import PromptTemplate
import re
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
from .database import (
    get_db_connection,
    insert_user,
    insert_conversation,
    fetch_conversations,
    fetch_user_by_id,
    fetch_user_conversation_summaries,
    fetch_conversation_by_id,
    fetch_user_by_email,
    fetch_user_by_phone,
    hash_password,
    verify_password,
)
from langchain.chains.question_answering import load_qa_chain
from langchain_community.vectorstores import FAISS
from typing import Optional
import base64
from deep_translator import GoogleTranslator
import requests
import re

load_dotenv()
router = APIRouter()

# Nearby mandis mapping for price comparison
NEARBY_MANDIS = {
    'agra': ['mathura', 'firozabad', 'mainpuri'],
    'lucknow': ['kanpur', 'barabanki', 'sitapur'],
    'ludhiana': ['jalandhar', 'moga', 'ferozepur'],
    'mumbai': ['pune', 'nashik', 'aurangabad'],
    'bangalore': ['mysore', 'mandya', 'tumkur'],
    'varanasi': ['allahabad', 'mirzapur', 'chandauli'],
    'kanpur': ['lucknow', 'unnao', 'fatehpur'],
    'pune': ['mumbai', 'satara', 'solapur'],
    'noida': ['ghaziabad', 'meerut', 'bulandshahr'],
    'gorakhpur': ['deoria', 'kushinagar', 'maharajganj'],
    'hubballi': ['dharwad', 'gadag', 'haveri'],
    'hoshiarpur': ['jalandhar', 'kapurthala', 'nawanshahr'],
    'patiala': ['ludhiana', 'sangrur', 'fatehgarh sahib']
}

# Load environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise HTTPException(status_code=500, detail="Google API key not found.")

DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY")

GLOBAL_INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "global_faiss_index")
_global_vector_store: Optional[FAISS] = None

class CreateProfileRequest(BaseModel):
    name: str
    email: str
    password: str
    district: Optional[str] = None
    crop: Optional[str] = None
    state: Optional[str] = None
    phone_number: str
    language: Optional[str] = None


class AskRequest(BaseModel):
    user_id: str
    question: str
    conversation_id: Optional[str] = None


class AnalyzeImageRequest(BaseModel):
    user_id: str
    image_base64: str
    mime_type: Optional[str] = "image/jpeg"
    question: Optional[str] = None
    conversation_id: Optional[str] = None

def _load_global_vector_store() -> FAISS:
    global _global_vector_store
    if _global_vector_store is None:
        if not os.path.isdir(GLOBAL_INDEX_DIR):
            raise HTTPException(
                status_code=500,
                detail="Global FAISS index not found. Run ingestion script first."
            )
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        try:
            _global_vector_store = FAISS.load_local(
                GLOBAL_INDEX_DIR,
                embeddings,
                allow_dangerous_deserialization=True,
            )
        except TypeError:
            # Older langchain-community versions don't support this kwarg
            _global_vector_store = FAISS.load_local(
                GLOBAL_INDEX_DIR,
                embeddings,
            )
    return _global_vector_store


def get_conversational_chain():
    prompt_template = (
        "You are Agri-Sahayak, a friendly and helpful AI advisor for Indian farmers. "
        "Your role is to provide practical, easy-to-understand agricultural advice in a conversational tone. "
        "Always be helpful, encouraging, and focus on actionable steps that farmers can implement.\n\n"
        "Guidelines for your responses:\n"
        "- Keep answers conversational and friendly, like talking to a friend\n"
        "- Focus on practical, actionable advice rather than technical details\n"
        "- If the context has specific information, use it but explain it simply\n"
        "- If you don't have specific information, provide general best practices\n"
        "- Always encourage farmers to consult local agricultural experts for specific conditions\n"
        "- Keep responses concise but informative (2-4 paragraphs maximum)\n"
        "- Use simple language that farmers can easily understand\n\n"
        "Context from agricultural guides: {context}\n"
        "Farmer's question: {question}\n\n"
        "Provide a helpful, conversational response:"
    )
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain


def _fallback_translate_via_llm(text: str, src: str, dest: str) -> str:
    """Fallback translation using the chat model to improve reliability."""
    try:
        src_name = "Hindi" if src.startswith("hi") else ("English" if src.startswith("en") else src)
        dest_name = "Hindi" if dest.startswith("hi") else ("English" if dest.startswith("en") else dest)
        model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)
        prompt = (
            f"Translate the following text from {src_name} to {dest_name}. "
            "Only return the translated text without quotes or comments.\n\n"
            f"Text: {text}"
        )
        resp = model.invoke(prompt)
        
        # Properly extract the translated text from the response
        if hasattr(resp, 'content'):
            out = resp.content
        elif hasattr(resp, 'output_text'):
            out = resp.output_text
        elif isinstance(resp, dict):
            out = resp.get("content") or resp.get("output_text") or ""
        else:
            out = str(resp)
        
        # Clean up the output - remove any extra formatting
        if isinstance(out, str):
            out = out.strip()
            # Remove any "content = " prefixes that might be present
            if out.startswith("content = "):
                out = out[10:].strip()
            # Remove quotes if present
            if (out.startswith("'") and out.endswith("'")) or (out.startswith('"') and out.endswith('"')):
                out = out[1:-1].strip()
        
        return (out or text).strip()
    except Exception as e:
        try:
            print(f"--- FALLBACK LLM TRANSLATION ERROR: {e} ---")
        except Exception:
            pass
        return text


def translate_text(text: str, src: str, dest: str) -> str:
    """Translate text from source language to destination language with fallback."""
    # Primary attempt: deep-translator
    translated = text
    try:
        result = GoogleTranslator(source=src, target=dest).translate(text)
        translated = (result or text).strip()
    except Exception as e:
        try:
            print(f"--- GOOGLETRANS ERROR: {e} ---")
        except Exception:
            pass
        translated = text

    # If translation failed or didn't change, try LLM fallback
    if not translated or translated.strip() == text.strip():
        translated = _fallback_translate_via_llm(text, src, dest)
    return translated


def _is_hindi_language(value: str) -> bool:
    """Robust Hindi language check to catch common variants."""
    l = (value or "").strip().lower()
    return l in {"hindi", "hi", "हिन्दी", "हिंदी"} or ("हिं" in l) or ("हिन्द" in l)


def _strip_markdown(text: str) -> str:
    """Remove common Markdown formatting like **bold**, *italics*, inline code, and star bullets.
    Keeps numbered lists. Also collapses excessive blank lines."""
    try:
        s = text or ""
        # Remove bold and italics markers
        s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
        s = re.sub(r"\*(.*?)\*", r"\1", s)
        # Remove inline/backtick code markers
        s = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", s)
        # Remove leading star bullets like "* "
        s = re.sub(r"(?m)^\s*\*\s+", "", s)
        # Normalize multiple blank lines to max 2
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()
    except Exception:
        return text

@router.post("/create_profile")
async def create_profile(req: CreateProfileRequest):
    # Enforce unique email
    existing = fetch_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Enforce unique phone number
    if req.phone_number:
        existing_phone = fetch_user_by_phone(req.phone_number)
        if existing_phone:
            raise HTTPException(status_code=409, detail="Phone number already registered")

    password_hash = hash_password(req.password)
    user_id = insert_user(
        name=req.name,
        district=req.district,
        crop=req.crop,
        state=req.state,
        email=req.email,
        password_hash=password_hash,
        phone_number=req.phone_number,
        language=req.language,
    )
    return {"user_id": user_id, "name": req.name}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(req: LoginRequest):
    user = fetch_user_by_email(req.email)
    if not user or not user.get("password_hash") or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": user["id"], "name": user["name"]}


class LogoutRequest(BaseModel):
    user_id: str


@router.post("/logout")
async def logout(_: LogoutRequest):
    # Stateless API; frontend should clear its local session storage
    return {"ok": True}


class StartConversationRequest(BaseModel):
    user_id: str
    category: str


@router.post("/conversations/start")
async def start_conversation(req: StartConversationRequest):
    user = fetch_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_language = (user.get("language") or "").strip().lower()
    is_hindi = _is_hindi_language(user_language)

    welcome_messages = {
        "farming": {
            "en": "Hello! How can I assist you with farming today?",
            "hi": "नमस्ते! मैं आज खेती-बाड़ी में आपकी क्या मदद कर सकता हूँ?",
        },
        "loans": {
            "en": "Hello! What would you like to know about agricultural loans?",
            "hi": "नमस्ते! आप कृषि लोन के बारे में क्या जानना चाहेंगे?",
        },
        "market_prices": {
            "en": "Hello! Which crop's market price are you interested in?",
            "hi": "नमस्ते! आप किस फसल का बाज़ार भाव जानना चाहते हैं?",
        },
        "weather": {
            "en": "Hello! How can I help you with the weather forecast?",
            "hi": "नमस्ते! मैं मौसम पूर्वानुमान में आपकी कैसे मदद कर सकता हूँ?",
        },
        "livestock": {
            "en": "Of course. I can help with questions about cattle, dairy, and other livestock. What would you like to know?",
            "hi": "ज़रूर, मैं मवेशियों, डेयरी और अन्य पशुधन के बारे में सवालों में मदद कर सकता हूँ। आप क्या जानना चाहेंगे?",
        },
    }

    category_key = req.category.lower()
    if category_key not in welcome_messages:
        raise HTTPException(status_code=400, detail="Invalid category")

    lang_key = "hi" if is_hindi else "en"
    welcome_message = welcome_messages[category_key][lang_key]

    conversation_id = str(os.urandom(16).hex())

    # Create a title for the conversation
    title = f"{req.category.replace('_', ' ').title()} Conversation"

    insert_conversation(
        user_id=req.user_id,
        question=f"Started conversation in category: {req.category}",
        answer=welcome_message,
        conversation_id=conversation_id,
        title=title,
    )

    return {"conversation_id": conversation_id, "welcome_message": welcome_message}



@router.get("/health/index/{user_id}")
async def health_check_index(user_id: str):
    """Return readiness of state-specific FAISS index for this user.

    Always 200 with { ready: bool, state: str | None, reason?: str }
    """
    user = fetch_user_by_id(user_id)
    if not user:
        return {"ready": False, "state": None, "reason": "User not found"}

    user_state = (user.get("state") or "").strip().lower().replace(" ", "_")
    if not user_state:
        return {"ready": False, "state": None, "reason": "User state not set"}

    index_dir = os.path.join(os.path.dirname(__file__), "faiss_indexes", f"{user_state}_faiss_index")
    if not os.path.isdir(index_dir):
        return {"ready": False, "state": user_state, "reason": f"Missing index dir {user_state}_faiss_index"}

    return {"ready": True, "state": user_state}


@router.post("/ask")
async def ask(req: AskRequest):
    # Validate user exists
    user = fetch_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Check user's language preference
    user_language = (user.get("language") or "").strip().lower()
    original_question = question
    processed_question = question

    # Check if this is a price/market query
    price_keywords = ['price', 'market', 'rate', 'mandi', 'cost', 'भाव', 'दाम', 'मंडी', 'कीमत']
    is_price_query = any(keyword in question.lower() for keyword in price_keywords)
    
    if is_price_query:
        # Handle market price comparison
        return await handle_price_query(req, user, question, original_question, user_language)
    
    # If user prefers Hindi, translate question to English for processing
    if _is_hindi_language(user_language):
        try:
            processed_question = translate_text(question, "hi", "en")
            print(f"Original Hindi question: {question}")
            print(f"Translated to English: {processed_question}")
        except Exception as e:
            print(f"Failed to translate Hindi question: {e}")
            # Continue with original question if translation fails

    # Determine user's state and load the matching FAISS index
    user_state = (user.get("state") or "").strip().lower().replace(" ", "_")
    if not user_state:
        raise HTTPException(status_code=400, detail="User state is not set. Please update profile.")

    index_dir = os.path.join(os.path.dirname(__file__), "faiss_indexes", f"{user_state}_faiss_index")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = None
    if os.path.isdir(index_dir):
        try:
            try:
                vector_store = FAISS.load_local(
                    index_dir,
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
            except TypeError:
                # Fallback for environments without the kwarg
                vector_store = FAISS.load_local(
                    index_dir,
                    embeddings,
                )
        except Exception as e:
            # Attempt fallback to global index
            try:
                vector_store = _load_global_vector_store()
            except Exception:
                # As a last resort, continue without vector store; the LLM will answer generally
                try:
                    print(f"Vector index load failed for state '{user_state}': {e}. Proceeding without retrieval.")
                except Exception:
                    pass
                vector_store = None
    else:
        # No state index dir; attempt global index
        try:
            vector_store = _load_global_vector_store()
        except Exception:
            # Proceed without retrieval
            try:
                print(f"Missing FAISS index dir for state '{user_state}'. Proceeding without retrieval.")
            except Exception:
                pass
            vector_store = None
    # Retrieve more documents and log scores to reduce disparity due to translation variance
    docs = []
    if vector_store is not None:
        try:
            docs_with_scores = vector_store.similarity_search_with_score(processed_question, k=4)
            try:
                print("--- RETRIEVAL DEBUG (processed_question) ---")
                print(processed_question)
                for i, (d, s) in enumerate(docs_with_scores[:3]):
                    preview = (d.page_content or "")[:180].replace("\n", " ")
                    print(f"Top{i+1} score={s:.4f} preview={preview}")
            except Exception:
                pass
            docs = [d for d, _ in docs_with_scores]
        except Exception:
            # Fallback if vector store backend doesn't support scores
            try:
                docs = vector_store.similarity_search(processed_question, k=4)
            except Exception as e:
                try:
                    print(f"Vector similarity search failed: {e}. Proceeding with empty docs.")
                except Exception:
                    pass
                docs = []

    answer = ""
    try:
        if docs:
            chain = get_conversational_chain()
            response = chain.invoke({"input_documents": docs, "question": processed_question})
            # Properly extract the answer text from LangChain response
            if hasattr(response, 'content'):
                answer = response.content
            elif hasattr(response, 'output_text'):
                answer = response.output_text
            elif isinstance(response, dict):
                answer = response.get("output_text") or response.get("content") or ""
            else:
                answer = str(response)
        else:
            # Fallback: no retrieval available, answer directly with LLM
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
            direct_prompt = (
                "You are Agri-Sahayak, a friendly and practical AI advisor for Indian farmers. "
                "Provide a concise, helpful answer using best practices even without external documents.\n\n"
                f"Farmer's question: {processed_question}\n\n"
                "Answer:"
            )
            resp = llm.invoke(direct_prompt)
            if hasattr(resp, 'content'):
                answer = resp.content or ""
            elif hasattr(resp, 'output_text'):
                answer = resp.output_text or ""
            else:
                answer = str(resp)
    except Exception as e:
        # Last-resort fallback to direct LLM if chain failed
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
            resp = llm.invoke(processed_question)
            if hasattr(resp, 'content'):
                answer = resp.content or ""
            elif hasattr(resp, 'output_text'):
                answer = resp.output_text or ""
            else:
                answer = str(resp)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Unable to generate answer: {e2}")
    
    # Clean up the answer - remove any extra formatting
    if isinstance(answer, str):
        answer = answer.strip()
        # Remove any "content = " prefixes that might be present
        if answer.startswith("content = "):
            answer = answer[10:].strip()
        # Remove quotes if present
        if (answer.startswith("'") and answer.endswith("'")) or (answer.startswith('"') and answer.endswith('"')):
            answer = answer[1:-1].strip()

    # If user prefers Hindi, translate the English answer back to Hindi
    if _is_hindi_language(user_language):
        # Log the raw English answer before translation
        try:
            print(f"--- RAW ENGLISH ANSWER TO BE TRANSLATED: {answer} ---")
        except Exception:
            # Ensure logging itself never breaks the request
            pass
        try:
            hindi_answer = translate_text(answer, "en", "hi")
            try:
                print(f"--- SUCCESSFULLY TRANSLATED TO HINDI: {hindi_answer} ---")
            except Exception:
                pass
            answer = hindi_answer
        except Exception as e:
            try:
                print(f"--- ERROR DURING HINDI TRANSLATION: {e} ---")
            except Exception:
                pass
            # Keep English answer if translation fails

    # Persist conversation with conversation_id
    conv_id = req.conversation_id or str(os.urandom(16).hex())
    insert_conversation(req.user_id, original_question, answer, conversation_id=conv_id)

    return {"answer": answer, "conversation_id": conv_id}


async def handle_price_query(req: AskRequest, user: dict, question: str, original_question: str, user_language: str):
    """Handle market price comparison queries"""
    try:
        # Extract user's district and crop from profile
        user_district = (user.get("district") or "").strip().lower()
        user_crop = (user.get("crop") or "").strip().lower()
        
        # Try to extract crop from question if not in profile
        if not user_crop:
            user_crop = extract_crop_from_question(question)
        
        if not user_district:
            return {"answer": "Please update your profile with your district to get market price comparisons.", "conversation_id": req.conversation_id or str(os.urandom(16).hex())}
        
        if not user_crop:
            return {"answer": "Please specify the crop name in your question or update your profile with your primary crop.", "conversation_id": req.conversation_id or str(os.urandom(16).hex())}
        # Normalize crop to canonical key (e.g., ragi/finger millet -> ragi, bajra/pearl millet -> millet)
        norm_crop = normalize_crop_name(user_crop).lower()

        # Fetch price data for user's district and nearby mandis
        price_data = await fetch_market_prices(user_district, norm_crop)
        
        if not price_data:
            return {"answer": f"Sorry, I couldn't find current market prices for {norm_crop} in {user_district}. Please try again later.", "conversation_id": req.conversation_id or str(os.urandom(16).hex())}
        
        # Format context for LLM
        context = format_price_context(price_data, norm_crop, user_district)
        
        # Generate AI response with price context
        answer = await generate_price_response(context, question, user_language)
        
        # Persist conversation
        conv_id = req.conversation_id or str(os.urandom(16).hex())
        insert_conversation(req.user_id, original_question, answer, conversation_id=conv_id)
        
        return {"answer": answer, "conversation_id": conv_id}
        
    except Exception as e:
        print(f"Error in price query handling: {e}")
        return {"answer": "I'm having trouble fetching market prices right now. Please try again later.", "conversation_id": req.conversation_id or str(os.urandom(16).hex())}


def extract_crop_from_question(question: str) -> str:
    """Extract crop name from user's question"""
    # Common crop names mapping
    crop_keywords = {
        'wheat': ['wheat', 'गेहूं'],
        'rice': ['rice', 'paddy', 'धान', 'चावल'],
        'sugarcane': ['sugarcane', 'गन्ना'],
        'cotton': ['cotton', 'कपास'],
        'maize': ['maize', 'corn', 'मक्का'],
        'soybean': ['soybean', 'सोयाबीन'],
        'mustard': ['mustard', 'सरसों'],
        'onion': ['onion', 'प्याज'],
        'potato': ['potato', 'आलू'],
        'tomato': ['tomato', 'टमाटर'],
        # Added ragi (finger millet) and millet (bajra/pearl millet) synonyms
        'ragi': ['ragi', 'finger millet', 'mandua', 'nachni', 'नाचनी', 'मंडुआ'],
        'millet': ['millet', 'millets', 'bajra', 'pearl millet', 'बाजरा']
    }
    
    question_lower = question.lower()
    for crop, keywords in crop_keywords.items():
        if any(keyword in question_lower for keyword in keywords):
            return crop
    
    return ""


def normalize_crop_name(crop: str) -> str:
    """Normalize user-provided crop names (Hindi/English) to canonical English keys.

    Supported keys (canonical): wheat, rice, sugarcane, cotton, maize, soybean, mustard, onion, potato, tomato
    """
    c = (crop or "").strip().lower()
    mapping = {
        # Wheat
        "wheat": "wheat", "गेहूं": "wheat", "गेहुँ": "wheat", "गेहूँ": "wheat",
        # Rice / Paddy
        "rice": "rice", "paddy": "rice", "धान": "rice", "चावल": "rice",
        # Sugarcane
        "sugarcane": "sugarcane", "गन्ना": "sugarcane",
        # Cotton
        "cotton": "cotton", "कपास": "cotton",
        # Maize / Corn
        "maize": "maize", "corn": "maize", "मक्का": "maize",
        # Soybean
        "soybean": "soybean", "सोयाबीन": "soybean",
        # Mustard
        "mustard": "mustard", "सरसों": "mustard",
        # Onion
        "onion": "onion", "प्याज": "onion",
        # Potato
        "potato": "potato", "आलू": "potato",
        # Tomato
        "tomato": "tomato", "टमाटर": "tomato",
        # Ragi / Finger millet
        "ragi": "ragi", "finger millet": "ragi", "mandua": "ragi", "nachni": "ragi", "नाचनी": "ragi", "मंडुआ": "ragi",
        # Millet (bajra / pearl millet)
        "millet": "millet", "millets": "millet", "bajra": "millet", "pearl millet": "millet", "बाजरा": "millet",
    }
    return mapping.get(c, c)


async def fetch_market_prices(user_district: str, crop: str) -> dict:
    """Fetch market prices from data.gov.in API for user's district and nearby mandis"""
    price_data = {}
    
    # List of districts to check (user's + nearby)
    districts_to_check = [user_district]
    if user_district in NEARBY_MANDIS:
        districts_to_check.extend(NEARBY_MANDIS[user_district])
    
    for district in districts_to_check:
        try:
            price = await fetch_price_for_district(district, crop)
            if price:
                price_data[district] = price
        except Exception as e:
            print(f"Failed to fetch price for {district}: {e}")
            continue
    
    return price_data


async def fetch_price_for_district(district: str, crop: str) -> Optional[dict]:
    """Fetch price data for a specific district and crop from data.gov.in API"""
    try:
        # Data.gov.in API endpoint for market prices
        # Note: This is a mock implementation - replace with actual API endpoint
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        
        params = {
            'api-key': DATA_GOV_API_KEY,
            'format': 'json',
            'filters[district]': district.title(),
            'filters[commodity]': crop.title(),
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('records') and len(data['records']) > 0:
                record = data['records'][0]
                return {
                    'district': district,
                    'crop': crop,
                    'price': record.get('modal_price', 'N/A'),
                    'unit': 'INR/quintal',
                    'date': record.get('arrival_date', 'N/A')
                }
        
        # Fallback: Generate mock data for demo purposes
        # Remove this in production and handle API errors appropriately
        import random
        base_prices = {
            'wheat': 2500, 'rice': 3000, 'sugarcane': 3500, 'cotton': 6000,
            'maize': 2200, 'soybean': 4500, 'mustard': 5000, 'onion': 1500,
            'potato': 1200, 'tomato': 2000,
            # Added canonical crops
            'ragi': 2800, 'millet': 2200
        }
        
        if crop in base_prices:
            # Add some variation for different districts
            variation = random.randint(-200, 300)
            mock_price = base_prices[crop] + variation
            return {
                'district': district,
                'crop': crop,
                'price': mock_price,
                'unit': 'INR/quintal',
                'date': 'Today'
            }
        
        return None
        
    except Exception as e:
        print(f"API call failed for {district}, {crop}: {e}")
        return None


def format_price_context(price_data: dict, crop: str, user_district: str) -> str:
    """Format price data into context string for LLM"""
    if not price_data:
        return f"No current market price data available for {crop}."
    
    context_parts = [f"Latest market prices for {crop.title()}:"]
    
    # Sort by price to show best deals first
    sorted_prices = sorted(
        [(district, data) for district, data in price_data.items()],
        key=lambda x: x[1]['price'] if isinstance(x[1]['price'], (int, float)) else 0,
        reverse=True
    )
    
    for district, data in sorted_prices:
        price = data['price']
        unit = data.get('unit', 'INR/quintal')
        if district == user_district:
            context_parts.append(f"• {district.title()} (Your district): ₹{price} {unit}")
        else:
            context_parts.append(f"• {district.title()}: ₹{price} {unit}")
    
    return "\n".join(context_parts)


async def generate_price_response(context: str, question: str, user_language: str) -> str:
    """Generate AI response using price context with fallback for quota issues"""
    try:
        # Create prompt for price comparison
        prompt_template = """
        You are an agricultural market expert helping farmers with price comparisons.
        
        Context: {context}
        
        Question: {question}
        
        Based on the provided market price data, provide a clear and structured response in this format:

        Market Price Analysis for [Crop Name]

        Current Prices:
        - [District 1]: ₹[Price]/quintal
        - [District 2]: ₹[Price]/quintal
        - [District 3]: ₹[Price]/quintal

        Best Market: [District with highest price] offers the best rate at ₹[Price]/quintal

        Recommendation: [2-3 sentences of practical advice about where to sell, considering transportation costs and market accessibility]

        Keep your response concise, well-formatted, and farmer-friendly. Use simple language and avoid any markdown formatting like ** or * symbols.
        """
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=GOOGLE_API_KEY
        )
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        response = llm.invoke(prompt.format(context=context, question=question))
        
        answer = ""
        if hasattr(response, 'content'):
            answer = response.content
        elif hasattr(response, 'output_text'):
            answer = response.output_text
        else:
            answer = str(response)
        
        # Translate to Hindi if needed
        if _is_hindi_language(user_language):
            try:
                answer = translate_text(answer, "en", "hi")
            except Exception as e:
                print(f"Translation failed: {e}")
        
        return answer.strip()
        
    except Exception as e:
        print(f"Error generating price response: {e}")
        
        # Fallback response when API quota is exhausted
        if "quota" in str(e).lower() or "429" in str(e):
            return generate_fallback_price_response(context, user_language)
        
        return "I'm having trouble analyzing the market prices right now. Please try again later."


def generate_fallback_price_response(context: str, user_language: str) -> str:
    """Generate a simple price comparison response without using AI when quota is exhausted"""
    try:
        # Parse the context to extract price information
        lines = context.split('\n')
        if len(lines) < 2:
            return "Price data is currently unavailable. Please try again later."
        
        crop_info = lines[0]  # "Latest market prices for Sugarcane:"
        crop_name = crop_info.replace("Latest market prices for ", "").replace(":", "")
        price_lines = [line for line in lines[1:] if line.strip().startswith('•')]
        
        if not price_lines:
            return "No price comparison data available at the moment."
        
        # Find highest and lowest prices
        prices = []
        for line in price_lines:
            try:
                # Extract price from line like "• Agra: ₹3500 INR/quintal"
                parts = line.split('₹')
                if len(parts) > 1:
                    price_part = parts[1].split()[0]
                    price = int(price_part.replace(',', ''))
                    district = line.split(':')[0].replace('•', '').strip()
                    prices.append((district, price))
            except:
                continue
        
        if not prices:
            return context + "\n\nPrice comparison data is available above."
        
        # Sort by price (highest first)
        prices.sort(key=lambda x: x[1], reverse=True)
        highest = prices[0]
        lowest = prices[-1]
        
        # Generate clean, structured response
        response_parts = [
            f"**Market Price Analysis for {crop_name}**",
            "",
            "**Current Prices:**"
        ]
        
        for district, price in prices:
            if "(Your district)" in district:
                clean_district = district.replace(" (Your district)", "")
                response_parts.append(f"- {clean_district} (Your district): ₹{price:,}/quintal")
            else:
                response_parts.append(f"- {district}: ₹{price:,}/quintal")
        
        response_parts.extend([
            "",
            f"**Best Market:** {highest[0].replace(' (Your district)', '')} offers the best rate at ₹{highest[1]:,}/quintal",
            "",
            f"**Recommendation:** Consider selling in {highest[0].replace(' (Your district)', '')} for the highest price. However, factor in transportation costs and market accessibility when making your final decision."
        ])
        
        response = "\n".join(response_parts)
        
        # Translate to Hindi if needed
        if _is_hindi_language(user_language):
            try:
                response = translate_text(response, "en", "hi")
            except Exception as e:
                print(f"Fallback translation failed: {e}")
        
        return response
        
    except Exception as e:
        print(f"Error in fallback response: {e}")
        return "Market price information is temporarily unavailable. Please try again later."


@router.post("/analyze_image")
async def analyze_image(req: AnalyzeImageRequest):
    """Analyze a crop image using a multimodal Gemini model and return a simple description."""
    user = fetch_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Debug: log incoming payload sizes (avoid printing image data itself)
        try:
            print(
                f"[analyze_image] user={req.user_id} mime={req.mime_type} b64_len={len(req.image_base64 or '')}"
            )
        except Exception:
            pass

        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        if not req.image_base64 or not isinstance(req.image_base64, str):
            raise HTTPException(status_code=400, detail="image_base64 is required")
        image_bytes = base64.b64decode(req.image_base64)
        try:
            print(f"[analyze_image] decoded_bytes={len(image_bytes)}")
        except Exception:
            pass
        # Basic sanity check: ensure we got non-trivial bytes
        if not image_bytes or len(image_bytes) < 100:
            raise HTTPException(status_code=400, detail="Invalid or too-small image payload. Please reattach a clear image.")
        base_prompt = (
            "You are an agricultural and veterinary assistant for farmers. "
            "The image may contain: crop plants (leaves, stems, fruits), soil, pests, farm equipment, or livestock animals (e.g., cow, buffalo, goat, sheep, poultry). "
            "Carefully analyze what is present and tailor your response accordingly. "
            "For plants: describe visible signs of disease, pests, or nutrient deficiency; if healthy, say so. "
            "For animals: describe visible signs (e.g., swelling, wounds, discharge, lesions, abnormal posture, body condition). "
            "Provide simple, actionable next steps and risk flags. Avoid making a definitive medical diagnosis; include a disclaimer that a licensed veterinarian/extension officer should be consulted for confirmation and treatment. "
            "Respond in clear plain text without any Markdown formatting (no **, *, #, or backticks). If you need a list, use simple numbered lines without bold."
        )
        # Detect user's preferred language
        user_language = (user.get("language") or "").strip().lower()
        is_hindi = _is_hindi_language(user_language)

        # If question is provided in Hindi, translate to English for the model
        extra = (req.question or "").strip()
        if is_hindi and extra:
            try:
                extra = translate_text(extra, "hi", "en")
            except Exception as _:
                pass

        full_prompt = base_prompt if not extra else f"{base_prompt}\nAdditional question/instructions: {extra}"
        result = model.generate_content([
            full_prompt,
            {"mime_type": req.mime_type or "image/jpeg", "data": image_bytes},
        ])
        text = (result.text or "").strip()
        if not text:
            text = "I could not extract a description from the image. Please try another photo with good lighting and focus."
        # Translate answer back to Hindi if needed
        if is_hindi:
            try:
                text = translate_text(text, "en", "hi")
            except Exception as _:
                pass
        # Ensure no Markdown symbols remain
        text = _strip_markdown(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {e}")

    conv_id = req.conversation_id or str(os.urandom(16).hex())
    question_text = (req.question or "Analyze crop image").strip() or "Analyze crop image"
    insert_conversation(req.user_id, question_text, text, conversation_id=conv_id)
    return {"answer": text, "conversation_id": conv_id}


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user}


@router.get("/market-price/{user_id}")
async def get_market_price(user_id: str):
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    district = (user.get("district") or "").strip().lower()
    crop = normalize_crop_name((user.get("crop") or "").strip()).lower()

    if not district or not crop:
        raise HTTPException(status_code=400, detail="User profile must have district and crop set for price history.")

    # This is a simplified version, the full logic will be in market-price-history
    price_data = await fetch_market_prices(district, crop)
    
    user_price = price_data.get(district, {})

    return {
        "crop": crop.title(),
        "district": district.title(),
        "price": user_price.get('price', 0),
        "history": [] # Placeholder
    }


@router.get("/market-price-history/{user_id}")
async def get_market_price_history(user_id: str):
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    district = (user.get("district") or "").strip().lower()
    # Normalize crop to canonical English key to support Hindi/English values
    crop = normalize_crop_name((user.get("crop") or "").strip()).lower()

    if not district or not crop:
        raise HTTPException(status_code=400, detail="User profile must have district and crop set for price history.")

    # Fetch prices for user's district and nearby mandis
    price_data = await fetch_market_prices(district, crop)

    # Mock data generation for 30-day price history for the primary district
    today = datetime.now()
    price_history = []
    base_price = price_data.get(district, {}).get('price') or (hash(f"{district}{crop}") % 500 + 2000)

    for i in range(30):
        date = today - timedelta(days=i)
        fluctuation = (hash(date.strftime('%Y-%m-%d')) % 200 - 100) / 10
        price = base_price + (base_price * 0.1 * fluctuation / 100) + (i * 0.5)
        price_history.append({"date": date.isoformat(), "price": round(price, 2)})

    price_history.reverse() # Oldest to newest

    # Format prices for nearby mandis
    nearby_prices = []
    # Add a mock trend for visual representation
    for i, (mandi, data) in enumerate(price_data.items()):
        nearby_prices.append({
            "district": mandi.title(),
            "price": data.get('price'),
            "is_user_district": mandi == district,
            "trend": "up" if i % 2 == 0 else "down"  # Mock trend based on index
        })

    # Sort by user district first, then alphabetically
    nearby_prices.sort(key=lambda x: (not x['is_user_district'], x['district']))

    return {
        "crop": crop.title(),
        "district": district.title(),
        "price_history": price_history,
        "nearby_prices": nearby_prices
    }

@router.get("/users/{user_id}/suggestions")
async def get_startup_suggestions(user_id: str):
    """Return 3-4 contextually relevant starter questions based on user's profile.

    This is heuristic and can be improved later; for now we branch on crop/state.
    """
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    state = (user.get("state") or "").strip()
    crop = (user.get("crop") or "").strip()
    lower_state = state.lower()
    lower_crop = crop.lower()

    suggestions: list[str] = []

    # Crop-specific suggestions
    if "wheat" in lower_crop:
        suggestions += [
            "What is the best fertilizer dose for wheat?",
            f"Show me current market prices for wheat in {state or 'my state'}",
            "How can I control rust or other common wheat diseases?",
        ]
    elif "rice" in lower_crop or "paddy" in lower_crop:
        suggestions += [
            "Recommend a nutrient schedule for rice",
            f"What is the recommended paddy variety for {state or 'my region'}?",
            "Best water management practices for transplanted paddy?",
        ]
    elif "cotton" in lower_crop:
        suggestions += [
            "How do I manage bollworm infestation?",
            f"What is the ideal sowing window for cotton in {state or 'my state'}?",
            "Suggest an IPM plan for cotton pests",
        ]
    elif "sugarcane" in lower_crop:
        suggestions += [
            "What is the recommended fertilizer schedule for sugarcane?",
            "How to improve ratoon crop yield in sugarcane?",
            f"Any subsidy schemes for sugarcane planters in {state or 'my state'}?",
        ]

    # State/market/credit generics
    suggestions += [
        f"Show me current market prices for {crop or 'my crop'} in {state or 'my state'}",
        "What are the best practices for soil health and testing?",
        "How can I get a loan or subsidy for new farm machinery?",
    ]

    # Deduplicate while preserving order
    seen = set()
    unique_suggestions: list[str] = []
    for s in suggestions:
        if s and s not in seen:
            unique_suggestions.append(s)
            seen.add(s)

    # Limit to 4
    return {"suggestions": unique_suggestions[:4]}

CROP_ACTIVITIES = {
    "wheat": {
        "august": ["Land preparation", "Seed treatment"],
        "september": ["Sowing", "First irrigation"],
        "october": ["Weed control", "Fertilizer application"],
        "november": ["Pest monitoring", "Second irrigation"],
        "december": ["Growth monitoring", "Disease prevention"],
        "january": ["Pre-harvest check", "Harvesting preparation"],
    },
    "rice": {
        "june": ["Nursery preparation", "Seed selection"],
        "july": ["Transplanting", "Water management"],
        "august": ["Weed management", "Nutrient application"],
        "september": ["Pest and disease control", "Mid-season irrigation"],
        "october": ["Flowering stage care", "Grain filling monitoring"],
        "november": ["Harvesting", "Post-harvest handling"],
    },
    "sugarcane": {
        "january": ["Planting", "Initial irrigation"],
        "february": ["Weed control", "Gap filling"],
        "march": ["Fertilizer application", "Earthing up"],
        "april": ["Propping and tying", "Pest management"],
        "may": ["Irrigation management", "Growth monitoring"],
        "june": ["Pre-monsoon care", "Disease scouting"],
        "july": ["Monsoon management", "Drainage check"],
        "august": ["Tying and propping", "Top dressing"],
        "september": ["Ripening monitoring", "Pest control"],
        "october": ["Harvesting preparation", "Seed cane selection"],
        "november": ["Harvesting", "Ratoon management"],
        "december": ["Harvesting continues", "Field cleaning"],
    },
    "cotton": {
        "may": ["Land preparation", "Sowing"],
        "june": ["Thinning", "Weed control"],
        "july": ["Fertilizer top dressing", "Pest scouting"],
        "august": ["Flowering and boll formation care", "Irrigation"],
        "september": ["Bollworm management", "Nutrient spray"],
        "october": ["Picking of cotton", "Quality management"],
        "november": ["Second picking", "Pest clean-up"],
    },
    "maize": {
        "june": ["Sowing", "Weed management"],
        "july": ["Nitrogen top dressing", "Irrigation"],
        "august": ["Pest control (stem borer)", "Tasseling and silking care"],
        "september": ["Grain filling", "Harvesting for fodder (if any)"],
        "october": ["Harvesting", "Drying and storage"],
    },
    "ragi": {
        "june": ["Nursery raising / direct sowing", "Seed treatment"],
        "july": ["Transplanting (if nursery)", "First weeding and gap filling"],
        "august": ["Top dressing of nitrogen", "Weed management"],
        "september": ["Pest and disease scouting", "Irrigation as needed"],
        "october": ["Ear head emergence care", "Foliar nutrition if required"],
        "november": ["Harvesting at physiological maturity", "Threshing and drying"],
    },
    "millet": {
        "june": ["Field preparation", "Sowing of bajra/pearl millet"],
        "july": ["Thinning and weeding", "Basal/Top fertilizer application"],
        "august": ["Pest monitoring (shoot fly/aphids)", "Moisture conservation"],
        "september": ["Ear emergence care", "Disease management (downy mildew)"],
        "october": ["Harvesting at 15–20% grain moisture", "Drying and storage"],
    },
}

@router.get("/crop_activities")
async def get_crop_activities(crop: str, month: str):
    """
    Returns a list of suggested crop activities for a given crop and month.
    """
    crop_lower = normalize_crop_name(crop).lower()
    month_lower = month.lower()
    
    if crop_lower not in CROP_ACTIVITIES:
        try:
            print(f"[DEBUG] crop_activities crop={crop} -> norm={crop_lower} month={month_lower} not-found")
        except Exception:
            pass
        return {"activities": []}
        
    activities = CROP_ACTIVITIES[crop_lower].get(month_lower, [])
    try:
        print(f"[DEBUG] crop_activities crop={crop_lower} month={month_lower} count={len(activities)}")
    except Exception:
        pass
    return {"activities": activities}

# @router.get("/get_conversation/")
# async def get_conversation(pdf_id: str):
#     if pdf_id not in conversations:
#         raise HTTPException(status_code=404, detail="No conversation history found for this PDF.")
    
#     return {"conversation": conversations[pdf_id]}

@router.get("/users/{user_id}/conversations")
async def list_user_conversations(user_id: str):
    summaries = fetch_user_conversation_summaries(user_id)
    # Ensure stable keys
    conversations = [
        {"conversation_id": s["conversation_id"], "title": s["title"], "timestamp": s["first_timestamp"]}
        for s in summaries
    ]
    # Ensure stable keys
    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation_by_id_route(conversation_id: str):
    rows = fetch_conversation_by_id(conversation_id)
    conversation = [
        {"question": row["question"], "answer": row["answer"], "timestamp": row["timestamp"]}
        for row in rows
    ]
    # Ensure stable keys
    return {"conversation": conversation}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
            return {"message": "Conversation deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


@router.patch("/conversations/{conversation_id}")
async def update_conversation_title(conversation_id: str, title_update: dict):
    """Update the title of a conversation (first question)."""
    new_title = title_update.get("title", "").strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Update the first question (title) for this conversation
            cursor.execute("""
                UPDATE conversations 
                SET question = ? 
                WHERE conversation_id = ? AND timestamp = (
                    SELECT MIN(timestamp) 
                    FROM conversations 
                    WHERE conversation_id = ?
                )
            """, (new_title, conversation_id, conversation_id))
            conn.commit()
            return {"message": "Conversation title updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update conversation title: {str(e)}")

# District coordinates for weather alerts
DISTRICT_COORDINATES = {
    'bangalore': (12.9716, 77.5946),
    'mysore': (12.2958, 76.6394),
    'mumbai': (19.0760, 72.8777),
    'pune': (18.5204, 73.8567),
    'ludhiana': (30.9010, 75.8573),
    'amritsar': (31.6340, 74.8723),
    'lucknow': (26.8467, 80.9462),
    'kanpur': (26.4499, 80.3319),
    'agra': (27.1767, 78.0081),
    'varanasi': (25.3176, 82.9739),
    'hoshiarpur': (31.5344, 75.9119),
    'patiala': (30.3398, 76.3869),
    'noida': (28.5355, 77.3910),
    'hubballi': (15.3647, 75.1240),
    'gorakhpur': (26.7606, 83.3732)
}

def fetch_weather_data_for_alerts(district):
    """Fetch weather data for alerts using OpenWeatherMap API"""
    if district not in DISTRICT_COORDINATES:
        return None
    
    lat, lon = DISTRICT_COORDINATES[district]
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "05b6e91c54291c719f5226c3ff40a9a5")
    
    try:
        # Current weather API
        current_url = f"https://api.openweathermap.org/data/2.5/weather"
        current_params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        
        current_response = requests.get(current_url, params=current_params, timeout=10)
        current_response.raise_for_status()
        current_data = current_response.json()
        
        # 5-day forecast API
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        
        forecast_response = requests.get(forecast_url, params=forecast_params, timeout=10)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        # Process forecast data to create daily summaries
        daily_temps = {}
        for item in forecast_data['list']:  # Process all available forecast items
            date = item['dt_txt'][:10]

            if date not in daily_temps:
                daily_temps[date] = {
                    'temps': [],
                    'humidity': [],
                    'wind_speed': [],
                    'rain': 0,
                    'weathers': []  # collect weather snapshots to choose a representative one
                }

            daily_temps[date]['temps'].append(item['main']['temp'])
            daily_temps[date]['humidity'].append(item['main']['humidity'])
            daily_temps[date]['wind_speed'].append(item['wind']['speed'])
            if item.get('weather'):
                # store first weather object of this 3h slot
                daily_temps[date]['weathers'].append(item['weather'][0])
            if 'rain' in item:
                daily_temps[date]['rain'] += item['rain'].get('3h', 0)

        # Create daily summaries
        daily_data = []
        for date, data in daily_temps.items():  # Process all available days
            representative_weather = []
            if data['weathers']:
                # pick the most frequent main condition, fallback to first
                try:
                    from collections import Counter
                    most_common_main = Counter([w.get('main') for w in data['weathers'] if w.get('main')]).most_common(1)
                    if most_common_main:
                        # find first weather object matching that main
                        chosen = next((w for w in data['weathers'] if w.get('main') == most_common_main[0][0]), data['weathers'][0])
                        representative_weather = [
                            {
                                'main': chosen.get('main'),
                                'description': chosen.get('description'),
                                'icon': chosen.get('icon')
                            }
                        ]
                    else:
                        representative_weather = [data['weathers'][0]]
                except Exception:
                    representative_weather = [data['weathers'][0]]

            daily_summary = {
                'date': date,
                'temp': {
                    'max': max(data['temps']) if data['temps'] else None,
                    'min': min(data['temps']) if data['temps'] else None,
                },
                'humidity': (sum(data['humidity']) / len(data['humidity'])) if data['humidity'] else None,
                'wind_speed': max(data['wind_speed']) if data['wind_speed'] else None,
                # OpenWeather forecast provides "pop" (probability of precipitation) per 3h item; we approximated using rain volume.
                # Expose a coarse pop derived from rain presence.
                'pop': 1.0 if data['rain'] > 0 else 0.0,
                'weather': representative_weather,
            }
            daily_data.append(daily_summary)
        
        return {
            'current': {
                'temp': current_data['main']['temp'],
                'humidity': current_data['main']['humidity'],
                'wind_speed': current_data['wind']['speed'],
                'weather': current_data['weather']
            },
            'daily': daily_data,
            'hourly': forecast_data.get('list', [])
        }
        
    except Exception as e:
        return None

def analyze_weather_for_alerts(weather_data, district):
    """Analyze weather data and return alerts"""
    if not weather_data or 'daily' not in weather_data:
        return []
    
    alerts = []
    
    for day_idx in range(min(2, len(weather_data['daily']))):
        day_data = weather_data['daily'][day_idx]
        
        max_temp = day_data['temp']['max']
        min_temp = day_data['temp']['min']
        rain_mm = day_data.get('rain', {}).get('1h', 0) * 24
        wind_speed = day_data['wind_speed'] * 3.6  # Convert m/s to km/h
        humidity = day_data['humidity']
        
        day_name = "today" if day_idx == 0 else "tomorrow"
        
        # Alert conditions
        if max_temp > 40:
            alerts.append({
                'type': 'heatwave',
                'title': 'Heatwave Warning',
                'message': f"Temperature expected to reach {max_temp:.1f}°C {day_name}. Ensure adequate irrigation and provide shade for livestock.",
                'severity': 'high',
                'icon': '🌡️'
            })
        
        if rain_mm > 50:
            alerts.append({
                'type': 'heavy_rain',
                'title': 'Heavy Rainfall Alert',
                'message': f"{rain_mm:.1f}mm rain expected {day_name}. Protect crops from waterlogging and ensure proper drainage.",
                'severity': 'high',
                'icon': '🌧️'
            })
        
        if wind_speed > 30:
            alerts.append({
                'type': 'high_wind',
                'title': 'High Wind Warning',
                'message': f"Wind speeds up to {wind_speed:.1f} km/h expected {day_name}. Secure farm structures and protect young plants.",
                'severity': 'medium',
                'icon': '💨'
            })
        
        if min_temp < 5:
            alerts.append({
                'type': 'frost',
                'title': 'Frost Warning',
                'message': f"Temperature may drop to {min_temp:.1f}°C {day_name}. Protect sensitive crops from frost damage.",
                'severity': 'high',
                'icon': '❄️'
            })
        
        if humidity > 90 and max_temp > 30:
            alerts.append({
                'type': 'disease_risk',
                'title': 'Disease Risk Alert',
                'message': f"High humidity ({humidity}%) and temperature ({max_temp:.1f}°C) {day_name} may increase fungal disease risk. Monitor crops closely.",
                'severity': 'medium',
                'icon': '🦠'
            })
    
    return alerts

@router.get("/weather-alerts/{user_id}")
async def get_weather_alerts(user_id: str):
    """Get weather alerts for a specific user based on their district"""
    try:
        # Fetch user details
        user = fetch_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_district = user.get("district", "").lower().strip()
        if not user_district:
            return {"alerts": [], "district": None}
        
        # Fetch weather data for user's district
        weather_data = fetch_weather_data_for_alerts(user_district)
        if not weather_data:
            return {"alerts": [], "district": user_district, "error": "Weather data unavailable"}
        
        # Analyze weather for alerts
        alerts = analyze_weather_for_alerts(weather_data, user_district)
        
        # Add timestamp and district info
        for alert in alerts:
            alert['timestamp'] = datetime.now().isoformat()
            alert['district'] = user_district.title()
        
        return {
            "alerts": alerts,
            "district": user_district.title(),
            "total_alerts": len(alerts),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather alerts: {str(e)}")


# New: expose 5-day weather forecast for user's district
@router.get("/weather-forecast/{user_id}")
async def get_weather_forecast(user_id: str):
    """Return compact 5-day forecast for the user's district.

    Shape: { district, current, daily: [{ date, temp_max, temp_min, humidity, weather: [{main, description, icon}] }] }
    """
    try:
        user = fetch_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_district = (user.get("district") or "").strip().lower()
        if not user_district:
            return {"district": None, "daily": []}

        weather_data = fetch_weather_data_for_alerts(user_district)
        if not weather_data:
            return {"district": user_district, "daily": [], "error": "Weather data unavailable"}

        # Normalize output
        daily = []
        for d in weather_data.get("daily", []):
            daily.append({
                "date": d.get("date"),
                "temp_max": d.get("temp", {}).get("max"),
                "temp_min": d.get("temp", {}).get("min"),
                "humidity": d.get("humidity"),
                "pop": d.get("pop"),
                "weather": d.get("weather", []),
            })

        return {
            "district": user_district,
            "current": weather_data.get("current", {}),
            "daily": daily,
            "hourly": weather_data.get("hourly", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather forecast: {str(e)}")


# New: expose market prices for user's crop and district
@router.get("/market-prices/{user_id}")
async def get_market_prices(user_id: str):
    """Return market prices for the user's primary crop in their district and nearby mandis.

    Shape: { crop, district, prices: { [district]: { price, unit, date } } }
    """
    try:
        user = fetch_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_district = (user.get("district") or "").strip().lower()
        user_crop = normalize_crop_name((user.get("crop") or "").strip())
        user_crop = (user_crop or "").lower()
        if not user_district or not user_crop:
            return {"district": user_district or None, "crop": user_crop or None, "prices": {}}

        prices = await fetch_market_prices(user_district, user_crop)
        try:
            print(f"[DEBUG] market-prices user_id={user_id} district={user_district} crop={user_crop} count={len(prices)}")
        except Exception:
            pass
        return {"district": user_district, "crop": user_crop, "prices": prices or {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market prices: {str(e)}")
