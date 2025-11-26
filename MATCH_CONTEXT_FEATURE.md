# 🎯 Match Context Display Feature

## Overview

Articles now display **match context** instead of the full summary - showing exactly **why** each article matched a keyword, with 2 lines before and after the matched keyword.

---

## ✨ What Changed

### **Before:**
```
📰 Article Card
┌─────────────────────────────────┐
│ Title: Trump announces policy   │
│ Summary: Full translated        │
│ summary of the entire article   │
│ that might be very long and...  │
└─────────────────────────────────┘
```

**Problem:** Users couldn't see WHY the article matched.

### **After:**
```
📰 Article Card
┌─────────────────────────────────┐
│ Title: Trump announces policy   │
│ 🎯 سياق المطابقة:              │
│ [...] President Trump made      │
│ announcement. **Trump** said    │
│ the new policy will affect [...]│
└─────────────────────────────────┘
```

**Benefit:** Users see the **exact context** where the keyword appeared!

---

## 🔧 How It Works

### **Backend Process:**

1. **Article Matching:**
   ```python
   matched_keywords = match_article_against_keywords(article, keywords)
   # Result: [{'keyword_ar': 'ترامب', 'matched_variants': [...]}]
   ```

2. **Context Extraction:**
   ```python
   match_contexts = extract_all_match_contexts(article, matched_keywords)
   # Result: [{
   #   'keyword_ar': 'ترامب',
   #   'matched_variant': 'Trump',
   #   'full_snippet': '[...] President **Trump** announced [...]',
   #   'full_snippet_ar': '[...] الرئيس **ترامب** أعلن [...]'
   # }]
   ```

3. **Translation:**
   - If article is not Arabic, the context snippet is translated
   - Both original and Arabic versions stored

4. **Storage:**
   - Match context saved in `keywords_translations` JSON field
   - Format:
     ```json
     {
       "primary": "ترامب",
       "match_contexts": [
         {
           "keyword_ar": "ترامب",
           "matched_variant": "Trump",
           "full_snippet": "[...] President **Trump** announced [...]",
           "full_snippet_ar": "[...] الرئيس **ترامب** أعلن [...]"
         }
       ]
     }
     ```

### **Frontend Display:**

1. **Check for Match Context:**
   ```javascript
   const hasMatchContext = article.match_context && 
                          article.match_context.full_snippet_ar
   ```

2. **Display Context with Highlighting:**
   ```javascript
   // Parse **keyword** markers
   const parts = text.split(/(\*\*[^*]+\*\*)/)
   
   // Highlight keywords in yellow
   if (part.startsWith('**') && part.endsWith('**')) {
     return <span className="bg-yellow-200 font-bold">{keyword}</span>
   }
   ```

3. **Show Indicator:**
   ```jsx
   <div className="text-emerald-600 font-semibold">
     🎯 سياق المطابقة:
   </div>
   ```

---

## 📊 Context Format

### **Structure:**

```
[...] + 2 lines before + **KEYWORD** + 2 lines after + [...]
```

### **Examples:**

#### **Example 1: English Article**
```
Original:
"Trump announces new policy. President Trump made a 
significant announcement today. The new policy will 
affect trade relations. Many experts have praised..."

Context Extracted:
"[...] President Trump made a significant announcement 
today. **Trump** said the new policy will affect trade 
relations [...]"
```

#### **Example 2: Arabic Article**
```
Original:
"السعودية تعلن عن مشروع جديد. أعلنت المملكة العربية 
السعودية عن مشروع ضخم. يهدف المشروع إلى تطوير..."

Context Extracted:
"**السعودية** أعلنت المملكة العربية السعودية عن 
مشروع ضخم. يهدف المشروع إلى [...]"
```

#### **Example 3: Multi-Paragraph**
```
Original: (10 paragraphs)

Context Extracted: (Only relevant part)
"[...] The president announced. Trump revealed new 
measures. **Trump** said the initiative will begin 
next month. Officials welcomed [...]"
```

---

## 🎨 UI Features

### **Match Context Indicator:**

```
🎯 سياق المطابقة:
```

Shown above the context snippet to clarify this is NOT the full summary.

### **Keyword Highlighting:**

- **Background:** Yellow (`#fef08a`)
- **Font:** Bold
- **Padding:** Slight padding for visibility
- **Rounded:** Subtle border-radius

### **Expand/Collapse:**

- If context is > 200 characters, show "اظهر المزيد" button
- Expands to show full context
- Collapses back to 5 lines max

### **Fallback:**

If match context is not available (old articles):
- Falls back to displaying full summary
- No "🎯 سياق المطابقة:" indicator shown

---

## 📁 Files Modified

### **Backend:**

1. **`match_context_extractor.py`** (NEW - 200 lines)
   - Extracts context around keyword matches
   - Handles Arabic and English
   - Returns formatted snippet with `**keyword**` markers

2. **`async_monitor_wrapper.py`** (UPDATED)
   - Imports `extract_all_match_contexts`
   - Extracts context when saving articles
   - Translates context to Arabic
   - Stores in `keywords_translations` JSON

3. **`app.py`** (UPDATED)
   - Parses `keywords_translations` JSON
   - Extracts `match_contexts`
   - Returns in API response as `match_context` field

### **Frontend:**

4. **`ArticleCard.jsx`** (UPDATED)
   - Checks for `article.match_context`
   - Displays context with "🎯 سياق المطابقة:" indicator
   - Highlights keywords in yellow
   - Falls back to full summary if no context

---

## 🧪 Testing

### **Test Context Extraction:**

```bash
cd backend
python match_context_extractor.py
```

**Expected Output:**
```
1. English Article Test:
Keyword: ترامب
Matched: Trump
Context: **Trump** President Trump made a significant...

2. Arabic Article Test:
Keyword: السعودية
Matched: السعودية
Context: **السعودية** أعلنت المملكة العربية...

✅ Context extraction tests complete
```

### **Test Full Pipeline:**

1. **Start backend:**
   ```bash
   cd backend
   python app.py
   ```

2. **Run monitoring:**
   - Trigger via frontend or API

3. **Check articles:**
   - Go to الخلاصة page
   - Look for "🎯 سياق المطابقة:" indicator
   - Verify keyword is highlighted in yellow
   - Verify [...] markers show truncation

---

## 💡 Benefits

### **1. Explainability**

Users can see **exactly** why each article matched:
- Which keyword variant appeared
- Where in the article it appeared
- The surrounding context

### **2. Relevance Verification**

Users can quickly verify if the match is relevant:
- See if keyword is used in the right context
- Distinguish between "Trump" (person) and "trump card"
- Identify false positives

### **3. Better UX**

- **Faster scanning:** See relevant part immediately
- **Less noise:** Don't have to read full summary
- **Visual highlighting:** Yellow background makes keywords pop

### **4. Space Efficiency**

- Show only relevant excerpt (2-4 lines)
- Full summary available via expand button
- More cards visible on screen

---

## 🎯 Example Use Cases

### **Use Case 1: Proper Noun Disambiguation**

**Article:** "Playing the trump card in negotiations"

**Context Display:**
```
[...] The team used their trump card strategy [...]
```

**User sees:** "trump card" (lowercase) - not about the person
**Action:** User understands this might not be relevant

---

### **Use Case 2: Relevant Match**

**Article:** "Trump announces new trade policy"

**Context Display:**
```
President Trump made announcement. **Trump** said the 
new policy will affect trade relations [...]
```

**User sees:** "Trump" (person) in relevant context
**Action:** User reads article

---

### **Use Case 3: Multi-Language**

**Article (French):** "Trump annonce une nouvelle politique"

**Context Display (Arabic):**
```
[...] الرئيس **ترامب** أعلن عن سياسة جديدة [...]
```

**User sees:** Translated context with highlighted keyword
**Action:** User understands content in Arabic

---

## 📊 Context vs Full Summary

| Feature | Match Context | Full Summary |
|---------|---------------|--------------|
| **Length** | 2-4 lines | 10-20 lines |
| **Focus** | Keyword area only | Entire article |
| **Highlighting** | ✅ Keyword highlighted | ❌ No highlighting |
| **Truncation** | [...] markers | Full text or ellipsis |
| **Loading time** | ✅ Fast (shorter) | Slower (longer) |
| **Relevance** | ✅ High (focused) | Variable |
| **Explainability** | ✅ Shows WHY matched | ❌ Unclear |

---

## 🔄 Migration

### **Existing Articles:**

Articles saved before this feature:
- Have NO `match_contexts` in `keywords_translations`
- Will fall back to displaying full summary
- No "🎯 سياق المطابقة:" indicator

### **New Articles:**

Articles saved after this feature:
- Have `match_contexts` with highlighted keywords
- Display context with "🎯 سياق المطابقة:" indicator
- Keyword highlighted in yellow

### **No Database Migration Needed:**

- Uses existing `keywords_translations` TEXT field
- JSON format allows adding new fields
- Backward compatible

---

## ⚙️ Configuration

### **Context Length:**

Default: 2 lines before + 2 lines after

To change:
```python
# In async_monitor_wrapper.py
match_contexts = extract_all_match_contexts(
    article, 
    matched_keywords, 
    lines_before=3,  # Change this
    lines_after=3    # Change this
)
```

### **Highlight Color:**

Default: Yellow (`#fef08a`)

To change:
```jsx
// In ArticleCard.jsx
<span 
  className="bg-yellow-200 font-bold px-1 rounded"
  style={{ backgroundColor: '#your-color-here' }}
>
```

### **Disable Feature:**

To disable and show full summary:
```jsx
// In ArticleCard.jsx
const hasMatchContext = false  // Force disable
```

---

## 🎉 Summary

**Match context display provides:**

✅ **Explainability** - See exactly why article matched
✅ **Relevance** - Verify match is in correct context
✅ **Efficiency** - Read only relevant excerpt
✅ **Visual clarity** - Highlighted keywords pop out
✅ **Multi-language** - Translated context in Arabic

**Users can now understand at a glance WHY each article was matched and whether it's relevant to their interests!**

---

**Status:** ✅ **IMPLEMENTED AND READY**

**سياق المطابقة نشط الآن! 🎯**
