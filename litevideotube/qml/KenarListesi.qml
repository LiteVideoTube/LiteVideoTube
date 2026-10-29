import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects

// Sol kenarda abonelik listesi: üst şeritteki ☰ ile açılıp kapanır. Sıra ve işaretler
// abonelik.kenarListesi'nde: izlediğin kanallar önde, sonra yeni videosu olanlar (mavi nokta), sonra abece.
// Canlı yayındaki kanalın resminde kırmızı halka. YouTube'daki gibi ilk yedisi, altında "Daha fazla göster".
Rectangle {
    id: k
    color: Renk.zemin
    property var kanallar: []
    property bool hepsi: false
    readonly property int ilkSayi: 7
    signal sec(string id, string ad)
    signal yeniSekmede(string id, string ad)
    function yenile() { if (abonelik) kanallar = abonelik.kenarListesi() }
    // Sayfada bul (Ctrl+F): kanal adlarında, gizli olanlar dahil; bulunan gizliyse liste açılır.
    // Liste sayfanın solunda durduğu için bulunanların başında sayılır.
    property string bulunan: ""
    BulKaynagi {
        hedef: k
        function eslesmeler(sorgu) {
            var l = []
            for (var i = 0; i < k.kanallar.length; i++)
                if (pencere.bulKucuk(k.kanallar[i].ad || "").indexOf(sorgu) >= 0) l.push({ y: i - 1000000, i: i, id: k.kanallar[i].id })
            return l
        }
        function goster(m) {
            if (m.i >= k.ilkSayi) k.hepsi = true
            k.bulunan = m.id
            Qt.callLater(function() { liste.positionViewAtIndex(m.i, ListView.Contain) })
        }
        function birak() { k.bulunan = "" }
    }
    onVisibleChanged: if (visible) yenile()
    Connections { target: abonelik; function onKenarDegisti() { if (k.visible) k.yenile() } }

    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Renk.k("#2a2a2a", "#e5e5e5") }

    ListView {
        id: liste
        objectName: "kenarListesi"
        anchors.fill: parent; anchors.rightMargin: 1; anchors.leftMargin: 8; anchors.topMargin: 8
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        TekerlekHizi { hedef: liste }
        model: k.hepsi ? k.kanallar : k.kanallar.slice(0, k.ilkSayi)
        header: Text { text: qsTr("Abonelikler"); color: Renk.yazi; font.pixelSize: 16; font.weight: Font.Medium
            leftPadding: 12; topPadding: 4; bottomPadding: 8 }
        delegate: Rectangle {
            id: satir
            width: liste.width - 12; height: 40; radius: 10
            color: fare.containsMouse ? Renk.yuzey : "transparent"
            border.color: Renk.mavi; border.width: k.bulunan === modelData.id ? 2 : 0
            Item {
                id: kutu
                anchors.left: parent.left; anchors.leftMargin: 12; width: 24; height: 24; anchors.verticalCenter: parent.verticalCenter
                Image { id: resim; anchors.fill: parent; source: modelData.resim; asynchronous: true
                    sourceSize: Qt.size(48, 48); visible: false }
                Rectangle { id: maske; anchors.fill: parent; radius: 12; visible: false; layer.enabled: true }
                MultiEffect { anchors.fill: parent; source: resim; maskEnabled: true; maskSource: maske
                    visible: resim.status === Image.Ready }
                Rectangle { anchors.fill: parent; radius: 12; color: Renk.yuzeyAcik; visible: resim.status !== Image.Ready
                    Text { anchors.centerIn: parent; text: (modelData.ad || "?").charAt(0).toLocaleUpperCase()
                        color: Renk.yazi; font.pixelSize: 12; font.bold: true } }
                Rectangle { visible: modelData.canli; anchors.fill: parent; anchors.margins: -3; radius: width / 2
                    color: "transparent"; border.color: "#cc0000"; border.width: 2 }
            }
            Text {
                anchors { left: kutu.right; leftMargin: 16; right: modelData.canli ? canliSimge.left : nokta.left; rightMargin: 8
                    verticalCenter: parent.verticalCenter }
                text: modelData.ad; color: Renk.yazi; font.pixelSize: 14; elide: Text.ElideRight
            }
            Rectangle { id: nokta; width: 6; height: 6; radius: 3; color: Renk.mavi; visible: modelData.nokta && !modelData.canli
                anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter } }
            // Canlı yayındaki kanalın sağında yayın simgesi (YouTube'un yan listesindeki gibi). Mavi
            // noktanın yerinde durur: kanal canlıyken yeni video noktası gösterilmez.
            Image { id: canliSimge; visible: modelData.canli; width: 20; height: 20; sourceSize: Qt.size(40, 40)
                source: "../simgeler/sensors_kirmizi.svg"
                anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter } }
            ToolTip.visible: fare.containsMouse && modelData.canli; ToolTip.delay: 500; ToolTip.text: qsTr("Şu an canlı yayında")
            // Sol tık kanalı açar; orta tık ya da Ctrl+tık yeni sekmede, sağ tık "Yeni sekmede aç" (tarayıcı alışkanlığı).
            MouseArea {
                id: fare
                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                onClicked: function(m) {
                    if (m.button === Qt.RightButton) pencere.yeniSekmeMenusu(function() { k.yeniSekmede(modelData.id, modelData.ad) })
                    else if (m.button === Qt.MiddleButton || (m.modifiers & Qt.ControlModifier)) k.yeniSekmede(modelData.id, modelData.ad)
                    else k.sec(modelData.id, modelData.ad)
                }
            }
        }
        footer: Rectangle {
            visible: k.kanallar.length > k.ilkSayi
            width: liste.width - 12; height: visible ? 40 : 0; radius: 10
            color: dahaFare.containsMouse ? Renk.yuzey : "transparent"
            Image { id: ok; anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; width: 24; height: 24; sourceSize: Qt.size(48, 48)
                source: Renk.simge(k.hepsi ? "expand_less" : "expand_more") }
            Text { anchors { left: ok.right; leftMargin: 16; verticalCenter: parent.verticalCenter }
                color: Renk.yazi; font.pixelSize: 14
                text: k.hepsi ? qsTr("Daha az göster") : qsTr("Daha fazla göster (%1)").arg(k.kanallar.length - k.ilkSayi) }
            MouseArea { id: dahaFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                onClicked: k.hepsi = !k.hepsi }
        }
    }
}
