import { useState } from 'react'
import { Play, Loader2, Check, AlertCircle, Download, Trash2 } from 'lucide-react'

export default function Settings() {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exportResult, setExportResult] = useState(null)

  const runMonitoring = async () => {
    setRunning(true)
    setResult(null)

    try {
      const res = await fetch('/api/monitor/run', { method: 'POST' })
      
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.error || 'فشل تشغيل المراقبة')
      }

      const data = await res.json()
      setResult(data)
    } catch (error) {
      console.error('Error running monitoring:', error)
      setResult({ error: error.message })
    } finally {
      setRunning(false)
    }
  }

  const exportAndReset = async () => {
    if (!confirm('هل أنت متأكد من حفظ البيانات وإعادة تهيئة النظام؟\n\nسيتم:\n1. تصدير جميع الأخبار إلى ملف Excel\n2. حذف جميع الأخبار\n3. حذف جميع الكلمات المفتاحية\n\nهذا الإجراء لا يمكن التراجع عنه!')) {
      return
    }

    setExporting(true)
    setExportResult(null)

    try {
      const res = await fetch('/api/articles/export-and-reset', { method: 'POST' })
      
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.error || 'فشل التصدير')
      }

      const data = await res.json()
      setExportResult(data)
      
      // Download the file
      if (data.download_url) {
        window.location.href = data.download_url
      }

      // Refresh page after 2 seconds
      setTimeout(() => {
        window.location.reload()
      }, 2000)

    } catch (error) {
      console.error('Error exporting and resetting:', error)
      setExportResult({ error: error.message })
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الإعدادات</h1>
        <p className="text-gray-600 mt-1">تشغيل المراقبة وإدارة النظام</p>
      </div>

      {/* Info Alert */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">معلومات هامة:</p>
            <ul className="list-disc list-inside space-y-1 mr-3">
              <li>يتم جلب الأخبار من جميع المصادر المفعلة</li>
              <li>تتم مطابقة الأخبار مع الكلمات المفتاحية المضافة</li>
              <li>يستخدم مكتبة Google Translate لترجمة النصوص</li>
              <li>قد تستغرق العملية عدة دقائق حسب عدد المصادر</li>
              <li>يتم حفظ النتائج في قاعدة البيانات</li>
              <li>يمكنك عرض النتائج من صفحة الخلاصة</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Main Action Card */}
      <div className="card p-8">
        <div className="text-center space-y-6">
          {/* Main Button */}
          <button
            onClick={runMonitoring}
            disabled={running}
            className="btn text-lg px-8 py-4 mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {running ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                جاري مراقبة المصادر...
              </>
            ) : (
              <>
                <Play className="w-6 h-6" />
                تشغيل نظام عين 
              </>
            )}
          </button>

          {/* Progress Bar */}
          {running && (
            <div className="w-full">
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-emerald-500 to-emerald-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: '100%', animation: 'shimmer 2s infinite' }}
                />
              </div>
              <p className="text-sm text-gray-600 mt-2">يرجى الانتظار...</p>
            </div>
          )}

          {/* Results */}
          {result && !result.error && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-3xl font-bold text-blue-600">{result.total_fetched || 0}</div>
                <div className="text-sm text-blue-800">تم الفحص</div>
              </div>
              <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                <div className="text-3xl font-bold text-emerald-600">{result.total_processed || 0}</div>
                <div className="text-sm text-emerald-800">تمت المعالجة</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="text-3xl font-bold text-green-600">
                  <Check className="w-8 h-8 inline" />
                </div>
                <div className="text-sm text-green-800">اكتمل</div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div className="text-3xl font-bold text-purple-600">
                  {result.total_processed > 0 ? Math.round((result.total_processed / result.total_fetched) * 100) : 0}%
                </div>
                <div className="text-sm text-purple-800">معدل القبول</div>
              </div>
            </div>
          )}

          {/* Error */}
          {result && result.error && (
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-red-800">❌ {result.error}</p>
            </div>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="card p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">حالة النظام</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">المصادر النشطة</div>
            <div className="text-2xl font-bold text-gray-900">--</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">الكلمات المفتاحية</div>
            <div className="text-2xl font-bold text-gray-900">--</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">آخر تحديث</div>
            <div className="text-2xl font-bold text-gray-900">--</div>
          </div>
        </div>
      </div>

      {/* Export & Reset */}
      <div className="card p-6 border-2 border-orange-200">
        <div className="flex items-start gap-3 mb-4">
          <AlertCircle className="w-6 h-6 text-orange-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">حفظ البيانات وإعادة تهيئة</h3>
            <p className="text-sm text-gray-600 mb-3">
              تصدير جميع الأخبار إلى ملف Excel ثم حذف جميع البيانات من النظام
            </p>
            <ul className="text-sm text-gray-600 space-y-1 mr-5 list-disc">
              <li>سيتم تصدير جميع الأخبار إلى ملف Excel</li>
              <li>سيتم التحقق من سلامة التصدير قبل الحذف</li>
              <li>سيتم حذف جميع الأخبار والكلمات المفتاحية</li>
              <li>سيتم تنزيل ملف Excel تلقائياً</li>
            </ul>
          </div>
        </div>

        <button
          onClick={exportAndReset}
          disabled={exporting}
          className="btn bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {exporting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              جاري التصدير وإعادة التهيئة...
            </>
          ) : (
            <>
              <Download className="w-5 h-5" />
              حفظ البيانات وإعادة تهيئة
            </>
          )}
        </button>

        {/* Export Result */}
        {exportResult && !exportResult.error && (
          <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
            <p className="text-green-800 font-semibold">✅ تم التصدير وإعادة التهيئة بنجاح!</p>
            <p className="text-sm text-green-700 mt-1">
              تم تصدير {exportResult.article_count} مقالة إلى {exportResult.filename}
            </p>
            <p className="text-sm text-green-700">جاري تحديث الصفحة...</p>
          </div>
        )}

        {/* Export Error */}
        {exportResult && exportResult.error && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
            <p className="text-red-800">❌ {exportResult.error}</p>
          </div>
        )}
      </div>
    </div>
  )
}
