import React, { useMemo, useState } from "react";
import axios from "axios";
import locationData from "./locationData";
import { useTranslation } from "react-i18next";
import { ArrowLeft, MapPin, Sprout, Globe2, PhoneCall } from "lucide-react";

const Profile = ({ onCreated, onBack }) => {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [stateName, setStateName] = useState("");
  const [district, setDistrict] = useState("");
  const [crop, setCrop] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [language, setLanguage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError(t("nameRequired"));
      return;
    }

    if (!phoneNumber.trim()) {
      setError(t("phoneNumberRequired"));
      return;
    }

    try {
      setIsLoading(true);
      const res = await axios.post("http://127.0.0.1:8000/create_profile", {
        name: name.trim(),
        email: email.trim(),
        password: password.trim(),
        phone_number: phoneNumber.trim(),
        district: district.trim() || null,
        crop: crop.trim() || null,
        state: stateName || null,
        language: language || null,
      });
      const { user_id } = res.data || {};
      if (!user_id) throw new Error("Invalid server response");
      localStorage.setItem("user_id", user_id);
      localStorage.setItem("user_name", name.trim());
      onCreated?.(user_id);
    } catch (err) {
      const serverMsg = err?.response?.data?.detail || err?.message;
      setError(serverMsg || t("failedToCreateProfile"));
    } finally {
      setIsLoading(false);
    }
  };

  const availableStates = useMemo(() => Object.keys(locationData), []);
  const availableDistricts = useMemo(
    () => (stateName ? locationData[stateName] || [] : []),
    [stateName]
  );

  const handleStateChange = (e) => {
    const value = e.target.value;
    setStateName(value);
    setDistrict("");
  };

  return (
    <div className="min-h-[calc(100vh-64px)] bg-agri-pattern flex items-center justify-center px-4 md:px-8 py-8 md:py-12">
      <div className="auth-card w-full max-w-4xl agri-fade-in">
        <div className="grid grid-cols-1 md:grid-cols-[1.2fr_1fr]">
          <div className="p-8 md:p-10">
            {/* Back to sign-in */}
            {onBack && (
              <div className="mb-4 -mt-2">
                <button
                  type="button"
                  onClick={onBack}
                  className="inline-flex items-center gap-2 text-agri-primary hover:text-agri-success font-semibold px-2 py-1 rounded-xl hover:bg-agri-primary/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-agri-primary/30"
                  aria-label={'Back to SignIn'}
                  title={'Back to SignIn'}
                >
                  <ArrowLeft size={18} />
                  <span>Back to SignIn</span>
                </button>
              </div>
            )}
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 bg-gradient-to-br from-agri-primary to-agri-success rounded-2xl flex items-center justify-center shadow-agri-md">
                <span className="text-white text-xl">👤</span>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-agri-gradient mb-1">
                  {t("createYourProfile")}
                </h2>
                <p className="text-agri-secondary font-medium">
                  Personalized Agricultural Assistant
                </p>
              </div>
            </div>
            {error && <div className="text-sm text-red-700 bg-red-50/90 border border-red-200/50 rounded-2xl px-5 py-4 mb-6 font-medium backdrop-blur-sm">{error}</div>}
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                  {t("name")} *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your full name"
                  className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md"
                />
              </div>

              <div>
                <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                  {t("email")}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address"
                  className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md"
                />
              </div>

              <div>
                <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                  {t("password")}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Create a secure password"
                  className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md"
                />
              </div>

              <div>
                <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                  {t("phoneNumber")} *
                </label>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="Enter your mobile number"
                  className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md"
                />
              </div>

              <div>
                <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                  🌐 {t("selectPreferredLanguage")}
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md"
                >
                  <option value="">{t("selectPreferredLanguage")}</option>
                  <option value="English">🇬🇧 {t("english")}</option>
                  <option value="हिन्दी">🇮🇳 {t("hindi")}</option>
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div>
                  <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                    📍 {t("selectState")}
                  </label>
                  <select
                    value={stateName}
                    onChange={handleStateChange}
                    className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md"
                  >
                    <option value="">{t("selectState")}</option>
                    {availableStates.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                    🏘️ {t("selectDistrict")}
                  </label>
                  <select
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                    className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md disabled:opacity-50"
                    disabled={!stateName}
                  >
                    <option value="">
                      {stateName ? t("selectDistrict") : t("selectStateFirst")}
                    </option>
                    {availableDistricts.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-base font-bold mb-3 text-agri-primary dark:text-gray-300">
                  🌾 {t("primaryCrop")}
                </label>
                <input
                  type="text"
                  value={crop}
                  onChange={(e) => setCrop(e.target.value)}
                  placeholder="e.g., Rice, Wheat, Cotton, Sugarcane"
                  className="input rounded-2xl py-4 px-5 text-base transition-all duration-300 focus:shadow-agri-md"
                />
              </div>

              <button
                type="submit"
                className="btn-primary w-full rounded-2xl py-4 px-8 text-lg font-bold shadow-agri-md hover:shadow-agri-lg transition-all duration-300 hover:scale-[1.02] disabled:hover:scale-100 mt-6"
                disabled={isLoading}
              >
                {isLoading ? '⏳ Creating Profile...' : `🚀 ${t("createProfile")}`}
              </button>
            </form>
          </div>

          {/* Right side visual panel */}
          <div className="hidden md:flex items-center justify-center text-white p-10 relative overflow-hidden" style={{ background: 'var(--agri-gradient-primary)' }}>
            <div className="absolute inset-0 bg-agri-pattern opacity-10"></div>
            <div className="absolute top-0 right-0 w-28 h-28 bg-white/10 rounded-full -translate-y-14 translate-x-14"></div>
            <div className="absolute bottom-0 left-0 w-20 h-20 bg-white/10 rounded-full translate-y-10 -translate-x-10"></div>
            <div className="space-y-6 text-center relative z-10">
              <div className="w-18 h-18 bg-white/20 rounded-3xl flex items-center justify-center mx-auto mb-4 backdrop-blur-sm">
                <img src="/logo_new.png" alt="Agri‑Sahayak" className="w-14 h-14 rounded-2xl bg-white/15 p-2" />
              </div>
              <h3 className="text-2xl font-bold mb-1">AI Powered End to End System</h3>
              <p className="text-white/85 text-xs uppercase tracking-wide opacity-80 mb-2">AI Powered End to End System</p>
              <div className="space-y-4 text-base opacity-95 text-left w-full max-w-xs mx-auto">
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                    <MapPin size={18} />
                  </span>
                  <span className="leading-tight">Location‑based advice</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                    <Sprout size={18} />
                  </span>
                  <span className="leading-tight">Crop‑specific guidance</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                    <Globe2 size={18} />
                  </span>
                  <span className="leading-tight">Multilingual support</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white/10">
                    <PhoneCall size={18} />
                  </span>
                  <span className="leading-tight">Voice & SMS alerts</span>
                </div>
              </div>
              <div className="pt-4">
                <p className="text-white/85 text-sm font-medium tracking-wide">
                  Personalized agricultural intelligence
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
