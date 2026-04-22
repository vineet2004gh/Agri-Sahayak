import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import ReactAnimatedWeather from 'react-animated-weather';
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';
import { Sun, Cloud, CloudRain, CloudSnow, ArrowUp, ArrowDown, Calendar, AlertTriangle, Info, CheckCircle, Thermometer, Droplets, TrendingUp, Bell, CloudLightning, Wind, Sunrise, Sunset, Trash2, Edit, PlusCircle, PhoneCall } from 'lucide-react';
import PriceTrendChart from './PriceTrendChart';
// Chat is rendered by App.js at the bottom in embedded mode; avoid duplicating it here.

// Simple client-side mapping for common OpenWeather descriptions to Hindi
const toHindiWeatherDesc = (desc) => {
  if (!desc) return '';
  const key = String(desc).toLowerCase();
  const map = {
    'clear sky': 'निर्मल आकाश',
    'few clouds': 'कुछ बादल',
    'scattered clouds': 'बिखरे बादल',
    'broken clouds': 'टूटे बादल',
    'overcast clouds': 'घने बादल',
    'light rain': 'हल्की बारिश',
    'moderate rain': 'मध्यम बारिश',
    'heavy intensity rain': 'तेज़ बारिश',
    'very heavy rain': 'अत्यधिक बारिश',
    'thunderstorm': 'आंधी-तूफ़ान',
    'drizzle': 'बूंदाबांदी',
    'mist': 'धुंध',
    'haze': 'कोहरा',
    'fog': 'कोहरा',
    'snow': 'बर्फबारी',
    'light snow': 'हल्की बर्फबारी',
  };
  return map[key] || desc; // fallback to original if unknown
};

// Translate canonical crop names to Hindi for UI labels
const toHindiCrop = (crop) => {
  const c = (crop || '').toString().trim().toLowerCase();
  const map = {
    wheat: 'गेहूं',
    rice: 'धान/चावल',
    sugarcane: 'गन्ना',
    cotton: 'कपास',
    maize: 'मक्का',
    soybean: 'सोयाबीन',
    mustard: 'सरसों',
    onion: 'प्याज',
    potato: 'आलू',
    tomato: 'टमाटर',
    ragi: 'रागी (मंडुआ/नाचनी)',
    millet: 'बाजरा (मिलेट)'
  };
  return map[c] || crop;
};

// Fallback translator for crop activity strings to Hindi when i18n key is missing
const toHindiActivity = (text) => {
  if (!text) return '';
  let s = String(text);
  const phrases = [
    // Multi-word phrases first (order matters for regex replacement)
    [/land preparation and levelling/gi, 'भूमि तैयारी एवं समतलीकरण'],
    [/soil testing and nutrient planning/gi, 'मिट्टी परीक्षण एवं पोषक तत्व योजना'],
    [/green manure crop sowing/gi, 'हरी खाद की बुवाई'],
    [/pre-kharif field preparation/gi, 'खरीफ-पूर्व खेत की तैयारी'],
    [/input procurement \(seed, fertilizer\)/gi, 'इनपुट खरीद (बीज, उर्वरक)'],
    [/input procurement/gi, 'इनपुट खरीद'],
    [/nursery bed preparation/gi, 'नर्सरी बेड की तैयारी'],
    [/seed treatment and soaking/gi, 'बीज उपचार एवं भिगोना'],
    [/seed procurement planning/gi, 'बीज खरीद की योजना'],
    [/straw management and composting/gi, 'पुआल प्रबंधन एवं कम्पोस्ट'],
    [/rabi crop planning/gi, 'रबी फसल की योजना'],
    [/rabi rice harvesting \(if applicable\)/gi, 'रबी धान की कटाई (यदि लागू हो)'],
    [/rabi rice harvesting/gi, 'रबी धान की कटाई'],
    [/summer ploughing/gi, 'ग्रीष्मकालीन जुताई'],
    [/nursery preparation/gi, 'नर्सरी तैयारी'],
    [/nursery management/gi, 'नर्सरी प्रबंधन'],
    [/seed selection/gi, 'बीज चयन'],
    [/seed treatment/gi, 'बीज उपचार'],
    [/seed rate/gi, 'बीज दर'],
    [/water management/gi, 'जल प्रबंधन'],
    [/weed management/gi, 'खरपतवार प्रबंधन'],
    [/weed control/gi, 'खरपतवार नियंत्रण'],
    [/nutrient application/gi, 'पोषक तत्व का उपयोग'],
    [/nutrient spray/gi, 'पोषक तत्व स्प्रे'],
    [/pest and disease control/gi, 'कीट एवं रोग नियंत्रण'],
    [/pest and disease scouting/gi, 'कीट एवं रोग निरीक्षण'],
    [/pest monitoring/gi, 'कीट निगरानी'],
    [/pest control/gi, 'कीट नियंत्रण'],
    [/pest management/gi, 'कीट प्रबंधन'],
    [/disease management/gi, 'रोग प्रबंधन'],
    [/disease prevention/gi, 'रोग निवारण'],
    [/disease scouting/gi, 'रोग निरीक्षण'],
    [/mid-season irrigation/gi, 'मध्य-मौसम सिंचाई'],
    [/flowering stage care/gi, 'फूल आने की अवस्था की देखभाल'],
    [/grain filling monitoring/gi, 'दाना भरने की निगरानी'],
    [/grain filling/gi, 'दाना भरना'],
    [/post[- ]harvest handling/gi, 'कटाई के बाद प्रबंधन'],
    [/post[- ]harvest/gi, 'कटाई के बाद'],
    [/growth monitoring/gi, 'वृद्धि की निगरानी'],
    [/land preparation/gi, 'भूमि की तैयारी'],
    [/field preparation/gi, 'खेत की तैयारी'],
    [/fertilizer application/gi, 'उर्वरक का उपयोग'],
    [/fertilizer top dressing/gi, 'उर्वरक ऊपरी आवरण'],
    [/first irrigation/gi, 'पहली सिंचाई'],
    [/second irrigation/gi, 'दूसरी सिंचाई'],
    [/irrigation management/gi, 'सिंचाई प्रबंधन'],
    [/pre-harvest check/gi, 'कटाई-पूर्व जांच'],
    [/harvesting preparation/gi, 'कटाई की तैयारी'],
    [/bollworm management/gi, 'बॉलवॉर्म प्रबंधन'],
    [/stem borer/gi, 'तना छेदक'],
    [/ear head emergence care/gi, 'बाली निकलने की देखभाल'],
    [/ear emergence care/gi, 'बाली निकलने की देखभाल'],
    [/foliar nutrition/gi, 'पत्तियों पर पोषक स्प्रे'],
    [/physiological maturity/gi, 'शारीरिक परिपक्वता'],
    [/threshing and drying/gi, 'गहाई एवं सुखाई'],
    [/drying and storage/gi, 'सुखाई एवं भंडारण'],
    [/downy mildew/gi, 'डाउनी मिल्ड्यू'],
    [/moisture conservation/gi, 'नमी संरक्षण'],
    [/gap filling/gi, 'रिक्त स्थान भरना'],
    [/earthing up/gi, 'मिट्टी चढ़ाना'],
    [/propping and tying/gi, 'सहारा एवं बांधना'],
    [/tying and propping/gi, 'बांधना एवं सहारा'],
    [/top dressing/gi, 'ऊपरी उर्वरक'],
    [/ratoon management/gi, 'पेड़ी प्रबंधन'],
    [/ripening monitoring/gi, 'पकने की निगरानी'],
    [/seed cane selection/gi, 'बीज गन्ना चयन'],
    [/field cleaning/gi, 'खेत की सफाई'],
    [/pre-monsoon care/gi, 'मानसून-पूर्व देखभाल'],
    [/monsoon management/gi, 'मानसून प्रबंधन'],
    [/drainage check/gi, 'जल निकासी जांच'],
    [/picking of cotton/gi, 'कपास चुनाई'],
    [/quality management/gi, 'गुणवत्ता प्रबंधन'],
    [/second picking/gi, 'दूसरी चुनाई'],
    [/pest clean-up/gi, 'कीट सफाई'],
    [/nitrogen top dressing/gi, 'नाइट्रोजन ऊपरी उर्वरक'],
    [/tasseling and silking care/gi, 'नर एवं मादा फूल की देखभाल'],
    [/direct sowing/gi, 'सीधी बुवाई'],
    [/nursery raising/gi, 'नर्सरी उगाना'],
    [/line sowing/gi, 'कतार में बुवाई'],
    [/sowing/gi, 'बुवाई'],
    [/nursery/gi, 'नर्सरी'],
    [/transplanting/gi, 'रोपाई'],
    [/thinning/gi, 'छंटाई'],
    [/weeding/gi, 'निराई'],
    [/interculture|intercultural operations/gi, 'अंतर-क्रिया संचालन'],
    [/irrigation/gi, 'सिंचाई'],
    [/fertilizer/gi, 'उर्वरक'],
    [/manuring/gi, 'खत डालना'],
    [/spraying/gi, 'स्प्रे'],
    [/plant protection/gi, 'फसल संरक्षण'],
    [/mulching/gi, 'मल्चिंग'],
    [/pruning/gi, 'छँटाई'],
    [/harvesting/gi, 'कटाई'],
    [/storage/gi, 'भंडारण'],
    [/scheduling/gi, 'अनुसूची'],
    [/ploughing/gi, 'जुताई'],
    [/levelling/gi, 'समतलीकरण'],
    [/composting/gi, 'कम्पोस्ट बनाना'],
    [/if applicable/gi, 'यदि लागू हो'],
    [/if required/gi, 'यदि आवश्यक हो'],
    [/if any/gi, 'यदि कोई हो'],
    [/as needed/gi, 'आवश्यकतानुसार'],
  ];
  for (const [re, hi] of phrases) s = s.replace(re, hi);
  // common connectors/units
  s = s.replace(/kg\/ha/gi, 'किग्रा/हे');
  s = s.replace(/l\/ha/gi, 'ली/हे');
  s = s.replace(/per hectare/gi, 'प्रति हेक्टेयर');
  s = s.replace(/per acre/gi, 'प्रति एकड़');
  s = s.replace(/apply/gi, 'लगाएँ');
  s = s.replace(/monitor/gi, 'निगरानी करें');
  s = s.replace(/recommended/gi, 'अनुशंसित');
  return s;
};

// Lightweight translation for alert titles/messages to Hindi
const toHindiAlert = (text) => {
  if (!text) return '';
  let s = String(text);
  const map = [
    [/High Wind Warning/gi, 'तेज़ हवा की चेतावनी'],
    [/Thunderstorm Warning/gi, 'आंधी-तूफ़ान की चेतावनी'],
    [/Heavy Rain Alert/gi, 'भारी बारिश अलर्ट'],
    [/Heat Wave Alert/gi, 'लू (हीट वेव) अलर्ट'],
    [/Cold Wave Alert/gi, 'शीत लहर अलर्ट'],
    [/Fog Alert/gi, 'कोहरे का अलर्ट'],
    [/hail/gi, 'ओलावृष्टि'],
    [/wind/gi, 'हवा'],
    [/speed/gi, 'गति'],
    [/warning/gi, 'चेतावनी'],
    [/alert/gi, 'अलर्ट'],
    [/tomorrow/gi, 'कल'],
    [/today/gi, 'आज'],
    [/expected/gi, 'संभावना'],
    [/protect/gi, 'सुरक्षित रखें'],
    [/structures/gi, 'संरचनाएं'],
    [/plants/gi, 'पौधे'],
    [/young plants/gi, 'नवीन पौधे'],
    [/secure/gi, 'मजबूत करें'],
    [/rain/gi, 'बारिश'],
    [/thunderstorm/gi, 'आंधी-तूफ़ान'],
    [/temperature/gi, 'तापमान'],
    [/humidity/gi, 'आर्द्रता'],
  ];
  for (const [re, hi] of map) s = s.replace(re, hi);
  // units and connectors
  s = s.replace(/km\/?h|kmh/gi, 'किमी/घं');
  s = s.replace(/m\/?s/gi, 'मी/से');
  s = s.replace(/\bup to\b/gi, 'तक');
  s = s.replace(/\bpossible\b/gi, 'संभव');
  return s;
};

const getWeatherKey = (main) => {
  const m = (main || '').toLowerCase();
  if (m.includes('thunder')) return 'thunderstorm';
  if (m.includes('drizzle')) return 'drizzle';
  if (m.includes('rain')) return 'rain';
  if (m.includes('snow')) return 'snow';
  if (m.includes('cloud')) return 'clouds';
  if (m.includes('mist')) return 'mist';
  if (m.includes('fog')) return 'fog';
  if (m.includes('haze')) return 'haze';
  return 'clear';
};

const weatherIconMap = {
  'thunderstorm': 'RAIN',
  'drizzle': 'RAIN',
  'rain': 'RAIN',
  'snow': 'SNOW',
  'clouds': 'CLOUDY',
  'mist': 'FOG',
  'fog': 'FOG',
  'haze': 'FOG',
  'clear': 'CLEAR_DAY',
};

const AnimatedWeatherIcon = ({ condition, ...props }) => {
  const icon = weatherIconMap[condition] || 'CLEAR_DAY';
  return <ReactAnimatedWeather icon={icon} color="#fff" size={props.size || 48} animate={true} />;
};

const getGradientByWeather = (main) => {
  const key = getWeatherKey(main);
  const gradients = {
    thunderstorm: 'from-gray-700 to-gray-900',
    rain: 'from-blue-400 to-blue-600',
    drizzle: 'from-blue-300 to-blue-500',
    snow: 'from-white to-gray-300 text-gray-800',
    clouds: 'from-sky-400 to-sky-600',
    mist: 'from-gray-400 to-gray-500',
    fog: 'from-gray-400 to-gray-500',
    haze: 'from-yellow-400 to-yellow-600',
    clear: 'from-cyan-400 to-cyan-600',
  };
  return gradients[key] || gradients.clear;
};

const WeatherIcon = ({ condition, ...props }) => {
  const iconMap = {
    thunderstorm: CloudLightning,
    rain: CloudRain,
    drizzle: CloudRain,
    snow: CloudSnow,
    clouds: Cloud,
    mist: Wind,
    fog: Wind,
    haze: Wind,
    clear: Sun,
  };
  const IconComponent = iconMap[condition] || Sun;
  if (condition === 'animated') {
    return <AnimatedWeatherIcon {...props} />
  }
  return <IconComponent {...props} />;
};

const Card = ({ title, children, right, className }) => {
  return (
    <div className={`agri-card hover:shadow-agri-xl transition-all duration-300 ease-in-out ${className}`}>
      <div className="px-5 py-4 border-b border-agri-primary/10 dark:border-gray-800 flex items-center justify-between">
        <h3 className="text-base font-bold text-agri-primary dark:text-agri-success">{title}</h3>
        {right}
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
};

const DailyWeatherChart = ({ data }) => {
  if (!data || data.length < 2) return null;

  const chartData = data.map(d => ({
    name: new Date(d.dt * 1000).toLocaleTimeString([], { hour: '2-digit' }),
    temp: Math.round(d.main.temp),
  }));

  return (
    <div className="w-full h-16 mt-2">
      <ResponsiveContainer>
        <LineChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
          <XAxis dataKey="name" tick={{ fontSize: 10 }} strokeOpacity={0.5} />
          <YAxis tick={{ fontSize: 10 }} strokeOpacity={0.5} />
          <Line type="monotone" dataKey="temp" stroke="#ffffff" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export const WeatherWidget = ({ userId }) => {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) return;
    (async () => {
      try {
        setLoading(true);
        const res = await axios.get(`http://127.0.0.1:8000/weather-forecast/${userId}`);
        setData(res.data);
      } catch (_) {
        setData(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [userId]);

  const weatherKey = getWeatherKey(data?.current?.weather?.[0]?.main);
  const gradientClass = getGradientByWeather(data?.current?.weather?.[0]?.main);

  const isHi = i18n.language === 'hi';
  if (loading) return <Card title={isHi ? 'मौसम' : (t('weather') || 'Weather')}><div className="h-40 animate-pulse" /></Card>;
  if (!data || !data.daily) return <Card title={isHi ? 'मौसम' : (t('weather') || 'Weather')}><p className="text-sm text-gray-500">{isHi ? 'पूर्वानुमान उपलब्ध नहीं' : (t('noForecastData') || 'No forecast data')}</p></Card>;

  // Guard against partial/missing fields from API
  const title = (isHi ? 'मौसम' : (t('weather') || 'Weather')) + (data.district ? ` • ${String(data.district).toUpperCase()}` : '');
  const current = data?.current || {};
  const today = (data?.daily && data.daily.length > 0 ? data.daily[0] : {}) || {};
  const currTemp = Number.isFinite(current?.temp) ? Math.round(current.temp) : null;
  const currDesc = current?.weather?.[0]?.description || (isHi ? 'डेटा उपलब्ध नहीं' : 'No data');
  // support either flat temp_max/min or nested temp.max/min
  const tMax = Number.isFinite(today?.temp_max) ? Math.round(today.temp_max) : (Number.isFinite(today?.temp?.max) ? Math.round(today.temp.max) : null);
  const tMin = Number.isFinite(today?.temp_min) ? Math.round(today.temp_min) : (Number.isFinite(today?.temp?.min) ? Math.round(today.temp.min) : null);
  const currHum = Number.isFinite(current?.humidity) ? current.humidity : null;
  const currWind = Number.isFinite(current?.wind_speed) ? current.wind_speed : null;

  return (
    <Card title={title} right={<Sun size={18} className="text-agri-info" />} className="bg-gradient-to-br from-nature-sky/20 to-agri-info/10 dark:bg-agri-info/20 border-agri-info/30 col-span-1 md:col-span-2 lg:col-span-3 overflow-hidden relative">
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-agri-info/10 to-transparent rounded-full -translate-y-16 translate-x-16"></div>
      <div className="flex flex-col md:flex-row gap-6 items-center relative z-10">

        {/* Left Side: Main Info */}
        <div className="flex items-center gap-6 flex-1">
          <div className="w-20 h-20 bg-white/20 rounded-3xl flex items-center justify-center backdrop-blur-sm border border-white/30">
            <AnimatedWeatherIcon condition={weatherKey} size={72} color="#4682B4" />
          </div>
          <div>
            <p className="text-5xl font-light text-agri-primary dark:text-white mb-1">{currTemp !== null ? `${currTemp}°` : '--'}</p>
            <p className="text-lg font-bold text-agri-secondary dark:text-gray-300 capitalize mb-1">{isHi ? toHindiWeatherDesc(currDesc) : currDesc}</p>
            <p className="text-sm text-agri-primary/70 dark:text-gray-400 font-medium">
              {isHi
                ? `अधिकतम ${tMax !== null ? tMax + '°' : '--'} / न्यूनतम ${tMin !== null ? tMin + '°' : '--'}`
                : `H: ${tMax !== null ? tMax + '°' : '--'} / L: ${tMin !== null ? tMin + '°' : '--'}`}
            </p>
          </div>
        </div>

        {/* Middle: Details */}
        <div className="flex-1 grid grid-cols-2 gap-x-8 gap-y-4 text-sm text-agri-primary dark:text-gray-300">
          <div className="flex items-center gap-3 bg-white/20 rounded-2xl px-4 py-3 backdrop-blur-sm">
            <Droplets size={18} className="text-agri-info" />
            <span className="font-semibold">{isHi ? `${currHum !== null ? currHum : '--'}% आर्द्रता` : `${currHum !== null ? currHum : '--'}% Humidity`}</span>
          </div>
          <div className="flex items-center gap-3 bg-white/20 rounded-2xl px-4 py-3 backdrop-blur-sm">
            <Wind size={18} className="text-agri-info" />
            <span className="font-semibold">{isHi ? `${currWind !== null ? currWind : '--'} m/s हवा` : `${currWind !== null ? currWind : '--'} m/s Wind`}</span>
          </div>
          <div className="flex items-center gap-3 bg-white/20 rounded-2xl px-4 py-3 backdrop-blur-sm col-span-2">
            <CloudRain size={18} className="text-agri-info" />
            <span className="font-semibold">{isHi ? `${Math.round((today.pop || 0) * 100)}% वर्षा की संभावना` : `${Math.round((today.pop || 0) * 100)}% Rain Chance`}</span>
          </div>
        </div>

        {/* Right Side: 3-Day Forecast */}
        <div className="flex-1 grid grid-cols-3 gap-3 text-center">
          {(data?.daily || []).slice(1, 4).map((d, i) => (
            <div key={i} className="p-4 rounded-2xl bg-white/30 dark:bg-gray-800/50 backdrop-blur-sm border border-white/20 hover:bg-white/40 transition-all duration-300">
              <p className="text-sm font-bold text-agri-primary dark:text-white mb-2">{d?.date ? new Date(d.date).toLocaleDateString(i18n.language, { weekday: 'short' }) : '--'}</p>
              <div className="w-10 h-10 mx-auto my-2">
                <AnimatedWeatherIcon condition={getWeatherKey(d?.weather?.[0]?.main)} size={40} color="#4682B4" />
              </div>
              <p className="text-sm font-semibold text-agri-secondary dark:text-gray-300">
                {Number.isFinite(d?.temp_max) || Number.isFinite(d?.temp?.max) ? Math.round(Number.isFinite(d?.temp_max) ? d.temp_max : d.temp.max) : '--'}°/
                {Number.isFinite(d?.temp_min) || Number.isFinite(d?.temp?.min) ? Math.round(Number.isFinite(d?.temp_min) ? d.temp_min : d.temp.min) : '--'}°
              </p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};

export const MarketTicker = ({ userId, onOpenChart }) => {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        const res = await axios.get(`http://127.0.0.1:8000/market-price-history/${userId}`);
        setData(res.data);
      } catch (error) {
        console.error("Error fetching market prices:", error);
        setData(null);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [userId]);

  const isHi = i18n.language === 'hi';
  if (loading) {
    return <Card title={isHi ? 'बाज़ार भाव' : t('MarketPrices')}><div className="h-32 animate-pulse bg-gray-200 dark:bg-gray-700 rounded-md" /></Card>;
  }

  if (!data || !data.nearby_prices || data.nearby_prices.length === 0) {
    return <Card title={isHi ? 'बाज़ार भाव' : t('MarketPrices')}><p className="text-sm text-gray-500">{isHi ? 'हाल के दाम उपलब्ध नहीं' : t('noRecentPrices')}</p></Card>;
  }

  const cropLabel = data?.crop ? (isHi ? toHindiCrop(data.crop) : String(data.crop).toUpperCase()) : '';
  const title = ((isHi ? 'बाज़ार भाव' : (t('MarketPrices') || 'Market Prices'))) + (cropLabel ? ` • ${cropLabel}` : '');

  return (
    <Card title={title} right={<button onClick={onOpenChart} aria-label={t('viewPriceChart')} className="p-2 rounded-lg hover:bg-agri-accent/10 transition-colors"><TrendingUp size={18} className="text-agri-accent hover:text-agri-warning" /></button>}>
      <div className="space-y-3" >
        {data.nearby_prices.map((item, index) => {
          const isUp = item.trend === 'up';
          return (
            <div
              key={index}
              onClick={onOpenChart}
              className={`flex justify-between items-center p-4 rounded-2xl cursor-pointer transition-all duration-300 hover:scale-[1.02] ${item.is_user_district ? 'bg-gradient-to-r from-agri-success/20 to-agri-success/10 border-2 border-agri-success/30' : 'hover:bg-agri-primary/5 dark:hover:bg-gray-800/50 border border-transparent hover:border-agri-primary/20'}`}>
              <div>
                <p className="font-bold text-agri-primary dark:text-gray-100">{item.district}</p>
                {item.is_user_district && <p className="text-sm text-agri-success dark:text-agri-success font-medium flex items-center gap-1">📍 {isHi ? 'आपका जिला' : t('YourDistrict')}</p>}
              </div>
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-full ${isUp ? 'bg-agri-success/20' : 'bg-red-500/20'}`}>
                  {isUp ? <ArrowUp size={16} className="text-agri-success" /> : <ArrowDown size={16} className="text-red-500" />}
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg text-agri-primary dark:text-white">₹{String(item.price).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}</p>
                  <p className="text-xs text-agri-secondary dark:text-gray-400 font-medium">{isHi ? 'प्रति क्विंटल' : 'per quintal'}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};


export const CropActivityCalendar = ({ userId }) => {
  const { t, i18n } = useTranslation();
  const [user, setUser] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) return;
    (async () => {
      try {
        const res = await axios.get(`http://127.0.0.1:8000/users/${userId}`);
        setUser(res.data.user);
      } catch (_) {
        setUser(null);
      }
    })();
  }, [userId]);

  const crop = useMemo(() => (user?.crop || '').toLowerCase(), [user]);

  useEffect(() => {
    if (!crop) return;

    (async () => {
      try {
        setLoading(true);
        const monthName = new Date().toLocaleDateString('en-US', { month: 'long' }).toLowerCase();
        const res = await axios.get(`http://127.0.0.1:8000/crop_activities?crop=${crop}&month=${monthName}`);
        console.debug('[CropActivityCalendar] crop, month, response', crop, monthName, res.data);
        setActivities(res.data.activities || []);
      } catch (err) {
        setActivities([]);
      } finally {
        setLoading(false);
      }
    })();

  }, [crop]);

  const isHi = i18n.language === 'hi';
  const tTitle = t('cropActivityCalendar');
  const titleBase = (tTitle && tTitle !== 'cropActivityCalendar')
    ? tTitle
    : (isHi ? 'फसल गतिविधि कैलेंडर' : 'CropActivity Calendar');
  const title = titleBase + (crop ? ` • ${String(crop).toUpperCase()}` : '');

  return (
    <Card title={title} right={<Calendar size={18} className="text-agri-success" />} className="bg-gradient-to-br from-agri-success/10 to-nature-leaf/10 dark:bg-agri-success/20 border-agri-success/30 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-agri-success/10 to-transparent rounded-full -translate-y-12 translate-x-12"></div>
      <div className="mb-4 relative z-10">
        <h4 className="font-bold text-agri-primary dark:text-gray-100 text-lg">
          🗓️ {new Date().toLocaleDateString(i18n.language, { month: 'long', year: 'numeric' })}
        </h4>
      </div>
      {loading ? (
        <div className="h-20 agri-loading" />
      ) : (
        <ul className="space-y-4 relative z-10">
          {activities.length === 0 ? (
            <p className="text-sm text-agri-primary/70 font-medium">{isHi ? 'इस माह के लिए कोई गतिविधि नहीं' : (t('noActivities') || 'No activities for this month')}</p>
          ) : (
            activities.map((act, idx) => (
              <li key={idx} className="flex items-start p-3 bg-white/30 dark:bg-gray-800/30 rounded-2xl backdrop-blur-sm border border-agri-success/20 hover:bg-white/50 transition-all duration-300">
                <div className="flex-shrink-0 mt-1">
                  <CheckCircle className="h-5 w-5 text-agri-success" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-semibold text-agri-primary dark:text-gray-200">
                    {(() => {
                      const norm = String(act).toLowerCase().replace(/[^a-z0-9]/gi, '');
                      const keyCrop = `cropActivities.${crop}.${norm}`;
                      let translated = t(keyCrop, { defaultValue: act });
                      if (translated === act) {
                        const keyCommon = `cropActivities.common.${norm}`;
                        translated = t(keyCommon, { defaultValue: act });
                      }
                      return isHi ? toHindiActivity(translated) : translated;
                    })()}
                  </p>
                </div>
              </li>
            ))
          )}
        </ul>
      )}
    </Card>
  );
};

export const RecentAlertsPanel = ({ userId }) => {
  const { t, i18n } = useTranslation();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) return;
    (async () => {
      try {
        setLoading(true);
        const res = await axios.get(`http://127.0.0.1:8000/weather-alerts/${userId}`);
        setAlerts(res.data.alerts || []);
      } catch (_) {
        setAlerts([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [userId]);

  const isHi = i18n.language === 'hi';
  const severityMap = {
    high: {
      label: isHi ? 'चेतावनी' : t('alertWarning'),
      icon: AlertTriangle,
      colorClasses: 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300',
      iconColor: 'text-red-500',
    },
    medium: {
      label: isHi ? 'सतर्क' : t('alertWatch'),
      icon: Info,
      colorClasses: 'bg-yellow-50 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
      iconColor: 'text-yellow-500',
    },
    low: {
      label: isHi ? 'सलाह' : t('alertAdvisory'),
      icon: CheckCircle,
      colorClasses: 'bg-blue-50 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
      iconColor: 'text-blue-500',
    },
  };

  return (
    <Card title={isHi ? 'हालिया अलर्ट' : t('RecentAlerts')} right={<Bell size={18} className="text-agri-warning" />}>
      {loading ? (
        <div className="h-28 agri-loading" />
      ) : alerts.length === 0 ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-agri-success/20 rounded-full flex items-center justify-center">
            <CheckCircle size={32} className="text-agri-success" />
          </div>
          <p className="text-sm text-agri-primary font-medium">{isHi ? 'कोई हालिया अलर्ट नहीं' : t('noRecentAlerts')}</p>
        </div>
      ) : (
        <ul className="space-y-4">
          {alerts.slice(0, 3).map((a, idx) => {
            const severity = severityMap[a.severity] || {
              label: a.severity,
              icon: Info,
              colorClasses: 'bg-gray-100/80 text-gray-800 dark:bg-gray-800/80 dark:text-gray-300 border-gray-200',
              iconColor: 'text-gray-500',
            };
            const Icon = severity.icon;
            return (
              <li key={idx} className={`flex items-start p-4 rounded-2xl backdrop-blur-sm border transition-all duration-300 hover:scale-[1.02] ${severity.colorClasses}`}>
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white/50 flex items-center justify-center mr-4">
                  <Icon className={`h-5 w-5 ${severity.iconColor}`} />
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-baseline mb-2">
                    <p className="text-sm font-bold">{isHi ? toHindiAlert(a.title) : a.title}</p>
                    <span className="text-xs font-bold uppercase px-2 py-1 rounded-full bg-white/50">{severity.label}</span>
                  </div>
                  <p className="text-sm opacity-90 leading-relaxed">{isHi ? toHindiAlert(a.message) : a.message}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
};

const Dashboard = ({ userId, children, scrollToCall, onScrollComplete }) => {
  const { t, i18n } = useTranslation();
  const [isChartOpen, setChartOpen] = useState(false);
  const [isCalling, setIsCalling] = useState(false);
  const [callMsg, setCallMsg] = useState("");

  useEffect(() => {
    if (scrollToCall) {
      // Small timeout to ensure rendering
      const timer = setTimeout(() => {
        const el = document.getElementById('voice-assistant');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          if (onScrollComplete) onScrollComplete();
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [scrollToCall, onScrollComplete]);

  const handleRequestCall = async () => {
    if (!userId) return;
    setIsCalling(true);
    setCallMsg("");
    try {
      const res = await axios.post('http://127.0.0.1:8000/call/initiate', { user_id: userId });
      const sid = res?.data?.sid || "";
      setCallMsg(sid ? (i18n.language === 'hi' ? 'कॉल शुरू हो गई है। आपका फोन जल्द ही बजेगा।' : 'Call initiated. Your phone will ring shortly.') : (i18n.language === 'hi' ? 'कॉल शुरू हो गई।' : 'Call initiated.'));
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || 'Failed to initiate call';
      setCallMsg(String(detail));
    } finally {
      setIsCalling(false);
    }
  };

  return (
    <div className="space-y-6 md:space-y-8">
      {/* Voice Call Card */}
      <div id="voice-assistant">
        <Card
          title={(i18n.language === 'hi') ? 'वॉइस असिस्टेंट' : (t('VoiceAssistant') || 'Voice Assistant')}
          right={<PhoneCall size={18} className="text-agri-success" />}
          className="bg-gradient-to-r from-agri-success/10 to-agri-primary/10 dark:bg-agri-success/20 border-agri-success/30 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-agri-success/10 to-transparent rounded-full -translate-y-16 translate-x-16"></div>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 relative z-10">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-agri-success/20 rounded-2xl flex items-center justify-center">
                📞
              </div>
              <div>
                <p className="text-base font-semibold text-agri-primary dark:text-gray-200 mb-1">
                  {i18n.language === 'hi' ? 'एआई सहायक से बात करें' : 'Speak with AI Assistant'}
                </p>
                <p className="text-sm text-agri-secondary dark:text-gray-400">
                  {i18n.language === 'hi' ? 'अपनी पसंदीदा भाषा में त्वरित वॉइस सहायता पाएं' : 'Get instant voice support in your preferred language'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {callMsg ? (
                <span className="text-sm text-agri-primary dark:text-gray-400 font-medium">{callMsg}</span>
              ) : null}
              <button
                onClick={handleRequestCall}
                disabled={isCalling}
                className={`px-6 py-3 rounded-2xl text-white font-semibold transition-all duration-300 shadow-agri-md hover:shadow-agri-lg hover:scale-105 ${isCalling ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-r from-agri-success to-agri-primary hover:from-agri-primary hover:to-agri-success'}`}
              >
                {isCalling ? (i18n.language === 'hi' ? '📞 अनुरोध कर रहे…' : '📞 Requesting…') : (i18n.language === 'hi' ? '📞 कॉल का अनुरोध करें' : '📞 Request Call')}
              </button>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <WeatherWidget userId={userId} />
        <RecentAlertsPanel userId={userId} />
        <MarketTicker userId={userId} onOpenChart={() => setChartOpen(true)} />
        <CropActivityCalendar userId={userId} />
      </div>

      {children ? <div className="min-h-0">{children}</div> : null}
      <PriceTrendChart isOpen={isChartOpen} onClose={() => setChartOpen(false)} userId={userId} />
    </div>
  );
}
  ;

export default Dashboard;
