import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Oynatıcının üstündeki çubuk ve dokunma davranışları:
// solda oynat, sonraki, ses, baştan oynat, döngü; ortada hız; sağda altyazı, ses dili, kalite,
// görünüm, tam ekran. Çubuk fare alt kenara yaklaşınca görünür, 1 sn kıpırdamayınca gizlenir.
Item {
    id: c
    property var oynatici
    property bool tamEkran: false
    // Hangi düğmeler çubukta (yandaki videoda, boyu ne olursa olsun hız, altyazı, kalite gibi
    // düğmeler kayboluyordu; yorum düzeninde dar videoda tam ekran sağdan taşıyordu). Karar videonun yerine
    // değil genişliğine göre: oynat, ses, zaman, görünüm, tam ekran hep durur; öbürleri önem sırasıyla sığdıkça
    // eklenir, sığmayanlar "⋯" menüsüne geçer. Zaman, sürenin iki katı yazısıyla ölçülür (saniyeler
    // ilerledikçe düğmeler gidip gelmesin).
    readonly property var sigan: {
        var d = 14, simge = 40
        var zamanEn = c.oynatici.canli ? canliYazi.implicitWidth : zamanOlcu.width
        var temel = 16 + 44 + d + simge + d + zamanEn + d + d + simge + d + simge + (c.sonrakiVar ? simge + d : 0)
        var aday = [["hiz", 150 + 2 * d], ["kalite", simge + d], ["altyazi", simge + d], ["sesDili", simge + d]]
        if (!c.oynatici.canli) aday.push(["bastan", simge + d], ["dongu", simge + d])
        var s = {}, kalan = c.width - temel
        if (aday.reduce(function(t, a) { return t + a[1] }, 0) <= kalan) {
            aday.forEach(function(a) { s[a[0]] = true }); return s
        }
        kalan -= simge + d
        aday.forEach(function(a) { if (a[1] <= kalan) { s[a[0]] = true; kalan -= a[1] } })
        s.daha = true
        return s
    }
    // Hız sürgüsü: çubukta ve "⋯" menüsünde aynısı.
    component HizSurgusu: Item {
        property bool menude: false   // menü açık görünümde beyaz; yol orada koyu
        Slider {
            id: hizSurgu
            anchors.fill: parent
            from: 0.5; to: 2.0; stepSize: 0.1
            value: c.oynatici.hiz
            onMoved: c.oynatici.hizAyarla(value)
            ToolTip.visible: hovered; ToolTip.delay: 600
            ToolTip.text: qsTr("Hız %1x").arg(c.oynatici.hiz.toFixed(1))
            background: Rectangle { x: hizSurgu.leftPadding; y: hizSurgu.topPadding + hizSurgu.availableHeight / 2 - 2
                width: hizSurgu.availableWidth; height: 4; radius: 2; color: menude ? Renk.k("#99ffffff", "#c6c6c6") : "#99ffffff" }
            handle: Rectangle { x: hizSurgu.leftPadding + hizSurgu.visualPosition * (hizSurgu.availableWidth - width)
                y: hizSurgu.topPadding + hizSurgu.availableHeight / 2 - height / 2; width: 36; height: 20; radius: 10; color: "#e0202020"; border.color: "white"
                Text { anchors.centerIn: parent; color: "white"; font.pixelSize: 11; text: c.oynatici.hiz.toFixed(1) + "x" } }
        }
        // Tekerlek hızı ancak fare sürgünün üstünde yarım saniye tekerleksiz durduktan sonra değiştirir; öncesinde
        // sayfayı kaydırır (kaydırırken fare sürgünün üstünden geçince hız istemeden değişiyordu).
        // Kaydırma sürdükçe süre yeniden başlar: video yandayken sayfa kayar, sürgü farenin altında durur.
        property real sakinden: 0
        HoverHandler { onHoveredChanged: { parent.sakinden = Date.now(); c.hizUstunde = hovered; if (!hovered) gizle.restart() } }
        MouseArea {
            anchors.fill: parent; acceptedButtons: Qt.RightButton
            onClicked: c.oynatici.hizAyarla(1.0)
            onWheel: function(w) {
                if (Date.now() - parent.sakinden < 500) { parent.sakinden = Date.now(); w.accepted = false; return }
                c.oynatici.hizAyarla(c.oynatici.hiz + (w.angleDelta.y > 0 ? 0.1 : -0.1))
            }
        }
    }

    TextMetrics { id: zamanOlcu; font.pixelSize: 14; text: c.zaman(c.oynatici.sure) + " / " + c.zaman(c.oynatici.sure) }
    // Menü hem kendi düğmesinden hem "⋯" menüsünden açılır; yer: menünün üstünde açılacağı öğe.
    function menuAc(m, yer) { m.parent = yer; m.opened ? m.close() : m.open() }
    property var gorunum
    property bool sonrakiVar: false      // bir liste oynuyor ve sırada video var
    signal sonrakiIstendi()
    signal tamEkranIstendi()

    readonly property bool gorunur: yakin || c.oynatici.durakli || c.oynatici.sonda || sesAcik || suruklenen || menuAcik
    property bool menuAcik: false
    property bool yakin: false
    property bool sesAcik: false
    property bool suruklenen: false
    property string baslik      // kare kaydedilirken dosya adı

    // Çubuktaki zamanlar hıza göre: 10 dakikalık video 2x'te "5:00" görünür, geçen süre de öyle.
    // Yorumlardaki zamanlar videonun kendi zamanıdır, onlara dokunulmaz.
    function zaman(s) {
        s = Math.max(0, Math.floor(s / (c.oynatici.hiz > 0 ? c.oynatici.hiz : 1)))
        var sa = Math.floor(s / 3600), dk = Math.floor(s % 3600 / 60), sn = s % 60
        return (sa > 0 ? sa + ":" + (dk < 10 ? "0" : "") : "") + dk + ":" + (sn < 10 ? "0" : "") + sn
    }

    // Fare hız sürgüsünün üstündeyken çubuk gizlenmez: tekerlekle hız için yarım saniye beklenirken gitmesin.
    property bool hizUstunde: false
    Timer { id: gizle; interval: 1000; onTriggered: if (!c.hizUstunde) c.yakin = false }
    // Zaman yalnız çubuk görünürken sorulur (saniyede 4 kez); gizliyken hiç.
    Binding { target: c.oynatici; property: "zamanAraligi"; value: c.gorunur ? 250 : 0 }
    // Çubuk görünürken altyazı çubuğun üstüne çıkar (YouTube'daki gibi); mpv'nin birimi 720 piksel
    // yüksekliğe göre ölçeklenmiş piksel.
    Binding { target: c.oynatici; property: "altyaziPayi"; value: c.height > 0 ? Math.round(((c.gorunur ? cubuk.height : 0) + 22) * 720 / c.height) : 22 }
    // Qt, altındaki görüntü değişince (her video karesinde) fare kıpırdamasa da fare olayı
    // gönderebiliyor; süre yalnız farenin yeri gerçekten değişince yenilenir.
    property point sonYer: Qt.point(-1, -1)
    function kipirti(p, altKenar) {   // p: sahne (pencere) koordinatı
        if (p.x === sonYer.x && p.y === sonYer.y) return
        sonYer = p
        if (altKenar || c.tamEkran) { c.yakin = true; gizle.restart() }
    }

    // Tek tık duraklatır, çift tık tam ekran (YouTube gibi). Tek tık, çift tık olmadığı anlaşılınca işlenir.
    MouseArea {
        id: alan
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: c.gorunur || !c.tamEkran ? Qt.ArrowCursor : Qt.BlankCursor
        onPositionChanged: function(m) { c.kipirti(mapToItem(null, m.x, m.y), m.y > height - 120) }
        onExited: gizle.restart()
        // Sağ tık YouTube'daki gibi menü açar (SagTikMenusu.qml).
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(m) { if (m.button === Qt.RightButton) { tekTik.stop(); sagMenu.ac(m.x, m.y) } else tekTik.restart() }
        onDoubleClicked: function(m) { if (m.button !== Qt.LeftButton) return; tekTik.stop(); c.tamEkranIstendi() }
        Timer { id: tekTik; interval: 220; onTriggered: c.oynatici.durdurOynat() }
        // Video üstünde tekerlek sayfayı kaydırır (22 Ekim): olay sayfaya geçsin diye kabul edilmez.
        onWheel: function(w) { w.accepted = false }
    }

    SagTikMenusu { id: sagMenu; oynatici: c.oynatici; baslik: c.baslik; onIstatistikIstendi: c.istatistikAcik = true }

    // İstatistikler (sağ tık menüsünden): eski bilgisayarda videonun neden takıldığı. Açıkken saniyede bir sorulur.
    property bool istatistikAcik: false
    property var istatistik: ({})
    Timer { interval: 1000; repeat: true; triggeredOnStart: true; running: c.istatistikAcik && c.visible
        onTriggered: c.istatistik = c.oynatici.istatistik() }
    Rectangle {
        visible: c.istatistikAcik
        // Sol üst köşenin hemen altında: köşe, yorum düzeninde videoyu büyütme tutamağının yeri.
        anchors { left: parent.left; top: parent.top; leftMargin: 12; topMargin: 40 }
        width: istatistikSatirlari.implicitWidth + 24; height: istatistikSatirlari.implicitHeight + 20
        radius: 8; color: "#d0000000"
        Grid {
            id: istatistikSatirlari
            anchors.left: parent.left; anchors.leftMargin: 12; y: 10; columns: 2; columnSpacing: 14; rowSpacing: 3
            property var s: c.istatistik
            component Ad: Text { color: Renk.videoSoluk; font.pixelSize: 13 }
            component Deger: Text { color: "white"; font.pixelSize: 13 }
            Ad { text: qsTr("Boyut") }               Deger { text: (istatistikSatirlari.s.boyut || "-") + (c.oynatici.seciliKalite >= 0 && c.oynatici.kaliteler[c.oynatici.seciliKalite]
                                                   ? "  (" + c.oynatici.kaliteler[c.oynatici.seciliKalite].ad + ")" : "") }
            Ad { text: qsTr("Biçim") }               Deger { text: istatistikSatirlari.s.bicim || "-" }
            Ad { text: qsTr("Çözen") }               Deger { text: istatistikSatirlari.s.cozen || "-" }
            Ad { text: qsTr("Atlanan kare") }        Deger { text: istatistikSatirlari.s.atlanan !== undefined ? istatistikSatirlari.s.atlanan : "-" }
            Ad { text: qsTr("Önden inen") }          Deger { text: istatistikSatirlari.s.onden !== undefined ? qsTr("%1 sn").arg(istatistikSatirlari.s.onden) : "-" }
            Ad { text: qsTr("İndirme hızı") }        Deger { text: istatistikSatirlari.s.hiz !== undefined ? qsTr("%1 KB/sn").arg(istatistikSatirlari.s.hiz) : "-" }
        }
        Text { anchors { right: parent.right; top: parent.top; margins: 4 } text: "✕"; color: Renk.videoSoluk; font.pixelSize: 13
            MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: c.istatistikAcik = false } }
    }

    // Video bitince ortada "Tekrar oynat".
    Rectangle {
        visible: c.oynatici.sonda
        anchors.centerIn: parent
        width: tekrar.implicitWidth + 40; height: 52; radius: 26; color: "#cc000000"
        Row {
            id: tekrar; anchors.centerIn: parent; spacing: 8
            Image { source: "../simgeler/replay.svg"; width: 28; height: 28; sourceSize: Qt.size(56, 56); anchors.verticalCenter: parent.verticalCenter }
            Text { text: qsTr("Tekrar oynat"); color: "white"; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: c.oynatici.durdurOynat() }
    }
    // Yükleniyor işareti: video beklerken ya da açılırken.
    BusyIndicator {
        anchors.centerIn: parent
        running: c.oynatici.hata === "" && (c.oynatici.cozuluyor || c.oynatici.bekliyor || (c.oynatici.sure === 0 && !c.oynatici.bos))
        visible: running
    }
    // Zayıf internette kalite düşünce kısa bir not (kullanıcıdan saklanmaz; 1. ilke).
    property string not_: ""
    Connections {
        target: c.oynatici
        function onKaliteDusuruldu(ad) { c.not_ = qsTr("İnternet yavaş: kalite %1'ye indi").arg(ad); notSaati.restart() }
        function onBildirim(metin) { c.not_ = metin; notSaati.restart() }
    }
    Timer { id: notSaati; interval: 5000; onTriggered: c.not_ = "" }
    Rectangle {
        visible: c.not_ !== ""
        anchors { top: parent.top; right: parent.right; margins: 12 }
        width: notYazi.implicitWidth + 20; height: 30; radius: 6; color: "#e0202020"
        Text { id: notYazi; anchors.centerIn: parent; text: c.not_; color: "white"; font.pixelSize: 13 }
    }
    // Açılamayan video: düz bir açıklama ve yeniden deneme.
    Rectangle {
        visible: c.oynatici.hata !== ""
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, hataSutun.implicitWidth + 40); height: hataSutun.implicitHeight + 32
        radius: 12; color: "#e0202020"
        Column {
            id: hataSutun; anchors.centerIn: parent; spacing: 12
            width: Math.min(c.width - 80, 520)
            // Yazılar seçilip kopyalanır (hatayı bildirmek için). YouTube'un asıl (İngilizce) sebebi
            // ekranda değil, günlükte (oynatici._hata_ver).
            SecilirYazi { width: parent.width; visible: text !== ""; color: "white"; font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter
                text: c.oynatici.hataBaslik }
            SecilirYazi { width: parent.width; color: Renk.videoSoluk; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter
                text: c.oynatici.hata }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter; spacing: 12
                Button { text: qsTr("Yeniden dene"); onClicked: c.oynatici.yenidenDene() }
                // Hafif yol açamazsa video kullanıcının tarayıcısında (5. ilke: YouTube bot sandı).
                Button { text: qsTr("Tarayıcıda aç"); onClicked: Qt.openUrlExternally(c.oynatici.baglanti(false)) }
            }
        }
    }

    Item {
        id: cubuk
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 64
        opacity: c.gorunur ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 150 } }
        Rectangle {
            anchors.fill: parent
            gradient: Gradient { GradientStop { position: 0; color: "#00000000" } GradientStop { position: 1; color: "#b0000000" } }
        }
        // Fare çubuğun üstünde de olsa 1 sn kıpırdamayınca çubuk gizlenir; her kıpırtı süreyi yeniler.
        HoverHandler { onPointChanged: c.kipirti(point.scenePosition, true) }

        // Zaman çubuğu: çizgisiz, üç renk; zemin gri, saydamlık 0,7 (siyah videoda da seçilsin).
        Item {
            id: zamanCubugu
            visible: !c.oynatici.canli   // canlı yayında zaman çubuğu yok, yerine "CANLI" yazar
            anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 12; rightMargin: 12 }
            height: 16
            readonly property real oran: c.oynatici.sure > 0 ? Math.min(1, c.oynatici.konum / c.oynatici.sure) : 0
            // inmis: mpv'nin demuxer-cache-time'ı, önden inen payın bittiği an (videodaki yer, süre değil). Önceden
            // konuma ekleniyordu; videonun ortasında çubuk sonuna kadar inmiş görünüyordu (27 Ekim).
            readonly property real inmisOran: c.oynatici.sure > 0 ? Math.min(1, Math.max(c.oynatici.konum, c.oynatici.inmis) / c.oynatici.sure) : 0
            readonly property int kalinlik: zamanFare.containsMouse || c.suruklenen ? 6 : 4
            Rectangle { id: zemin; anchors.verticalCenter: parent.verticalCenter; width: parent.width; height: zamanCubugu.kalinlik; radius: 2; color: Renk.inmemis; opacity: 0.7 }
            Rectangle { anchors.verticalCenter: parent.verticalCenter; width: parent.width * zamanCubugu.inmisOran; height: zamanCubugu.kalinlik; radius: 2; color: Renk.inmis; opacity: 0.85 }
            Rectangle { anchors.verticalCenter: parent.verticalCenter; width: parent.width * zamanCubugu.oran; height: zamanCubugu.kalinlik; radius: 2; color: Renk.videoMavi }
            Rectangle {
                visible: zamanFare.containsMouse || c.suruklenen
                x: parent.width * zamanCubugu.oran - 6; anchors.verticalCenter: parent.verticalCenter
                width: 12; height: 12; radius: 6; color: Renk.videoMavi
            }
            Rectangle {
                visible: zamanFare.containsMouse
                x: Math.max(0, Math.min(parent.width - width, zamanFare.mouseX - width / 2)); y: -30
                width: ipucuZaman.implicitWidth + 12; height: 24; radius: 4; color: "#e0202020"
                Text { id: ipucuZaman; anchors.centerIn: parent; color: "white"; font.pixelSize: 13
                    text: c.zaman(c.oynatici.sure * Math.max(0, Math.min(1, zamanFare.mouseX / zamanCubugu.width))) }
            }
            MouseArea {
                id: zamanFare
                anchors.fill: parent; anchors.topMargin: -4; anchors.bottomMargin: -4
                hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                onPressed: function(m) { c.suruklenen = true; c.oynatici.git(c.oynatici.sure * Math.max(0, Math.min(1, m.x / width))) }
                onPositionChanged: function(m) { if (pressed) c.oynatici.git(c.oynatici.sure * Math.max(0, Math.min(1, m.x / width))) }
                onReleased: c.suruklenen = false
            }
        }

        RowLayout {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 8; rightMargin: 8; bottomMargin: 2 }
            height: 44
            spacing: 14   // düğmeler arası 14 px
            Simge { ad: c.oynatici.durakli || c.oynatici.sonda ? "play_arrow" : "pause"; golge: true; boy: 28
                ipucu: c.oynatici.durakli ? qsTr("Oynat (k)") : qsTr("Duraklat (k)"); onTiklandi: c.oynatici.durdurOynat() }
            Simge { visible: c.sonrakiVar; ad: "skip_next"; golge: true; ipucu: qsTr("Listede sıradaki (Shift+N)"); onTiklandi: c.sonrakiIstendi() }
            Item {
                Layout.preferredWidth: sesDugme.implicitWidth; Layout.preferredHeight: sesDugme.implicitHeight
                Simge { id: sesDugme; ad: c.oynatici.sessiz || c.oynatici.ses === 0 ? "volume_off" : "volume_up"; golge: true
                    ipucu: qsTr("Ses (m)"); onTiklandi: c.oynatici.sessizDegistir()
                    onTekerlek: function(a) { c.oynatici.sesAyarla(c.oynatici.ses + a * 5) } }
                HoverHandler { onHoveredChanged: if (hovered) { c.sesAcik = true; sesKapat.stop() } else sesKapat.restart() }
                Timer { id: sesKapat; interval: 600; onTriggered: c.sesAcik = sesAlan.containsMouse }
                // Ses düzeyi düğmenin üstünde dikey çubuk; tekerlek hem çubukta hem düğmede çalışır. Popup: çubuk
                // alt şeridin dışına taşıyor, şeridin dışındaki kısmına tıklama ulaşmıyordu (tık bazen
                // tutmuyor, basılı tutup çekmek ve tekerlek çalışıyor). Popup pencerenin üst katmanında durur.
                Popup {
                    id: sesCubugu
                    visible: c.sesAcik && c.visible
                    x: (parent.width - width) / 2; y: -height
                    width: 36; height: 120; padding: 0
                    modal: false; closePolicy: Popup.NoAutoClose
                    background: Rectangle { radius: 8; color: "#e0202020" }
                    contentItem: Item {
                        Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 12; width: 4; height: parent.height - 24; radius: 2; color: Renk.inmemis
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; radius: 2; color: Renk.videoMavi
                                height: parent.height * (c.oynatici.sessiz ? 0 : c.oynatici.ses / 100) } }
                        MouseArea {
                            id: sesAlan
                            anchors.fill: parent; hoverEnabled: true
                            onExited: sesKapat.restart()
                            function ayarla(y) { c.oynatici.sesAyarla(Math.round(100 * (1 - Math.max(0, Math.min(1, (y - 12) / (height - 24)))))) }
                            onPressed: function(m) { ayarla(m.y) }
                            onPositionChanged: function(m) { if (pressed) ayarla(m.y) }
                            onWheel: function(w) { c.oynatici.sesAyarla(c.oynatici.ses + w.angleDelta.y / 120 * 5) }
                        }
                    }
                }
            }
            Simge { ad: "replay"; golge: true; ipucu: qsTr("Baştan oynat"); onTiklandi: c.oynatici.git(0); visible: !!c.sigan.bastan }
            Simge { ad: "repeat"; golge: true; visible: !!c.sigan.dongu; ipucu: c.oynatici.dongu ? qsTr("Döngü açık") : qsTr("Döngü"); opacity: c.oynatici.dongu ? 1 : 0.6
                onTiklandi: c.oynatici.donguDegistir() }
            Text { id: zamanYazi; visible: !c.oynatici.canli; color: "white"; font.pixelSize: 14; style: Text.Outline; styleColor: "black"
                text: c.zaman(c.oynatici.konum) + " / " + c.zaman(c.oynatici.sure) }
            Text { id: canliYazi; visible: c.oynatici.canli; color: "#ff5252"; font.pixelSize: 14; font.bold: true; style: Text.Outline; styleColor: "black"
                text: qsTr("● CANLI") }
            Item { Layout.fillWidth: true }
            // Hız ortada, sürgüyle; 0,1'lik ince ayar. Sağ tık normal hız.
            HizSurgusu { visible: !!c.sigan.hiz; Layout.preferredWidth: 150; Layout.preferredHeight: 40 }
            Item { Layout.fillWidth: true; visible: !!c.sigan.hiz }
            Item {
                visible: !!c.sigan.altyazi
                Layout.preferredWidth: altyaziDugme.implicitWidth; Layout.preferredHeight: altyaziDugme.implicitHeight
                readonly property bool var_: c.oynatici.altyaziElle.length + c.oynatici.altyaziOtomatik.length + c.oynatici.altyaziCeviri.length > 0
                Simge { id: altyaziDugme; ad: "closed_caption"; golge: true; opacity: parent.var_ ? 1 : 0.4
                    ipucu: parent.var_ ? qsTr("Altyazı (c)") : qsTr("Bu videoda altyazı yok")
                    onTiklandi: if (parent.var_) c.menuAc(altyaziMenu, parent) }
                // Altyazı açıkken düğmenin altında mavi çizgi (YouTube'daki gibi).
                Rectangle { visible: c.oynatici.seciliAltyazi !== ""; anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 6; width: 20; height: 3; radius: 1.5; color: Renk.videoMavi }
                AltyaziMenusu { id: altyaziMenu; oynatici: c.oynatici }
            }
            Item {
                visible: !!c.sigan.sesDili
                Layout.preferredWidth: sesDiliDugme.implicitWidth; Layout.preferredHeight: sesDiliDugme.implicitHeight
                Simge { id: sesDiliDugme; ad: "record_voice_over"; golge: true
                    opacity: c.oynatici.sesler.length > 1 ? 1 : 0.4
                    ipucu: c.oynatici.sesler.length > 1 ? qsTr("Ses dili") : qsTr("Bu videonun tek sesi var")
                    onTiklandi: if (c.oynatici.sesler.length > 1) c.menuAc(sesMenu, parent) }
                SecimMenusu {
                    id: sesMenu
                    baslik: qsTr("Ses dili")
                    secenekler: c.oynatici.sesler
                    secili: c.oynatici.seciliSes
                    onSecildi: function(i) { c.oynatici.sesSec(i) }
                }
            }
            Item {
                visible: !!c.sigan.kalite
                Layout.preferredWidth: kaliteDugme.implicitWidth; Layout.preferredHeight: kaliteDugme.implicitHeight
                Simge { id: kaliteDugme; ad: "tune"; golge: true; opacity: c.oynatici.kaliteler.length ? 1 : 0.4
                    onTiklandi: if (c.oynatici.kaliteler.length) c.menuAc(kaliteMenu, parent) }
                // Oynayan kalitenin rozeti; "Kalite" ipucu yok (boşa dikkat çekiyor).
                readonly property var secili: c.oynatici.seciliKalite >= 0 ? c.oynatici.kaliteler[c.oynatici.seciliKalite] : null
                Rectangle { visible: parent.secili !== null; anchors.right: parent.right; anchors.top: parent.top; anchors.topMargin: 2
                    width: rozet.implicitWidth + 6; height: 14; radius: 3; color: Renk.videoMavi
                    Text { id: rozet; anchors.centerIn: parent; font.pixelSize: 10; font.bold: true; color: "black"
                        text: { var k = parent.parent.secili; if (!k) return ""
                                // Boyun kendisi (720'de de "HD" yazınca 720p'de kalındığı görünmüyordu; 29 Ekim)
                                var h = parseInt(k.ad); return h >= 2160 ? "4K" : String(h) } } }
                SecimMenusu {
                    id: kaliteMenu
                    objectName: "kaliteMenu"
                    baslik: qsTr("Kalite")
                    // Önce boyut, sonra biçim; büyütülmüş kopya ve AV1 açıkça söylenir (22-23 Ekim).
                    secenekler: c.oynatici.kaliteler.map(function(k) {
                        var ek = []
                        if (k.buyutulmus) ek.push(qsTr("YouTube'un büyüttüğü kopya"))
                        if (k.bicim === "AV1") ek.push(qsTr("AV1: eski bilgisayarda takılabilir"))
                        return k.ad + (ek.length ? "  ·  " + ek.join(", ") : "")
                    })
                    secili: c.oynatici.seciliKalite
                    onSecildi: function(i) { c.oynatici.kaliteSec(i) }
                    altNot: c.oynatici.kaliciSinirYazi > 0
                            ? qsTr("Sonraki videolar da en çok %1p açılır.").arg(c.oynatici.kaliciSinirYazi) : ""
                    altDugme: c.oynatici.kaliciSinirYazi > 0 ? qsTr("Sınırı kaldır") : ""
                    onAltTiklandi: c.oynatici.siniriKaldir()
                }
            }
            // Çubuğa sığmayan düğmeler.
            Item {
                id: dahaYer
                visible: !!c.sigan.daha
                Layout.preferredWidth: dahaDugme.implicitWidth; Layout.preferredHeight: dahaDugme.implicitHeight
                Simge { id: dahaDugme; ad: "more_horiz"; golge: true; ipucu: qsTr("Diğer")
                    onTiklandi: dahaMenu.opened ? dahaMenu.close() : dahaMenu.open() }
                MenuKutusu {
                    id: dahaMenu
                    objectName: "dahaMenu"
                    y: -height - 8
                    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                    onOpened: c.menuAcik = true
                    onClosed: c.menuAcik = false
                    function ac(m) { close(); c.menuAc(m, dahaYer) }
                    contentItem: Column {
                        spacing: 2
                        Row { anchors.left: parent.left;
                            visible: !c.sigan.hiz
                            leftPadding: 32; spacing: 8
                            Text { anchors.verticalCenter: parent.verticalCenter; width: 40; text: qsTr("Hız"); color: Renk.yazi; font.pixelSize: 14 }
                            HizSurgusu { menude: true; width: 210; height: 40 }
                        }
                        MenuSatiri { anchors.left: parent.left; visible: !c.sigan.altyazi; yazi: qsTr("Altyazı")
                            readonly property bool var_: c.oynatici.altyaziElle.length + c.oynatici.altyaziOtomatik.length + c.oynatici.altyaziCeviri.length > 0
                            tiklanir: var_; opacity: var_ ? 1 : 0.5
                            ipucu: !var_ ? qsTr("bu videoda yok") : c.oynatici.seciliAltyazi !== "" ? qsTr("açık") : qsTr("kapalı")
                            onTiklandi: dahaMenu.ac(altyaziMenu) }
                        MenuSatiri { anchors.left: parent.left; visible: !c.sigan.sesDili; yazi: qsTr("Ses dili")
                            tiklanir: c.oynatici.sesler.length > 1; opacity: tiklanir ? 1 : 0.5
                            ipucu: tiklanir ? c.oynatici.sesler[c.oynatici.seciliSes] || "" : qsTr("tek ses")
                            onTiklandi: dahaMenu.ac(sesMenu) }
                        MenuSatiri { anchors.left: parent.left; visible: !c.sigan.kalite; yazi: qsTr("Kalite")
                            tiklanir: c.oynatici.kaliteler.length > 0; opacity: tiklanir ? 1 : 0.5
                            ipucu: c.oynatici.seciliKalite >= 0 ? c.oynatici.kaliteler[c.oynatici.seciliKalite].ad : ""
                            onTiklandi: dahaMenu.ac(kaliteMenu) }
                        MenuSatiri { anchors.left: parent.left; visible: !c.sigan.bastan && !c.oynatici.canli; yazi: qsTr("Baştan oynat")
                            onTiklandi: { dahaMenu.close(); c.oynatici.git(0) } }
                        MenuSatiri { anchors.left: parent.left; visible: !c.sigan.dongu && !c.oynatici.canli; yazi: qsTr("Döngü"); ipucu: qsTr("bitince baştan")
                            secili: c.oynatici.dongu; onTiklandi: c.oynatici.donguDegistir() }
                    }
                }
            }
            Item {
                Layout.preferredWidth: gorunumDugme.implicitWidth; Layout.preferredHeight: gorunumDugme.implicitHeight
                Simge { id: gorunumDugme; ad: "aspect_ratio"; golge: true; ipucu: qsTr("Görünüm")
                    onTiklandi: gorunumMenu.opened ? gorunumMenu.close() : gorunumMenu.open() }
                GorunumMenusu { id: gorunumMenu; gorunum: c.gorunum }
            }
            Simge { ad: c.tamEkran ? "fullscreen_exit" : "fullscreen"; golge: true; ipucu: c.tamEkran ? qsTr("Tam ekrandan çık (f)") : qsTr("Tam ekran (f)")
                onTiklandi: c.tamEkranIstendi() }
        }
    }
}
