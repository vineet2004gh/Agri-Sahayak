import React, { useState } from "react";
import axios from "axios";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff, Mail, Globe2, Mic2, Image as ImageIcon, LineChart } from "lucide-react";

const Welcome = ({ onRegister, onSignIn }) => {
  const { t } = useTranslation();
  const [error, setError] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleEmailLogin = async () => {
    setError(null);
    try {
      if (!email.trim() || !password.trim()) {
        setError(t("invalidCredentials"));
        return;
      }
      setIsLoading(true);
      const res = await axios.post("http://127.0.0.1:8000/login", {
        email: email.trim(),
        password: password.trim(),
      });
      const { user_id, name } = res?.data || {};
      if (!user_id) throw new Error("Invalid login response");
      localStorage.setItem("user_id", user_id);
      localStorage.setItem("user_name", name || "");
      onSignIn?.(user_id);
    } catch (e) {
      setError(t("invalidCredentials"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4 md:px-8 py-8 md:py-12 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-gray-950 dark:to-slate-900 relative">
      <div className="absolute inset-0 pointer-events-none opacity-[0.08]">
        <div className="w-full h-full bg-agri-pattern" />
      </div>
      <div className="relative auth-card grid w-full max-w-[1100px] grid-cols-1 md:grid-cols-[1.05fr_0.95fr] rounded-3xl overflow-hidden shadow-agri-xl border border-gray-200/70 dark:border-gray-800/80 bg-white/85 dark:bg-gray-900/70 backdrop-blur-md">
        {/* Left: Sign in form */}
        <div className="p-7 md:p-10 lg:p-12">
          <div className="flex items-center gap-4 mb-6">
            <img src="/logo_new.png" alt="Agri‑Sahayak" className="w-16 h-16 rounded-3xl bg-white/10 p-2 shadow-agri-md" />
            <div>
              <h1 className="text-3xl md:text-[32px] leading-tight font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 mb-1">
                {t("welcomeToAgriSahayak")}
              </h1>
              <p className="text-agri-secondary dark:text-gray-400 font-medium">
                Smart Agricultural Assistant
              </p>
            </div>
          </div>
          <p className="text-agri-primary/70 dark:text-gray-300/80 mb-8 md:mb-10 text-base md:text-lg leading-relaxed">
            {t("signInWithEmailDescription")}
          </p>

          {error && <div className="text-sm text-red-700 bg-red-50/90 border border-red-200/50 rounded-2xl px-5 py-4 mb-6 font-medium backdrop-blur-sm">{error}</div>}

          <div className="space-y-6">
            <div>
              <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                {t("email")}
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address"
                  className="input rounded-2xl py-4 px-5 pr-14 text-base transition-all duration-300 focus:shadow-agri-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:border-agri-primary/50 focus:ring-2 focus:ring-agri-primary/20"
                  aria-label={t("email")}
                />
                <span className="absolute right-5 top-1/2 -translate-y-1/2 text-agri-primary/50 dark:text-gray-400">
                  <Mail size={20} />
                </span>
              </div>
              <p className="mt-3 text-sm text-agri-secondary dark:text-gray-400 font-medium">
                🔒 We'll never share your email.
              </p>
            </div>

            <div>
              <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                {t("password")}
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="input rounded-2xl py-4 px-5 pr-14 text-base transition-all duration-300 focus:shadow-agri-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:border-agri-primary/50 focus:ring-2 focus:ring-agri-primary/20"
                  aria-label={t("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 p-2 rounded-xl text-agri-primary/50 hover:text-agri-primary hover:bg-agri-primary/10 dark:text-gray-400 dark:hover:text-gray-200 transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-agri-primary/30"
                  aria-label={showPassword ? t("hidePassword") : t("showPassword")}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              <div className="mt-3 text-sm text-agri-secondary dark:text-gray-400">
                <button type="button" className="btn-link p-0 text-sm hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-agri-primary/30">
                  Forgot password?
                </button>
              </div>
            </div>

            <button
              onClick={handleEmailLogin}
              className="btn-primary rounded-2xl py-4 px-8 text-lg font-bold shadow-agri-md hover:shadow-agri-lg transition-all duration-300 w-full hover:scale-[1.02] disabled:hover:scale-100 focus:outline-none focus-visible:ring-4 focus-visible:ring-agri-primary/30"
              disabled={isLoading}
            >
              {isLoading ? '🔄 Signing in...' : `🚀 ${t("signInWithEmailButton")}`}
            </button>

            <div className="flex items-center justify-between pt-4">
              <p className="text-base text-agri-primary/70 dark:text-gray-300/80 font-medium">{t("noAccount")}</p>
              <button onClick={onRegister} className="btn-link text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-agri-primary/30">
                🌱 {t("createNewProfile")}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Visual/brand panel */}
        <div className="hidden md:flex items-center justify-center text-white p-10 lg:p-12 relative overflow-hidden bg-gradient-to-br from-indigo-600 to-purple-600">
          <div className="absolute inset-0 bg-agri-pattern opacity-10"></div>
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-16 translate-x-16"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/10 rounded-full translate-y-12 -translate-x-12"></div>
          <div className="space-y-6 text-center relative z-10">
            <img src="/logo_new.png" alt="Agri‑Sahayak" className="w-20 h-20 rounded-3xl mx-auto mb-6 backdrop-blur-sm bg-white/20 p-2" />
            <h2 className="text-3xl font-bold mb-2 tracking-tight">AI Powered End to End System</h2>
            <p className="text-white/85 mb-2 text-sm uppercase tracking-wide opacity-80">AI Powered End to End System</p>
            <div className="space-y-4 text-base opacity-95 text-left w-full max-w-xs mx-auto">
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                  <Globe2 size={18} />
                </span>
                <span className="leading-tight">Smart, multilingual advisory</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                  <Mic2 size={18} />
                </span>
                <span className="leading-tight">Voice-powered assistance</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                  <ImageIcon size={18} />
                </span>
                <span className="leading-tight">AI image analysis</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                  <LineChart size={18} />
                </span>
                <span className="leading-tight">Real‑time market insights</span>
              </div>
            </div>
            <div className="pt-6">
              <p className="text-white/85 text-sm font-medium tracking-wide">
                Empowering farmers with intelligent technology
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Welcome;
