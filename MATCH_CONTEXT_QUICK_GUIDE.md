# ⚡ Match Context - Quick Guide

## 🎯 What You Asked For

**Your Request:**
> "In each card, show 2 lines before the keyword, the keyword itself, then 2 lines after for context - all translated to Arabic"

**What We Built:**
✅ Exactly that! Articles now show **match context** instead of full summary.

---

## 📊 Before vs After

### **Before:**

```
┌──────────────────────────────────┐
│ 🗞️ Title                         │
│ Full article summary that may be │
│ very long and doesn't show why   │
│ the article matched...           │
└──────────────────────────────────┘
```

**Problem:** Can't see WHY article matched

---

### **After:**

```
┌──────────────────────────────────┐
│ 🗞️ Title                         │
│ 🎯 سياق المطابقة:               │
│ [...] context before keyword     │
│ The **Trump** announced policy   │
│ context after keyword [...]      │
└──────────────────────────────────┘
```

**Solution:** See EXACT context where keyword matched!

---

## ✨ Features

### **1. Match Context Indicator**
```
🎯 سياق المطابقة:
```
Shows above the text so users know this is the matching part.

### **2. Keyword Highlighting**
```
The **Trump** announced
     ^^^^^^
     Yellow background, bold
```
Keyword stands out with yellow background.

### **3. Truncation Markers**
```
[...] before text **keyword** after text [...]
```
Shows there's more text before/after.

### **4. Arabic Translation**
- Context translated to Arabic
- Keyword preserved in highlight
- Reads naturally in Arabic

---

## 📝 Examples

### **Example 1: English Article**

**Original Article:**
```
Trump Announces New Policy

President Trump made a significant announcement 
today. The new policy will affect trade relations. 
Trump said the implementation will begin next month. 
Many experts have praised the decision.
```

**Display in Card:**
```
🗞️ Trump Announces New Policy

🎯 سياق المطابقة:
[...] الرئيس ترامب قام بإعلان مهم اليوم. السياسة الجديدة 
ستؤثر على العلاقات التجارية. **ترامب** قال أن التنفيذ سيبدأ 
الشهر المقبل [...]
```

---

### **Example 2: Arabic Article**

**Original Article:**
```
السعودية تعلن عن مشروع جديد

أعلنت المملكة العربية السعودية عن مشروع ضخم في الرياض. 
يهدف المشروع إلى تطوير البنية التحتية. سيستفيد الملايين 
من المواطنين من هذا المشروع.
```

**Display in Card:**
```
🗞️ السعودية تعلن عن مشروع جديد

🎯 سياق المطابقة:
أعلنت المملكة العربية **السعودية** عن مشروع ضخم في الرياض. 
يهدف المشروع إلى تطوير البنية التحتية [...]
```

---

## 🎨 Visual Appearance

### **Keyword Highlighting:**

<img src="https://via.placeholder.com/400x100/fef08a/000000?text=Trump" />

- **Background:** Yellow (#fef08a)
- **Font:** Bold
- **Padding:** Small padding around keyword
- **Border:** Slightly rounded corners

### **Context Text:**

- **Color:** Gray (#374151)
- **Line height:** Relaxed for readability
- **Max lines:** 5 lines when collapsed
- **Expand:** "اظهر المزيد" button if longer

---

## 🚀 How to Use

### **1. Run Monitoring:**

```bash
cd backend
python app.py
# Then trigger monitoring via frontend
```

### **2. Check Articles:**

Go to **الخلاصة** page:
- Look for 🎯 سياق المطابقة: indicator
- See highlighted keyword in yellow
- Read 2 lines before + 2 lines after for context

### **3. Expand if Needed:**

If context is long:
- Click "اظهر المزيد" to expand
- Click "اخفِ النص" to collapse

---

## 💡 Benefits

### **1. Know WHY Article Matched**
```
❌ Before: "Why did this article match 'Trump'?"
✅ After: "Ah! Because it mentions **Trump** announcing policy"
```

### **2. Verify Relevance**
```
Article about "trump card" in games:
[...] team used trump card strategy [...]
↑ User sees it's not about the person
```

### **3. Faster Scanning**
```
❌ Before: Read full summary to find keyword
✅ After: Keyword highlighted immediately
```

### **4. Save Space**
```
❌ Before: 10-20 lines of summary per card
✅ After: 2-4 lines of relevant context
```

---

## 🔧 Files Changed

### **Backend:**

1. ✅ **`match_context_extractor.py`** (NEW)
   - Extracts context around matches
   - Returns formatted snippet

2. ✅ **`async_monitor_wrapper.py`** (UPDATED)
   - Extracts and translates context
   - Stores in database

3. ✅ **`app.py`** (UPDATED)
   - Returns match context in API

### **Frontend:**

4. ✅ **`ArticleCard.jsx`** (UPDATED)
   - Displays match context
   - Highlights keywords
   - Shows indicator

---

## 🧪 Test It

### **1. Extract Context Test:**

```bash
cd backend
python match_context_extractor.py
```

Should show:
```
✅ Context extraction tests complete
```

### **2. Full Pipeline Test:**

1. Start backend: `python app.py`
2. Trigger monitoring via frontend
3. Go to الخلاصة page
4. Look for articles with 🎯 indicator
5. Verify keywords are highlighted

---

## ⚠️ Important Notes

### **New Articles Only:**

- Only articles saved AFTER this update have match context
- Old articles fall back to showing full summary
- No database migration needed

### **Fallback Behavior:**

If match context not available:
- Shows full summary instead
- No 🎯 indicator shown
- Works exactly as before

### **Multiple Keywords:**

If article matches multiple keywords:
- Shows context for primary (first) keyword
- Other keywords still tracked in backend

---

## 📊 What's Displayed

### **Title:**
Always shown - translated to Arabic

### **Body:**
```
IF match context exists:
  Show: 🎯 سياق المطابقة
  Show: [...] context **keyword** context [...]
  
ELSE:
  Show: Full summary (as before)
```

### **Expand Button:**
Shown if context/summary > 200 characters

---

## ✅ Status

**Implementation:** ✅ COMPLETE

**Testing:** ✅ PASSING

**Documentation:** ✅ COMPLETE

**Ready for:** ✅ PRODUCTION

---

## 🎉 Summary

You now have exactly what you asked for:

✅ **2 lines before keyword**
✅ **Keyword highlighted**
✅ **2 lines after keyword**
✅ **All translated to Arabic**
✅ **Clear indicator (🎯 سياق المطابقة)**
✅ **Works for all languages**

**Just restart the backend and new articles will have match context!**

```bash
cd backend
python app.py
# Match context feature is now active!
```

---

**الميزة جاهزة! شغّل النظام وابدأ المراقبة 🎯**
