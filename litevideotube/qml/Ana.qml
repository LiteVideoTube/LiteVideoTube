import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import LiteVideoTube

ApplicationWindow {
    id: pencere
    width: 1280; height: 760
    minimumWidth: 640; minimumHeight: 420
    visible: true
    title: (sayfa === "video" || sayfa === "shorts") && videoBilgi.baslik ? qsTr("%1 - LiteVideoTube").arg(videoBilgi.baslik) : "LiteVideoTube"
    color: Renk.zemin
    // Sağdan sola diller (Arapça, ceviri.SAGDAN_SOLA): anchor'lar ve Row, Column gibi sıralar aynalanır; mutlak x
    // konumları ve video yanda dururken yapılan hesap LayoutMirroring.enabled'a göre elle çevrilir.
    LayoutMirroring.enabled: Qt.locale().textDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true
    // Açık ya da koyu görünüm (kişi menüsünden seçilir).
    Binding { target: Renk; property: "secim"; value: kisiler.gorunum }
    Binding { target: Renk; property: "enCokSutun"; value: Math.max(5, Math.round(500 / kisiler.acikYakinlik)) }

    // "arama" ya da "video"
    property string sayfa: "abonelik"
    property string sorgu: ""
    property var videoBilgi: ({})
    property string videoId: ""
    // Shorts görünümünde gezilen liste (açıldığı şerit ya da kanalın Shorts bölümü) ve bulunulan sıra.
    property var shortsListe: []
    property int shortsSira: 0
    // Listenin devamı (Shorts 24'te duruyordu, devamı için çıkıp girmek gerekiyordu):
    // "abonelik" kayıttaki son üç günden sıradaki parti, "kanal:<id>" YouTube'dan kanalın devamı, "kesfet" tek parti;
    // boşsa (bağlantıyla açılan tek Shorts) devam yok. Sona üç Shorts kala devamı istenir; hepsi bitince
    // "bitirdin" ekranı (shortsSonu) çıkar, video durur.
    property string shortsKaynak: ""
    property bool shortsBitti: true
    property bool shortsIsteniyor: false
    property bool shortsSonu: false
    property bool tamEkran: false
    // Sol kenardaki abonelik listesi: liste sayfalarında sayfayı sağa iter, açık ya da kapalı
    // olduğu hatırlanır (kenarAcik); video ve Shorts'ta sayfanın üstüne açılır, kanal seçilince ya da sayfa değişince
    // kapanır, video küçülmez (kenarUstte; YouTube'daki gibi).
    property bool kenarAcik: false
    property bool kenarUstte: false
    readonly property bool videoluSayfa: sayfa === "video" || sayfa === "shorts"
    readonly property bool kenarIter: kenarAcik && !videoluSayfa && !tamEkran
    function kenarDegistir() {
        if (videoluSayfa) { kenarUstte = !kenarUstte; return }
        kenarAcik = !kenarAcik
        kayit.ayarYaz("kenar", kenarAcik ? "1" : "0")
    }
    property string uyari: ""

    // Görünüm menüsünün seçimleri (oynatıcı çubuğundaki "Görünüm" düğmesi):
    // video açılınca nasıl görünsün, aşağı kaydırınca nereye geçsin. Program kapanınca da unutulmaz.
    QtObject {
        id: gorunum
        property string sayfa: "normal"   // video açılınca: normal | sinema | yorum | tam
        // aşağı kaydırınca: buyuk (önerilerin üstünde, en büyük; yazılar daralır) | genis (önerilerin
        // üstünde, sütun genişliğinde) | kucuk (sağ üstte) | yorumlar (yorumların yanında, en büyük; öneriler kapanır)
        property string yan: "buyuk"
        property int yanBoy: 0            // kullanıcının yandaki videoya köşesinden çekerek verdiği genişlik
        property bool yuklendi: false
        function kaydet() {
            if (yuklendi) kayit.ayarYaz("gorunum", JSON.stringify({ sayfa: sayfa, yan: yan, yanBoy: yanBoy }))
        }
        function varsayilan() { sayfa = "normal"; yan = "buyuk"; yanBoy = 0 }
        onSayfaChanged: {
            kaydet()
            if (pencere.sayfa === "video" && (sayfa === "tam") !== pencere.tamEkran) pencere.tamEkranDegistir()
        }
        onYanChanged: { yanBoy = 0; kaydet(); videoKutusu.yeniden() }
        onYanBoyChanged: { kaydet(); videoKutusu.yeniden() }
        Component.onCompleted: {
            try {
                var g = JSON.parse(kayit.ayar("gorunum") || "{}")
                if (["normal", "sinema", "yorum", "tam"].indexOf(g.sayfa) >= 0) sayfa = g.sayfa
                if (["buyuk", "genis", "kucuk", "yorumlar"].indexOf(g.yan) >= 0) yan = g.yan
                if (g.yanBoy > 0) yanBoy = g.yanBoy
            } catch (e) { }
            yuklendi = true
        }
    }

    // Oynayan liste (Sonra izle ya da kullanıcının listesi): video bitince sıradaki açılır. Listenin
    // dışından bir video açılınca liste biter (YouTube'daki gibi).
    property var calanListe: null     // {id, ad, videolar, sira}
    function listeOynat(listeId, sira) {
        var vler = listeler.videolar(listeId)
        if (sira < 0 || sira >= vler.length) return
        calanListe = { id: listeId, ad: listeler.ad(listeId), videolar: vler, sira: sira }
        videoAc(vler[sira].id, vler[sira], true)
    }
    function sonrakiVideo() {
        if (calanListe && calanListe.sira + 1 < calanListe.videolar.length) listeOynat(calanListe.id, calanListe.sira + 1)
    }
    readonly property bool sonrakiVar: calanListe !== null && calanListe.sira + 1 < calanListe.videolar.length
    Connections { target: oynatici; function onBitti() {
        // Shorts biter bitmez baştan oynar (YouTube'daki gibi); sıradakine kişi geçer.
        if (pencere.sayfa === "shorts") oynatici.git(0)
        else if (pencere.sonrakiVar && !oynatici.dongu) pencere.sonrakiVideo() } }

    // Shorts: dikey görünüm; liste içinde ↑ ↓ ve tekerlekle gezilir. Kaldığı yer tutulmaz,
    // her Shorts baştan açılır.
    function shortsAc(liste, i, kaynak) {
        if (!liste || i < 0 || i >= liste.length) return
        if (kaynak !== undefined) {
            shortsKaynak = kaynak; shortsBitti = kaynak === "" || kaynak === "kesfet"; shortsIsteniyor = false
        }
        shortsSonu = false
        var v = liste[i]
        if (sayfa !== "shorts" || videoId !== v.id) yerKaydet()
        calanListe = null
        shortsListe = liste; shortsSira = i
        videoId = v.id
        videoBilgi = v
        sayfa = "shorts"
        if (duraklatarakAc) oynatici.acDurakli(v.id, 0)
        else oynatici.ac(v.id, 0)
        veri.video(v.id)   // başlık, kanal, abone sayısı
        Qt.callLater(videoKutusu.yeniden)
    }
    // Liste içinde gezinmek geri geçmişine girmez (YouTube'da da Shorts'ta aşağı inmek bir sayfa değişimi sayılmaz).
    function shortsGec(adim) {
        if (shortsSonu) {   // "bitirdin" ekranından yukarı: son Shorts
            if (adim < 0) { geriDonuluyor = true; shortsAc(shortsListe, shortsListe.length - 1); geriDonuluyor = false }
            return
        }
        var i = shortsSira + adim
        if (i < 0) return
        if (i >= shortsListe.length) {
            if (shortsBitti && shortsKaynak !== "") { shortsSonu = true; oynatici.durdur() }
            else shortsDevamIste()
            return
        }
        geriDonuluyor = true; shortsAc(shortsListe, i); geriDonuluyor = false
        if (shortsListe.length - shortsSira <= 3) shortsDevamIste()
    }
    function shortsDevamIste() {
        if (shortsBitti || shortsIsteniyor) return
        if (shortsKaynak === "abonelik") {
            var yeni = abonelik.shortsDevami(shortsListe.map(function(v) { return v.id }))
            shortsEkle(yeni, yeni.length > 0)
        } else if (shortsKaynak.indexOf("kanal:") === 0) {
            shortsIsteniyor = true
            veri.kanalShortsDevami(shortsKaynak.slice(6))
        } else shortsBitti = true
    }
    function shortsEkle(vler, devam) {
        var var_ = {}
        shortsListe.forEach(function(v) { var_[v.id] = true })
        var ek = vler.filter(function(v) { return !var_[v.id] })
        if (ek.length) shortsListe = shortsListe.concat(ek)
        shortsBitti = !devam
    }
    Connections {
        target: veri
        function onKanalShortslariGeldi(id, vler, devam, ilk) {
            if (ilk || pencere.shortsKaynak !== "kanal:" + id) return
            pencere.shortsIsteniyor = false
            var ilkV = pencere.shortsListe[0] || {}
            vler.forEach(function(v) { v.kanal = v.kanal || ilkV.kanal || ""; v.kanal_id = id })
            pencere.shortsEkle(vler, devam)
        }
    }
    function shortsYeniSekmede(liste, i, kaynak) {
        if (!liste || !liste[i]) return
        yeniSekme({ sayfa: "shorts", videoId: liste[i].id, videoBilgi: liste[i], shortsListe: liste, shortsSira: i,
                    shortsKaynak: kaynak || "" }, false)
        uyari = qsTr("Yeni sekmede açıldı: %1").arg(liste[i].baslik || qsTr("Shorts")); uyariSaati.restart()
    }

    // Geri: tarayıcı alışkanlığı (Alt+Sol, farenin geri tuşu, üst şeritteki ok). Her sayfa geçişinden
    // önce bulunulan yer yığına girer; geri dönünce video kaldığı yerden açılır.
    property var yigin: []
    property bool geriDonuluyor: false
    function yerAl() {
        return { sayfa: sayfa, videoId: videoId, videoBilgi: videoBilgi, sorgu: sorgu,
                 kanalId: kanalSayfasi.kanalId, kanalAd: kanalSayfasi.bilgi.ad || "",
                 shortsListe: shortsListe, shortsSira: shortsSira, shortsKaynak: shortsKaynak }
    }
    function yerKaydet() {
        if (geriDonuluyor) return
        ileriYigin = []   // yeni bir yere gidildi: ileri geçmişi biter (tarayıcıdaki gibi)
        var y = yerAl()
        var son = yigin.length ? yigin[yigin.length - 1] : null
        if (son && son.sayfa === y.sayfa && son.videoId === y.videoId && son.sorgu === y.sorgu && son.kanalId === y.kanalId) return
        yigin = yigin.concat([y]).slice(-50)
    }
    function geri() {
        if (!yigin.length) return
        var y = yigin[yigin.length - 1]
        yigin = yigin.slice(0, -1)
        ileriYigin = ileriYigin.concat([yerAl()]).slice(-50)
        yereGit(y)
    }
    // İleri: geri dönülen yerlere yeniden gider; yeni bir yere gidilince boşalır.
    property var ileriYigin: []
    function ileri() {
        if (!ileriYigin.length) return
        var y = ileriYigin[ileriYigin.length - 1]
        ileriYigin = ileriYigin.slice(0, -1)
        yigin = yigin.concat([yerAl()]).slice(-50)
        yereGit(y)
    }
    // Yenile (⟳, F5, Ctrl+R): bulunulan sayfayı yeniden alır, geçmişe yer girmez. Video:
    // video kaldığı yerden yeniden açılır, öneriler ve yorumlar yeniden alınır. Abonelikler: arka plan
    // yoklamasının o ana kadar getirdikleri gösterilir (730 kanala birden sormak YouTube'u kızdırır).
    // Geçmiş ve listeler bilgisayardan okunur.
    function yenile() {
        if (sayfa === "shorts" && videoId) {
            oynatici.yenile()
        } else if (sayfa === "video" && videoId) {
            videoSayfasi.onerileriKoy([]); videoSayfasi.oneriDevamVar = false
            videoSayfasi.yorumlar.sifirla()
            if (videoId.indexOf("://") < 0) veri.video(videoId)
            oynatici.yenile()
        } else if (sayfa === "arama" && sorgu) {
            geriDonuluyor = true; aramaYap(sorgu); geriDonuluyor = false
        } else if (sayfa === "kanal" && kanalSayfasi.kanalId) {
            kanalSayfasi.ac(kanalSayfasi.kanalId, kanalSayfasi.bilgi.ad || "")
        } else if (sayfa === "abonelik") abonelikSayfasi.yenile()
        else if (sayfa === "gecmis") gecmisSayfasi.yenile()
        else if (sayfa === "liste") listelerSayfasi.yenile()
        else if (sayfa === "kesfet") kesfetSayfasi.yenile()
        else if (sayfa === "yenilikler") yeniliklerSayfasi.yenile()
    }
    // Adres satırında gösterilen adres: YouTube'da aynı sayfanın adresi (kopyalanıp tarayıcıda açılabilsin).
    readonly property string sayfaAdresi: {
        var y = "https://www.youtube.com/"
        if (sayfa === "video" && videoId) return videoId.indexOf("://") >= 0 ? videoId : y + "watch?v=" + videoId
        if (sayfa === "shorts" && videoId) return y + "shorts/" + videoId
        if (sayfa === "arama") return y + "results?search_query=" + sorgu.replace(/ /g, "+")
        if (sayfa === "kanal" && kanalSayfasi.kanalId) return y + "channel/" + kanalSayfasi.kanalId
        if (sayfa === "yenilikler") return "lvt://yenilikler"   // programın kendi sayfası, YouTube'da karşılığı yok
        // Keşfet'in YouTube'da tam karşılığı yok; en yakını öneri sayfası olan ana sayfa.
        return y + ({ abonelik: "feed/subscriptions", gecmis: "feed/history", liste: "feed/playlists" }[sayfa] || "")
    }
    // Adres satırına yazılanı açar: programın kendi gösterdiği adresler o sayfaya, kanal adresi kanala, öbür her
    // şey (video ve liste bağlantısı, söz) arama kutusunun yolundan (aramaYap).
    function adresAc(metin) {
        var m = metin.match(/youtube\.com\/results\?search_query=([^&#]*)/)
        if (m) {
            var q = m[1].replace(/\+/g, " ")
            try { q = decodeURIComponent(q) } catch (e) { }
            aramaYap(q); return
        }
        m = metin.match(/youtube\.com\/channel\/(UC[A-Za-z0-9_-]{22})/)
        if (m) { kanalAc(m[1], ""); return }
        m = metin.match(/youtube\.com\/(@[^\/?#]+)/)
        if (m) { aramaYap(m[1]); return }
        if (/youtube\.com\/feed\/subscriptions/.test(metin)) { sayfaya("abonelik"); return }
        if (/youtube\.com\/feed\/history/.test(metin)) { sayfaya("gecmis"); return }
        if (/youtube\.com\/feed\/playlists/.test(metin)) { sayfaya("liste"); return }
        if (/^lvt:\/\/yenilikler\/?$/.test(metin.trim())) { sayfaya("yenilikler"); return }
        if (/^(https?:\/\/)?(www\.)?youtube\.com\/?$/.test(metin.trim())) { sayfaya("kesfet"); return }
        aramaYap(metin)
    }
    // Kaydedilmiş bir yeri açar (geri ve sekme değişimi); yığına yeni yer girmez.
    function yereGit(y) {
        geriDonuluyor = true
        if (y.sayfa === "video") videoAc(y.videoId, y.videoBilgi)
        else if (y.sayfa === "shorts") shortsAc(y.shortsListe && y.shortsListe.length ? y.shortsListe : [y.videoBilgi], y.shortsSira || 0,
                                                y.shortsKaynak || "")
        else if (y.sayfa === "arama" && y.sorgu !== sorgu) aramaYap(y.sorgu)
        else if (y.sayfa === "kanal") kanalAc(y.kanalId, y.kanalAd)
        else sayfaya(y.sayfa)
        geriDonuluyor = false
    }

    // Sekmeler (2. ilke: "sekme yok bizde"): her sekme yalnız bulunduğu yeri ve kendi geri
    // yığınını tutar; sayfalar ve oynatıcı tektir (4 GB'lık makinede her sekmeye ayrı sayfa ve video ağır
    // olurdu). Sekmeye geçince yeri yeniden açılır: video kaldığı yerden (kayit.baslangic), başka aramadaysa
    // arama yeniden yapılır. Öndeki sekmenin yeri canlı durumdur, sekmeler dizisindeki kaydı geçerken yazılır.
    // Şerit tek sekmede de görünür (görünmezse kullanıcı sekme olduğunu bilmez, arkada açılan
    // sekmeyle şerit birden belirince kafası karışır).
    property var sekmeler: [{ yer: null, yigin: [] }]   // yer null: abonelik sayfası
    property int etkinSekme: 0
    function sekmeAdi(y) {
        if (!y) return qsTr("Abonelikler")
        if (y.sayfa === "video") return (y.videoBilgi && y.videoBilgi.baslik) || qsTr("Video")
        if (y.sayfa === "shorts") return (y.videoBilgi && y.videoBilgi.baslik) || qsTr("Shorts")
        if (y.sayfa === "arama") return qsTr("Ara: %1").arg(y.sorgu)
        if (y.sayfa === "kanal") return y.kanalAd || qsTr("Kanal")
        return { abonelik: qsTr("Abonelikler"), gecmis: qsTr("Geçmiş"), liste: qsTr("Kitaplık"), kesfet: qsTr("Keşfet"),
                 yenilikler: qsTr("Yenilikler") }[y.sayfa] || y.sayfa
    }
    readonly property var sekmeAdlari: sekmeler.map(function(x, i) { return sekmeAdi(i === etkinSekme ? yerAl() : x.yer) })
    function sekmeyeGec(i) {
        if (i === etkinSekme || i < 0 || i >= sekmeler.length) return
        var l = sekmeler.slice()
        l[etkinSekme] = { yer: yerAl(), yigin: yigin, ileri: ileriYigin }
        sekmeler = l
        etkinSekme = i
        yigin = l[i].yigin
        ileriYigin = l[i].ileri || []
        yereGit(l[i].yer || { sayfa: "abonelik" })
    }
    function yeniSekme(yer, gec) {
        sekmeler = sekmeler.concat([{ yer: yer, yigin: [] }])
        if (gec) sekmeyeGec(sekmeler.length - 1)
    }
    // Orta tık, Ctrl+tık ya da sağ tık "Yeni sekmede aç": tarayıcıdaki gibi arkada açılır, öndeki sayfa değişmez.
    function videoYeniSekmede(v) {
        if (!v || !v.id) return
        yeniSekme({ sayfa: "video", videoId: v.id, videoBilgi: v }, false)
        uyari = qsTr("Yeni sekmede açıldı: %1").arg(v.baslik || v.id); uyariSaati.restart()
    }
    // Sağ tık "Yeni sekmede aç" menüsü: video kartları, öneriler, geçmiş ve liste satırları, üstteki sayfa
    // düğmeleri için tek menü (her karta ayrı menü bellek tutardı). is: seçilince yapılacak iş. altinda verilirse
    // (üstteki düğmeler) menü o öğenin tam altında, sağ kenarı öğeninkiyle hizalı açılır; yoksa farenin yerinde.
    property var menuIs: null
    // Farenin pencerede son bastığı yer (uygulama.py, OdakBekcisi yazar); sağ tık menüleri orada açılır (MenuKutusu.popup).
    property point sonBasis: Qt.point(0, 0)
    function yeniSekmeMenusu(is, altinda) {
        menuIs = is
        if (!altinda) { kartMenu.popup(); return }
        // Sağdan sola dilde sol kenarı öğeninkiyle hizalı.
        var p = altinda.mapToItem(null, pencere.LayoutMirroring.enabled ? 0 : altinda.width, altinda.height)
        kartMenu.x = pencere.LayoutMirroring.enabled ? p.x : Math.max(0, p.x - kartMenu.implicitWidth); kartMenu.y = p.y
        kartMenu.open()
    }
    function kartMenusu(v) { yeniSekmeMenusu(function() { pencere.videoYeniSekmede(v) }) }
    MenuKutusu {
        id: kartMenu
        contentItem: Column {
            MenuSatiri { width: 220; yazi: qsTr("Yeni sekmede aç"); onTiklandi: { kartMenu.close(); pencere.menuIs() } }
        }
    }
    // Üstteki Abonelikler, Listeler, Geçmiş düğmeleri: orta tık ya da sağ tık menüsüyle arkada yeni sekmede.
    function sayfaYeniSekmede(ad) {
        yeniSekme({ sayfa: ad }, false)
        uyari = qsTr("Yeni sekmede açıldı: %1").arg(sekmeAdi({ sayfa: ad })); uyariSaati.restart()
    }
    // Program kapanınca sekmeler hatırlanır, açılınca geri gelir ("kaldığın yeri karşına getirme
    // babında güzel"); tarayıcının "kaldığım yerden devam et"i gibi. Her sekmenin yeri ve son 20 adımlık geri/ileri
    // geçmişi. Öndeki sekme video ya da Shorts ise video kaldığı yerde duraklatılmış açılır (ses birden çalmasın).
    property bool duraklatarakAc: false
    function sekmeleriKaydet() {
        var l = sekmeler.slice()
        l[etkinSekme] = { yer: yerAl(), yigin: yigin, ileri: ileriYigin }
        l = l.map(function(s) { return { yer: s.yer, yigin: (s.yigin || []).slice(-20), ileri: (s.ileri || []).slice(-20) } })
        kayit.ayarYaz("sekmeler", JSON.stringify({ sekmeler: l, etkin: etkinSekme }))
    }
    function sekmeleriGetir() {
        var k
        try { k = JSON.parse(kayit.ayar("sekmeler") || "null") } catch (e) { return }
        if (!k || !k.sekmeler || !k.sekmeler.length) return
        var e = Math.max(0, Math.min(k.etkin || 0, k.sekmeler.length - 1))
        sekmeler = k.sekmeler
        etkinSekme = e
        yigin = k.sekmeler[e].yigin || []
        ileriYigin = k.sekmeler[e].ileri || []
        duraklatarakAc = !kisiler.yenidenOynat   // yakınlık için yeniden açıldıysa video sürer
        yereGit(k.sekmeler[e].yer || { sayfa: "abonelik" })
        duraklatarakAc = false
        if (kisiler.yenidenKaydirma) { kaydirmaSaati.hedef = JSON.parse(kisiler.yenidenKaydirma); kaydirmaSaati.kalan = 30; kaydirmaSaati.start() }
    }
    onClosing: sekmeleriKaydet()
    function sekmeKapat(i) {
        if (i < 0 || i >= sekmeler.length) return
        if (sekmeler.length < 2) { pencere.close(); return }   // tek sekme: tarayıcıdaki gibi pencere kapanır
        if (i === etkinSekme) sekmeyeGec(i + 1 < sekmeler.length ? i + 1 : i - 1)
        var l = sekmeler.slice()
        l.splice(i, 1)
        if (etkinSekme > i) etkinSekme--
        sekmeler = l
    }
    function kanalAc(id, ad) {
        if (!id) return
        if (abonelik) abonelik.kanalaGirildi(id, "")   // sol listedeki mavi nokta söner
        if (kanalSayfasi.kanalId !== id || !kanalSayfasi.videolar.length) kanalSayfasi.ac(id, ad)
        sayfaya("kanal")
    }

    function videoAc(id, onBilgi, listeden) {
        if (sayfa !== "video" || videoId !== id) yerKaydet()
        if (!listeden) calanListe = null
        if (gorunum.sayfa === "tam" && !tamEkran) tamEkranDegistir()
        videoId = id
        videoBilgi = onBilgi || ({ id: id })
        videoSayfasi.onerileriKoy([])
        videoSayfasi.oneriDevamVar = false
        videoSayfasi.basaDon()
        sayfa = "video"
        oynatici.canliIpucu(!!videoBilgi.canli)
        // Kaldığı yerden; bitmiş ya da başta kalmışsa baştan.
        if (duraklatarakAc) oynatici.acDurakli(id, kayit.baslangic(id))
        else oynatici.ac(id, kayit.baslangic(id))
        if (id.indexOf("://") < 0) veri.video(id)   // tam adres: YouTube dışı dosya (sınama)
    }
    function aramaYap(metin) {
        metin = metin.trim()
        if (!metin) return
        // Yalnız liste bağlantısı (playlist?list=...): liste programa alınır. İçinde video da olan
        // bağlantı (watch?v=...&list=...) videoyu açar, YouTube'daki gibi.
        if (/[?&]list=[A-Za-z0-9_-]+/.test(metin) && !/[?&]v=/.test(metin)) {
            pencere.uyari = qsTr("Liste okunuyor…"); uyariSaati.restart()
            listeler.bagliListeAl(metin); return
        }
        var m = metin.match(/shorts\/([A-Za-z0-9_-]{11})/)
        if (m) { shortsAc([{ id: m[1] }], 0, ""); return }
        m = metin.match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{11})/)
        if (m) { videoAc(m[1]); return }
        sorgu = metin
        aramaSayfasi.sonuclar = []
        aramaSayfasi.yukleniyor = true
        aramaSayfasi.basaDon()
        sayfaya("arama")
        veri.ara(metin)
    }
    function sayfaya(ad) {
        if (ad !== sayfa) yerKaydet()
        if ((sayfa === "video" || sayfa === "shorts") && ad !== sayfa) { oynatici.durdur(); calanListe = null }
        if (ad === "gecmis") gecmisSayfasi.yenile()
        if (ad === "abonelik") abonelikSayfasi.yenile()
        if (ad === "kesfet") kesfetSayfasi.yenile()
        if (ad === "liste") listelerSayfasi.yenile()
        if (ad === "yenilikler") yeniliklerSayfasi.yenile()
        sayfa = ad
    }
    // Tam ekrandan çıkınca pencere girmeden önceki hâline döner: büyütülmüşse büyütülmüş, kendisi tam
    // ekransa tam ekran (showNormal büyütülmüş pencereyi küçük boyuna indiriyordu).
    property int tamEkrandanOnce: Window.Windowed
    // Pencere 5 dakikadan uzun küçültülmüşse (liste ya da müzik dinlerken) görüntü çözülmez, yalnız ses sürer;
    // pencere açılınca geri gelir (oynatici.goruntu). Kısa küçültmede hiçbir şey değişmez: geri açınca ses 1-2 sn
    // durduğu için sık küçültüp açanı rahatsız etmesin (28 Ekim).
    property bool goruntuKapali: false
    property int kucukSuresi: 5 * 60 * 1000   // denemede LVT_KUCUK_SN ile kısalır (uygulama.py)
    Timer {
        id: kucukSaati; interval: pencere.kucukSuresi
        onTriggered: { oynatici.goruntu(false); pencere.goruntuKapali = true }
    }
    onVisibilityChanged: {
        if (visibility === Window.Minimized) kucukSaati.restart()
        else {
            kucukSaati.stop()
            if (goruntuKapali) { oynatici.goruntu(true); goruntuKapali = false }
        }
    }
    function tamEkranDegistir() {
        tamEkran = !tamEkran
        if (tamEkran) {
            tamEkrandanOnce = pencere.visibility
            pencere.showFullScreen()
        } else if (tamEkrandanOnce === Window.Maximized) pencere.showMaximized()
        else if (tamEkrandanOnce !== Window.FullScreen) pencere.showNormal()
    }

    // Geçmiş: video açılınca değil, birkaç saniye oynayınca (oynatici.py, IZLEME_SN).
    Connections {
        target: oynatici
        function onIzlemeBasladi(id) {
            if (id === pencere.videoId) kayit.izlendi(Object.assign({}, pencere.videoBilgi, { id: id }))
        }
    }
    Connections {
        target: veri
        function onAramaGeldi(q, videolar, devamVar) {
            if (q !== pencere.sorgu) return
            aramaSayfasi.sonuclar = aramaSayfasi.sonuclar.concat(videolar)
            aramaSayfasi.devamVar = devamVar
            aramaSayfasi.yukleniyor = false
        }
        function onVideoGeldi(id, bilgi) {
            if (id !== pencere.videoId) return
            pencere.videoBilgi = bilgi
            kayit.bilgiTamamla(id, bilgi)
            if (pencere.sayfa === "shorts") return   // Shorts görünümünde öneri ve yorum yok
            videoSayfasi.onerileriKoy(bilgi.oneriler)
            videoSayfasi.oneriDevamVar = true
            Qt.callLater(videoSayfasi.yorumlariDenetle)   // yenilemede yorumların ilk sayfası aynı olabilir
        }
        function onOnerilerGeldi(id, oneriler, devamVar) {
            if (id !== pencere.videoId) return
            videoSayfasi.onerileriEkle(oneriler)
            videoSayfasi.oneriDevamVar = devamVar
            videoSayfasi.devamIstendi = false
        }
        function onHata(ne, metin) {
            aramaSayfasi.yukleniyor = false
            pencere.uyari = qsTr("YouTube'dan %1 alınamadı: %2").arg(ne).arg(metin)
            uyariSaati.restart()
        }
    }
    Timer { id: uyariSaati; interval: 6000; onTriggered: pencere.uyari = "" }
    Connections { target: indirici; function onBildirim(metin) { pencere.uyari = metin; uyariSaati.restart() } }
    Connections {
        target: listeler
        function onIceAlindi(no, metin) {
            pencere.uyari = metin; uyariSaati.restart()
            if (no > 0) { sayfaya("liste"); listelerSayfasi.sec(no) }
        }
    }

    // Yazı kutusu bırakılınca tuşlar yeniden videoya gider. Yazı kutusunun dışına ya da bir düğmeye
    // tıklayınca uygulama.py'deki OdakBekcisi bunu çağırır.
    function tuslariVideoyaVer() { kisayol.forceActiveFocus() }

    // ---- Tarayıcı alışkanlıkları: yazı seçip kopyalama, sayfada bul, yapıştır, adres çubuğu.
    property var seciliYazi: null          // en son fareyle seçilen yazı (SecilirYazi): Ctrl+C onu kopyalar
    function yaziSecildi(y) {
        if (seciliYazi && seciliYazi !== y) seciliYazi.deselect()
        seciliYazi = y
    }
    // OdakBekcisi her basıştan sonra çağırır: seçili yazının dışına basılınca seçim kalkar (tarayıcıdaki gibi).
    function basildi(x, y) {
        if (seciliYazi && !seciliYazi.contains(seciliYazi.mapFromItem(null, x, y))) { seciliYazi.deselect(); seciliYazi = null }
    }
    // Türkçe küçük harf: I -> ı, İ -> i (JavaScript'in toLowerCase'i dili bilmiyor). Yalnız ekran dili Türkçeyken ya da
    // aranan söz Türkçeye özgü harf içerirken (bicim.turkce_mi gibi); İngilizcede "I" -> "i".
    readonly property bool bulTurkce: Qt.locale().name.indexOf("tr") === 0 || /[ıİğĞşŞ]/.test(bulKutu.text)
    function bulKucuk(s) { return (bulTurkce ? s.replace(/I/g, "ı") : s).replace(/İ/g, "i").toLowerCase() }
    // Bir öğenin içindeki bir yeri (öğenin y'si) görünür yapar: öğenin içinde olduğu kaydırılabilir sayfa kaydırılır.
    function kaydirGoster(oge, icY) {
        var f = oge.parent
        while (f && typeof f.flickableDirection === "undefined") f = f.parent
        if (!f) return
        var n = oge.mapToItem(f.contentItem, 0, icY)
        f.contentY = Math.max(f.originY, Math.min(f.originY + Math.max(0, f.contentHeight - f.height), n.y - f.height / 3))
    }
    property var bulKaynaklari: []         // BulKaynagi kendini buraya yazar
    property string bulunanId: ""          // video kartı bulunduysa çerçevelenir (VideoKarti)
    property var bulunanlar: []
    property int bulSira: -1
    function bulYenile() {
        for (var k = 0; k < bulKaynaklari.length; k++) bulKaynaklari[k].birak()
        var sorgu = bulKucuk(bulKutu.text), l = []
        if (sorgu.length) for (var i = 0; i < bulKaynaklari.length; i++) {
            var kaynak = bulKaynaklari[i]
            if (!kaynak.hedef || !kaynak.hedef.visible) continue
            var e = kaynak.eslesmeler(sorgu)
            for (var j = 0; j < e.length; j++) { e[j].kaynak = kaynak; l.push(e[j]) }
        }
        l.sort(function(a, b) { return a.y - b.y })
        bulunanlar = l
    }
    function bulGit(yon) {
        if (!bulunanlar.length) { bulSira = -1; return }
        if (bulSira >= 0 && bulSira < bulunanlar.length) bulunanlar[bulSira].kaynak.birak()
        bulSira = ((bulSira < 0 ? (yon > 0 ? -1 : 0) : bulSira) + yon + bulunanlar.length) % bulunanlar.length
        bulunanlar[bulSira].kaynak.goster(bulunanlar[bulSira])
    }
    // Kutuda önceki aramanın yazısı kalmışsa yeniden aranır (kapatıp açınca sayfada olan yazıya
    // "Bulunamadı" diyordu; yazı değişmediği için arama yapılmıyordu, Enter'a basınca düzeliyordu).
    function bulAc() {
        bulCubugu.visible = true; bulKutu.forceActiveFocus(); bulKutu.selectAll()
        if (bulKutu.text) { bulSira = -1; bulYenile(); bulGit(1) }
    }
    function bulKapat() {
        for (var k = 0; k < bulKaynaklari.length; k++) bulKaynaklari[k].birak()
        bulunanlar = []; bulSira = -1; bulCubugu.visible = false; kisayol.forceActiveFocus()
    }
    // Video kutusu Shorts ile video sayfası arasında geçerken yeniden yerleşir: video sayfasının yer tutucusu yerinden
    // oynamayınca kutu Shorts'un dikey boyunda kalıyordu, sayfa biraz kaydırılınca düzeliyordu (28 Ekim).
    onSayfaChanged: { kenarUstte = false; if (bulCubugu.visible) bulKapat(); if (videoluSayfa) Qt.callLater(videoKutusu.yeniden) }
    Shortcut { sequences: [StandardKey.Find]; onActivated: pencere.bulAc() }
    Shortcut { sequences: [StandardKey.Copy]; enabled: !!pencere.seciliYazi && pencere.seciliYazi.selectedText !== ""
        onActivated: pencere.seciliYazi.copy() }
    // Adres çubuğu gibi: arama kutusuna gider, içindekini seçer.
    Shortcut { sequences: ["Ctrl+L"]; onActivated: adresSatiri.yazmayaBasla() }   // tarayıcıdaki gibi adres çubuğu
    Shortcut { sequences: ["F5", "Ctrl+R"]; onActivated: pencere.yenile() }
    // Yakınlık (tarayıcıdaki gibi; Ctrl+artı/eksi/0, Ctrl+tekerlek, kişi menüsü): seçim kaydedilir, ortada yüzdesi
    // görünür. Değiştirmek bitince (Ctrl bırakıldıktan ~1 sn sonra) program bir kez yeniden açılır ve yeni boyla
    // gelir; her adımda açılmaz. Başa dönülürse açılmaz. Anında büyütme (sayfa tek kutuda ölçeklenince) yazıları ve
    // videoyu bulanıklaştırıyordu (28 Ekim); yeniden açılınca Qt her şeyi o boyda baştan çiziyor.
    function yakinlikDegistir(yon) {
        kisiler.yakinlikDegistir(yon)
        yakinlikGostergesi.goster()
        if (kisiler.yakinlik === kisiler.acikYakinlik) yakinlikSaati.stop()
        else yakinlikSaati.restart()
    }
    Connections { target: kisiler; function onTekerlek(yon) { pencere.yakinlikDegistir(yon) } }
    Timer {
        id: yakinlikSaati; interval: 1000
        onTriggered: {
            if (kisiler.ctrlBasili()) { restart(); return }   // hâlâ ayarlıyor
            if (kisiler.yakinlik !== kisiler.acikYakinlik) pencere.yakinlikUygula()
        }
    }
    function yakinlikUygula() { durumlaYenidenAc() }
    // Program aynı yerden yeniden açılır (yakınlık, dil): sekmeler, oynayan video, pencerenin yeri ve kaydırma.
    function durumlaYenidenAc() {
        kisiler.yenidenAc(JSON.stringify({
            oynat: (sayfa === "video" || sayfa === "shorts") && !oynatici.durakli, kaydirma: kaydirmaAl(),
            x: pencere.x, y: pencere.y, w: pencere.width, h: pencere.height,
            buyuk: pencere.visibility === Window.Maximized, olcek: kisiler.acikYakinlik }))
    }
    // Yakınlıkla yeniden açılınca sayfa aynı yerden sürsün. Sütun sayısı değiştiği için piksel değil, en üstteki
    // video saklanır (ızgaralar); başlık bölümündeyse ya da ızgara değilse sayfadaki oranı.
    function kaydirmaAlani() {
        var s = ({ abonelik: abonelikSayfasi, arama: aramaSayfasi, kanal: kanalSayfasi, kesfet: kesfetSayfasi,
                   gecmis: gecmisSayfasi, video: videoSayfasi })[sayfa]
        return s ? s.kaydirmaAlani : null
    }
    function kaydirmaAl() {
        var f = kaydirmaAlani()
        if (!f || f.contentY - f.originY < 4) return null
        var ust = f.contentY - f.originY, bas = f.headerItem ? f.headerItem.height : 0
        var i = f.indexAt ? f.indexAt(f.contentX + 20, f.contentY + 20) : -1
        if (i >= 0) return { i: i }
        if (bas > 0 && ust < bas) return { baslik: ust / bas }
        return { oran: ust / Math.max(1, f.contentHeight) }
    }
    Timer {
        id: kaydirmaSaati; interval: 300; repeat: true
        property var hedef: null
        property int kalan: 0
        onTriggered: {
            var f = pencere.kaydirmaAlani(), h = hedef
            if (!f || !h || --kalan < 0) { stop(); return }
            if (h.i !== undefined) {
                if (f.count > h.i) { f.positionViewAtIndex(h.i, GridView.Beginning); stop() }
                else f.contentY = f.originY + Math.max(0, f.contentHeight - f.height)   // ardı gelsin
            } else if (h.baslik !== undefined) {
                if (f.headerItem && f.headerItem.height > 0) { f.contentY = f.originY + h.baslik * f.headerItem.height; stop() }
            } else if (f.contentHeight > f.height) {
                f.contentY = f.originY + Math.min(h.oran * f.contentHeight, f.contentHeight - f.height); stop()
            }
        }
    }
    Rectangle {
        id: yakinlikGostergesi
        parent: Overlay.overlay
        anchors.centerIn: parent
        z: 1000
        width: yakinlikYazi.implicitWidth + 48; height: yakinlikYazi.implicitHeight + 28; radius: 12
        color: "#e0202020"
        opacity: 0; visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 150 } }
        function goster() { opacity = 1; yakinlikGizle.restart() }
        Timer { id: yakinlikGizle; interval: 1200; onTriggered: if (!yakinlikSaati.running) yakinlikGostergesi.opacity = 0 }
        Column {
            id: yakinlikYazi
            anchors.centerIn: parent
            spacing: 4
            Text { anchors.horizontalCenter: parent.horizontalCenter; color: "white"; font.pixelSize: 28; font.bold: true
                text: qsTr("%%1").arg(kisiler.yakinlik) }
            Text { anchors.horizontalCenter: parent.horizontalCenter; color: "#c0c0c0"; font.pixelSize: 13
                text: yakinlikSaati.running ? qsTr("Bırakınca uygulanır") : "" ; visible: text !== "" }
        }
    }
    Shortcut { sequences: [StandardKey.ZoomIn]; onActivated: pencere.yakinlikDegistir(1); onActivatedAmbiguously: pencere.yakinlikDegistir(1) }
    Shortcut { sequences: ["Ctrl+="]; onActivated: pencere.yakinlikDegistir(1); onActivatedAmbiguously: pencere.yakinlikDegistir(1) }
    Shortcut { sequences: [StandardKey.ZoomOut]; onActivated: pencere.yakinlikDegistir(-1); onActivatedAmbiguously: pencere.yakinlikDegistir(-1) }
    Shortcut { sequences: ["Ctrl+0"]; onActivated: pencere.yakinlikDegistir(0) }
    Shortcut { sequences: [StandardKey.Forward]; onActivated: pencere.ileri(); onActivatedAmbiguously: pencere.ileri() }
    Shortcut { sequences: [StandardKey.AddTab]; onActivated: pencere.yeniSekme(null, true) }
    Shortcut { sequences: ["Ctrl+W"]; enabled: pencere.sekmeler.length > 1; onActivated: pencere.sekmeKapat(pencere.etkinSekme) }
    Shortcut { sequences: ["Ctrl+Tab", "Ctrl+PgDown"]; onActivated: pencere.sekmeyeGec((pencere.etkinSekme + 1) % pencere.sekmeler.length) }
    Shortcut { sequences: ["Ctrl+Shift+Tab", "Ctrl+Backtab", "Ctrl+PgUp"]
        onActivated: pencere.sekmeyeGec((pencere.etkinSekme + pencere.sekmeler.length - 1) % pencere.sekmeler.length) }
    // Yazı kutusu dışında Ctrl+V: panodaki YouTube bağlantısı açılır (yazı kutusunda kutunun kendi yapıştırması çalışır).
    Shortcut { sequences: [StandardKey.Paste]
        onActivated: {
            var m = pano.oku().trim()
            if (/(youtube\.com|youtu\.be)\//.test(m)) pencere.aramaYap(m)
        } }
    Connections { target: ust; function onYaziyorChanged() { if (!ust.yaziyor) kisayol.forceActiveFocus() } }
    Connections { target: adresSatiri; function onYaziyorChanged() { if (!adresSatiri.yaziyor) kisayol.forceActiveFocus() } }
    // Başka bir yazı kutusu (liste adı gibi) kapanınca da odak boşta kalmasın, tuşlar videoya dönsün.
    onActiveFocusItemChanged: if (!activeFocusItem) Qt.callLater(function() { if (!pencere.activeFocusItem) kisayol.forceActiveFocus() })
    Component.onCompleted: {
        kenarAcik = kayit.ayar("kenar") === "1"; kisayol.forceActiveFocus(); abonelikSayfasi.yenile()
        sekmeleriGetir()
    }

    // Üstten aşağı tarayıcıdaki sıra: sekmeler, adres satırı, programın kendi üst şeridi, sayfa.
    AdresSatiri {
        id: adresSatiri
        layer.enabled: visible   // bkz. videoSayfasi
        anchors { left: parent.left; right: parent.right; top: sekmeSeridi.bottom }
        visible: !pencere.tamEkran
        height: visible ? 44 : 0
        adres: pencere.sayfaAdresi
        geriVar: pencere.yigin.length > 0
        ileriVar: pencere.ileriYigin.length > 0
        onGeri: pencere.geri()
        onIleri: pencere.ileri()
        onYenile: pencere.yenile()
        onGit: function(metin) { pencere.adresAc(metin) }
    }

    Ust {
        id: ust
        layer.enabled: visible   // bkz. videoSayfasi
        anchors { left: parent.left; right: parent.right; top: adresSatiri.bottom }
        visible: !pencere.tamEkran
        height: visible ? 56 : 0
        onAra: function(metin) { pencere.aramaYap(metin) }
        // Addaki tıklama abonelik sayfasına götürür (bugünkü düzendeki gibi).
        onAnaSayfa: pencere.sayfaya("abonelik")
        onAbonelikler: pencere.sayfaya("abonelik")
        onGecmis: pencere.sayfaya("gecmis")
        onKitaplik: pencere.sayfaya("liste")
        onKesfet: pencere.sayfaya("kesfet")
        onGeriBildirim: geriBildirimPenceresi.ac(pencere.sayfaAdresi)
        onMenu: pencere.kenarDegistir()
        kutuYazisi: pencere.sayfa === "arama" ? pencere.sorgu : ""
    }

    SekmeSeridi {
        id: sekmeSeridi
        layer.enabled: visible   // bkz. videoSayfasi
        anchors { left: parent.left; right: parent.right; top: parent.top }
        visible: !pencere.tamEkran
        height: visible ? 36 : 0
        adlar: pencere.sekmeAdlari
        etkin: pencere.etkinSekme
        onSec: function(i) { pencere.sekmeyeGec(i) }
        onKapat: function(i) { pencere.sekmeKapat(i) }
        onYeni: pencere.yeniSekme(null, true)
    }

    KenarListesi {
        id: kenar
        anchors { left: parent.left; top: ust.bottom; bottom: parent.bottom }
        width: 240
        visible: pencere.kenarIter || (pencere.kenarUstte && !pencere.tamEkran)
        z: 5
        onSec: function(id, ad) { pencere.kenarUstte = false; pencere.kanalAc(id, ad) }
        onYeniSekmede: function(id, ad) {
            pencere.yeniSekme({ sayfa: "kanal", kanalId: id, kanalAd: ad }, false)
            pencere.uyari = qsTr("Yeni sekmede açıldı: %1").arg(ad); uyariSaati.restart()
        }
    }
    // Liste videonun üstüne açılınca arkası kararır; tıklayınca liste kapanır.
    Rectangle {
        anchors.fill: icerik
        visible: pencere.kenarUstte && kenar.visible
        z: 4
        color: "#99000000"
        MouseArea { anchors.fill: parent; onClicked: pencere.kenarUstte = false }
    }

    Item {
        id: icerik
        anchors { left: parent.left; right: parent.right; top: ust.bottom; bottom: parent.bottom }
        anchors.leftMargin: pencere.kenarIter ? kenar.width : 0
        clip: true
        // Farenin yan tuşu (geri) bir önceki sayfaya döner.
        TapHandler { acceptedButtons: Qt.BackButton; onTapped: pencere.geri() }
        TapHandler { acceptedButtons: Qt.ForwardButton; onTapped: pencere.ileri() }

        AramaSayfasi {
            id: aramaSayfasi
            anchors.fill: parent
            visible: pencere.sayfa === "arama"
            onSec: function(v) { pencere.videoAc(v.id, v) }
            onDahaFazla: veri.aramaDevami(pencere.sorgu)
        }
        AboneliklerSayfasi {
            id: abonelikSayfasi
            anchors.fill: parent
            visible: pencere.sayfa === "abonelik"
            onSec: function(v) { pencere.videoAc(v.id, v) }
        }
        ShortsSayfasi {
            id: shortsSayfasi
            anchors.fill: parent
            visible: pencere.sayfa === "shorts"
            liste: pencere.shortsListe
            sira: pencere.shortsSira
            bilgi: pencere.videoBilgi
            kaynak: pencere.shortsKaynak
            sonda: pencere.shortsSonu
            onOnceki: pencere.shortsGec(-1)
            onSonraki: pencere.shortsGec(1)
        }
        KesfetSayfasi {
            id: kesfetSayfasi
            anchors.fill: parent
            visible: pencere.sayfa === "kesfet"
        }
        GecmisSayfasi {
            id: gecmisSayfasi
            objectName: "gecmisSayfasi"
            anchors.fill: parent
            visible: pencere.sayfa === "gecmis"
            onSec: function(v) { pencere.videoAc(v.id, v) }
        }
        KanalSayfasi {
            id: kanalSayfasi
            objectName: "kanalSayfasi"
            anchors.fill: parent
            visible: pencere.sayfa === "kanal"
            onSec: function(v) { pencere.videoAc(v.id, v) }
        }
        YeniliklerSayfasi {
            id: yeniliklerSayfasi
            objectName: "yeniliklerSayfasi"
            anchors.fill: parent
            visible: pencere.sayfa === "yenilikler"
        }
        ListelerSayfasi {
            id: listelerSayfasi
            anchors.fill: parent
            visible: pencere.sayfa === "liste"
            onOynat: function(listeId, sira) { pencere.listeOynat(listeId, sira) }
        }
        VideoSayfasi {
            id: videoSayfasi
            // Video her karede bütün pencereyi yeniden çizdiriyordu (Qt Quick hep tamamını çizer): sayfa bir kez
            // dokuya çizilip saklanır, karede yalnız o doku konur. Sayfada bir şey değişince doku yenilenir
            // (28 Ekim ölçümü: oynarken işlemci %21'den %39'a sayfa dolunca çıkıyordu).
            layer.enabled: visible
            calanListe: pencere.calanListe
            oynatici: oynatici
            onListeSec: function(i) { pencere.listeOynat(pencere.calanListe.id, i) }
            onListeKapat: pencere.calanListe = null
            anchors.fill: parent
            visible: pencere.sayfa === "video"
            bilgi: pencere.videoBilgi
            onSec: function(v) { pencere.videoAc(v.id, v) }
            onDahaFazla: veri.oneriDevami(pencere.videoId)
            onYerDegisti: videoKutusu.yerlestir()
            kip: gorunum.sayfa === "sinema" || gorunum.sayfa === "yorum" ? gorunum.sayfa : "normal"
            elleBoy: gorunum.yanBoy
            videoOrani: oynatici.oran
            onKipChanged: Qt.callLater(videoKutusu.yeniden)
            videoYanda: videoKutusu.yanda
            videoSolda: videoKutusu.solda
        }

        // Tek oynatıcı: sayfadaki yer tutucunun üstüne yerleşir; tam ekranda bütün pencereyi kaplar.
        // Böylece sayfa değişse ya da kaydırılsa da video öğesi yeniden kurulmaz.
        // Aşağı kaydırınca videonun yarısından çoğu görünmez olursa video yana geçer:
        // önerilerin sütununun üstüne, sütun genişliğinde; ya da sağ üste küçük. Sağ altta
        // durmaz, çünkü aşağı inerken yeni gelen önerileri kapatıyordu.
        Item {
            id: videoKutusu
            objectName: "videoKutusu"
            visible: pencere.sayfa === "video" || (pencere.sayfa === "shorts" && !pencere.shortsSonu)
            z: 10
            property bool yanda: false
            property bool solda: false        // yandayken ok düğmesiyle sola alındı (önerilere bakmak için)
            property bool gizli: false        // yandayken ✕ ile gizlendi: görüntü gider, ses sürer
            property bool ilkYerlesme: false  // yana yeni geçti: kaydırma durunca satırlar hizalanır
            property int cekilenBoy: 0        // köşeden çekilirken geçici genişlik
            readonly property int kenar: 16
            readonly property bool ters: LayoutMirroring.enabled
            // Yandaki video fiziksel olarak solda mı. Soldaki ana sütuna ok ile alınınca (solda) ve sağdan sola kipte
            // varsayılan: öneriler sütunu soldadır, video orada durur.
            readonly property bool fizikselSol: (solda && videoSayfasi.sagGenislik > 0) !== ters
            function yeniden() { yanda = false; yerlestir() }
            // Yandaki videonun x'i: fizikselSol ise sol kenardaki sütunun solu, değilse sağ kenardaki sütunun sağı
            // (ters kipte sütunlar yer değiştirir). Öneriler yoksa yan sütun kenarda durur.
            function yanX(genislik) {
                var anaSol = videoSayfasi.solSutun.mapToItem(icerik, 0, 0).x, anaSag = anaSol + videoSayfasi.solSutun.width
                var sutun = videoSayfasi.sagGenislik > 0
                var oneriSol = sutun ? videoSayfasi.sagSutun.mapToItem(icerik, 0, 0).x : kenar
                var oneriSag = sutun ? oneriSol + videoSayfasi.sagGenislik : icerik.width - kenar
                if (fizikselSol) return ters ? oneriSol : anaSol
                return ters ? anaSag - genislik : oneriSag - genislik
            }
            function yerlestir() {
                if (pencere.tamEkran) { videoSayfasi.yanVideoEn = 0; yanda = false; x = 0; y = 0; width = icerik.width; height = icerik.height; return }
                if (pencere.sayfa === "shorts") {
                    var sy = shortsSayfasi.videoYeri, sp = sy.mapToItem(icerik, 0, 0)
                    yanda = false; gizli = false; x = sp.x; y = sp.y; width = sy.width; height = sy.height
                    return
                }
                var h = videoSayfasi.videoYeri
                var p = h.mapToItem(icerik, 0, 0)
                // Yorum düzeninde video sütunundan ayrılmaz ve boyu değişmez; sayfa aşağı kayınca üst kenara
                // değdiği an orada durur (video yarısına kadar üst şeridin altına giriyordu,
                // en büyük boydayken de yandaki küçük videonun 960 px sınırına küçülüyordu).
                if (videoSayfasi.duzen === "yorum" && h.height > 0) {
                    videoSayfasi.yanVideoEn = 0; solda = false
                    yanda = p.y < 0
                    if (!yanda) gizli = false
                    // Köşeden çekilirken yalnız video büyür (sağ kenarı yerinde); sayfa bırakınca yeni boya göre
                    // dizilir (her fare adımında yüzlerce yorumu yeniden dizmemek için).
                    width = cekilenBoy ? Math.round(Math.max(320, Math.min(cekilenBoy, icerik.width * 0.6))) : h.width
                    height = cekilenBoy ? Math.round(width * 9 / 16) : h.height
                    x = ters ? p.x : p.x + h.width - width; y = Math.max(p.y, 0)
                    return
                }
                var gorunen = Math.min(p.y + h.height, icerik.height) - Math.max(p.y, 0)
                if (h.height <= 0 || gorunen >= h.height / 2) {
                    videoSayfasi.yanVideoEn = 0
                    yanda = false; gizli = false; solda = false
                    x = p.x; y = p.y; width = h.width; height = h.height
                    return
                }
                var sutun = videoSayfasi.sagGenislik > 0
                var boy = cekilenBoy || gorunum.yanBoy
                // Ok düğmesiyle sola alınmışsa sol sütunun başında durur (sol kenarı sabit), yoksa sağ kenarda.
                if (sutun && (gorunum.yan === "buyuk" || gorunum.yan === "yorumlar")) {
                    // En büyük (aşağı inince videodan mahrum kalmamak, yorumları okurken yukarı
                    // çıkmadan izlemek): pencerenin %60'ı, yüksekliğin %70'ine sığacak kadar; yazılara en az 400 px
                    // kalır. Yazılar video bırakılınca daralır (çekerken her fare adımında yorumları yeniden dizmemek için).
                    // Köşeden çekilen boy ve "yorumlar" seçimi daha büyüyebilir: öneriler kapanır, video pencerenin alt
                    // kenarına ya da yazılara 400 px kalana kadar (29 Ekim: video sağda, solda yorumlar).
                    var yaziPayi = videoSayfasi.solSutun.width + videoSayfasi.sagGenislik - 400
                    var enCok = Math.min(yaziPayi, icerik.height * 16 / 9)
                    var sinir = Math.min(icerik.width * 0.6, yaziPayi)
                    var en = boy ? Math.min(boy, enCok)
                           : gorunum.yan === "yorumlar" ? enCok : Math.min(sinir, icerik.height * 0.7 * 16 / 9)
                    width = Math.round(Math.max(videoSayfasi.sagGenislik, en))
                    height = Math.round(width * 9 / 16)
                    x = yanX(width); y = 0
                    if (!cekilenBoy) videoSayfasi.yanVideoEn = width
                    if (!yanda) ilkYerlesme = true
                    yanda = true
                    return
                }
                videoSayfasi.yanVideoEn = 0
                if (sutun && gorunum.yan === "genis" && !boy) {
                    width = videoSayfasi.sagGenislik
                    height = Math.round(width * 9 / 16)
                    x = yanX(width); y = 0
                    if (!yanda) ilkYerlesme = true
                } else {
                    var en = Math.min(sutun ? icerik.width * 0.6 : icerik.width * 0.5, 960)
                    width = Math.round(Math.max(240, Math.min(boy || 320, en)))
                    height = Math.round(width * 9 / 16)
                    // Sütun varken üst kenara yapışık (üstünden öneri görünmesin); dar pencerede köşeden içeride.
                    x = yanX(width); y = sutun ? 0 : kenar
                }
                yanda = true
            }
            // Görüntü yandayken ✕ ile gizlenince öğe çizilmez; mpv sesi çalmayı sürdürür.
            Oynatici { id: oynatici; anchors.fill: parent; visible: !videoKutusu.gizli }
            OynaticiCubugu {
                anchors.fill: parent
                visible: !videoKutusu.gizli
                oynatici: oynatici
                tamEkran: pencere.tamEkran
                gorunum: gorunum
                baslik: pencere.videoBilgi.baslik || ""
                sonrakiVar: pencere.sonrakiVar
                onSonrakiIstendi: pencere.sonrakiVideo()
                onTamEkranIstendi: pencere.tamEkranDegistir()
            }
            // Yandaki videonun düğmeleri: yerine dön, gizle; sol üst köşeden çekerek boyutlandırma (4. ilke:
            // gizli kısayol bilmeden). Alt köşeler oynatıcı çubuğunun, sağ üst bu düğmelerin.
            HoverHandler { id: yanFare; enabled: videoKutusu.yanda || videoSayfasi.duzen === "yorum" }
            Row {
                visible: videoKutusu.yanda && !videoKutusu.gizli && (yanFare.hovered || cekme.pressed)
                x: videoKutusu.fizikselSol ? 4 : parent.width - width - 4; y: 4
                spacing: 2
                Simge { ad: "arrow_upward"; golge: true; boy: 22; ipucu: qsTr("Videonun yerine dön")
                    onTiklandi: videoSayfasi.basaDon() }
                Simge { ad: "close"; golge: true; boy: 22; ipucu: qsTr("Görüntüyü gizle (ses sürer)")
                    onTiklandi: videoKutusu.gizli = true }
            }
            Rectangle {
                visible: (videoKutusu.yanda || videoSayfasi.duzen === "yorum") && !pencere.tamEkran && !videoKutusu.gizli
                         && (yanFare.hovered || cekme.pressed)
                // Video sola alınmışsa tutamak sağ üstte, düğmeler sol üstte (sabit kenar sol).
                x: videoKutusu.fizikselSol ? parent.width - width - 4 : 4; y: 4
                width: 26; height: 26; color: "#b0000000"; radius: 4
                Image { anchors.centerIn: parent; source: "../simgeler/open_in_full.svg"; width: 18; height: 18; sourceSize: Qt.size(36, 36)
                    rotation: videoKutusu.fizikselSol ? 0 : 90 }
                MouseArea {
                    id: cekme
                    anchors.fill: parent; anchors.margins: -4
                    cursorShape: videoKutusu.fizikselSol ? Qt.SizeBDiagCursor : Qt.SizeFDiagCursor
                    property real sabit: 0   // çekerken yerinde kalan kenar
                    onPressed: function(m) { sabit = videoKutusu.fizikselSol ? videoKutusu.x : videoKutusu.x + videoKutusu.width }
                    onPositionChanged: function(m) {
                        if (!pressed) return
                        var px = mapToItem(icerik, m.x, m.y).x
                        videoKutusu.cekilenBoy = Math.max(240, videoKutusu.fizikselSol ? px - sabit : sabit - px)
                        videoKutusu.yerlestir()
                    }
                    onReleased: {
                        var b = videoKutusu.width
                        videoKutusu.cekilenBoy = 0
                        gorunum.yanBoy = b
                    }
                    ToolTip.visible: containsMouse && !pressed; ToolTip.delay: 600
                    ToolTip.text: qsTr("Büyüt, küçült")
                    hoverEnabled: true
                }
            }
            // Ok düğmesi: yandaki video tek tıkla öbür tarafa geçer; sağdayken yorumlar okunur,
            // soldayken öneriler açıkta kalır. Fare videonun üstündeyken görünür; ok videonun gideceği yönü gösterir.
            Rectangle {
                visible: videoKutusu.yanda && !videoKutusu.gizli && videoSayfasi.sagGenislik > 0 && !pencere.tamEkran
                         && videoSayfasi.duzen !== "yorum" && (yanFare.hovered || tarafFare.containsMouse)
                x: videoKutusu.fizikselSol ? parent.width - width - 8 : 8
                anchors.verticalCenter: parent.verticalCenter
                width: 44; height: 44; radius: 22; color: tarafFare.containsMouse ? "#e0303030" : "#b0000000"
                Image { anchors.centerIn: parent; width: 26; height: 26; sourceSize: Qt.size(52, 52)
                    source: "../simgeler/" + (videoKutusu.fizikselSol ? "arrow_forward" : "arrow_back") + ".svg" }
                MouseArea {
                    id: tarafFare
                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: { videoKutusu.solda = !videoKutusu.solda; videoKutusu.yerlestir() }
                    ToolTip.visible: containsMouse; ToolTip.delay: 600
                    ToolTip.text: videoKutusu.fizikselSol ? qsTr("Videoyu sağa al") : qsTr("Videoyu sola al")
                }
            }
        }
        // Görüntü gizliyken: ses sürüyor, tek tıkla geri gelir (kullanıcıdan saklanmaz).
        Rectangle {
            visible: pencere.sayfa === "video" && videoKutusu.gizli
            anchors { top: parent.top; right: parent.right; margins: 12 }
            z: 11
            width: gizliSatir.implicitWidth + 24; height: 36; radius: 18; color: Renk.yuzey
            Row {
                id: gizliSatir; anchors.centerIn: parent; spacing: 10
                Text { text: qsTr("Görüntü gizli, ses sürüyor"); color: Renk.yaziSoluk; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                Text { text: qsTr("Göster"); color: Renk.mavi; font.pixelSize: 13; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter }
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: videoKutusu.gizli = false }
        }
        // Video önerilerin üstündeyken kaydırma durunca sayfa en yakın satıra kayar (en çok yarım satır):
        // videonun alt kenarı bir öneri satırının başına değer, satırın resmini ve başlığını kesmez
        // ("yapışsın fakat girmesin"). Yana yeni geçildiyse her zaman; sonra yalnız fare
        // öneriler sütunundayken (kişi önerilere bakıyor). Soldaki yazıyı okuyanın sayfası oynamaz.
        Timer {
            id: yerlesme
            interval: 160
            onTriggered: {
                var k = videoKutusu, vs = videoSayfasi, f = vs.kaydirma
                if (!k.yanda || k.gizli || k.fizikselSol || pencere.tamEkran || vs.sagGenislik === 0) return
                if (gorunum.yan !== "buyuk" && gorunum.yan !== "yorumlar" && (gorunum.yan !== "genis" || gorunum.yanBoy)) return
                if (f.moving || f.dragging) { restart(); return }
                if (!k.ilkYerlesme && !vs.sagUstunde) return
                k.ilkYerlesme = false
                var adim = vs.satirAdimi
                var alt = k.y + k.height
                var ilk = vs.sagSutun.mapToItem(icerik, 0, 0).y
                if (ilk >= alt) return
                var fark = ((alt - ilk) % adim + adim) % adim
                if (fark === 0) return
                var enCok = Math.max(0, f.contentHeight - f.height)
                // İki aday: satırları aşağı (sayfa yukarı) ya da yukarı (sayfa aşağı) kaydırmak; yakın olan,
                // video yanda kalıyorsa ve sayfanın sınırındaysa.
                var adaylar = fark <= adim / 2 ? [f.contentY - fark, f.contentY + adim - fark] : [f.contentY + adim - fark, f.contentY - fark]
                for (var i = 0; i < adaylar.length; i++) {
                    var c = adaylar[i]
                    if (c < 0 || c > enCok) continue
                    var yer = vs.videoYeri, ust = yer.mapToItem(icerik, 0, 0).y + (f.contentY - c)
                    var gorunen = Math.min(ust + yer.height, icerik.height) - Math.max(ust, 0)
                    if (gorunen >= yer.height / 2) continue
                    hizala.to = c; hizala.restart()
                    return
                }
            }
        }
        NumberAnimation { id: hizala; target: videoSayfasi.kaydirma; property: "contentY"; duration: 140; easing.type: Easing.OutCubic }
        Connections { target: videoSayfasi; function onYerDegisti() { if (!hizala.running) yerlesme.restart() } }
        onWidthChanged: videoKutusu.yeniden()
        onHeightChanged: videoKutusu.yeniden()
    }
    onTamEkranChanged: Qt.callLater(videoKutusu.yeniden)

    // StandardKey.Back Linux'ta ve Windows'ta Alt+Sol; aynı tuşu ikinci kez yazmak kısayolu "belirsiz"
    // yapıp hiç çalıştırmıyordu.
    Shortcut { sequences: [StandardKey.Back]; onActivated: pencere.geri(); onActivatedAmbiguously: pencere.geri() }

    // Bir yazı kutusu seçili değilse tuşlar videoya gider (YouTube kısayolları).
    Kisayollar {
        id: kisayol
        objectName: "kisayol"
        anchors.fill: parent
        etkin: (pencere.sayfa === "video" || pencere.sayfa === "shorts") && !ust.yaziyor && !adresSatiri.yaziyor
        shortsKipi: pencere.sayfa === "shorts"
        onShortsGec: function(adim) { pencere.shortsGec(adim) }
        oynatici: oynatici
        onTamEkranIstendi: pencere.tamEkranDegistir()
        onCikis: if (pencere.tamEkran) pencere.tamEkranDegistir()
        onSonraki: pencere.sonrakiVideo()
        onGeri: pencere.geri()
    }

    // Sayfada bul çubuğu (Ctrl+F): Enter sonraki, Shift+Enter önceki, Esc kapatır.
    Rectangle {
        id: bulCubugu
        visible: false
        z: 60
        // Solda: sağ üstte aşağı kaydırınca video duruyor, onu kapatmasın. Sol kenardaki liste açıksa onun sağında.
        anchors { left: kenar.visible ? kenar.right : parent.left; top: ust.bottom; leftMargin: 24; topMargin: 8 }
        // Eni içindekilerden: sabit 420 iken düğmeler sığmıyor, kapatma çarpısı kutunun dışına taşıyordu.
        width: bulSatir.implicitWidth + 18; height: 44; radius: 10; color: Renk.yuzey; border.color: Renk.cizgi
        Row {
            id: bulSatir
            anchors { fill: parent; leftMargin: 12; rightMargin: 6 }
            spacing: 6
            TextField {
                id: bulKutu
                objectName: "bulKutu"
                width: 230; anchors.verticalCenter: parent.verticalCenter
                placeholderText: qsTr("Sayfada bul"); placeholderTextColor: Renk.yaziSoluk
                color: Renk.yazi; font.pixelSize: 14; background: null; selectByMouse: true
                onTextChanged: { pencere.bulSira = -1; pencere.bulYenile(); pencere.bulGit(1) }
                Keys.onReturnPressed: function(e) { if (!pencere.bulunanlar.length) pencere.bulYenile(); pencere.bulGit(e.modifiers & Qt.ShiftModifier ? -1 : 1) }
                Keys.onEnterPressed: function(e) { pencere.bulGit(e.modifiers & Qt.ShiftModifier ? -1 : 1) }
                Keys.onEscapePressed: pencere.bulKapat()
            }
            Text {
                width: 70; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight
                color: pencere.bulunanlar.length || !bulKutu.text ? Renk.yaziSoluk : Renk.hata; font.pixelSize: 13
                text: !bulKutu.text ? "" : pencere.bulunanlar.length ? (pencere.bulSira + 1) + " / " + pencere.bulunanlar.length : qsTr("Bulunamadı")
            }
            Simge { ad: "expand_less"; boy: 22; ipucu: qsTr("Önceki (Shift+Enter)"); anchors.verticalCenter: parent.verticalCenter; onTiklandi: pencere.bulGit(-1) }
            Simge { ad: "expand_more"; boy: 22; ipucu: qsTr("Sonraki (Enter)"); anchors.verticalCenter: parent.verticalCenter; onTiklandi: pencere.bulGit(1) }
            Simge { ad: "close"; boy: 20; ipucu: qsTr("Kapat (Esc)"); anchors.verticalCenter: parent.verticalCenter; onTiklandi: pencere.bulKapat() }
        }
    }

    GeriBildirimPenceresi { id: geriBildirimPenceresi }
    // Dil: ilk açılışta (dil hiç seçilmemişse) kendiliğinden, sonra kişi menüsünden (dilPenceresiniAc).
    DilPenceresi { id: dilPenceresi }
    function dilPenceresiniAc() { dilPenceresi.open() }
    Timer { running: !kisiler.dilSecildi; interval: 400; onTriggered: dilPenceresi.open() }
    // Yeni sürüm arka planda indirilince (guncelleme.py).
    GuncellemePenceresi { id: guncellemePenceresi; objectName: "guncellemePenceresi" }
    // Güncellendikten sonraki ilk açılış (yenilikler.py): sürümün ana başlıkları. Dil penceresi açıksa beklenir.
    GuncellendiPenceresi { id: guncellendiPenceresi; objectName: "guncellendiPenceresi" }
    property bool guncellendiGosterildi: false
    Timer { running: !pencere.guncellendiGosterildi && yenilikler.oncekiSurum !== "" && kisiler.dilSecildi && !dilPenceresi.opened
        interval: 600; onTriggered: { pencere.guncellendiGosterildi = true; guncellendiPenceresi.ac() } }
    // Seçili yazıyı programda aramak (SecileniAra): video ya da Shorts açıksa durmasın diye yeni sekmede.
    function secileniAra(metin) {
        if (sayfa === "video" || sayfa === "shorts") yeniSekme({ sayfa: "arama", sorgu: metin }, true)
        else aramaYap(metin)
    }
    // Yenilikler sayfası: video ya da Shorts açıksa (yeniden açılışta kaldığı yerden) durmasın diye yeni sekmede.
    function yenilikleriAc() {
        if (sayfa === "video" || sayfa === "shorts") yeniSekme({ sayfa: "yenilikler" }, true)
        else sayfaya("yenilikler")
    }
    // Dil penceresi açıksa (ilk açılış) onun üstüne açılmaz, dil seçilince açılır. Başka bir dil seçilirse program
    // yeniden açılır; yeni kopya güncellemeye yeniden bakar, pencere o dilde gelir.
    property string bekleyenSurum: ""
    // "Güncellendi" penceresi açıkken de bekler (yeni bir sürüm daha indiyse).
    Connections { target: guncelleme; function onHazir(surum) {
        if (dilPenceresi.opened || !kisiler.dilSecildi || guncellendiPenceresi.opened) pencere.bekleyenSurum = surum
        else guncellemePenceresi.ac(surum) } }
    Connections { target: dilPenceresi; function onClosed() { if (pencere.bekleyenSurum) bekleyenAc.start() } }
    Connections { target: guncellendiPenceresi; function onClosed() { if (pencere.bekleyenSurum) bekleyenAc.start() } }
    Timer { id: bekleyenAc; interval: 300
        onTriggered: { guncellemePenceresi.ac(pencere.bekleyenSurum); pencere.bekleyenSurum = "" } }
    // Abonelikler getirilirken hiçbir tarayıcıda YouTube girişi yoksa (tarayici.py).
    FirefoxPenceresi { objectName: "firefoxPenceresi" }

    Rectangle {
        visible: pencere.uyari !== ""
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 24 }
        width: uyariYazi.implicitWidth + 32; height: 40; radius: 8; color: "#323232"; z: 100
        Text { id: uyariYazi; anchors.centerIn: parent; text: pencere.uyari; color: Renk.videoYazi; font.pixelSize: 14 }
    }
}
