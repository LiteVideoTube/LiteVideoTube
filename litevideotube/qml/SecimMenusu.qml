import QtQuick
import QtQuick.Controls.Basic

// Oynatıcı çubuğundaki düğmenin üstünde açılan seçim listesi (kalite, ses dili).
MenuKutusu {
    id: m
    property string baslik
    property var secenekler: []
    property int secili: -1
    // Listenin altında soluk bir not ve isteğe bağlı bir düğme satırı (kalite menüsünde kalıcı sınır).
    property string altNot: ""
    property string altDugme: ""
    signal secildi(int i)
    signal altTiklandi()
    y: -height - 8
    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    onOpened: c.menuAcik = true
    onClosed: c.menuAcik = false
    contentItem: Column {
        spacing: 2
        MenuBasligi { anchors.left: parent.left; text: m.baslik }
        Repeater {
            model: m.secenekler
            Rectangle { anchors.left: parent.left;
                width: Math.max(220, satir.implicitWidth + 44); height: 34; radius: 8
                color: fare.containsMouse ? Renk.menuVurgu : "transparent"
                Text { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: index === m.secili ? "✓" : ""; color: Renk.mavi; font.pixelSize: 14 }
                Text { id: satir; anchors.left: parent.left; anchors.leftMargin: 32; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: Renk.yazi; font.pixelSize: 14 }
                MouseArea { id: fare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: { m.close(); m.secildi(index) } }
            }
        }
        Text { anchors.left: parent.left; visible: m.altNot !== ""; width: 220; leftPadding: 10; rightPadding: 10; topPadding: 6; bottomPadding: 2
            text: m.altNot; color: Renk.yaziSoluk; font.pixelSize: 12; wrapMode: Text.WordWrap }
        Rectangle { anchors.left: parent.left;
            visible: m.altDugme !== ""
            width: 220; height: 30; radius: 8
            color: altFare.containsMouse ? Renk.menuVurgu : "transparent"
            Text { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: m.altDugme; color: Renk.mavi; font.pixelSize: 13 }
            MouseArea { id: altFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                onClicked: { m.close(); m.altTiklandi() } }
        }
    }
}
