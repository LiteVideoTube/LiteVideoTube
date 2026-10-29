import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects

// Kanal sayfası: kanalın resmi, adı, abone ve video sayısı, açıklaması, "Abone ol" ve videoları
// (en yeniler önde, aşağı indikçe devamı gelir). Abonelik yalnız programda kalır, YouTube hesabına
// yazılmaz.
Item {
    id: ks
    readonly property Flickable kaydirmaAlani: izgara   // yakınlıkla yeniden açılınca kaydırma yeri (Ana.qml)
    property string kanalId: ""
    property var bilgi: ({})
    // Kanal şu an canlı yayındaysa yayın (abonelik.canliYayin): resmin çevresinde kırmızı halka, tıklayınca yayın açılır
    // (YouTube'daki gibi). Program yalnız abone olunan kanalların yayınını bilir.
    property var canli: ({})
    // Başlığın boyu kanal bilgisi geldikten sonra da büyüyor; kişi kaydırmaya başlayana kadar boy değiştikçe sayfa
    // başa alınır (AboneliklerSayfasi gibi). Önceden sayfa başı üstten kesik açılıyordu.
    property bool basaAl: false
    property var videolar: []
    property bool devamVar: false
    property bool yukleniyor: false
    // Videolar ve Shorts bölümü (bir kanalın bütün Shorts'larını görmek isteyen buraya girer).
    // Shorts bölümü ilk seçilince istenir.
    property string bolum: "videolar"
    property var shorts: []
    property bool shortsDevamVar: false
    property bool shortsIstendi: false
    readonly property bool shortsta: bolum === "shorts"
    signal sec(var v)
    function bolumSec(b) {
        bolum = b
        if (b === "shorts" && !shortsIstendi) { shortsIstendi = true; yukleniyor = true; veri.kanalShorts(kanalId) }
    }
    function ac(id, ad) {
        kanalId = id; bilgi = { ad: ad || "" }; videolar = []; devamVar = false; yukleniyor = true
        canli = abonelik ? abonelik.canliYayin(id) : ({})
        bolum = "videolar"; shorts = []; shortsDevamVar = false; shortsIstendi = false
        basaAl = true
        izgara.contentY = izgara.originY
        veri.kanal(id)
    }
    Connections {
        target: veri
        function onKanalGeldi(id, k) {
            if (id !== ks.kanalId) return
            ks.bilgi = k; ks.videolar = k.videolar; ks.devamVar = k.devamVar; ks.yukleniyor = false
            if (abonelik) abonelik.kanalaGirildi(id, k.resim || "")   // sol listedeki mavi nokta söner
            Qt.callLater(function() { izgara.contentY = izgara.originY })   // başlık görünsün
        }
        function onKanalVideolariGeldi(id, vler, devam) {
            if (id !== ks.kanalId) return
            ks.videolar = ks.videolar.concat(vler); ks.devamVar = devam; ks.yukleniyor = false
        }
        function onKanalShortslariGeldi(id, vler, devam, ilk) {
            if (id !== ks.kanalId) return
            // Shorts sekmesinde kanal adı yok: Shorts görünümünde kanal ve "Abone ol" hemen görünsün.
            vler.forEach(function(v) { v.kanal = ks.bilgi.ad || ""; v.kanal_id = ks.kanalId })
            ks.shorts = ilk ? vler : ks.shorts.concat(vler); ks.shortsDevamVar = devam; ks.yukleniyor = false
        }
    }

    readonly property int sutun: ks.shortsta ? Math.max(2, Math.floor((width - 32) / 200))
                                              : Math.max(1, Math.min(Renk.enCokSutun, Math.floor((width - 32) / 300)))

    GridView {
        id: izgara
        TekerlekHizi { hedef: izgara }
        IzgaraBul { izgara: izgara; liste: ks.shortsta ? ks.shorts : ks.videolar }
        anchors.fill: parent; anchors.leftMargin: 24; anchors.topMargin: 0
        cellWidth: (width - 8) / ks.sutun
        cellHeight: ks.shortsta ? (cellWidth - 16) * 16 / 9 + 76 : cellWidth * 9 / 16 + 112
        model: ks.shortsta ? ks.shorts : ks.videolar
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        onMovementStarted: ks.basaAl = false
        header: Item {
            width: izgara.width - 16; height: ust.implicitHeight + 40
            onHeightChanged: if (ks.basaAl) Qt.callLater(function() { izgara.contentY = izgara.originY })
            Column {
                id: ust
                y: 24; width: parent.width; spacing: 16
                Row { anchors.left: parent.left;
                    spacing: 20
                    Item {
                        width: 96; height: 96
                        Image { id: avatar; anchors.fill: parent; source: ks.bilgi.resim || ""; asynchronous: true
                            sourceSize: Qt.size(192, 192); visible: false }
                        Rectangle { id: maske; anchors.fill: parent; radius: 48; visible: false; layer.enabled: true }
                        MultiEffect { anchors.fill: parent; source: avatar; maskEnabled: true; maskSource: maske
                            visible: avatar.status === Image.Ready }
                        Rectangle { anchors.fill: parent; radius: 48; color: Renk.yuzey; visible: avatar.status !== Image.Ready
                            Text { anchors.centerIn: parent; text: (ks.bilgi.ad || "?").charAt(0); color: Renk.yazi; font.pixelSize: 40 } }
                        Rectangle { visible: !!ks.canli.id; anchors.fill: parent; anchors.margins: -5; radius: width / 2
                            color: "transparent"; border.color: "#cc0000"; border.width: 3 }
                        Rectangle { visible: !!ks.canli.id; anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom; anchors.bottomMargin: -10
                            width: canliYazi.implicitWidth + 10; height: 18; radius: 3; color: "#cc0000"
                            Text { id: canliYazi; anchors.centerIn: parent; text: qsTr("CANLI"); color: "white"; font.pixelSize: 11; font.bold: true } }
                        MouseArea { visible: !!ks.canli.id; anchors.fill: parent; anchors.margins: -5
                            cursorShape: Qt.PointingHandCursor; onClicked: ks.sec(ks.canli) }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter; spacing: 6
                        Text { anchors.left: parent.left; text: ks.bilgi.ad || ""; color: Renk.yazi; font.pixelSize: 28; font.bold: true; SecimKatmani { } }
                        Text { anchors.left: parent.left; color: Renk.yaziSoluk; font.pixelSize: 14
                            text: [ks.bilgi.tutamac, ks.bilgi.abone, ks.bilgi.video_sayisi].filter(function(x) { return x }).join("  ·  ")
                            SecimKatmani { } }
                        Text { anchors.left: parent.left; width: Math.min(700, izgara.width - 200); color: Renk.yaziSoluk; font.pixelSize: 13
                            text: (ks.bilgi.aciklama || "").split("\n")[0]; elide: Text.ElideRight; visible: text !== ""
                            SecimKatmani { } }
                        AboneDugmeleri { anchors.left: parent.left; kanalId: ks.kanalId; kanalAd: ks.bilgi.ad || "" }
                    }
                }
                // Bölümler: seçili olanın altı çizili (YouTube'daki sekmeler gibi).
                Row { anchors.left: parent.left;
                    spacing: 28
                    Repeater {
                        model: [{ ad: "videolar", yazi: qsTr("Videolar") }, { ad: "shorts", yazi: qsTr("Shorts") }]
                        Column {
                            spacing: 6
                            Text { anchors.left: parent.left; text: modelData.yazi; font.pixelSize: 18; font.bold: true
                                color: ks.bolum === modelData.ad ? Renk.yazi : Renk.yaziSoluk
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: ks.bolumSec(modelData.ad) } }
                            Rectangle { width: parent.width; height: 3; radius: 1.5; color: ks.bolum === modelData.ad ? Renk.yazi : "transparent" }
                        }
                    }
                }
            }
        }
        delegate: ks.shortsta ? shortsKarti : videoKarti
        // Kart hücrenin başında (sağdan sola dilde sağında, anchors.left aynalanır; AramaSayfasi gibi).
        Component { id: videoKarti; Item { width: izgara.cellWidth; height: izgara.cellHeight
            VideoKarti { anchors.left: parent.left; width: izgara.cellWidth - 16; v: modelData; onSec: ks.sec(modelData) } } }
        Component { id: shortsKarti; Item { width: izgara.cellWidth; height: izgara.cellHeight
            ShortsKarti { anchors.left: parent.left; width: izgara.cellWidth - 16; liste: ks.shorts; sira: index; kaynak: "kanal:" + ks.kanalId } } }
        // İlk videolar ekrana sığıyorsa kaydıracak yer olmadığından içerik boyu değişince de bakılır (AramaSayfasi gibi).
        function devamBak() {
            if (ks.yukleniyor || contentY + height <= contentHeight - 600) return
            if (ks.shortsta && ks.shortsDevamVar) { ks.yukleniyor = true; veri.kanalShortsDevami(ks.kanalId) }
            else if (!ks.shortsta && ks.devamVar) { ks.yukleniyor = true; veri.kanalDevami(ks.kanalId) }
        }
        onContentYChanged: devamBak()
        onContentHeightChanged: Qt.callLater(devamBak)
        Connections { target: ks; function onYukleniyorChanged() { if (!ks.yukleniyor) Qt.callLater(izgara.devamBak) } }
    }
    Text {
        anchors.centerIn: parent
        visible: (ks.shortsta ? ks.shorts : ks.videolar).length === 0
        color: Renk.yaziSoluk; font.pixelSize: 16
        text: ks.yukleniyor ? (ks.shortsta ? qsTr("Shorts yükleniyor…") : qsTr("Kanal yükleniyor…"))
                            : (ks.shortsta ? qsTr("Bu kanalda Shorts yok.") : qsTr("Bu kanalda video bulunamadı."))
        SecimKatmani { }
    }
}
