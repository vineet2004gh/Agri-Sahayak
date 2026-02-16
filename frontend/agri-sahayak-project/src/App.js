import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import Welcome from './Welcome';
import Profile from './Profile';
import Chat from './Chat';
import Dashboard from './Dashboard';
import CategorySelector from './CategorySelector';
import ConversationSidebar from './ConversationSidebar';
import ActivityBar from './ActivityBar'; // Import the new component
import { X, Plus, Menu, Sun, Moon, Globe, Bell, User, Settings } from 'lucide-react';

const App = () => {
  const { t, i18n } = useTranslation();
  const [userId, setUserId] = useState(null);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [showProfile, setShowProfile] = useState(false);
  const [isDark, setIsDark] = useState(false);
  // State for the new collapsible sidebar
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // Manages hover state
  const [isSidebarPinned, setIsSidebarPinned] = useState(false); // Manages pinned state
  const [sidebarKey, setSidebarKey] = useState(Date.now());

  const handleSelectCategory = async (category) => {
    try {
      const response = await axios.post('http://127.0.0.1:8000/conversations/start', {
        user_id: userId,
        category: category,
      });
      const newConversationId = response.data.conversation_id;
      setSelectedConversationId(newConversationId);
      setSidebarKey(Date.now());
    } catch (error) {
      console.error('Error starting new conversation:', error);
    }
  };

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const shouldDark = saved ? saved === "dark" : false;
    setIsDark(shouldDark);
    document.documentElement.classList.toggle("dark", shouldDark);
  }, []);

  const handleNewChat = () => {
    setSelectedConversationId(null);
  };

  const handleLogout = () => {
    try {
      localStorage.removeItem("user_id");
      localStorage.removeItem("user_name");
    } catch {}
    setSelectedConversationId(null);
    setUserId(null);
    setShowProfile(false);
  };

  useEffect(() => {
    const existing = localStorage.getItem("user_id");
    if (!existing) return;
    (async () => {
      try {
        await axios.get(`http://127.0.0.1:8000/users/${existing}`);
        setUserId(existing);
      } catch (e) {
        localStorage.removeItem("user_id");
        localStorage.removeItem("user_name");
        setUserId(null);
        setShowProfile(false);
      }
    })();
  }, []);

  const handleProfileCreated = (id) => {
    setUserId(id);
  };

  if (!userId) {
    return (
      <div className="min-h-screen flex flex-col bg-white dark:bg-gray-900">
        <header className="sticky top-0 z-30 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-b border-gray-200 dark:border-gray-800 shadow-sm">
          <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <img src="/logo_new.png" alt="Agri-Sahayak" className="h-10 w-10 rounded-xl bg-white/10 p-1.5 shadow-sm" />
              <div className="flex flex-col">
                <span className="text-xl font-extrabold text-gray-800 dark:text-gray-100 leading-tight tracking-tight">
                  AI Powered End to End System
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                  {i18n.language === 'hi' ? 'एआई संचालित एंड-टू-एंड सिस्टम' : 'AI Powered End to End System'}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center">
                <div className="inline-flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                  <button
                    onClick={() => i18n.changeLanguage('en')}
                    className={`px-3 py-1.5 text-sm font-semibold ${i18n.language === 'en' ? 'bg-agri-accent text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                  >EN</button>
                  <button
                    onClick={() => i18n.changeLanguage('hi')}
                    className={`px-3 py-1.5 text-sm font-semibold ${i18n.language === 'hi' ? 'bg-agri-warning text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                  >हि</button>
                </div>
              </div>
              <button
                onClick={() => {
                  const newIsDark = !isDark;
                  setIsDark(newIsDark);
                  localStorage.setItem("theme", newIsDark ? "dark" : "light");
                  document.documentElement.classList.toggle("dark", newIsDark);
                }}
                className="p-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200"
                title="Toggle dark mode"
              >
                {isDark ? "☀️" : "🌙"}
              </button>
            </div>
          </div>
        </header>
        <main className="flex-1">
          {showProfile ? (
            <Profile onCreated={handleProfileCreated} onBack={() => setShowProfile(false)} />
          ) : (
            <Welcome
              onRegister={() => setShowProfile(true)}
              onSignIn={(id) => setUserId(id)}
            />
          )}
        </main>
      </div>
    );
  }

  const handleTogglePin = () => {
    setIsSidebarPinned(prev => !prev);
  };

  const isSidebarVisible = isSidebarOpen || isSidebarPinned;

  return (
    <div className="h-screen bg-agri-pattern dark:bg-gray-900 flex">
      {/* Collapsible Sidebar Container */}
      <div
        onMouseLeave={() => {
          if (!isSidebarPinned) {
            setIsSidebarOpen(false);
          }
        }}
        className="relative flex flex-col h-full glass-effect border-r border-agri-primary/20 dark:border-gray-700 transition-all duration-300 ease-in-out shadow-agri-xl"
        style={{ width: isSidebarVisible ? '280px' : '60px' }}
      >
        {isSidebarVisible ? (
          // Expanded Conversation Sidebar
          <div className="flex flex-col h-full w-[280px] overflow-x-hidden">
            <div className="flex items-center justify-between p-5 border-b border-agri-primary/10 dark:border-gray-700">
              <h2 className="text-xl font-bold text-agri-primary dark:text-agri-success flex items-center gap-2 whitespace-nowrap">
                💬 {t('conversations')}
              </h2>
              <button
                onClick={handleNewChat}
                className="p-2.5 rounded-xl hover:bg-agri-primary/10 dark:hover:bg-gray-700 transition-all duration-200 hover:scale-105"
                title={t('newChat')}
              >
                <Plus size={20} className="text-agri-primary dark:text-agri-success" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <ConversationSidebar
                key={sidebarKey}
                userId={userId}
                selectedConversationId={selectedConversationId}
                onSelect={setSelectedConversationId}
                onLogout={handleLogout}
              />
            </div>
          </div>
        ) : (
          // Collapsed Activity Bar
          <ActivityBar
            onMouseEnter={() => setIsSidebarOpen(true)}
            onTogglePin={handleTogglePin}
            onNewChat={handleNewChat}
            onSearchClick={() => setIsSidebarOpen(true)}
            onProfileClick={() => alert('Profile click handler to be implemented')}
          />
        )}
      </div>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <div className="sticky top-0 z-10 glass-effect border-b border-agri-primary/10 dark:border-gray-700 px-6 py-4 shadow-agri-sm">
          <div className="flex items-center justify-between">
            {/* Clickable brand (logo + title) */}
            <button
              type="button"
              onClick={handleNewChat}
              className="group flex items-center gap-3 rounded-xl px-1 py-1 hover:bg-agri-primary/5 dark:hover:bg-white/5 transition-colors"
              title={i18n.language === 'hi' ? 'मुख्य डैशबोर्ड पर जाएं' : 'Go to dashboard'}
              aria-label={i18n.language === 'hi' ? 'मुख्य डैशबोर्ड' : 'Dashboard home'}
            >
              <img src="/logo_new.png" alt="Agri-sahayak" className="w-10 h-10 rounded-xl bg-white/10 p-1.5 shadow-sm" />
              <div className="text-left">
                <h1 className="text-xl font-bold text-agri-primary dark:text-white group-hover:opacity-90">
                  AI Powered End to End System
                </h1>
                <p className="text-xs text-agri-secondary dark:text-gray-400 font-medium group-hover:opacity-90">
                  {i18n.language === 'hi' ? 'एआई संचालित एंड-टू-एंड सिस्टम' : 'AI Powered End to End System'}
                </p>
              </div>
            </button>
            <div className="flex items-center space-x-3">
               <button
                 onClick={() => {
                   const el = document.getElementById('voice-assistant');
                   if (el) {
                     el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                   }
                 }}
                 className="px-3 py-2 rounded-xl bg-gradient-to-r from-agri-success to-agri-primary text-white text-sm font-semibold hover:from-agri-primary hover:to-agri-success transition-all duration-200 shadow-agri-sm"
               >
                 {i18n.language === 'hi' ? '📞 कॉल पर जाएं' : '📞 Request Call'}
               </button>
               <div className="inline-flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                 <button
                   onClick={() => i18n.changeLanguage('en')}
                   className={`px-3 py-2 text-sm font-semibold ${i18n.language === 'en' ? 'bg-agri-accent text-white' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                 >EN</button>
                 <button
                   onClick={() => i18n.changeLanguage('hi')}
                   className={`px-3 py-2 text-sm font-semibold ${i18n.language === 'hi' ? 'bg-agri-warning text-white' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                 >हि</button>
               </div>
               <button
                 onClick={() => {
                   const newIsDark = !isDark;
                   setIsDark(newIsDark);
                   localStorage.setItem("theme", newIsDark ? "dark" : "light");
                   document.documentElement.classList.toggle("dark", newIsDark);
                 }}
                 className="p-3 rounded-xl hover:bg-agri-info/10 dark:hover:bg-gray-700 transition-all duration-200 hover:scale-105"
                 title={t('toggleTheme')}
               >
                 {isDark ? (
                   <Sun size={20} className="text-agri-warning" />
                 ) : (
                   <Moon size={20} className="text-agri-info" />
                 )}
               </button>
             </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 md:p-8 overflow-y-auto">
          {selectedConversationId ? (
            <Chat
              key={selectedConversationId} // Re-mounts Chat on conversation change
              conversationId={selectedConversationId}
              userId={userId}
            />
          ) : (
            <>
              <Dashboard userId={userId} />
              <div className="mt-6 md:mt-8">
                <CategorySelector onSelectCategory={handleSelectCategory} />
              </div>
              <Chat
                userId={userId}
                conversationId={null}
                embedOnDashboard={true}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;
