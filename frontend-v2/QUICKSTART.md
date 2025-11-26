# ⚡ عين (Ain) - Quick Start

## 🚀 3 Steps to Launch

### Step 1: Install (2 minutes)
```bash
cd c:\Users\pcc\OneDrive\Desktop\ain-news-monitor\frontend-v2
npm install
```

### Step 2: Start Backend (Required)
```bash
# Open NEW terminal window
cd c:\Users\pcc\OneDrive\Desktop\ain-news-monitor\backend
python app.py
```

### Step 3: Start Frontend
```bash
# In original terminal
npm run dev
```

**OR** use the batch file:
```bash
START_FRONTEND.bat
```

---

## 🌐 Access

- **Frontend:** http://localhost:5173
- **Backend:** http://localhost:5000

---

## 📱 First Use Tutorial

### 1. Add Keywords (Settings Tab)
```
1. Click "الكلمات المفتاحية" in sidebar
2. Type: الذكاء الاصطناعي
3. Click "إضافة"
4. Wait ~10s for AI translation
```

### 2. Run Monitoring (Settings Tab)
```
1. Click "الإعدادات" in sidebar
2. Click "تشغيل المراقبة الآن"
3. Wait 2-3 minutes
4. Check results summary
```

### 3. View Results (Dashboard Tab)
```
1. Click "الخلاصة" in sidebar
2. See articles in 3-column grid
3. Use filters to narrow results
4. Click article cards to read more
```

---

## 🎨 UI Features

### Beautiful Design
- ✨ Cairo Arabic font
- ✨ Emerald green theme (#059669)
- ✨ Glassmorphism cards
- ✨ Smooth animations
- ✨ RTL layout

### Responsive
- 📱 Mobile: 1 column
- 📱 Tablet: 2 columns
- 💻 Desktop: 3 columns

### Interactive
- 🔍 Search & filters
- 📊 Live statistics
- 🎯 Sentiment analysis
- 🌍 Country badges

---

## 🐛 Troubleshooting

### Backend not running?
```bash
cd ../backend
python app.py
```

### Port already used?
Change port in `vite.config.js`:
```js
server: { port: 5174 }
```

### Styles not working?
```bash
npm install
```

---

## ✅ Success Checklist

- [ ] Backend running (port 5000)
- [ ] Frontend running (port 5173)
- [ ] Can see sidebar with 4 menu items
- [ ] Cairo font loaded (check browser inspector)
- [ ] Can add keywords
- [ ] Can run monitoring
- [ ] Articles display in grid

---

## 📚 Pages Overview

| Page | Arabic | Purpose |
|------|--------|---------|
| Dashboard | الخلاصة | View all news articles |
| Countries | الدول | Manage RSS sources |
| Keywords | الكلمات المفتاحية | Manage search keywords |
| Settings | الإعدادات | Run monitoring |

---

## 🎯 Common Tasks

### Add a Keyword
```
الكلمات المفتاحية → Type keyword → إضافة
```

### Run Monitoring
```
الإعدادات → تشغيل المراقبة الآن
```

### Filter Articles
```
الخلاصة → Use filter dropdowns
```

### Enable/Disable Countries
```
الدول → Toggle switches on cards
```

---

## 💡 Pro Tips

1. **Start with popular keywords**: "الذكاء الاصطناعي", "تكنولوجيا"
2. **Run monitoring during peak news hours** for more articles
3. **Use filters** to focus on specific countries or sentiments
4. **Check Gemini API quota** if translations fail
5. **Refresh page** if components don't load

---

## 📞 Need Help?

1. Check `README.md` for full documentation
2. Check `DEPLOYMENT_SUMMARY.md` for implementation details
3. Check browser console (F12) for errors
4. Check backend terminal for API errors

---

## 🎉 You're Ready!

The app is fully functional and ready to use. Enjoy monitoring Arabic news with beautiful UI! ✨

**Time to first article:** ~3 minutes
**Gemini AI:** Used for translation & sentiment
**Languages supported:** Arabic, English, Russian, Chinese, French, Spanish

---

**Happy monitoring! 🌍📰**
