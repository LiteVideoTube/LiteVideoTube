import QtQuick
import QtQuick.Controls.Basic

// Dikey Shorts görünümü: video ortada, pencere boyunda dikey; tekerlek, ↑ ↓ tuşları ya da
// sağdaki oklarla aynı listenin öncekine, sıradakine geçilir. Video tek oynatıcıdır (Ana.qml, videoKutusu): bu
// sayfa yalnız yerini (videoYeri) ve yanındaki bilgiyi verir. Yorumlar ve açıklama için video normal sayfada açılır.
Item {
    id: s
    property var liste: []
    property int sira: 0
    property var bilgi: ({})
    property string kaynak     // listenin devamı nereden (Ana.qml, shortsKaynak); boşsa sonuncuda aşağı ok kapalı
    property bool sonda: false // sonuncudan sonra "bitirdin" ekranı; video durmuş, yeri boş
    readonly property alias videoYeri: yer
    signal onceki()
    signal sonraki()

    Item {
        id: yer
        height: s.height - 32
        width: Math.round(height * 9 / 16)
        x: Math.round((s.width - width) / 2); y: 16
    }

    // "Bitirdin" ekranı: videonun yerinde; abonelik Shorts'larından sonra Keşfet'inkilere geçilebilir.
    Rectangle {
        id: son
        property var kesfet: []
        x: yer.x; y: yer.y; width: yer.width; height: yer.height
        visible: s.sonda; radius: 12; color: Renk.yuzey
        onVisibleChanged: kesfet = visible && s.kaynak === "abonelik" && abonelik ? abonelik.kesfetShorts() : []
        Column {
            anchors.centerIn: parent; width: parent.width - 48; spacing: 20
            Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                color: Renk.yazi; font.pixelSize: 18; font.weight: Font.Medium
                text: s.kaynak === "abonelik" ? qsTr("Son üç günün Shorts'larını bitirdin.")
                    : s.kaynak === "kesfet" ? qsTr("Keşfet'teki Shorts'ları bitirdin.")
                    : qsTr("Bu kanalın bütün Shorts'larını gördün.")
                SecimKatmani { } }
            Button {
                id: kesfeteGec
                visible: son.kesfet.length > 0
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Keşfet'teki Shorts'lara geç")
                onClicked: pencere.shortsAc(son.kesfet, 0, "kesfet")
                contentItem: Text { text: kesfeteGec.text; color: "black"; font.pixelSize: 15; font.weight: Font.Medium
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { implicitHeight: 40; implicitWidth: 240; radius: 20
                    color: kesfeteGec.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu }
            }
        }
    }

    // Videonun sağında (sağdan sola kipte solunda): başlık, kanal, abone olma ve zil, normal sayfada açma.
    Column {
        visible: !s.sonda && width >= 200
        x: LayoutMirroring.enabled ? yer.x - 24 - width : yer.x + yer.width + 24
        width: Math.max(0, Math.min(380, LayoutMirroring.enabled ? yer.x - 120 : s.width - yer.x - yer.width - 120))
        anchors.bottom: yer.bottom; anchors.bottomMargin: 24
        spacing: 12
        Text { width: parent.width; text: s.bilgi.baslik || ""; color: Renk.yazi; font.pixelSize: 18; font.bold: true
            wrapMode: Text.Wrap; maximumLineCount: 4; elide: Text.ElideRight; SecimKatmani { } }
        Column { anchors.left: parent.left;
            spacing: 2
            Text { anchors.left: parent.left; text: s.bilgi.kanal || ""; color: Renk.yazi; font.pixelSize: 15; font.weight: Font.Medium
                font.underline: kanalSecim.ustunde && !!s.bilgi.kanal_id
                SecimKatmani { id: kanalSecim
                    tiklama: s.bilgi.kanal_id ? function(tuslar) { pencere.kanalAc(s.bilgi.kanal_id, s.bilgi.kanal) } : null } }
            Text { anchors.left: parent.left; text: s.bilgi.abone || ""; color: Renk.yaziSoluk; font.pixelSize: 12; visible: text !== ""; SecimKatmani { } }
        }
        AboneDugmeleri { anchors.left: parent.left; kanalId: s.bilgi.kanal_id || ""; kanalAd: s.bilgi.kanal || "" }
        FavoriDugmesi { anchors.left: parent.left; v: s.bilgi }
        Text { anchors.left: parent.left; color: Renk.yaziSoluk; font.pixelSize: 13
            text: [s.bilgi.izlenme, s.bilgi.tarih].filter(function(x) { return x }).join("  ·  ")
            SecimKatmani { } }
        Button { anchors.left: parent.left;
            id: normal
            text: qsTr("Yorumlar ve açıklama")
            onClicked: pencere.videoAc(s.bilgi.id, s.bilgi)
            contentItem: Row {
                spacing: 6
                Image { source: Renk.simge("forum"); width: 18; height: 18; sourceSize: Qt.size(36, 36); anchors.verticalCenter: parent.verticalCenter }
                Text { text: normal.text; color: Renk.yazi; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
            }
            background: Rectangle { radius: 18; implicitHeight: 36; color: normal.hovered ? Renk.yuzeyAcik : Renk.yuzey }
        }
    }

    // Yukarı ve aşağı düğmesi.
    component Ok: Rectangle {
        id: ok
        property string ad
        property bool var_: true
        property string ipucu
        signal tik()
        width: 52; height: 52; radius: 26
        color: okFare.containsMouse && var_ ? Renk.yuzeyAcik : Renk.yuzey
        opacity: var_ ? 1 : 0.35
        Image { anchors.centerIn: parent; source: Renk.simge(ok.ad); width: 26; height: 26; sourceSize: Qt.size(52, 52) }
        MouseArea { id: okFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: if (ok.var_) ok.tik() }
        ToolTip.visible: okFare.containsMouse; ToolTip.delay: 500; ToolTip.text: ok.ipucu
    }

    // Sağ kenarda yukarı ve aşağı (YouTube'daki gibi); sıra numarası aralarında.
    Column {
        anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Ok { anchors.left: parent.left; ad: "arrow_upward"; var_: s.sira > 0 || s.sonda; ipucu: qsTr("Önceki (↑)"); onTik: s.onceki() }
        Text { anchors.horizontalCenter: parent.horizontalCenter; color: Renk.yaziSoluk; font.pixelSize: 13
            text: s.liste.length && !s.sonda ? (s.sira + 1) + " / " + s.liste.length : "" }
        Ok { anchors.left: parent.left; ad: "arrow_downward"; var_: !s.sonda && (s.sira + 1 < s.liste.length || s.kaynak !== ""); ipucu: qsTr("Sıradaki (↓)"); onTik: s.sonraki() }
    }

    // Tekerleğin bir çentiği bir Shorts; art arda gelen çentikler kısa bir süre yutulur ki tek hareket birkaç Shorts atlamasın.
    WheelHandler {
        property real birikim: 0
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(w) {
            if (bekle.running) return
            birikim += w.angleDelta.y
            if (Math.abs(birikim) < 120) return
            if (birikim < 0) s.sonraki(); else s.onceki()
            birikim = 0
            bekle.restart()
        }
    }
    Timer { id: bekle; interval: 350 }
}
