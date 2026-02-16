#importing libraries
from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel
from fastapi.responses import Response
from typing import Optional
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from .database import (
    fetch_user_by_phone,
    fetch_user_by_id,
    insert_conversation,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain_community.vectorstores import FAISS
from deep_translator import GoogleTranslator
import asyncio
import inspect
import os
import traceback
from dotenv import load_dotenv

router = APIRouter()
load_dotenv()  # Ensure .env is loaded even if import order changes


def _load_state_index_dir(user_state: str) -> str:
    user_state_key = (user_state or "").strip().lower().replace(" ", "_")
    base = os.path.dirname(__file__)
    index_dir = os.path.join(base, "faiss_indexes", f"{user_state_key}_faiss_index")
    if not os.path.isdir(index_dir):
        raise RuntimeError(f"Missing FAISS index for state '{user_state_key}'")
    return index_dir


def _fallback_translate_via_llm(text: str, src: str, dest: str) -> str:
    try:
        src_name = "Hindi" if src.startswith("hi") else ("English" if src.startswith("en") else src)
        dest_name = "Hindi" if dest.startswith("hi") else ("English" if dest.startswith("en") else dest)
        model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)
        prompt = (
            f"Translate the following text from {src_name} to {dest_name}. Only return the translated text.\n\n"
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
        print(f"FALLBACK LLM TRANSLATION ERROR: {e}")
        return text


async def translate_text_async(text: str, src: str, dest: str) -> str:
    """Translate text using deep-translator with LLM fallback."""
    out = None
    try:
        result = GoogleTranslator(source=src, target=dest).translate(text)
        # deep-translator is synchronous, no need for await
        out = result
    except Exception as e:
        try:
            print(f"Translation error: {e}")
        except Exception:
            pass
        out = None

    if not out or out.strip() == text.strip():
        out = _fallback_translate_via_llm(text, src, dest)
    return out.strip()


def _is_hindi_language(value: str) -> bool:
    l = (value or "").strip().lower()
    return l in {"hindi", "hi", "हिन्दी", "हिंदी"} or ("हिं" in l) or ("हिन्द" in l)


def _answer_with_rag(user_id: str, question: str) -> str:
    user = fetch_user_by_id(user_id)
    if not user:
        return "We could not find your profile. Please register on the website first."

    user_state = (user.get("state") or "").strip()
    if not user_state:
        return "Your state is not set in profile. Please update it on the website."

    # Validate Google API key presence early
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        print("[VOICE][ERROR] GOOGLE_API_KEY is not set in environment.")
        raise RuntimeError("GOOGLE_API_KEY not configured")

    try:
        index_dir = _load_state_index_dir(user_state)
    except Exception as e:
        print(f"[VOICE][ERROR] Could not load FAISS index for state='{user_state}': {e}")
        raise

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        # Note: Older langchain-community versions (<0.0.15) don't support allow_dangerous_deserialization
        vector_store = FAISS.load_local(index_dir, embeddings)
        docs = vector_store.similarity_search(question, k=3)
    except Exception as e:
        print(f"[VOICE][ERROR] Vector store init/search failed: {e}")
        traceback.print_exc()
        raise

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
    try:
        response = chain.invoke({"input_documents": docs, "question": question})
    except Exception as e:
        print(f"[VOICE][ERROR] QA chain invocation failed: {e}")
        traceback.print_exc()
        raise
    
    # Properly extract the answer text from LangChain response
    if hasattr(response, 'content'):
        answer = response.content
    elif hasattr(response, 'output_text'):
        answer = response.output_text
    elif isinstance(response, dict):
        answer = response.get("output_text") or response.get("content") or ""
    else:
        answer = str(response)
    
    # Clean up the answer - remove any extra formatting
    if isinstance(answer, str):
        answer = answer.strip()
        # Remove any "content = " prefixes that might be present
        if answer.startswith("content = "):
            answer = answer[10:].strip()
        # Remove quotes if present
        if (answer.startswith("'") and answer.endswith("'")) or (answer.startswith('"') and answer.endswith('"')):
            answer = answer[1:-1].strip()
    
    insert_conversation(user_id, question, answer, conversation_id=None)
    return answer or "I could not find an answer from the documents."


class CallInitiateRequest(BaseModel):
    user_id: str


@router.post("/call/initiate")
async def call_initiate(req: CallInitiateRequest):
    """Initiate an outbound call to the user's registered phone number.

    Expects environment variables:
    - TWILIO_ACCOUNT_SID
    - TWILIO_API_KEY_SID
    - TWILIO_API_KEY_SECRET
    - TWILIO_PHONE_NUMBER (E.164 format)
    - PUBLIC_BASE_URL (publicly reachable base URL exposing this FastAPI app)
    """
    user = fetch_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    to_number = (user.get("phone_number") or "").strip()
    if not to_number:
        raise HTTPException(status_code=400, detail="User does not have a registered phone number")

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    api_key_sid = os.getenv("TWILIO_API_KEY_SID")
    api_key_secret = os.getenv("TWILIO_API_KEY_SECRET")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    public_base_url = os.getenv("PUBLIC_BASE_URL")

    # Validate minimal required fields
    missing = []
    if not account_sid:
        missing.append("TWILIO_ACCOUNT_SID")
    if not from_number:
        missing.append("TWILIO_PHONE_NUMBER")
    if not public_base_url:
        missing.append("PUBLIC_BASE_URL")

    # Must have either API Key SID+Secret OR Auth Token
    has_api_key = bool(api_key_sid and api_key_secret)
    has_auth_token = bool(auth_token)
    if not (has_api_key or has_auth_token):
        missing.append("TWILIO_API_KEY_SID/TWILIO_API_KEY_SECRET or TWILIO_AUTH_TOKEN")

    if missing:
        raise HTTPException(status_code=500, detail=f"Missing configuration: {', '.join(missing)}")

    # Derive final webhook URL
    base = public_base_url.strip()
    if "/voice/incoming" in base:
        webhook_url = base
    else:
        webhook_url = f"{base.rstrip('/')}/voice/incoming"

    try:
        # Prefer API Key auth, fallback to Account SID + Auth Token
        if has_api_key:
            client = Client(api_key_sid, api_key_secret, account_sid)
        else:
            client = Client(account_sid, auth_token)
        try:
            masked_to = to_number[:-4].replace("+", "+*") + "****" if len(to_number) > 4 else to_number
            masked_from = (from_number[:-4] + "****") if from_number and len(from_number) > 4 else from_number
            print(f"[VOICE] Initiating call: to={masked_to}, from={masked_from}, webhook={webhook_url}")
        except Exception:
            pass
        call = client.calls.create(
            url=webhook_url,
            to=to_number,
            from_=from_number,
        )
        return {"sid": call.sid, "to": to_number}
    except Exception as e:
        try:
            print(f"[VOICE][ERROR] Failed to initiate call: {e}")
            traceback.print_exc()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {e}")


@router.post("/voice/incoming")
async def voice_incoming(
    Caller: Optional[str] = Form(default=None),
    From_: Optional[str] = Form(default=None, alias="From"),
    To: Optional[str] = Form(default=None, alias="To"),
):
    """Entry point for incoming calls. Detect user's language and set TwiML attrs."""
    vr = VoiceResponse()
    caller = (Caller or "").strip()
    from_num = (From_ or "").strip()
    to_num = (To or "").strip()

    # Determine the actual user phone number
    # Inbound customer calls: user's number is From_
    # Outbound calls we initiated: user's number is To
    user = None
    probe_numbers = [n for n in [caller, from_num, to_num] if n]
    for num in probe_numbers:
        user = fetch_user_by_phone(num)
        if user:
            break
    is_hindi = _is_hindi_language(user.get("language")) if user else False

    if is_hindi:
        vr.say("अग्री सहायक में आपका स्वागत है। कृपया अपना प्रश्न अभी बोलें।", language="hi-IN")
        gather = Gather(
            input="speech",
            action="/voice/process",
            method="POST",
            timeout=5,
            language="hi-IN",
            speech_model="experimental_utterances",
        )
    else:
        vr.say("Welcome to Agri Sahayak. Please state your question now.")
        gather = Gather(input="speech", action="/voice/process", method="POST", timeout=5)
    vr.append(gather)
    return Response(content=str(vr), media_type="application/xml")


@router.post("/voice/process")
async def voice_process(
    Caller: Optional[str] = Form(default=None),
    From_: Optional[str] = Form(default=None, alias="From"),
    To: Optional[str] = Form(default=None, alias="To"),
    SpeechResult: Optional[str] = Form(default=None),
    CallSid: Optional[str] = Form(default=None),
):
    vr = VoiceResponse()

    # Normalize
    caller = (Caller or "").strip()
    from_num = (From_ or "").strip()
    to_num = (To or "").strip()
    speech = (SpeechResult or "").strip()
    # Determine actual user by trying all provided numbers
    user = None
    for num in [n for n in [caller, from_num, to_num] if n]:
        user = fetch_user_by_phone(num)
        if user:
            break
    is_hindi = _is_hindi_language(user.get("language")) if user else False

    # Stop words or empty
    if not speech or speech.lower() in {"goodbye", "bye", "quit", "exit"}:
        if is_hindi:
            vr.say("कॉल करने के लिए धन्यवाद। अलविदा!", language="hi-IN")
        else:
            vr.say("Thank you for calling. Goodbye!")
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    # Lookup user by phone
    if not user:
        # Default to English if user not found
        vr.say(
            "We could not find your phone number in our system. Please register on the website first."
        )
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    # Translate-Process-Translate for Hindi
    processed_question = speech
    if is_hindi:
        try:
            processed_question = await translate_text_async(speech, "hi", "en")
            try:
                print(f"Original Hindi question: {speech}")
                print(f"Translated to English: {processed_question}")
            except Exception:
                pass
        except Exception as e:
            try:
                print(f"Failed to translate Hindi question: {e}")
            except Exception:
                pass
            processed_question = speech

    # Run RAG using processed question (English for Hindi users)
    try:
        answer = _answer_with_rag(user_id=user["id"], question=processed_question)
    except Exception as e:
        try:
            uid = user.get("id") if user else None
            print(f"[VOICE][ERROR] RAG failure for user_id={uid}: {e}")
            traceback.print_exc()
        except Exception:
            pass
        answer = "We faced a technical issue answering your question. Please try again later."

    # If Hindi user, translate answer back to Hindi
    if is_hindi:
        try:
            english_answer = answer
            try:
                print(f"--- RAW ENGLISH ANSWER TO BE TRANSLATED (VOICE): {english_answer} ---")
            except Exception:
                pass
            answer_hi = await translate_text_async(english_answer, "en", "hi")
            try:
                print(f"--- SUCCESSFULLY TRANSLATED TO HINDI (VOICE): {answer_hi} ---")
            except Exception:
                pass
            answer = answer_hi
        except Exception as e:
            try:
                print(f"--- ERROR DURING HINDI TRANSLATION (VOICE): {e} ---")
            except Exception:
                pass

    # Respond and loop
    if is_hindi:
        # answer is already Hindi via translate-process-translate, speak with Hindi voice
        vr.say(answer, language="hi-IN")
        vr.say("क्या आपके पास कोई और प्रश्न है?", language="hi-IN")
        gather = Gather(
            input="speech",
            action="/voice/process",
            method="POST",
            timeout=5,
            language="hi-IN",
            speech_model="experimental_utterances",
        )
    else:
        vr.say(answer)
        vr.say("Do you have another question?")
        gather = Gather(input="speech", action="/voice/process", method="POST", timeout=5)
    vr.append(gather)
    return Response(content=str(vr), media_type="application/xml")


