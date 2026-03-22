"""
Türkçe UI String'leri — Tüm kullanıcıya görünen metinler.

Widget içinde hardcoded metin kullanılmaz. Tüm string'ler buradan
import edilir. İleride çoklu dil desteği eklenecekse, bu dosya
yerine language-dispatch mekanizması konulabilir.
"""

# ── Uygulama ─────────────────────────────────────────────────────

APP_TITLE = "Elektronik Harp Arayüz Sistemi"
APP_VERSION = "v0.1.0"
APP_FULL_TITLE = f"{APP_TITLE} — {APP_VERSION}"

# ── Menü ─────────────────────────────────────────────────────────

MENU_FILE = "Dosya"
MENU_FILE_NEW = "Yeni Proje"
MENU_FILE_OPEN = "Proje Aç..."
MENU_FILE_SAVE = "Kaydet"
MENU_FILE_SAVE_AS = "Farklı Kaydet..."
MENU_FILE_EXIT = "Çıkış"

MENU_EDIT = "Düzenle"

MENU_HELP = "Yardım"
MENU_HELP_ABOUT = "Hakkında"

# ── Toolbar ──────────────────────────────────────────────────────

TOOLBAR_RUN = "Başlat"
TOOLBAR_STOP = "Durdur"
TOOLBAR_RESET = "Sıfırla"

TOOLTIP_RUN = "Uygulamayı çalıştır"
TOOLTIP_STOP = "Uygulamayı durdur"
TOOLTIP_RESET = "Uygulamayı sıfırla"

# ── Sekmeler ─────────────────────────────────────────────────────

TAB_FLOW_GRAPH = "Akış Grafiği"
TAB_PLOTS = "Grafikler"

# ── Akış Grafiği panelleri ───────────────────────────────────────

PALETTE_TITLE = "Blok Paleti"
PALETTE_SEARCH = "Blok ara..."
PROPERTIES_TITLE = "Özellikler"
LOG_TITLE = "Terminal"

# ── Blok kategorileri ────────────────────────────────────────────

CAT_SOURCES = "Kaynaklar"
CAT_PROCESSORS = "İşleyiciler"
CAT_VIEWERS = "Görüntüleyiciler"
CAT_DETECTORS = "Tespit"
CAT_CLASSIFIERS = "Sınıflandırma"
CAT_TRACKING = "İzleme"

# ── Grafik panelleri ─────────────────────────────────────────────

PLOT_SPECTRUM = "Spektrum"
PLOT_WATERFALL = "Waterfall"
PLOT_IQ = "IQ / Zaman"
PLOT_DETECTIONS = "Tespitler"

PLOT_FREQUENCY_LABEL = "Frekans (MHz)"
PLOT_POWER_LABEL = "Güç (dB)"
PLOT_TIME_LABEL = "Zaman (örnek)"
PLOT_AMPLITUDE_LABEL = "Genlik"

# ── Doğrulama / hata mesajları ───────────────────────────────────

VALIDATION_ERROR_TITLE = "Doğrulama Hatası"
VALIDATION_OK = "Sistem geçerli."

ERROR_PIPELINE_EMPTY = "Çalıştırılacak hiçbir blok yok — en az bir blok ekleyin."
ERROR_NO_SOURCE = "Kaynak (source) bloğu bulunamadı."
ERROR_PORT_NOT_CONNECTED = "Zorunlu giriş portu bağlı değil"
ERROR_PORT_INCOMPATIBLE = "Port tipi uyumsuz"
ERROR_CYCLE = "Sistem üzerinde döngü tespit edildi"
WARNING_NO_SINK = "Görüntüleyici (sink) bloğu yok — çıktı görünmeyecek."

# ── Durum çubuğu ─────────────────────────────────────────────────

STATUS_READY = "Hazır"
STATUS_RUNNING = "Çalışıyor..."
STATUS_STOPPED = "Durduruldu"
STATUS_ERROR = "Hata"

# ── Diyaloglar ───────────────────────────────────────────────────

DIALOG_UNSAVED = "Kaydedilmemiş değişiklikler var. Kaydetmek ister misiniz?"
DIALOG_UNSAVED_TITLE = "Kaydedilmemiş Değişiklikler"
DIALOG_ABOUT_TEXT = (
    f"<h3>{APP_TITLE}</h3>"
    f"<p>{APP_VERSION}</p>"
    "<p>SDR tabanlı Elektronik Harp Arayüz Sistemi</p>"
    "<p>TEKNOFEST 2026</p>"
)

DIALOG_FILE_FILTER = "EH Proje Dosyası (*.ehproj);;Tüm Dosyalar (*)"

# ── Log seviyesi prefix'leri ─────────────────────────────────────

LOG_INFO = "[BİLGİ]"
LOG_WARNING = "[UYARI]"
LOG_ERROR = "[HATA]"
LOG_DEBUG = "[DEBUG]"

# ── Sağ tık menüsü ──────────────────────────────────────────────

CTX_DELETE = "Sil"
CTX_DUPLICATE = "Çoğalt"
CTX_PROPERTIES = "Özellikler"
CTX_DISCONNECT = "Bağlantıları Kes"
CTX_ADD_BLOCK = "Blok Ekle"
CTX_SELECT_ALL = "Tümünü Seç"
CTX_RESET_VIEW = "Görünümü Sıfırla"
CTX_FIT_ALL = "Tümünü Sığdır"
