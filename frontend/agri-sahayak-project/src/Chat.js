import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Send, Mic, MicOff, Volume2, VolumeX, Camera, Image, X, AlertCircle, User, Bot, Copy, Share2, Paperclip } from 'lucide-react';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';


const ConversationHistory = ({
  conversation,
  isLoading,
  error,
  endRef,
  onSpeak,
  isSpeaking,
  welcomeMessage,
}) => {
  const { t, i18n } = useTranslation();
  return (
    <div className="flex-1 px-4 md:px-8 py-6 space-y-8 bg-agri-pattern">
      {error && (
        <div className="agri-fade-in flex items-center gap-3 text-sm text-red-700 bg-red-50/90 dark:bg-red-900/30 border border-red-200/50 dark:border-red-800/50 rounded-2xl px-5 py-4 backdrop-blur-sm shadow-agri-sm">
          <AlertCircle size={20} className="text-red-500 flex-shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {conversation.filter(entry => !entry.question?.startsWith('Started conversation in category:')).length === 0 && !!welcomeMessage && (
        <div className="flex justify-start agri-fade-in">
          <div className="flex items-start gap-4 max-w-[85%] md:max-w-[75%]">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-agri-success to-nature-leaf flex items-center justify-center shadow-agri-md ring-2 ring-agri-success/20">
              <Bot size={18} className="text-white" />
            </div>
            <div className="chat-bubble-ai flex-1 text-sm leading-relaxed">
              <div className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">
                {welcomeMessage}
              </div>
            </div>
          </div>
        </div>
      )}

      {conversation
        .filter(entry => !entry.question?.startsWith('Started conversation in category:'))
        .map((entry, index) => (
          <div key={index} className="space-y-4">
            {/* User Message */}
            <div className="flex justify-end agri-fade-in">
              <div className="flex items-start gap-4 max-w-[85%] md:max-w-[75%]">
                <div className="chat-bubble-user flex-1 text-sm leading-relaxed font-medium">
                  {entry.question}
                </div>
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-agri-primary to-agri-success flex items-center justify-center shadow-agri-md ring-2 ring-white/20">
                  <User size={18} className="text-white" />
                </div>
              </div>
            </div>

            {/* AI Response */}
            {entry.answer !== null ? (
              <div className="flex justify-start agri-fade-in">
                <div className="flex items-start gap-4 max-w-[85%] md:max-w-[75%]">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-agri-success to-nature-leaf flex items-center justify-center shadow-agri-md ring-2 ring-agri-success/20">
                    <Bot size={18} className="text-white" />
                  </div>
                  <div className="chat-bubble-ai flex-1 text-sm leading-relaxed">
                    <div className="flex items-start gap-3">
                      <div className="flex-1 whitespace-pre-wrap break-words overflow-x-hidden text-gray-800 dark:text-gray-200">
                        {Array.isArray(entry.answer) ? (
                          <ul className="list-disc pl-5 space-y-1">
                            {entry.answer.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        ) : typeof entry.answer === "string" &&
                          entry.answer.length > 180 &&
                          entry.answer.includes("\n") ? (
                          <ul className="list-disc pl-5 space-y-1">
                            {entry.answer
                              .split(/\n|\r/)
                              .filter(Boolean)
                              .map((line, idx) => (
                                <li key={idx}>{line}</li>
                              ))}
                          </ul>
                        ) : (
                          entry.answer
                        )}
                      </div>
                      <div className="flex items-center gap-2 pl-2">
                        <button
                          onClick={() => {
                            try {
                              navigator.clipboard.writeText(entry.answer || "");
                              const toast = document.createElement("div");
                              toast.textContent = "Copied!";
                              toast.className =
                                "fixed bottom-4 left-1/2 -translate-x-1/2 bg-agri-primary text-white text-xs px-4 py-2 rounded-xl shadow-agri-lg z-50 font-medium";
                              document.body.appendChild(toast);
                              setTimeout(() => toast.remove(), 1200);
                            } catch { }
                          }}
                          title="Copy"
                          className="p-2 rounded-lg text-gray-400 hover:text-agri-success hover:bg-agri-success/10 transition-all duration-200"
                        >
                          <Copy size={16} />
                        </button>
                        <button
                          onClick={() => {
                            const text = encodeURIComponent(entry.answer || "");
                            const url = `https://wa.me/?text=${text}`;
                            window.open(url, "_blank");
                          }}
                          title="Share via WhatsApp"
                          className="p-2 rounded-lg text-gray-400 hover:text-agri-accent hover:bg-agri-accent/10 transition-all duration-200"
                        >
                          <Share2 size={16} />
                        </button>
                        <button
                          onClick={() => onSpeak?.(entry.answer)}
                          aria-label={
                            isSpeaking ? t("stopReading") : t("readAnswer")
                          }
                          className="p-2 rounded-lg text-gray-400 hover:text-agri-info hover:bg-agri-info/10 transition-all duration-200"
                        >
                          {isSpeaking ? "⏹️" : "🔊"}
                        </button>
                      </div>
                    </div>
                    {entry.timestamp && (
                      <div className="mt-3 text-xs text-gray-400 dark:text-gray-500 font-medium">
                        {new Date(entry.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex justify-start agri-fade-in">
                <div className="flex items-start gap-4 max-w-[85%] md:max-w-[75%]">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-agri-success to-nature-leaf flex items-center justify-center shadow-agri-md ring-2 ring-agri-success/20 agri-pulse">
                    <Bot size={18} className="text-white" />
                  </div>
                  <div className="chat-bubble-ai flex-1 break-words overflow-x-hidden">
                    <div className="flex items-center gap-3">
                      <div className="flex space-x-1">
                        <div className="w-2.5 h-2.5 bg-agri-success rounded-full agri-bounce"></div>
                        <div
                          className="w-2.5 h-2.5 bg-agri-success rounded-full agri-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2.5 h-2.5 bg-agri-success rounded-full agri-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                      <span className="text-sm text-agri-primary dark:text-agri-success font-medium">
                        AI is thinking...
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

      <div ref={endRef} />
      {isLoading && conversation.length === 0 && (
        <div className="flex justify-center items-center py-16">
          <div className="flex items-center gap-4 agri-fade-in">
            <div className="flex space-x-2">
              <div className="w-3 h-3 bg-agri-success rounded-full agri-bounce"></div>
              <div
                className="w-3 h-3 bg-agri-success rounded-full agri-bounce"
                style={{ animationDelay: "0.1s" }}
              ></div>
              <div
                className="w-3 h-3 bg-agri-success rounded-full agri-bounce"
                style={{ animationDelay: "0.2s" }}
              ></div>
            </div>
            <span className="text-base text-agri-primary dark:text-agri-success font-medium">
              Loading conversation...
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

const QuestionInput = ({
  question,
  setQuestion,
  onSend,
  isLoading,
  disabled,
  onVoiceInput,
  isListening,
  onAttach,
  hasPendingImage,
  setPendingImage,
}) => {
  const { t } = useTranslation();
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="max-w-4xl mx-auto relative">
      {hasPendingImage && (
        <div className="absolute bottom-full left-4 mb-2 text-sm text-agri-primary dark:text-agri-success flex items-center gap-3 px-3 py-2 bg-agri-primary/10 dark:bg-agri-success/10 rounded-xl border border-agri-primary/20 dark:border-agri-success/20 shadow-lg">
          <Image size={16} className="flex-shrink-0" />
          <span className="font-medium">{t("imageAttached")}</span>
          <button onClick={() => setPendingImage(null)} className="p-1 rounded-full hover:bg-black/10 dark:hover:bg-white/10">
            <X size={14} />
          </button>
        </div>
      )}
      <div className="relative flex items-center w-full p-2 rounded-full bg-white/80 dark:bg-gray-800/60 backdrop-blur-md border border-gray-200 dark:border-gray-700 shadow-md">
        {/* Left controls: Mic, Attachment */}
        <div className="flex items-center gap-1.5 pl-1">
          <button
            title={t("voiceInput")}
            aria-label={isListening ? t("listening") : t("voiceInput")}
            className={`p-2.5 rounded-full transition-all duration-200 disabled:opacity-50 flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-agri-primary/30 dark:focus:ring-agri-success/30 ${isListening ? "text-agri-success bg-agri-success/20" : "text-gray-600 hover:text-agri-primary hover:bg-agri-primary/10 dark:text-gray-300 dark:hover:text-agri-success"}`}
            onClick={onVoiceInput}
            disabled={isLoading}
          >
            <Mic size={22} />
          </button>
          <button
            title={t("attach")}
            aria-label={t("attach")}
            className="p-2.5 rounded-full text-gray-600 hover:text-agri-primary hover:bg-agri-primary/10 dark:text-gray-300 dark:hover:text-agri-success transition-all duration-200 disabled:opacity-50 flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-agri-primary/30 dark:focus:ring-agri-success/30"
            onClick={onAttach}
            disabled={isLoading}
          >
            <Paperclip size={22} />
          </button>
        </div>

        {/* Text input */}
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={isListening ? t('listening') : 'Type your message…'}
          className="flex-1 mx-2 px-4 py-3 rounded-2xl bg-transparent text-base md:text-lg text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:ring-0 focus:outline-none transition-all duration-200 resize-none overflow-hidden"
          rows={1}
          style={{ minHeight: '52px', maxHeight: '220px' }}
          onInput={(e) => {
            e.target.style.height = 'auto';
            e.target.style.height = `${e.target.scrollHeight}px`;
          }}
          disabled={isLoading}
        />

        {/* Send button */}
        <div className="pr-1">
          <button
            className="p-3 rounded-full text-white transition-transform duration-200 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}
            onClick={() => onSend()}
            disabled={isLoading || (!question.trim() && !hasPendingImage) || disabled}
            title={t('send') || 'Send'}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

const Chat = ({
  userId,
  conversationId,
  onConversationIdChange,
  indexReady = true,
  isDashboardView,
  embedOnDashboard,
}) => {
  const { t, i18n } = useTranslation();
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [pendingImage, setPendingImage] = useState(null); // { base64, mime }
  const [welcomeMessage, setWelcomeMessage] = useState("");

  const endRef = useRef(null);
  const scrollRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const fileInputRef = useRef(null);
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition();

  // Normalize user preferred language to canonical codes
  const normalizePreferredLang = (raw, fallback) => {
    const s = (raw || '').toString().trim().toLowerCase();
    if (!s) return fallback || 'en';
    // Hindi variants: hi, hi-in, hin, hindi, हिंदी
    if (s === 'hi' || s.startsWith('hi-') || s === 'hin' || s.includes('hindi') || s.includes('हिंदी')) {
      return 'hi';
    }
    // English variants: en, en-in, english
    if (s === 'en' || s.startsWith('en-') || s.includes('english')) {
      return 'en';
    }
    return fallback || 'en';
  };

  // Build a localized welcome message for empty conversations
  const buildWelcomeMessage = (userProfile, tFn, preferredLang) => {
    // Safe translator: if key is missing (t returns the key), use fallback
    const tr = (key, fallback) => {
      try {
        const v = tFn(key, { lng: preferredLang });
        return !v || v === key ? fallback : v;
      } catch {
        return fallback;
      }
    };

    const name = userProfile?.name || userProfile?.username || null;
    const state = userProfile?.state || null;
    const crop = userProfile?.crop || null;

    // Hardcoded Hindi message if user's preferred language is Hindi
    if ((preferredLang || '').toLowerCase().startsWith('hi')) {
      const greetHi = name ? `नमस्ते, ${name}! ` : 'नमस्ते! ';
      const baseHi = 'मैं आपका एग्री‑सहायक AI हूँ।';
      const askHi = 'आज आप खेती के बारे में क्या सीखना चाहते हैं?';
      const stateHi = state ? ` मैं ${state} के लिए सुझाव दे सकता/सकती हूँ।` : '';
      const cropHi = crop ? ` हम ${crop} के बारे में बात कर सकते हैं।` : '';
      return `${greetHi}${baseHi}\n${askHi}${stateHi}${cropHi}`.trim();
    }

    const base = tr('welcomePrompt', "Hi! I'm your Agri-Sahayak assistant.");
    const ask = tr('welcomeAsk', 'What would you like to learn about farming today?');
    const stateLine = state ? ` ${tr('welcomeStateLine', 'I can tailor tips for')} ${state}.` : '';
    const cropLine = crop ? ` ${tr('welcomeCropLine', 'We can talk about')} ${crop}.` : '';
    const greetName = name ? `${tr('hello', 'Hello')}, ${name}! ` : '';
    return `${greetName}${base}\n${ask}${stateLine}${cropLine}`.trim();
  };

  useEffect(() => {
    if (autoScroll) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [conversation, autoScroll]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const threshold = 96; // px tolerance from bottom
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
    setAutoScroll(atBottom);
  }, []);

  // Keep input synced with mic transcript
  useEffect(() => {
    if (transcript) setQuestion(transcript);
  }, [transcript]);

  // Fetch conversation history whenever a conversation is selected
  // Generate localized suggestions based on user profile
  const generateLocalizedSuggestions = useCallback((userProfile) => {
    if (!userProfile) return [];

    const { state, crop } = userProfile;
    const suggestions = [];
    const lowerCrop = crop?.toLowerCase() || '';

    // Crop-specific suggestions
    if (lowerCrop.includes('wheat')) {
      suggestions.push(
        t('suggestions.wheat.fertilizer'),
        t('suggestions.wheat.marketPrices', { state: state || t('selectState') }),
        t('suggestions.wheat.diseases')
      );
    } else if (lowerCrop.includes('rice') || lowerCrop.includes('paddy')) {
      suggestions.push(
        t('suggestions.rice.nutrientSchedule'),
        t('suggestions.rice.variety', { state: state || t('selectState') }),
        t('suggestions.rice.waterManagement')
      );
    } else if (lowerCrop.includes('cotton')) {
      suggestions.push(
        t('suggestions.cotton.bollworm'),
        t('suggestions.cotton.sowingWindow', { state: state || t('selectState') }),
        t('suggestions.cotton.ipmPlan')
      );
    } else if (lowerCrop.includes('sugarcane')) {
      suggestions.push(
        t('suggestions.sugarcane.fertilizerSchedule'),
        t('suggestions.sugarcane.ratoonYield'),
        t('suggestions.sugarcane.subsidySchemes', { state: state || t('selectState') })
      );
    }

    // Add general suggestions
    suggestions.push(
      t('suggestions.general.marketPrices', { crop: crop || t('primaryCrop'), state: state || t('selectState') }),
      t('suggestions.general.soilHealth'),
      t('suggestions.general.loanSubsidy')
    );

    // Remove duplicates and limit to 4
    const uniqueSuggestions = [...new Set(suggestions)];
    return uniqueSuggestions.slice(0, 4);
  }, [t]);

  useEffect(() => {
    if (!conversationId) {
      setConversation([]);
      setWelcomeMessage("");
      // Generate localized suggestions for new chat
      (async () => {
        try {
          if (!userId) return;
          const userRes = await axios.get(`http://127.0.0.1:8000/users/${userId}`);
          const userProfile = userRes?.data?.user;
          const localizedSuggestions = generateLocalizedSuggestions(userProfile);
          setSuggestions(localizedSuggestions);
          // Prepare a dashboard welcome for new chat (no conversation selected)
          const rawLang = userProfile?.language || userProfile?.preferred_language || '';
          const preferredLang = normalizePreferredLang(rawLang, i18n.language || 'en');
          const wm = buildWelcomeMessage(userProfile, t, preferredLang);
          setWelcomeMessage(wm);
        } catch (_) {
          setSuggestions([]);
          setWelcomeMessage("");
        }
      })();
    } else {
      // fetch conversation history
      (async () => {
        try {
          if (!userId) return;
          const res = await axios.get(
            `http://127.0.0.1:8000/conversations/${conversationId}`
          );
          const history = res?.data?.conversation ?? [];
          setConversation(history);
          setError(null);
          setSuggestions([]);

          // If no user-visible messages yet, show an intro bubble.
          // Prefer a category-specific intro if conversation was started via Quick Pick.
          const visibleCount = (history || []).filter(e => !e?.question?.startsWith('Started conversation in category:')).length;
          if (visibleCount === 0) {
            let categoryIntro = '';
            try {
              const starter = (history || []).find(e => e?.question?.startsWith('Started conversation in category:'))?.question || '';
              const category = starter.split(':').slice(1).join(':').trim();

              // Load user profile for personalization and language
              const userRes = await axios.get(`http://127.0.0.1:8000/users/${userId}`);
              const userProfile = userRes?.data?.user;
              const rawLang = userProfile?.language || userProfile?.preferred_language || '';
              const preferredLang = normalizePreferredLang(rawLang, i18n.language || 'en');

              const name = userProfile?.name || userProfile?.username || '';
              const greetEn = name ? `Hello, ${name}! ` : 'Hello! ';
              const greetHi = name ? `नमस्ते, ${name}! ` : 'नमस्ते! ';

              const isHi = (preferredLang || '').toLowerCase().startsWith('hi');
              const mapIntro = (cat) => {
                const c = (cat || '').toLowerCase();
                if (isHi) {
                  if (c.includes('weather')) return `${greetHi}यह मौसम वार्ता है। अपने क्षेत्र का तापमान, वर्षा संभावना और पवन गति के बारे में पूछें।`;
                  if (c.includes('market')) return `${greetHi}यह बाज़ार भाव वार्ता है। फसल के ताज़ा दाम, आपके ज़िले के भाव और रुझान पूछें।`;
                  if (c.includes('loan') || c.includes('finance')) return `${greetHi}यह ऋण/वित्त वार्ता है। किसान क्रेडिट कार्ड, सब्सिडी और पात्रता पर प्रश्न पूछें।`;
                  if (c.includes('farming')) return `${greetHi}यह खेती सलाह वार्ता है। बुवाई, पोषण, रोग/कीट प्रबंधन आदि पूछें।`;
                  if (c.includes('livestock') || c.includes('dairy')) return `${greetHi}यह पशुधन/डेयरी वार्ता है। चारा, दूध उत्पादन, पशु स्वास्थ्य और टीकाकरण पर प्रश्न पूछें।`;
                  return `${greetHi}मैं आपका एग्री‑सहायक AI हूँ। आप अपने विषय से जुड़े प्रश्न पूछ सकते हैं।`;
                }
                // English
                if (c.includes('weather')) return `${greetEn}This is a Weather conversation. Ask about temperature, rain chance, and wind for your area.`;
                if (c.includes('market')) return `${greetEn}This is a Market Prices conversation. Ask for latest crop prices, your district rates, and trends.`;
                if (c.includes('loan') || c.includes('finance')) return `${greetEn}This is a Loans/Finance conversation. Ask about KCC, subsidies, and eligibility.`;
                if (c.includes('farming')) return `${greetEn}This is a Farming advisory conversation. Ask about sowing, nutrition, and pest/disease management.`;
                if (c.includes('livestock') || c.includes('dairy')) return `${greetEn}This is a Livestock/Dairy conversation. Ask about feed, milk yield, animal health, and vaccinations.`;
                return `${greetEn}I'm your Agri‑Sahayak AI. Ask anything related to your selected topic.`;
              };

              if (category) {
                categoryIntro = mapIntro(category);
              }

              // Fallback to generic welcome if we didn't detect a category
              if (!categoryIntro) {
                categoryIntro = buildWelcomeMessage(userProfile, t, preferredLang);
              }
              setWelcomeMessage(categoryIntro);
            } catch {
              setWelcomeMessage(t('welcomeDefault') || 'Hi! What would you like to learn about farming today?');
            }
          } else {
            setWelcomeMessage("");
          }
        } catch (err) {
          setError(t("failedToLoadConversationHistory"));
        }
      })();
    }
  }, [conversationId, userId, generateLocalizedSuggestions]);

  const handleSend = async (overrideQuestion) => {
    const text = overrideQuestion ?? question;
    const trimmed = typeof text === "string" ? text.trim() : "";
    const hasImage = !!pendingImage;
    if (!trimmed && !hasImage) return;

    setError(null);
    setIsLoading(true);
    // Hide welcome once user engages
    setWelcomeMessage("");
    if (overrideQuestion === undefined) setQuestion("");

    // Decide which endpoint
    const placeholderQuestion = hasImage
      ? trimmed || "Analyze crop image"
      : trimmed;

    setConversation((prev) => [
      ...prev,
      {
        question: placeholderQuestion,
        answer: null,
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      const uid = localStorage.getItem("user_id") || userId;
      let res;
      if (hasImage) {
        try { console.debug('[Chat] Sending analyze_image with mime', pendingImage?.mime, 'b64.len', (pendingImage?.base64 || '').length); } catch { }
        res = await axios.post("http://127.0.0.1:8000/analyze_image", {
          user_id: uid,
          image_base64: pendingImage.base64,
          mime_type: pendingImage.mime,
          question: trimmed || null,
          conversation_id: conversationId || null,
        });
      } else {
        res = await axios.post("http://127.0.0.1:8000/ask", {
          user_id: uid,
          question: trimmed,
          conversation_id: conversationId || null,
        });
      }
      const answer = res?.data?.answer ?? "";
      const returnedConversationId = res?.data?.conversation_id;
      if (!conversationId && returnedConversationId && onConversationIdChange) {
        onConversationIdChange(returnedConversationId);
      }
      setSuggestions([]);
      setConversation((prev) => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        if (lastIndex >= 0) {
          updated[lastIndex] = { ...updated[lastIndex], answer };
        }
        return updated;
      });
    } catch (err) {
      setError(t("failedToGetAnswer"));
      setConversation((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
      setPendingImage(null);
    }
  };

  const handleSuggestionClick = async (text) => {
    if (!text) return;
    handleSend(text);
  };

  const toggleVoice = () => {
    try {
      const lang = (i18n?.language || 'en').toLowerCase().startsWith('hi') ? 'hi-IN' : 'en-IN';
      if (listening) {
        SpeechRecognition.stopListening();
        return;
      }
      resetTranscript();
      SpeechRecognition.startListening({
        continuous: true,
        interimResults: false,
        language: lang,
      });
    } catch { }
  };

  const handleSpeak = (text) => {
    try {
      if (typeof window === "undefined" || !window.speechSynthesis) return;
      const synth = window.speechSynthesis;
      if (synth.speaking || isSpeaking) {
        synth.cancel();
        setIsSpeaking(false);
        return;
      }
      const raw = String(text || "");
      // Detect Devanagari characters or rely on UI language to choose Hindi
      const hasDevanagari = /[\u0900-\u097F]/.test(raw);
      const uiLang = (i18n?.language || 'en').toLowerCase();
      const lang = (uiLang.startsWith('hi') || hasDevanagari) ? 'hi-IN' : 'en-IN';

      const speakWithVoice = () => {
        const utterance = new SpeechSynthesisUtterance(raw);
        utterance.lang = lang;
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.volume = 1;
        // Try to pick a matching voice if available (browser-dependent)
        try {
          const voices = synth.getVoices ? synth.getVoices() : [];
          const preferredNames = [
            // Common Chrome voices
            'Google हिन्दी', 'Google हिंदी', 'Google Hindi',
            // Edge/Windows voices
            'Microsoft Heera Online (Natural) - Hindi (India)',
            'Microsoft Kalpana Online (Natural) - Hindi (India)',
            'Microsoft Swara Online (Natural) - Hindi (India)'
          ];
          let match = voices.find(v => (v.lang || '').toLowerCase().startsWith(lang.toLowerCase()))
            || voices.find(v => (v.lang || '').toLowerCase().startsWith(lang.slice(0, 2).toLowerCase()));
          if (!match) match = voices.find(v => preferredNames.includes(v.name));
          if (match) utterance.voice = match;
        } catch { }
        utterance.onend = () => setIsSpeaking(false);
        setIsSpeaking(true);
        synth.cancel();
        synth.speak(utterance);
      };

      // If voices are not loaded yet, wait for them
      const available = synth.getVoices ? synth.getVoices() : [];
      if (!available || available.length === 0) {
        const once = () => {
          try { synth.removeEventListener('voiceschanged', once); } catch { }
          speakWithVoice();
        };
        try { synth.addEventListener('voiceschanged', once); } catch { speakWithVoice(); }
        // Also set a short timeout fallback in case event doesn't fire
        setTimeout(() => {
          try { synth.removeEventListener('voiceschanged', once); } catch { }
          if (!synth.speaking) speakWithVoice();
        }, 500);
      } else {
        speakWithVoice();
      }
    } catch { }
  };

  const openFilePicker = () => {
    if (!fileInputRef.current) {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      input.onchange = async (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        try {
          const b64 = await toBase64(file);
          try { console.debug('[Chat] Selected image', { name: file.name, type: file.type, size: file.size, b64len: b64.length }); } catch { }
          setPendingImage({ base64: b64, mime: file.type || "image/jpeg" });
        } catch (_) { }
        // Reset the input so the same file can be selected again
        e.target.value = '';
      };
      fileInputRef.current = input;
    }
    fileInputRef.current.click();
  };

  const toBase64 = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result || "";
        const commaIdx = String(result).indexOf(",");
        resolve(
          commaIdx >= 0 ? String(result).slice(commaIdx + 1) : String(result)
        );
      };
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
    });

  // Embedded mode for dashboard: render only sticky input,
  // without introducing another scroll container.
  if (embedOnDashboard) {
    return (
      <div className="sticky bottom-0 z-10 p-4 bg-transparent">
        <QuestionInput
          question={question}
          setQuestion={setQuestion}
          onSend={handleSend}
          isLoading={isLoading}
          disabled={!userId || !indexReady}
          onVoiceInput={
            browserSupportsSpeechRecognition ? toggleVoice : undefined
          }
          isListening={browserSupportsSpeechRecognition ? listening : false}
          onAttach={openFilePicker}
          hasPendingImage={!!pendingImage}
          setPendingImage={setPendingImage}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-0 h-full">
      {/* Scrollable messages area */}
      <div
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 overscroll-contain custom-scrollbar scroll-smooth relative"
        ref={scrollRef}
        onScroll={handleScroll}
      >
        {/* Focused Chat View: show conversation history */}
        {!isDashboardView && (
          <ConversationHistory
            conversation={conversation}
            isLoading={isLoading}
            error={error}
            endRef={endRef}
            onSpeak={handleSpeak}
            isSpeaking={isSpeaking}
            welcomeMessage={welcomeMessage}
          />
        )}

        {/* Dashboard View: show startup prompts */}
        {isDashboardView && conversation.length === 0 && suggestions.length > 0 && (
          <div className="px-2 md:px-6 pb-8">
            <div className="max-w-4xl mx-auto">
              <div className="text-base text-agri-primary dark:text-agri-success mb-8 font-semibold text-center">
                <span className="inline-flex items-center gap-2">
                  🌾 {t("tryOneOfThese")}:
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {suggestions.map((s, idx) => (
                  <button
                    key={idx}
                    className="group w-full text-left p-6 agri-card hover:shadow-agri-lg transition-all duration-300 text-sm text-gray-700 dark:text-gray-300 hover:text-agri-primary dark:hover:text-agri-success hover:scale-[1.02] agri-fade-in"
                    style={{ animationDelay: `${idx * 0.1}s` }}
                    onClick={() => handleSuggestionClick(s)}
                  >
                    <div className="flex items-start gap-4">
                      <div className="w-3 h-3 bg-gradient-to-br from-agri-success to-nature-leaf rounded-full mt-1.5 opacity-70 group-hover:opacity-100 transition-all duration-300 group-hover:scale-125"></div>
                      <span className="flex-1 leading-relaxed font-medium group-hover:font-semibold transition-all duration-300">{s}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Jump to latest button */}
        {!autoScroll && (
          <button
            type="button"
            onClick={() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })}
            className="absolute right-6 bottom-6 z-10 px-4 py-3 text-sm rounded-2xl text-white shadow-agri-lg hover:shadow-agri-xl transition-all duration-300 hover:scale-105 font-medium backdrop-blur-sm"
            style={{ background: 'var(--agri-gradient-primary)' }}
            title={t('jumpToLatest') || 'Jump to latest'}
          >
            <span className="flex items-center gap-2">
              ⬇️ {t('jumpToLatest') || 'Jump to latest'}
            </span>
          </button>
        )}
      </div>

      {/* Sticky input area at bottom (always visible) */}
      <div className="sticky bottom-0 z-10 p-4 bg-transparent">
        <QuestionInput
          question={question}
          setQuestion={setQuestion}
          onSend={handleSend}
          isLoading={isLoading}
          disabled={!userId || !indexReady}
          onVoiceInput={
            browserSupportsSpeechRecognition ? toggleVoice : undefined
          }
          isListening={browserSupportsSpeechRecognition ? listening : false}
          onAttach={openFilePicker}
          hasPendingImage={!!pendingImage}
          setPendingImage={setPendingImage}
        />
      </div>
    </div>
  );
};

export default Chat;
