import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects

// Keşfet: abone olmadığın, izlediklerine göre ilgini çekebilecek kanallar. Önce abonelik sayfasının
// başındaydı; "Abonelikler" başlığının altında abone olunmayan kanallar çelişkili olduğu için ayrı sayfa oldu.
// Sıralama programın kendisinin (ilgi.py), YouTube'un algoritması değil; hesap yok, ek istek yok.
Item {
    id: k
    readonly property Flickable kaydirmaAlani: kaydirma   // yakınlıkla yeniden açılınca kaydırma yeri (Ana.qml)
    property var ilgili: []
    property var shorts: []
    property var videolar: []
    // Videolar ve Shorts kayıttan hemen gösterilir; son bakış üç saatten eskiyse arka planda yenilenir (abonelik.py).
    function yenile() {
        ilgili = abonelik.ilgiliKanallar(); videolar = abonelik.kesfetVideolar(); shorts = abonelik.kesfetShorts()
        abonelik.kesfetYenile()
    }
    Connections { target: abonelik
        function onKesfetDegisti() { if (k.visible) { k.videolar = abonelik.kesfetVideolar(); k.shorts = abonelik.kesfetShorts() } } }
    readonly property int sutunSayisi: Math.max(1, Math.min(Renk.enCokSutun, Math.floor((sutun.width - 32) / 300)))

    Flickable {
        id: kaydirma
        TekerlekHizi { hedef: kaydirma }
        anchors.fill: parent
        contentHeight: sutun.implicitHeight + 48
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        Column {
            id: sutun
            anchors.left: parent.left; anchors.leftMargin: 24; y: 12
            width: kaydirma.width - 48
            spacing: 12
            Text { anchors.left: parent.left; text: qsTr("Keşfet"); color: Renk.yazi; font.pixelSize: 22; font.bold: true; SecimKatmani { } }
            Text { anchors.left: parent.left;
                visible: k.ilgili.length === 0
                width: Math.min(560, parent.width); wrapMode: Text.Wrap
                text: qsTr("Video izledikçe burada sana uygun kanallar çıkar.")
                color: Renk.yaziSoluk; font.pixelSize: 16
                SecimKatmani { }
            }
            // Programın kendi önerisi (YouTube'un algoritması yerine, 24 Ekim): izlediğin ama abone olmadığın ya
            // da izlediğin videoların yanında sık çıkan kanallar; YouTube'daki gibi yuvarlak resimleriyle (25 Ekim).
            // Resim yoksa (henüz o kanalın bir videosu ya da önerisi görülmediyse) adının ilk harfi.
            Column {
                visible: k.ilgili.length > 0
                width: sutun.width
                height: visible ? implicitHeight : 0
                spacing: 10
                topPadding: 8
                bottomPadding: visible ? 16 : 0
                BolumBasligi { anchors.left: parent.left; simge: "explore"; simgeRenk: ["4dd0c4", "00897b"]; baslik: qsTr("İlgini çekebilecek kanallar"); kapanir: false; bulSira: -1 }
                Flow { anchors.left: parent.left;
                    width: parent.width - 8
                    spacing: 8
                    Repeater {
                        model: k.ilgili
                        Item {
                            width: 104; height: 108
                            Rectangle { anchors.fill: parent; radius: 12; color: kanalUstunde.hovered ? Renk.yuzey : "transparent" }
                            HoverHandler { id: kanalUstunde }
                            Item {
                                id: yuvarlak
                                width: 64; height: 64; y: 8; anchors.horizontalCenter: parent.horizontalCenter
                                Image { id: kresim; anchors.fill: parent; source: modelData.resim || ""; asynchronous: true
                                    sourceSize: Qt.size(128, 128); visible: false }
                                Rectangle { id: kmaske; anchors.fill: parent; radius: 32; visible: false; layer.enabled: true }
                                MultiEffect { anchors.fill: parent; source: kresim; maskEnabled: true; maskSource: kmaske
                                    visible: kresim.status === Image.Ready }
                                Rectangle { anchors.fill: parent; radius: 32; color: Renk.yuzeyAcik; visible: kresim.status !== Image.Ready
                                    Text { anchors.centerIn: parent; text: (modelData.ad || "?").charAt(0); color: Renk.yazi; font.pixelSize: 26 } }
                            }
                            Text {
                                anchors.top: yuvarlak.bottom; anchors.topMargin: 8
                                width: parent.width - 8; anchors.horizontalCenter: parent.horizontalCenter
                                horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                                text: modelData.ad; color: Renk.yazi; font.pixelSize: 13
                                z: 1   // sürükleyince seçilir, tıklayınca kanal (SecimKatmani)
                                SecimKatmani { tiklama: function(tuslar) { pencere.kanalAc(modelData.id, modelData.ad) } }
                            }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: pencere.kanalAc(modelData.id, modelData.ad) }
                        }
                    }
                }
            }
            // Bu kanalların en son uzun videoları, kanal başına iki (28 Ekim; sayfa doldurulmasın).
            Column {
                visible: k.videolar.length > 0
                width: sutun.width
                height: visible ? implicitHeight : 0
                spacing: 8
                bottomPadding: visible ? 16 : 0
                BolumBasligi { anchors.left: parent.left; simge: "video_library"; simgeRenk: ["9fa8da", "3f51b5"]; baslik: qsTr("Bu kanallardan videolar"); kapanir: false; bulSira: -0.5 }
                BulKaynagi {
                    hedef: kartlar
                    function eslesmeler(sorgu) {
                        var l = []
                        for (var i = 0; i < k.videolar.length; i++) {
                            var v = k.videolar[i]
                            if (pencere.bulKucuk((v.baslik || "") + " " + (v.kanal || "")).indexOf(sorgu) >= 0)
                                l.push({ y: -0.5 + (i + 1) / 1000, id: v.id, i: i })
                        }
                        return l
                    }
                    function goster(m) { var kart = kartRep.itemAt(m.i); if (kart) pencere.kaydirGoster(kart, 0); pencere.bulunanId = m.id }
                    function birak() { pencere.bulunanId = "" }
                }
                Flow {
                    id: kartlar
                    width: parent.width
                    spacing: 16
                    Repeater {
                        id: kartRep
                        model: k.videolar
                        VideoKarti { width: Math.floor((sutun.width + 16) / k.sutunSayisi) - 16; v: modelData
                            onSec: pencere.videoAc(modelData.id, modelData) }
                    }
                }
                Rectangle { anchors.left: parent.left; width: parent.width - 8; height: 1; color: Renk.cizgi }
            }
            ShortsSeridi { width: sutun.width; liste: k.shorts; kaynak: "kesfet"; tekSatir: false
                baslik: qsTr("Bu kanallardan Shorts") }
        }
    }
}
