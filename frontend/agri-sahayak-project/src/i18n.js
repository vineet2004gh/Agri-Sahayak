import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  // load translation using http -> see /public/locales (i.e. https://github.com/i18next/react-i18next/tree/master/example/react/public/locales)
  // learn more: https://github.com/i18next/i18next-http-backend
  .use(Backend)
  // detect user language
  // learn more: https://github.com/i18next/i18next-browser-languagedetector
  .use(LanguageDetector)
  // pass the i18n instance to react-i18next.
  .use(initReactI18next)
  // init i18next
  // for all options read: https://www.i18next.com/overview/configuration-options
  .init({
    fallbackLng: 'en',
    debug: false,

    interpolation: {
      escapeValue: false, // not needed for react as it escapes by default
    },

    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },

    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },

    resources: {
      en: {
        translation: {
          conversations: 'Conversations',
          noConversationsYet: 'No conversations yet',
          failedToLoadConversations: 'Failed to load conversations',
          askYourQuestion: 'Ask your question...',
          addNoteAboutImage: 'Add a note about the image or press Send...',
          send: 'Send',
          imageAttached: 'Image attached. It will be analyzed when you press Send.',
          tryOneOfThese: 'Try one of these:',
          // Suggestion translations
          suggestions: {
            wheat: {
              fertilizer: "What is the best fertilizer dose for wheat?",
              marketPrices: "Show me current market prices for wheat in {{state}}",
              diseases: "How can I control rust or other common wheat diseases?"
            },
            rice: {
              nutrientSchedule: "Recommend a nutrient schedule for rice",
              variety: "What is the recommended paddy variety for {{state}}?",
              waterManagement: "Best water management practices for transplanted paddy?"
            },
            cotton: {
              bollworm: "How do I manage bollworm infestation?",
              sowingWindow: "What is the ideal sowing window for cotton in {{state}}?",
              ipmPlan: "Suggest an IPM plan for cotton pests"
            },
            sugarcane: {
              fertilizerSchedule: "What is the recommended fertilizer schedule for sugarcane?",
              ratoonYield: "How to improve ratoon crop yield in sugarcane?",
              subsidySchemes: "Any subsidy schemes for sugarcane planters in {{state}}?"
            },
            general: {
              marketPrices: "Show me current market prices for {{crop}} in {{state}}",
              soilHealth: "What are the best practices for soil health and testing?",
              loanSubsidy: "How can I get a loan or subsidy for new farm machinery?"
            }
          },
          failedToGetAnswer: 'Failed to get answer. Please try again.',
          welcomeToAgriSahayak: 'Welcome to Agri‑Sahayak',
          signInWithEmail: 'Sign in with email',
          email: 'Email',
          password: 'Password',
          signInWithEmailButton: 'Sign In with Email',
          noAccount: 'No account?',
          createNewProfile: 'Create New Profile',
          createYourProfile: 'Create your profile',
          name: 'Name',
          phoneNumber: 'Phone Number',
          selectPreferredLanguage: 'Select Preferred Language',
          english: 'English',
          hindi: 'हिन्दी',
          selectState: 'Select State',
          selectDistrict: 'Select District',
          selectStateFirst: 'Select a state first',
          primaryCrop: 'Primary Crop',
          createProfile: 'Create Profile',
          creating: 'Creating...',
          failedToCreateProfile: 'Failed to create profile. Please try again.',
          nameRequired: 'Name is required',
          phoneNumberRequired: 'Phone number is required',
          invalidCredentials: 'Invalid email or password.',
          userNotFound: 'User not found. Please check the ID or register new profile.',
          signInWithEmailDescription: 'Sign in with email, or register a new profile.',
          agriSahayak: 'Agri‑Sahayak',
          farmer: 'Farmer',
          logout: 'Logout',
          failedToLoadConversationHistory: 'Failed to load conversation history.',
          listening: 'Listening...',
          voiceInput: 'Voice input',
          attach: 'Attach',
          stopReading: 'Stop reading',
          readAnswer: 'Read answer',
          untitledConversation: 'Untitled conversation',
          weatherAlerts: 'Weather Alerts',
          loadingAlerts: 'Loading alerts...',
          noWeatherAlerts: 'No weather alerts at this time',
          stayTuned: 'We\'ll notify you of any weather conditions that may affect your crops',
          refreshing: 'Refreshing...',
          refresh: 'Refresh',
          quickStart: 'Quick Start',
          farming: 'Crop Advisory',
          loans: 'Finance & Loans',
          market_prices: 'Market Prices',
          weather: 'Weather',
          livestock: 'Livestock & Dairy',
          smartAgriculturalAssistant: 'Smart Agricultural Assistant',
          emailPrivacy: "We'll never share your email.",
          forgotPassword: 'Forgot password?',
          aiPoweredSystem: 'AI Powered End to End System',
          smartMultilingualAdvisory: 'Smart, multilingual advisory',
          voicePoweredAssistance: 'Voice-powered assistance',
          aiImageAnalysis: 'AI image analysis',
          realTimeMarketInsights: 'Real‑time market insights',
          empoweringFarmers: 'Empowering farmers with intelligent technology',
          enterEmail: 'Enter your email address',
          enterPassword: 'Enter your password',
          signingIn: 'Signing in...',
          backToSignIn: 'Back to SignIn',
          personalizedAssistant: 'Personalized Agricultural Assistant',
          enterFullName: 'Enter your full name',
          createSecurePassword: 'Create a secure password',
          enterMobileNumber: 'Enter your mobile number',
          cropPlaceholder: 'e.g., Rice, Wheat, Cotton, Sugarcane',
          creatingProfile: 'Creating Profile...',
          locationBasedAdvice: 'Location\u2011based advice',
          cropSpecificGuidance: 'Crop\u2011specific guidance',
          multilingualSupport: 'Multilingual support',
          voiceSmsAlerts: 'Voice & SMS alerts',
          personalizedIntelligence: 'Personalized agricultural intelligence',
        }
      },
      hi: {
        translation: {
          conversations: 'बातचीत',
          noConversationsYet: 'अभी तक कोई बातचीत नहीं',
          failedToLoadConversations: 'बातचीत लोड करने में विफल',
          askYourQuestion: 'अपना प्रश्न पूछें...',
          addNoteAboutImage: 'छवि के बारे में नोट जोड़ें या भेजने के लिए दबाएं...',
          send: 'भेजें',
          imageAttached: 'छवि संलग्न है। जब आप भेजें दबाएंगे तो इसका विश्लेषण किया जाएगा।',
          tryOneOfThese: 'इनमें से एक को आज़माएं:',
          // Suggestion translations in Hindi
          suggestions: {
            wheat: {
              fertilizer: "गेहूं के लिए सबसे अच्छी खाद की मात्रा क्या है?",
              marketPrices: "{{state}} में गेहूं के वर्तमान बाजार भाव दिखाएं",
              diseases: "गेहूं में रतुआ या अन्य सामान्य बीमारियों को कैसे नियंत्रित करूं?"
            },
            rice: {
              nutrientSchedule: "धान के लिए पोषक तत्वों का कार्यक्रम सुझाएं",
              variety: "{{state}} के लिए अनुशंसित धान की किस्म क्या है?",
              waterManagement: "रोपित धान के लिए सबसे अच्छी जल प्रबंधन प्रथाएं?"
            },
            cotton: {
              bollworm: "गुलाबी सुंडी के संक्रमण को कैसे नियंत्रित करूं?",
              sowingWindow: "{{state}} में कपास की आदर्श बुआई का समय क्या है?",
              ipmPlan: "कपास के कीटों के लिए एक IPM योजना सुझाएं"
            },
            sugarcane: {
              fertilizerSchedule: "गन्ने के लिए अनुशंसित उर्वरक कार्यक्रम क्या है?",
              ratoonYield: "गन्ने में रेटून फसल की उपज कैसे बढ़ाएं?",
              subsidySchemes: "{{state}} में गन्ना उत्पादकों के लिए कोई सब्सिडी योजनाएं?"
            },
            general: {
              marketPrices: "{{state}} में {{crop}} के वर्तमान बाजार भाव दिखाएं",
              soilHealth: "मिट्टी के स्वास्थ्य और परीक्षण के लिए सबसे अच्छी प्रथाएं क्या हैं?",
              loanSubsidy: "नई कृषि मशीनरी के लिए ऋण या सब्सिडी कैसे प्राप्त करूं?"
            }
          },
          failedToGetAnswer: 'उत्तर प्राप्त करने में विफल। कृपया पुनः प्रयास करें।',
          welcomeToAgriSahayak: 'अग्री-सहायक में आपका स्वागत है',
          signInWithEmail: 'ईमेल से साइन इन करें',
          email: 'ईमेल',
          password: 'पासवर्ड',
          signInWithEmailButton: 'ईमेल से साइन इन करें',
          noAccount: 'खाता नहीं है?',
          createNewProfile: 'नया प्रोफ़ाइल बनाएं',
          createYourProfile: 'अपना प्रोफ़ाइल बनाएं',
          name: 'नाम',
          phoneNumber: 'फ़ोन नंबर',
          selectPreferredLanguage: 'पसंदीदा भाषा चुनें',
          english: 'English',
          hindi: 'हिन्दी',
          selectState: 'राज्य चुनें',
          selectDistrict: 'जिला चुनें',
          selectStateFirst: 'पहले राज्य चुनें',
          primaryCrop: 'मुख्य फसल',
          createProfile: 'प्रोफ़ाइल बनाएं',
          creating: 'बना रहा है...',
          failedToCreateProfile: 'प्रोफ़ाइल बनाने में विफल। कृपया पुनः प्रयास करें।',
          nameRequired: 'नाम आवश्यक है',
          phoneNumberRequired: 'फ़ोन नंबर आवश्यक है',
          invalidCredentials: 'अमान्य ईमेल या पासवर्ड।',
          userNotFound: 'उपयोगकर्ता नहीं मिला। कृपया ID जांचें या नया प्रोफ़ाइल पंजीकृत करें।',
          signInWithEmailDescription: 'ईमेल से साइन इन करें, या नया प्रोफ़ाइल पंजीकृत करें।',
          agriSahayak: 'अग्री-सहायक',
          farmer: 'किसान',
          logout: 'लॉगआउट',
          failedToLoadConversationHistory: 'बातचीत का इतिहास लोड करने में विफल।',
          listening: 'सुन रहा है...',
          voiceInput: 'आवाज़ इनपुट',
          attach: 'संलग्न करें',
          stopReading: 'पढ़ना बंद करें',
          readAnswer: 'उत्तर पढ़ें',
          untitledConversation: 'अनाम बातचीत',
          weatherAlerts: 'मौसम चेतावनी',
          loadingAlerts: 'चेतावनी लोड हो रही है...',
          noWeatherAlerts: 'इस समय कोई मौसम चेतावनी नहीं',
          stayTuned: 'हम आपको किसी भी मौसमी स्थिति की जानकारी देंगे जो आपकी फसलों को प्रभावित कर सकती है',
          refreshing: 'रीफ्रेश हो रहा है...',
          refresh: 'रीफ्रेश करें',
          quickStart: 'त्वरित आरंभ',
          farming: 'फसल सलाहकार',
          loans: 'वित्त और ऋण',
          market_prices: 'बाजार मूल्य',
          weather: 'मौसम',
          livestock: 'पशुधन व डेयरी',
          smartAgriculturalAssistant: 'स्मार्ट कृषि सहायक',
          emailPrivacy: 'हम आपका ईमेल कभी साझा नहीं करेंगे।',
          forgotPassword: 'पासवर्ड भूल गए?',
          aiPoweredSystem: 'एआई संचालित एंड-टू-एंड सिस्टम',
          smartMultilingualAdvisory: 'स्मार्ट, बहुभाषी सलाह',
          voicePoweredAssistance: 'आवाज़ से संचालित सहायता',
          aiImageAnalysis: 'एआई छवि विश्लेषण',
          realTimeMarketInsights: 'रीयल-टाइम बाज़ार जानकारी',
          empoweringFarmers: 'बुद्धिमान तकनीक से किसानों को सशक्त बनाना',
          enterEmail: 'अपना ईमेल पता दर्ज करें',
          enterPassword: 'अपना पासवर्ड दर्ज करें',
          signingIn: 'साइन इन हो रहा है...',
          backToSignIn: 'साइन इन पर वापस जाएं',
          personalizedAssistant: 'व्यक्तिगत कृषि सहायक',
          enterFullName: 'अपना पूरा नाम दर्ज करें',
          createSecurePassword: 'एक सुरक्षित पासवर्ड बनाएं',
          enterMobileNumber: 'अपना मोबाइल नंबर दर्ज करें',
          cropPlaceholder: 'जैसे, चावल, गेहूं, कपास, गन्ना',
          creatingProfile: 'प्रोफ़ाइल बन रहा है...',
          locationBasedAdvice: 'स्थान\u2011आधारित सलाह',
          cropSpecificGuidance: 'फसल\u2011विशिष्ट मार्गदर्शन',
          multilingualSupport: 'बहुभाषी समर्थन',
          voiceSmsAlerts: 'आवाज़ और SMS अलर्ट',
          personalizedIntelligence: 'व्यक्तिगत कृषि बुद्धिमत्ता',
        }
      }
    }
  });

export default i18n;
