# LiteVideoTube

**Windows için indir: [LiteVideoTube-win-Setup.exe](https://github.com/LiteVideoTube/LiteVideoTube/releases/latest/download/LiteVideoTube-win-Setup.exe)**. İndirip çift tıklayın. Windows "bilinmeyen yayımcı" derse "Ek bilgi" → "Yine de çalıştır".

Eski ve zayıf bilgisayarlarda YouTube videolarını hafifçe gezip izlemek için masaüstü programı (Windows, Linux). Hiçbir ayar yapmadan açılır; videolar tarayıcı yerine programın kendi hafif oynatıcısında oynar. Abonelikler, izleme geçmişi ve listeler yalnız bu bilgisayarda durur, YouTube hesabına bir şey yazılmaz.

## Kurmak

- Windows: sürümler (Releases) sayfasındaki `LiteVideoTube-win-Setup.exe`. Program yeni sürümleri kendisi indirir ve "Yeni sürüm var" penceresiyle sorar.
- Linux: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m litevideotube`. Sistemde libmpv (`libmpv2`) ve güncel yt-dlp gerekir.

## Yapı

Python + PySide6 (Qt Quick) arayüz; video libmpv ile programın kendi penceresinin içine çizilir; video adresleri yt-dlp'den, sayfa verisi (arama, öneriler) YouTube'un kendi veri kapılarından.

- `litevideotube/`: program (`uygulama.py` açılış, `oynatici.py` video öğesi ve altyazı, `cozumle.py` video adresleri (yt-dlp), `youtube.py` sayfa verisi ve yorumlar, `veri.py` arka plan köprüsü, `kayit.py` geçmiş, kaldığı yer ve ayarlar, `abonelik.py` (abonelik sayfasının bölümleri: `akis`), `ilgi.py` programın kendi sıralaması (izleme geçmişinden), `kisi.py` kişiler (her kişinin kayıtları ayrı klasörde: `yoklama.py`, `veri_klasoru`), `liste.py` oynatma listeleri ve Sonra izle, `indirme.py`, `diller.py` dil adları, `guncelleme.py` otomatik güncelleme, `geribildirim.py` hata bildirme, `qml/` arayüz, `simgeler/` Material Symbols).
- `paket/` ve `.github/workflows/windows-paket.yml`: Windows paketi (PyInstaller tek klasör; exe'nin yanında libmpv-2.dll, yt-dlp.exe, ffmpeg.exe, qjs.exe). ffmpeg yalnız indirmeye yeten küçük bir derleme (`paket/ffmpeg_derle.sh`, `ffmpeg.yml`).
- Yayın: `yayin.yml` (Velopack paketi → GitHub Releases; kurulu programlar oradan güncellenir), `ytdlp-izle.yml` (yt-dlp'nin yeni sürümünde programın yeni sürümünü çıkarır), `kaynak-kodu.yml` (libmpv ve ffmpeg'in kaynak arşivleri, sürümler sayfasında "kaynak-kodu").
- Sınama için ortam değişkenleri: `LVT_VERI` (kayıt klasörü), `LVT_INDIR` (indirme klasörü), `LVT_ARA`, `LVT_AC`, `LVT_SINAMA=<sn>,<png>`, `LVT_BUYUK`, `LVT_LOG` (mpv günlüğü), `LVT_MPV` (ek mpv ayarları), `LVT_YTDL` (yt-dlp yolu), `LVT_JS` (yt-dlp'nin JavaScript çalıştırıcısı), `LVT_GECERLILIK_SN` (video adresinin ömrünü kısaltır), `LVT_GUNCELLEME` (güncellemenin geleceği yer), `LVT_GUNCELLEME_GUNLUK`, `LVT_GUNCELLEME_SEC` (`simdi`/`sonra`: güncelleme penceresinin düğmesine kendisi basar), `LVT_GUNCELLEME_JETON` ve `LVT_GUNCELLEME_ON_SURUM` (gizli depodan ve ön sürümlerle güncelleme denemesi, `windows-guncelleme-github.yml`), `LVT_SENTRY_DSN` (geri bildirimin gideceği yer; boşsa gönderilmez), `LVT_DIL` (programın dili, örnek `en`; `litevideotube/ceviri.py`), `LVT_PROXY` (proxy adresi, `yok`: kapalı; verilmezse sistemin ayarı, `litevideotube/ag.py`).
- `araclar/arkada_sinama.py`: Windows paketinde arka plan yoklamasının denemesi (`windows-paket.yml` kullanır).

## Bağımsızlık

LiteVideoTube bağımsız, ticari olmayan bir projedir. YouTube veya Google ile bağlantılı değildir, onlar tarafından onaylanmamış ya da desteklenmemiştir. YouTube ve Google, Google LLC'nin ticari markalarıdır.

LiteVideoTube is an independent, non-commercial project. It is not affiliated with, endorsed by or sponsored by YouTube or Google. YouTube and Google are trademarks of Google LLC.

## Lisans

LiteVideoTube, GNU Genel Kamu Lisansı sürüm 3 ya da (dilediğiniz gibi) sonraki bir sürümü (GPL-3.0-or-later) koşullarında dağıtılır; tam metin `LICENSE`. Windows paketindeki başka programların (libmpv, ffmpeg, yt-dlp, Qt, QuickJS ve ötekiler) lisansları ve kaynak adresleri `paket/lisanslar/OKUBENI.txt`'te; paket yapılırken bu klasör, parçaların tam sürümleriyle (`SURUMLER.txt`) birlikte paketin `lisanslar/` klasörüne girer.

Copyright (C) 2026 Adeptus Vesperius Noctivagus
