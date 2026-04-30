import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Newspaper, Key, Globe, TrendingUp, X, ExternalLink, Loader2, Users, Sparkles, Rss, Play, Pause, Calendar, ChevronDown } from 'lucide-react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { apiFetch } from '../apiClient'

const REFRESH_INTERVAL = 30 * 60 * 1000 // 30 minutes

// Country metadata: coords, capital, flag
const COUNTRY_META = {
  'السعودية':                   { coords: [45.0, 24.7],   capital: 'الرياض',     flag: '🇸🇦' },
  'المملكة العربية السعودية':   { coords: [45.0, 24.7],   capital: 'الرياض',     flag: '🇸🇦' },
  'الإمارات':                   { coords: [54.0, 24.0],   capital: 'أبو ظبي',    flag: '🇦🇪' },
  'الإمارات العربية المتحدة':   { coords: [54.0, 24.0],   capital: 'أبو ظبي',    flag: '🇦🇪' },
  'مصر':                        { coords: [31.2, 30.0],   capital: 'القاهرة',    flag: '🇪🇬' },
  'العراق':                     { coords: [44.4, 33.3],   capital: 'بغداد',      flag: '🇮🇶' },
  'الأردن':                     { coords: [36.2, 31.9],   capital: 'عمّان',      flag: '🇯🇴' },
  'لبنان':                      { coords: [35.5, 33.9],   capital: 'بيروت',      flag: '🇱🇧' },
  'فلسطين':                     { coords: [35.2, 31.9],   capital: 'القدس',      flag: '🇵🇸' },
  'سوريا':                      { coords: [38.0, 35.0],   capital: 'دمشق',       flag: '🇸🇾' },
  'اليمن':                      { coords: [44.2, 15.5],   capital: 'صنعاء',      flag: '🇾🇪' },
  'عُمان':                      { coords: [57.5, 21.5],   capital: 'مسقط',       flag: '🇴🇲' },
  'عمان':                       { coords: [57.5, 21.5],   capital: 'مسقط',       flag: '🇴🇲' },
  'الكويت':                     { coords: [47.5, 29.3],   capital: 'الكويت',     flag: '🇰🇼' },
  'قطر':                        { coords: [51.2, 25.3],   capital: 'الدوحة',     flag: '🇶🇦' },
  'البحرين':                    { coords: [50.5, 26.0],   capital: 'المنامة',    flag: '🇧🇭' },
  'ليبيا':                      { coords: [17.2, 26.3],   capital: 'طرابلس',     flag: '🇱🇾' },
  'تونس':                       { coords: [9.5, 34.0],    capital: 'تونس',       flag: '🇹🇳' },
  'الجزائر':                    { coords: [3.0, 28.0],    capital: 'الجزائر',    flag: '🇩🇿' },
  'المغرب':                     { coords: [-7.1, 31.8],   capital: 'الرباط',     flag: '🇲🇦' },
  'موريتانيا':                  { coords: [-10.9, 20.3],  capital: 'نواكشوط',    flag: '🇲🇷' },
  'السودان':                    { coords: [32.5, 15.5],   capital: 'الخرطوم',    flag: '🇸🇩' },
  'الصومال':                    { coords: [46.2, 5.2],    capital: 'مقديشو',     flag: '🇸🇴' },
  'جيبوتي':                     { coords: [43.1, 11.6],   capital: 'جيبوتي',     flag: '🇩🇯' },
  'جزر القمر':                  { coords: [44.3, -12.2],  capital: 'موروني',     flag: '🇰🇲' },
  'تركيا':                      { coords: [35.2, 39.9],   capital: 'أنقرة',      flag: '🇹🇷' },
  'إيران':                      { coords: [53.7, 32.4],   capital: 'طهران',      flag: '🇮🇷' },
  'باكستان':                    { coords: [69.3, 30.4],   capital: 'إسلام آباد', flag: '🇵🇰' },
  'أفغانستان':                  { coords: [67.7, 33.9],   capital: 'كابول',      flag: '🇦🇫' },
  'الهند':                      { coords: [78.9, 20.6],   capital: 'نيودلهي',    flag: '🇮🇳' },
  'الصين':                      { coords: [104.2, 35.9],  capital: 'بكين',       flag: '🇨🇳' },
  'روسيا':                      { coords: [105.3, 61.5],  capital: 'موسكو',      flag: '🇷🇺' },
  'الولايات المتحدة':           { coords: [-95.7, 37.1],  capital: 'واشنطن',     flag: '🇺🇸' },
  'أمريكا':                     { coords: [-95.7, 37.1],  capital: 'واشنطن',     flag: '🇺🇸' },
  'بريطانيا':                   { coords: [-3.4, 55.4],   capital: 'لندن',       flag: '🇬🇧' },
  'المملكة المتحدة':            { coords: [-3.4, 55.4],   capital: 'لندن',       flag: '🇬🇧' },
  'فرنسا':                      { coords: [2.2, 46.6],    capital: 'باريس',      flag: '🇫🇷' },
  'ألمانيا':                    { coords: [10.4, 51.2],   capital: 'برلين',      flag: '🇩🇪' },
  'إسبانيا':                    { coords: [-3.7, 40.5],   capital: 'مدريد',      flag: '🇪🇸' },
  'إيطاليا':                    { coords: [12.6, 41.9],   capital: 'روما',       flag: '🇮🇹' },
  'كندا':                       { coords: [-106.3, 56.1], capital: 'أوتاوا',     flag: '🇨🇦' },
  'أستراليا':                   { coords: [133.8, -25.3], capital: 'كانبرا',     flag: '🇦🇺' },
  'اليابان':                    { coords: [138.3, 36.2],  capital: 'طوكيو',      flag: '🇯🇵' },
  'كوريا الجنوبية':             { coords: [127.8, 35.9],  capital: 'سيول',       flag: '🇰🇷' },
  'إسرائيل':                    { coords: [34.9, 31.0],   capital: 'تل أبيب',    flag: '🇮🇱' },
  'إثيوبيا':                    { coords: [40.5, 9.1],    capital: 'أديس أبابا', flag: '🇪🇹' },
  'كينيا':                      { coords: [37.9, -0.02],  capital: 'نيروبي',     flag: '🇰🇪' },
  'نيجيريا':                    { coords: [8.7, 9.1],     capital: 'أبوجا',      flag: '🇳🇬' },
  'جنوب أفريقيا':               { coords: [22.9, -30.6],  capital: 'بريتوريا',   flag: '🇿🇦' },
  'البرازيل':                   { coords: [-51.9, -14.2], capital: 'برازيليا',   flag: '🇧🇷' },
  'الأرجنتين':                  { coords: [-63.6, -38.4], capital: 'بوينس آيرس',flag: '🇦🇷' },
  'المكسيك':                    { coords: [-102.5, 23.6], capital: 'مكسيكو',     flag: '🇲🇽' },
  'إندونيسيا':                  { coords: [113.9, -0.8],  capital: 'جاكرتا',     flag: '🇮🇩' },
  'ماليزيا':                    { coords: [101.7, 4.2],   capital: 'كوالالمبور', flag: '🇲🇾' },
}

// Glossy iOS 26 card wrapper
const GlassCard = ({ children, className = '', style = {}, ...props }) => (
  <div
    className={`relative overflow-hidden rounded-2xl ${className}`}
    style={{
      background: 'linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.05) 100%)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      border: '1px solid rgba(255,255,255,0.12)',
      boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.15), 0 8px 32px rgba(0,0,0,0.3)',
      ...style,
    }}
    {...props}
  >
    {/* iOS specular highlight */}
    <div className="absolute inset-x-0 top-0 h-[1px]" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent)' }} />
    {children}
  </div>
)


export default function HomePage() {
  const mapContainer = useRef(null)
  const mapInstance = useRef(null)
  const [stats, setStats] = useState(null)
  const [userStats, setUserStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [mapReady, setMapReady] = useState(false)
  const layersAdded = useRef(false)

  // Detail panel state
  const [selectedCountry, setSelectedCountry] = useState(null)
  const [countryArticles, setCountryArticles] = useState([])
  const [panelLoading, setPanelLoading] = useState(false)
  const [countryBrief, setCountryBrief] = useState(null)
  const [briefLoading, setBriefLoading] = useState(false)

  // Show-more toggles
  const [showAllSources, setShowAllSources] = useState(false)
  const [showAllKeywords, setShowAllKeywords] = useState(false)
  const [showAllCountries, setShowAllCountries] = useState(false)

  // Timeline state
  const [timeline, setTimeline] = useState(null)     // { days: [...], data: { country: [...counts] } }
  const [timelineIdx, setTimelineIdx] = useState(-1)  // -1 = "all time" (default view)
  const [isPlaying, setIsPlaying] = useState(false)
  const playInterval = useRef(null)

  const fetchData = useCallback(async () => {
    try {
      const [mapRes, userRes] = await Promise.all([
        apiFetch('/api/home/map-data'),
        apiFetch('/api/home/stats'),
      ])
      if (mapRes.ok) setStats(await mapRes.json())
      if (userRes.ok) setUserStats(await userRes.json())
    } catch (err) {
      console.error('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch + 30 min auto-refresh
  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchData])

  // Fetch timeline data
  useEffect(() => {
    apiFetch('/api/home/map-timeline?days=30')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setTimeline(d) })
      .catch(() => {})
  }, [])

  // Play/pause auto-scrub
  useEffect(() => {
    if (isPlaying && timeline) {
      playInterval.current = setInterval(() => {
        setTimelineIdx(prev => {
          const next = prev + 1
          if (next >= timeline.days.length) { setIsPlaying(false); return -1 }
          return next
        })
      }, 600)
    } else {
      if (playInterval.current) clearInterval(playInterval.current)
    }
    return () => { if (playInterval.current) clearInterval(playInterval.current) }
  }, [isPlaying, timeline])

  // Initialize map
  useEffect(() => {
    if (loading) return
    if (!mapContainer.current || mapInstance.current) return

    const timer = setTimeout(() => {
      if (!mapContainer.current || mapInstance.current) return
      const map = new maplibregl.Map({
        container: mapContainer.current,
        style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
        center: [42, 24],
        zoom: 2.8,
        attributionControl: false,
        maxZoom: 10,
        minZoom: 1.5,
      })
      mapInstance.current = map
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
      map.on('load', () => setMapReady(true))
    }, 80)

    return () => {
      clearTimeout(timer)
      if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null }
    }
  }, [loading])

  // Open country panel — use cache first, fallback to API
  const openCountryPanel = useCallback(async (countryName, articleCount) => {
    setSelectedCountry({ name: countryName, count: articleCount, meta: COUNTRY_META[countryName] })
    setCountryBrief(null)
    const cached = stats?.country_articles?.[countryName]
    if (cached && cached.length > 0) {
      setCountryArticles(cached)
      return
    }
    // Fallback: fetch from dedicated endpoint
    setPanelLoading(true)
    setCountryArticles([])
    try {
      const res = await apiFetch(`/api/articles/countries/${encodeURIComponent(countryName)}/articles`)
      if (res.ok) {
        const data = await res.json()
        setCountryArticles(data.articles || data || [])
      }
    } catch (err) {
      console.error('Failed to fetch country articles:', err)
    } finally {
      setPanelLoading(false)
    }
  }, [stats])

  // Generate AI country brief
  const generateCountryBrief = useCallback(async (countryName) => {
    setBriefLoading(true)
    setCountryBrief(null)
    try {
      const res = await apiFetch('/api/ai/country-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ country: countryName }),
      })
      if (res.ok) {
        const data = await res.json()
        setCountryBrief(data.content)
      }
    } catch (err) {
      console.error('Country brief error:', err)
      setCountryBrief('حدث خطأ أثناء إنشاء الملخص.')
    } finally {
      setBriefLoading(false)
    }
  }, [])

  // Build / update WebGL layers (reactive to timeline slider)
  useEffect(() => {
    if (!mapReady || !mapInstance.current || !stats?.countries?.length) return
    const map = mapInstance.current

    // Compute countries data based on timeline position
    let countriesForMap
    if (timelineIdx >= 0 && timeline) {
      // Specific day from timeline
      countriesForMap = Object.entries(timeline.data)
        .map(([name, counts]) => ({ name, count: counts[timelineIdx] || 0 }))
        .filter(c => c.count > 0)
    } else {
      // All-time view (default)
      countriesForMap = stats.countries
    }

    const maxCount = Math.max(...countriesForMap.map(c => c.count), 1)
    const features = countriesForMap
      .filter(c => COUNTRY_META[c.name])
      .map(c => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: COUNTRY_META[c.name].coords },
        properties: { name: c.name, count: c.count, intensity: c.count / maxCount },
      }))
    const geojson = { type: 'FeatureCollection', features }

    // If source exists, just update data
    if (map.getSource('countries-data')) {
      map.getSource('countries-data').setData(geojson)
      return
    }

    map.addSource('countries-data', { type: 'geojson', data: geojson })

    // Heatmap aura
    map.addLayer({ id: 'country-heat', type: 'heatmap', source: 'countries-data', paint: {
      'heatmap-weight': ['get', 'intensity'], 'heatmap-intensity': 0.6,
      'heatmap-radius': ['interpolate', ['linear'], ['get', 'intensity'], 0, 25, 1, 70],
      'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(0,0,0,0)', 0.15, 'rgba(20,184,166,0.08)', 0.3, 'rgba(20,184,166,0.15)',
        0.5, 'rgba(20,184,166,0.25)', 0.7, 'rgba(234,179,8,0.3)', 1, 'rgba(239,68,68,0.4)'],
      'heatmap-opacity': 0.9,
    }})
    // Outer glow
    map.addLayer({ id: 'country-glow-outer', type: 'circle', source: 'countries-data', paint: {
      'circle-radius': ['interpolate', ['linear'], ['get', 'intensity'], 0, 18, 0.5, 28, 1, 42],
      'circle-color': ['interpolate', ['linear'], ['get', 'intensity'], 0, 'rgba(20,184,166,0.15)', 0.5, 'rgba(234,179,8,0.2)', 1, 'rgba(239,68,68,0.25)'],
      'circle-blur': 1,
    }})
    // Inner glow
    map.addLayer({ id: 'country-glow-inner', type: 'circle', source: 'countries-data', paint: {
      'circle-radius': ['interpolate', ['linear'], ['get', 'intensity'], 0, 10, 0.5, 16, 1, 24],
      'circle-color': ['interpolate', ['linear'], ['get', 'intensity'], 0, 'rgba(20,184,166,0.4)', 0.5, 'rgba(234,179,8,0.5)', 1, 'rgba(239,68,68,0.6)'],
      'circle-blur': 0.5,
    }})
    // Core dot
    map.addLayer({ id: 'country-core', type: 'circle', source: 'countries-data', paint: {
      'circle-radius': ['interpolate', ['linear'], ['get', 'intensity'], 0, 5, 0.5, 8, 1, 12],
      'circle-color': ['interpolate', ['linear'], ['get', 'intensity'], 0, '#14b8a6', 0.5, '#eab308', 1, '#ef4444'],
      'circle-stroke-width': 1.5, 'circle-stroke-color': 'rgba(255,255,255,0.7)',
    }})
    // Labels
    map.addLayer({ id: 'country-labels', type: 'symbol', source: 'countries-data', layout: {
      'text-field': ['get', 'count'], 'text-font': ['Open Sans Bold'],
      'text-size': ['interpolate', ['linear'], ['get', 'intensity'], 0, 10, 1, 14],
      'text-offset': [0, -1.8], 'text-allow-overlap': true,
    }, paint: { 'text-color': '#ffffff', 'text-halo-color': 'rgba(0,0,0,0.7)', 'text-halo-width': 1.5 }})

    // Hover
    map.on('mouseenter', 'country-core', () => { map.getCanvas().style.cursor = 'pointer' })
    map.on('mouseleave', 'country-core', () => { map.getCanvas().style.cursor = '' })
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14, className: 'map-hover-popup' })
    map.on('mousemove', 'country-core', (e) => {
      const f = e.features[0]; if (!f) return
      const meta = COUNTRY_META[f.properties.name]
      popup.setLngLat(e.lngLat).setHTML(`
        <div style="direction:rtl;text-align:right;font-family:Cairo,sans-serif;padding:2px 0;">
          <div style="font-size:13px;font-weight:700;color:#f1f5f9;">${meta?.flag || ''} ${f.properties.name}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px;">${f.properties.count} خبر — انقر للتفاصيل</div>
        </div>`).addTo(map)
    })
    map.on('mouseleave', 'country-core', () => popup.remove())
    // Click
    map.on('click', 'country-core', (e) => {
      const f = e.features?.[0]; if (!f) return
      openCountryPanel(f.properties.name, f.properties.count)
      map.flyTo({ center: e.lngLat, zoom: Math.max(map.getZoom(), 4.5), duration: 800 })
    })
    layersAdded.current = true
  }, [stats, mapReady, openCountryPanel, timelineIdx, timeline])

  // Derived data
  const statCards = [
    { label: 'إجمالي الأخبار', value: stats?.total_articles ?? 0, icon: Newspaper, color: '#0f766e', bg: 'rgba(15,118,110,0.1)' },
    { label: 'المستخدمون النشطون', value: stats?.active_users ?? 0, icon: Users, color: '#0f766e', bg: 'rgba(15,118,110,0.1)' },
    { label: 'الدول المغطاة', value: stats?.unique_countries ?? 0, icon: Globe, color: '#0f766e', bg: 'rgba(15,118,110,0.1)' },
    { label: 'أخباري', value: userStats?.total_articles ?? 0, subtitle: `${userStats?.keyword_count ?? 0} كلمة مراقبة`, icon: TrendingUp, color: '#0f766e', bg: 'rgba(15,118,110,0.1)' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)' }}>
            <svg className="w-5 h-5 text-white animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
          </div>
          <span className="text-sm text-slate-400">جاري التحميل...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Interactive Map — top of page */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.5 }}
        className="relative rounded-2xl overflow-hidden"
        style={{ border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 24px rgba(0,0,0,0.1)' }}>

        <div ref={mapContainer} style={{ width: '100%', height: 'calc(100vh - 220px)', minHeight: '500px' }} />

        {/* Legend */}
        <div className="absolute bottom-16 left-4 flex items-center gap-4 px-4 py-2.5 rounded-xl" style={{ background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(8px)' }}>
          <span className="text-[10px] text-slate-400 font-bold tracking-wider">مستوى التغطية</span>
          {[['#14b8a6','منخفض'],['#eab308','متوسط'],['#ef4444','مرتفع']].map(([c, l]) => (
            <div key={l} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: c, boxShadow: `0 0 6px ${c}` }} />
              <span className="text-[10px] text-slate-400">{l}</span>
            </div>
          ))}
        </div>

        {/* Timeline Slider */}
        {timeline && timeline.days.length > 0 && (
          <div className="absolute bottom-0 inset-x-0 px-4 py-3 flex items-center gap-3" dir="ltr"
            style={{ background: 'linear-gradient(0deg, rgba(15,23,42,0.92) 0%, rgba(15,23,42,0.6) 70%, transparent 100%)', backdropFilter: 'blur(6px)' }}>
            {/* Play / Pause */}
            <button
              onClick={() => {
                if (!isPlaying && timelineIdx === -1) setTimelineIdx(0)
                setIsPlaying(p => !p)
              }}
              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors hover:bg-white/10"
              style={{ background: 'rgba(20,184,166,0.25)', border: '1px solid rgba(20,184,166,0.4)' }}
            >
              {isPlaying
                ? <Pause className="w-3.5 h-3.5 text-teal-300" />
                : <Play className="w-3.5 h-3.5 text-teal-300 ml-0.5" />
              }
            </button>
            {/* Date label */}
            <div className="flex items-center gap-1.5 min-w-[110px] flex-shrink-0">
              <Calendar className="w-3 h-3 text-slate-500" />
              <span className="text-[11px] font-semibold text-slate-300 tabular-nums">
                {timelineIdx >= 0
                  ? new Date(timeline.days[timelineIdx]).toLocaleDateString('ar-EG', { month: 'short', day: 'numeric' })
                  : 'الكل'
                }
              </span>
            </div>
            {/* Range slider */}
            <input
              type="range"
              min={0}
              max={timeline.days.length - 1}
              value={timelineIdx >= 0 ? timelineIdx : timeline.days.length - 1}
              onChange={e => { setTimelineIdx(parseInt(e.target.value)); setIsPlaying(false) }}
              className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer timeline-slider"
              style={{ accentColor: '#14b8a6' }}
            />
            {/* Reset to all */}
            <button
              onClick={() => { setTimelineIdx(-1); setIsPlaying(false) }}
              className={`text-[10px] px-2.5 py-1 rounded-full font-semibold transition-all ${
                timelineIdx === -1
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
              }`}
            >
              الكل
            </button>
          </div>
        )}

        {/* ── Country Detail Panel (iOS 26 Glass) ── */}
        <AnimatePresence>
          {selectedCountry && (
            <motion.div
              initial={{ x: 380, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 380, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 260, damping: 28 }}
              className="absolute top-0 right-0 h-full w-[370px] overflow-y-auto z-20"
              style={{
                background: 'linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(15,23,42,0.88) 100%)',
                backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
                borderLeft: '1px solid rgba(255,255,255,0.08)',
              }}
            >
              {/* Specular top line */}
              <div className="absolute inset-x-0 top-0 h-[1px]" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)' }} />

              {/* Header */}
              <div className="sticky top-0 z-10 px-5 pt-5 pb-4" style={{ background: 'rgba(15,23,42,0.97)' }}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{selectedCountry.meta?.flag || '🌍'}</span>
                    <div>
                      <h3 className="text-lg font-bold text-white leading-tight">{selectedCountry.name}</h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">العاصمة: {selectedCountry.meta?.capital || '—'}</p>
                    </div>
                  </div>
                  <button onClick={() => setSelectedCountry(null)}
                    className="w-8 h-8 rounded-xl flex items-center justify-center transition-all hover:bg-white/10 active:scale-90"
                    style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <X className="w-4 h-4 text-slate-400" />
                  </button>
                </div>

                {/* Stats + AI Summary button */}
                <div className="flex items-center gap-2.5">
                  <GlassCard className="px-4 py-3">
                    <div className="text-xl font-bold text-teal-400">{selectedCountry.count}</div>
                    <div className="text-[10px] text-teal-400/60 font-semibold mt-0.5">إجمالي الأخبار</div>
                  </GlassCard>
                  <button
                    onClick={() => generateCountryBrief(selectedCountry.name)}
                    disabled={briefLoading}
                    className="flex-1 flex items-center justify-center gap-2 h-full py-3.5 rounded-2xl text-xs font-bold transition-all duration-200 active:scale-[0.97]"
                    style={{
                      background: 'linear-gradient(135deg, rgba(15,118,110,0.2) 0%, rgba(20,184,166,0.1) 100%)',
                      border: '1px solid rgba(20,184,166,0.2)',
                      color: '#5eead4',
                    }}
                  >
                    {briefLoading
                      ? <><Loader2 className="w-4 h-4 animate-spin" /> جاري التحليل...</>
                      : <><Sparkles className="w-4 h-4" /> ملخص ذكي</>
                    }
                  </button>
                </div>

                {/* AI Brief result */}
                <AnimatePresence>
                  {countryBrief && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3 }}
                      className="mt-3">
                      <GlassCard className="p-4" style={{ background: 'linear-gradient(135deg, rgba(15,118,110,0.1) 0%, rgba(20,184,166,0.05) 100%)', border: '1px solid rgba(20,184,166,0.12)' }}>
                        <div className="flex items-center gap-1.5 mb-2">
                          <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                          <span className="text-[11px] font-bold text-teal-400">ملخص ذكي — {selectedCountry.name}</span>
                        </div>
                        <p className="text-[12px] text-slate-300 leading-relaxed whitespace-pre-line">{countryBrief}</p>
                      </GlassCard>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Articles */}
              <div className="px-5 pb-6 pt-2">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-bold text-slate-400 tracking-wide">أحدث الأخبار</h4>
                  <span className="text-[10px] text-slate-600">{countryArticles.length} خبر</span>
                </div>

                {panelLoading ? (
                  <div className="text-center py-10">
                    <Loader2 className="w-6 h-6 text-teal-400 mx-auto mb-2 animate-spin" />
                    <p className="text-xs text-slate-500">جاري تحميل الأخبار...</p>
                  </div>
                ) : countryArticles.length === 0 ? (
                  <div className="text-center py-10">
                    <Newspaper className="w-7 h-7 text-slate-700 mx-auto mb-2" />
                    <p className="text-xs text-slate-500">لا توجد أخبار حالياً</p>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {countryArticles.map((article, i) => (
                      <motion.a
                        key={article.id || i}
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03, duration: 0.3 }}
                        className="block rounded-xl p-3 group transition-all duration-200"
                        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
                      >
                        <div className="flex gap-3">
                          {article.image_url && (
                            <img src={article.image_url} alt=""
                              className="w-16 h-16 rounded-lg object-cover flex-shrink-0 transition-transform duration-200 group-hover:scale-105"
                              style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                              onError={e => { e.target.style.display = 'none' }} />
                          )}
                          <div className="flex-1 min-w-0">
                            <p className="text-[12px] font-semibold text-slate-200 leading-relaxed line-clamp-2 group-hover:text-teal-300 transition-colors">
                              {article.title_ar || 'بدون عنوان'}
                            </p>
                            {article.summary_ar && (
                              <p className="text-[10px] text-slate-500 mt-1 line-clamp-1 leading-relaxed">{article.summary_ar}</p>
                            )}
                            <div className="flex items-center gap-2 mt-1.5">
                              {article.source_name && (
                                <span className="text-[9px] text-slate-600 font-medium">{article.source_name}</span>
                              )}
                              {article.keyword && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-400/80">{article.keyword}</span>
                              )}
                              <ExternalLink className="w-3 h-3 text-slate-700 mr-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                            </div>
                          </div>
                        </div>
                      </motion.a>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, idx) => {
          const Icon = stat.icon
          return (
            <motion.div key={idx} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="card p-5 group">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110" style={{ background: stat.bg }}>
                  <Icon className="w-5 h-5" style={{ color: stat.color }} />
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-900 truncate">{stat.value}</div>
              <div className="text-xs text-slate-500 mt-0.5 font-medium">{stat.label}</div>
              {stat.subtitle && <div className="text-[11px] text-slate-400 mt-0.5">{stat.subtitle}</div>}
            </motion.div>
          )
        })}
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Sources */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.5 }} className="card p-5">
          <h2 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Rss className="w-4 h-4 text-teal-600" />
            أبرز المصادر
          </h2>
          {stats?.top_sources?.length ? (
            <>
              <div className="space-y-2.5">
                {(showAllSources ? stats.top_sources : stats.top_sources.slice(0, 5)).map((src, i) => {
                  const maxSrc = stats.top_sources[0]?.count || 1
                  const pct = Math.round((src.count / maxSrc) * 100)
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs font-bold text-slate-400 w-5 text-center">{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs font-semibold text-slate-700 truncate">{src.name}</span>
                          <span className="text-xs text-slate-500 flex-shrink-0 mr-2">{src.count}</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ delay: 0.6 + i * 0.08, duration: 0.6, ease: 'easeOut' }} className="h-full rounded-full" style={{ background: 'linear-gradient(90deg, #7c3aed, #a78bfa)' }} />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
              {stats.top_sources.length > 5 && (
                <button onClick={() => setShowAllSources(p => !p)} className="mt-3 w-full flex items-center justify-center gap-1 text-[11px] font-semibold text-teal-600 hover:text-teal-700 transition-colors py-1.5 rounded-lg hover:bg-teal-50">
                  {showAllSources ? 'إخفاء' : 'المزيد'}
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAllSources ? 'rotate-180' : ''}`} />
                </button>
              )}
            </>
          ) : (
            <div className="text-center py-8">
              <Rss className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-400">لا توجد مصادر بعد</p>
            </div>
          )}
        </motion.div>

        {/* Top Keywords */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.5 }} className="card p-5">
          <h2 className="text-sm font-bold text-slate-800 mb-4">أكثر الكلمات رصداً</h2>
          {stats?.top_keywords?.length ? (
            <>
              <div className="space-y-2.5">
                {(showAllKeywords ? stats.top_keywords : stats.top_keywords.slice(0, 5)).map((kw, i) => {
                  const maxKw = stats.top_keywords[0]?.count || 1
                  const pct = Math.round((kw.count / maxKw) * 100)
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs font-bold text-slate-400 w-5 text-center">{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs font-semibold text-slate-700 truncate">{kw.keyword}</span>
                          <span className="text-xs text-slate-500 flex-shrink-0 mr-2">{kw.count}</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ delay: 0.7 + i * 0.08, duration: 0.6, ease: 'easeOut' }} className="h-full rounded-full" style={{ background: 'linear-gradient(90deg, #0f766e, #14b8a6)' }} />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
              {stats.top_keywords.length > 5 && (
                <button onClick={() => setShowAllKeywords(p => !p)} className="mt-3 w-full flex items-center justify-center gap-1 text-[11px] font-semibold text-teal-600 hover:text-teal-700 transition-colors py-1.5 rounded-lg hover:bg-teal-50">
                  {showAllKeywords ? 'إخفاء' : 'المزيد'}
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAllKeywords ? 'rotate-180' : ''}`} />
                </button>
              )}
            </>
          ) : (
            <div className="text-center py-8">
              <Key className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-400">لا توجد كلمات مراقبة بعد</p>
            </div>
          )}
        </motion.div>
      </div>

      {/* Countries Grid */}
      {stats?.countries?.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6, duration: 0.5 }} className="card p-5">
          <h2 className="text-sm font-bold text-slate-800 mb-4">توزيع الأخبار حسب الدولة</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {(showAllCountries ? stats.countries : stats.countries.slice(0, 18)).map((c, i) => {
              const meta = COUNTRY_META[c.name]
              return (
                <button key={i} onClick={() => openCountryPanel(c.name, c.count)}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-xl text-right transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 cursor-pointer"
                  style={{ background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(0,0,0,0.04)' }}>
                  <span className="text-sm">{meta?.flag || '🌍'}</span>
                  <span className="text-xs font-semibold text-slate-700 truncate flex-1">{c.name}</span>
                  <span className="text-xs font-bold text-teal-600">{c.count}</span>
                </button>
              )
            })}
          </div>
          {stats.countries.length > 18 && (
            <button onClick={() => setShowAllCountries(p => !p)} className="mt-3 w-full flex items-center justify-center gap-1 text-[11px] font-semibold text-teal-600 hover:text-teal-700 transition-colors py-1.5 rounded-lg hover:bg-teal-50">
              {showAllCountries ? 'إخفاء' : `المزيد (${stats.countries.length - 18})`}
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAllCountries ? 'rotate-180' : ''}`} />
            </button>
          )}
        </motion.div>
      )}
    </div>
  )
}
