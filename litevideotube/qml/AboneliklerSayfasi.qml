import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Abonelik akışı: en yeniler önde, izlenen video düşer. Yeni video gelince sayfanın başındaysa hemen eklenir,
// aşağıdaysa başa dönülünce (kişi bakarken kartlar kaymasın). Haber yazısı yok (yorucu).
Item {
    id: a
    readonly property Flickable kaydirmaAlani: izgara   // yakınlıkla yeniden açılınca kaydırma yeri (Ana.qml)
    // Kapanışta Python nesnesi QML'den önce gidebiliyor; o anda boş sayılır.
    readonly property int kanalSayisi: abonelik ? abonelik.kanalSayisi : 0
    readonly property int yeni: abonelik ? abonelik.yeni : 0
    property var akis: ({ canlilar: [], yeniler: [], ilgiler: [], zilliler: [], digerleri: [], shorts: [] })   // abonelik.py, akis
    // "Şu an canlı" kapalıyken canlı yayınlar başka bölümlerde de görünmez (canlı yayın görmek
    // istemeyen kapatır). Bölümde kanal başına bir yayın var; aynı kanalın öteki yayınları aşağıdaki listede.
    function canliSuz(l) { return a.kapalilar["canli"] ? l.filter(function(v) { return !v.canli }) : l }
    readonly property var videolar: canliSuz(akis.digerleri.concat(devami))
    // "Bütün abonelikler" aşağı inildikçe devam eder (abonelik.py, devami). Önceden en yeni
    // 400 videoda bitiyordu. Baştaki bölümler değişmesin diye ayrı tutulur.
    property var devami: []
    property bool devamVar: true
    function devamBak() {
        // contentY başlığın üstünden (originY) sayılır: başlık uzunken (gündem bölümleri) ardı hiç istenmiyordu.
        if (!a.visible || izgara.contentY - izgara.originY + izgara.height < izgara.contentHeight - 600) return
        if (a.gundemde) { if (a.gundem.length) abonelik.gundemDevami(); return }   // gündemin ardı (abonelik.py)
        if (!a.devamVar) return
        var l = akis.digerleri.concat(devami)
        if (l.length === 0) { a.devamVar = false; return }
        var gorulen = l.concat(akis.canlilar, akis.zilliler, akis.yeniler, akis.ilgiler).map(function(v) { return v.id })
        var yeni = abonelik.devami(gorulen, l[l.length - 1].yayin)
        if (yeni.length === 0) a.devamVar = false
        else devami = devami.concat(yeni)
    }
    // Sayfanın başındaki bölümler (abonelik.py, akis): canlı, zilli kanallar, yeni gelenler, izlediklerine göre.
    readonly property var canlilar: akis.canlilar   // şu an canlı yayında olan abonelikler; yalnız varken görünür
    readonly property var yeniler: canliSuz(akis.yeniler)
    readonly property var ilgiler: canliSuz(akis.ilgiler)
    readonly property var zilliler: canliSuz(akis.zilliler)
    readonly property var shorts: akis.shorts     // abonelerin son üç günkü Shorts'ları; uzun videolarla karışmaz
    property string not_: ""
    signal sec(var v)
    // Aboneliği olmayan kişide sayfa boş durmaz: YouTube'un konu sayfalarından gündem (abonelik.py, gundem). Abonelikler
    // gelince kendiliğinden kalkar.
    readonly property bool gundemde: kanalSayisi === 0
    property var gundem: []
    property var gundemDevam: []   // gündem bölümlerinin altında, aşağı inildikçe gelen öneriler
    function gundemeBak() { if (a.gundemde) { a.gundem = abonelik.gundem(); abonelik.gundemYenile() } }
    // Baştaki bölümler başlığa tıklayınca kapanır ve açılır (canlı yayın görmek istemeyen kapatır;
    // kapalı bölümün yalnız başlığı kalır). Son hâl kayda yazılır, program kapanıp açılınca da öyle kalır.
    property var kapalilar: ({})
    Component.onCompleted: {
        var k = {}
        try { (JSON.parse(kayit.ayar("kapali_bolumler") || "[]")).forEach(function(ad) { k[ad] = true }) } catch (e) { }
        kapalilar = k
        gundemeBak()
    }
    // Başlığa tıklayınca bölüm olduğu yerde açılır ya da kapanır (28 Ekim; önceden basınca sayfa yukarı fırlıyordu).
    // Izgara ilk videoyu yerinde tutup baştaki bölümleri yukarı doğru büyütüyordu: açılan bölümün boyu kadar
    // tıklanan başlık yukarı kaçıyordu. Sayfanın başından uzaklık korunur; başlık ve üstündekiler kıpırdamaz.
    property real yerTut: -1
    Timer { id: yerBirak; interval: 300; onTriggered: a.yerTut = -1 }
    function yeriKoru() {
        izgara.contentY = izgara.originY + Math.min(a.yerTut, Math.max(0, izgara.contentHeight - izgara.height))
    }
    function bolumuDegistir(ad) {
        a.basaAl = false
        a.yerTut = izgara.contentY - izgara.originY
        yerBirak.restart()
        var k = Object.assign({}, kapalilar)
        if (k[ad]) delete k[ad]; else k[ad] = true
        kapalilar = k
        kayit.ayarYaz("kapali_bolumler", JSON.stringify(Object.keys(k)))
    }
    function acikken(ad, l) { return kapalilar[ad] ? [] : l }   // sayfada bul kapalı bölümde aramaz
    // Sayfada bul: bölüm başlığının bulunanlar arasındaki yeri, ızgaradaki sırayla (IzgaraBul) aynı ölçüde.
    function bulOncesi(ad) {
        var sira = ["canli", "zil", "yeni", "ilgi"], n = 0
        var l = { canli: a.canlilar, zil: a.zilliler, yeni: a.yeniler, ilgi: a.ilgiler.slice(0, a.sutun) }
        for (var i = 0; i < sira.length && sira[i] !== ad; i++) n += a.acikken(sira[i], l[sira[i]]).length
        return n - 0.75
    }
    // Baştaki bölümlerin boyu sonradan belli oluyor (resimler, dizilim); kişi kaydırmaya başlayana kadar
    // boy değiştikçe sayfa başa alınır. Tekerlek ve kaydırma çubuğu da kaydırmaya başlamak sayılır (onMovementStarted
    // yalnız sürüklemede geliyor; tekerlekle inen kişi bir başlığa tıklayınca sayfa en başa fırlıyordu).
    property bool basaAl: false
    // Izgarada video yokken (aboneliği olmayanda yalnız baştaki gündem bölümleri var) positionViewAtBeginning işlemiyor,
    // görünüm bölümlerin sonunda kalıyordu.
    function basaGit() { if (izgara.count === 0) izgara.contentY = izgara.originY; else izgara.positionViewAtBeginning() }
    function yenile() {
        akis = abonelik.akis()
        devami = []
        devamVar = true
        basaAl = true
        gundemeBak()
        Qt.callLater(a.basaGit)
    }

    // Yeni gelen videolar (28 Ekim: videolar beklemeden aksın): sayfanın başındayken hemen eklenir;
    // aşağıdayken bakılan kartlar kaymasın diye beklenir, başa dönülünce eklenir. "N yeni video geldi, göster" düğmesi
    // kalktı (yorucuydu); yenisi gelen kanal sol listede mavi noktayla zaten görünüyor.
    readonly property bool bastaMi: izgara.contentY - izgara.originY < 8 && !izgara.moving
    function yenileriAl() { if (a.yeni > 0 && a.visible && a.videolar.length > 0 && a.bastaMi) a.yenile() }
    onYeniChanged: yenileriAl()
    onBastaMiChanged: yenileriAl()

    Connections {
        target: abonelik
        function onIceAlindi(eklenen, metin) {
            a.not_ = eklenen >= 0 ? qsTr("%1 %n yeni kanal eklendi, videoları geliyor.", "", eklenen).arg(metin) : metin
        }
        // İlk içe almada sayfa boşken gelenler hemen gösterilir.
        function onDurumDegisti() { if (a.videolar.length === 0 && a.visible) a.yenile() }
        // Firefox penceresi açılır (FirefoxPenceresi.qml); "Tarayıcılara bakılıyor…" kalmasın.
        function onGirisBulunamadi() { a.not_ = "" }
        function onHesaptaAbonelikYok() { a.not_ = "" }
        // Model yeni diziyle değişince ızgara başa dönüyordu; kişinin yeri korunur.
        function onGundemDevamGeldi(l) {
            if (!l.length) return
            var y = izgara.contentY
            a.gundemDevam = a.gundemDevam.concat(l)
            izgara.contentY = y
        }
        function onGundemDegisti() { a.gundem = abonelik.gundem(); a.basaAl = true; Qt.callLater(a.basaGit) }
    }
    Connections {
        target: firefox
        function onBirakildi() { a.not_ = qsTr("Abonelikler getirilmedi. İstediğin zaman “Abonelikleri getir”e yeniden basabilirsin.") }
    }

    // Yönet menüsü sağ üstteki düğmenin altında, sağa yaslı.
    function menuyuAc(dugme) {
        yonetMenu.parent = dugme
        yonetMenu.x = dugme.width - yonetMenu.width
        yonetMenu.y = dugme.height + 4
        yonetMenu.open()
    }

    readonly property int sutun: Math.max(1, Math.min(Renk.enCokSutun, Math.floor((width - 32) / 300)))

    component Bolum: Column {
        id: bolum
        property string ad          // kapalı bölümlerin kaydındaki adı
        readonly property bool kapali: !!a.kapalilar[ad]
        property string baslik
        property string simge
        property var simgeRenk: null
        property bool kirmizi: false   // başlığın önünde kırmızı nokta (Şu an canlı)
        property var videolar: []
        width: izgara.width
        visible: videolar.length > 0
        height: visible ? implicitHeight : 0
        spacing: 8
        bottomPadding: visible ? 16 : 0
        BolumBasligi { anchors.left: parent.left;
            kirmizi: bolum.kirmizi; simge: bolum.simge; simgeRenk: bolum.simgeRenk; baslik: bolum.baslik; bulSira: a.bulOncesi(bolum.ad)
            kapali: bolum.kapali; sayi: bolum.videolar.length
            onDegistir: a.bolumuDegistir(bolum.ad)
        }
        Flow {
            visible: !bolum.kapali
            width: parent.width
            Repeater {
                model: bolum.videolar
                Item {
                    width: izgara.cellWidth; height: izgara.cellHeight
                    VideoKarti { anchors.left: parent.left; width: izgara.cellWidth - 16; v: modelData; onSec: a.sec(modelData) }
                }
            }
        }
        Rectangle { anchors.left: parent.left; width: parent.width - 8; height: 1; color: Renk.cizgi }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: 24; anchors.topMargin: 12; spacing: 8
        // Başta yalnız başlık (gereksiz ayrıntı kafa karıştırır; program yeni videolara zaten
        // kendiliğinden bakıyor). Kanal sayısı, abonelikleri getirmek ve arka planda bakma ayarı "Yönet"in
        // içinde; hiç abonelik yokken düğme doğrudan "Abonelikleri getir" der.
        RowLayout {
            Layout.fillWidth: true; Layout.rightMargin: 24
            Text { text: qsTr("Abonelikler"); color: Renk.yazi; font.pixelSize: 22; font.bold: true; Layout.fillWidth: true; SecimKatmani { } }
            // Abonelik yokken mavi "Abonelikleri getir" burada durur, sayfanın ortasında değil (getirmek zorlanmasın:
            // program aboneliksiz de kullanılır).
            Button {
                id: yonet
                readonly property bool getir: a.kanalSayisi === 0
                text: getir ? qsTr("Abonelikleri getir") : qsTr("Yönet")
                onClicked: yonetMenu.opened ? yonetMenu.close() : a.menuyuAc(yonet)
                contentItem: Text { text: yonet.text; color: yonet.getir ? "black" : Renk.yazi; font.pixelSize: 14
                    font.weight: yonet.getir ? Font.Medium : Font.Normal
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 18; implicitHeight: 36; implicitWidth: yonet.getir ? 160 : 88
                    color: yonet.getir ? (yonet.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu) : yonet.hovered ? Renk.yuzeyAcik : Renk.yuzey }
                MenuKutusu {
                    id: yonetMenu
                    objectName: "yonetMenu"
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                    contentItem: Column {
                        spacing: 2
                        Text { anchors.left: parent.left; visible: a.kanalSayisi > 0; leftPadding: 10; topPadding: 8; bottomPadding: 6
                            text: qsTr("%n kanala abonesin", "", a.kanalSayisi); color: Renk.yazi; font.pixelSize: 14 }
                        MenuCizgisi { anchors.left: parent.left; visible: a.kanalSayisi > 0; width: 420 }
                        // Başlık satırı tıklanmaz; satırlar onun altında içeriden başlar.
                        MenuBasligi { anchors.left: parent.left; text: qsTr("Abonelikleri getir") }
                        // Satırlar uzun: "yeni kişi olarak" kesilmeden okunsun.
                        MenuSatiri { anchors.left: parent.left; width: 420; yazi: qsTr("Tarayıcıdaki YouTube hesabından")
                            onTiklandi: { yonetMenu.close(); a.not_ = qsTr("Tarayıcılara bakılıyor…"); abonelik.tarayicidanAl() } }
                        // İkinci hesap ayrı dursun diye: yeni kişi açılır, program o kişiyle yeniden açılıp getirir.
                        MenuSatiri { anchors.left: parent.left; width: 420; yazi: qsTr("Tarayıcıdaki YouTube hesabından, yeni kişi olarak")
                            onTiklandi: { yonetMenu.close(); kisiler.yeniKisiyeTarayicidanAl("") } }
                        MenuCizgisi { anchors.left: parent.left; visible: a.kanalSayisi > 0; width: 420 }
                        // Program kapalıyken de yoklama sürer (kanallara 5 saatte bir, zilli
                        // kanallara 15 dakikada bir; bilgisayar açılınca kendiliğinden başlar). Varsayılan açık.
                        MenuSatiri { anchors.left: parent.left; visible: a.kanalSayisi > 0; width: 420
                            yazi: qsTr("Program kapalıyken de yeni videolara bak"); secili: abonelik.arkadaYoklama
                            onTiklandi: { yonetMenu.close(); abonelik.arkadaYoklama = !abonelik.arkadaYoklama } }
                    }
                }
            }
        }
        // Liste eskimiş olabilecekken tek sade satır (internet yok, açılışta yetişiliyor);
        // her şey yolundayken boş, görünmez (abonelik.py, _durum_al).
        Text {
            objectName: "abonelikDurumu"
            visible: abonelik && abonelik.durum !== "" && a.kanalSayisi > 0; Layout.fillWidth: true; Layout.rightMargin: 24
            text: abonelik ? abonelik.durum : ""; color: Renk.yaziSoluk; font.pixelSize: 14; wrapMode: Text.Wrap
            SecimKatmani { }
        }
        Text {
            visible: a.not_ !== ""; Layout.fillWidth: true; Layout.rightMargin: 24
            text: a.not_; color: Renk.yaziSoluk; font.pixelSize: 13; wrapMode: Text.Wrap
            SecimKatmani { }
        }
        GridView {
            id: izgara
            objectName: "abonelikIzgara"
            TekerlekHizi { hedef: izgara; onWheel: a.basaAl = false }
            IzgaraBul { izgara: izgara; liste: a.videolar
                bastakiler: a.acikken("canli", a.canlilar).concat(a.acikken("zil", a.zilliler), a.acikken("yeni", a.yeniler), a.acikken("ilgi", a.ilgiler.slice(0, a.sutun))) }
            Layout.fillWidth: true; Layout.fillHeight: true
            cellWidth: (width - 8) / a.sutun; cellHeight: cellWidth * 9 / 16 + 112
            model: a.gundemde ? a.gundemDevam : a.videolar
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { onPressedChanged: if (pressed) a.basaAl = false }
            // Kart hücrenin başında (sağdan sola dilde sağında, anchors.left aynalanır; baştaki bölümler gibi).
            delegate: Item { width: izgara.cellWidth; height: izgara.cellHeight
                VideoKarti { anchors.left: parent.left; width: izgara.cellWidth - 16; v: modelData; onSec: a.sec(modelData) } }
            // Başta bölümler: canlı, zilli kanallar, yeni gelenler, izlediklerine göre (yalnız bir satır);
            // altta kalanlar zamana göre.
            onMovementStarted: a.basaAl = false
            onContentYChanged: a.devamBak()
            onContentHeightChanged: { if (a.yerTut >= 0) a.yeriKoru(); Qt.callLater(a.devamBak) }
            header: Column {
                width: izgara.width
                topPadding: 16   // ilk bölüm başlığı sayfa başlığına yapışmasın
                onHeightChanged: if (a.yerTut >= 0) a.yeriKoru(); else if (a.basaAl) Qt.callLater(a.basaGit)
                Text { anchors.left: parent.left; visible: a.gundemde && a.gundem.length > 0; width: izgara.width - 8; wrapMode: Text.Wrap
                       bottomPadding: 16; color: Renk.yaziSoluk; font.pixelSize: 14
                       text: qsTr("Henüz aboneliğin yok; şimdilik YouTube'da gündemde olanlar. İstersen sağ üstten aboneliklerini getirebilirsin.")
                       SecimKatmani { } }
                Repeater {
                    model: a.gundemde ? a.gundem : []
                    Bolum { anchors.left: parent.left; ad: "gundem-" + modelData.ad; simge: "trending_up"; simgeRenk: ["5bc46a", "1e8e3e"]; baslik: modelData.baslik; videolar: modelData.videolar.slice(0, a.sutun * 2) }
                }
                Item { visible: a.gundemde && a.gundemDevam.length > 0; width: izgara.width; height: visible ? dahaFazla.height + 8 : 0
                    BolumBasligi { id: dahaFazla; simge: "trending_up"; simgeRenk: ["5bc46a", "1e8e3e"]; baslik: qsTr("Daha fazlası"); kapanir: false; bulSira: -0.1 } }
                // Zil simgesi yok: yeni gelenler bütün aboneliklerden, zil taktığın kanallardan değil.
                Bolum { anchors.left: parent.left; ad: "canli"; kirmizi: true; simge: "sensors_kirmizi"; baslik: qsTr("Şu an canlı"); videolar: a.canlilar }
                Bolum { anchors.left: parent.left; ad: "zil"; simge: "notifications_active_mavi"; baslik: qsTr("Zil taktığın kanallardan"); videolar: a.zilliler }
                Bolum { anchors.left: parent.left; ad: "yeni"; simge: "bolt"; simgeRenk: ["ffb74d", "f29900"]; baslik: qsTr("Yeni gelenler"); videolar: a.yeniler }
                Bolum { anchors.left: parent.left; ad: "ilgi"; simge: "auto_awesome"; simgeRenk: ["b388ff", "8e44ec"]; baslik: qsTr("İzlediklerine göre")
                        videolar: a.ilgiler.slice(0, a.sutun) }
                ShortsSeridi { width: izgara.width; liste: a.shorts; kaynak: "abonelik"
                               kapanir: true; kapali: !!a.kapalilar["shorts"]; onDegistir: a.bolumuDegistir("shorts")
                               kaydirici: izgara; bulSira: a.bulOncesi("") + 0.25 }
                Item { visible: a.canlilar.length + a.yeniler.length + a.ilgiler.length + a.zilliler.length + a.shorts.length > 0 && a.videolar.length > 0
                    width: izgara.width; height: visible ? butun.height + 8 : 0
                    BolumBasligi { id: butun; simge: "subscriptions"; simgeRenk: ["aaaaaa", "606060"]; baslik: qsTr("Bütün abonelikler"); kapanir: false
                                   bulSira: a.bulOncesi("") + 0.7 } }
            }
        }
    }
    // Sayfada hiçbir şey yokken: aboneliği olmayanda (gündem gelene kadar ya da internet yokken) kısa bir yazı, abonelikleri
    // olanda yazısız yükleniyor işareti. Önceden "Kanallara bakılıyor; yeni videolar birazdan burada." yazıyordu; baştaki
    // bölümlerde video varken de sayfanın ortasında kalıyor, kaydırınca peşinden geliyordu (28 Ekim: "yapışıyor gitmiyor").
    readonly property bool hicYok: a.videolar.length === 0 && a.canlilar.length + a.yeniler.length + a.ilgiler.length
                                   + a.zilliler.length + a.shorts.length === 0 && !(a.gundemde && a.gundem.length > 0)
    Text {
        anchors.centerIn: parent
        visible: a.hicYok && a.gundemde
        width: Math.min(560, a.width - 48); wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
        color: Renk.yaziSoluk; font.pixelSize: 16
        text: qsTr("Henüz aboneliğin yok. İstersen sağ üstten YouTube hesabındaki aboneliklerini getirebilirsin; hesabına hiçbir şey yazılmaz.")
    }
    BusyIndicator { anchors.centerIn: parent; running: a.hicYok && !a.gundemde; visible: running }
}
