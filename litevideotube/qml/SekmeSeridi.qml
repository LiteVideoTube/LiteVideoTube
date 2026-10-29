import QtQuick
import QtQuick.Controls.Basic

// Sekme şeridi (Ana.qml, sekmeler): tıklayınca o sekmeye geçer; orta tık ya da ✕ kapatır;
// "+" yeni sekme. Tarayıcıdaki gibi: sekmeler sığdıkça geniş, çoğalınca daralır. ✕ her sekmede hep görünür;
// tek sekmenin ✕'i programı kapatır (ana sayfaya LiteVideoTube yazısı zaten götürüyor).
Rectangle {
    id: s
    property var adlar: []
    property int etkin: 0
    signal sec(int i)
    signal kapat(int i)
    signal yeni()
    color: Renk.zemin

    Row {
        id: satir
        anchors.left: parent.left; anchors.leftMargin: 8; height: parent.height; spacing: 4
        readonly property real sekmeEn: Math.max(90, Math.min(240, (s.width - 16 - 44 - s.adlar.length * 4) / Math.max(1, s.adlar.length)))
        Repeater {
            model: s.adlar
            Rectangle {
                width: satir.sekmeEn; height: s.height - 4; y: 4; radius: 8
                color: index === s.etkin ? Renk.yuzey : fare.containsMouse ? Renk.k("#1c1c1c", "#f7f7f7") : "transparent"
                MouseArea {
                    id: fare
                    anchors.fill: parent; hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                    onClicked: function(m) { if (m.button === Qt.MiddleButton) s.kapat(index); else s.sec(index) }
                    ToolTip.visible: containsMouse && baslik.truncated; ToolTip.delay: 600; ToolTip.text: modelData
                }
                Text {
                    id: baslik
                    anchors { left: parent.left; leftMargin: 12; right: kapatDugme.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
                    text: modelData; elide: Text.ElideRight; font.pixelSize: 13
                    color: index === s.etkin ? Renk.yazi : Renk.yaziSoluk
                }
                Rectangle {
                    id: kapatDugme
                    anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
                    width: 22; height: 22; radius: 11
                    color: kapatFare.containsMouse ? Renk.yuzeyAcik : "transparent"
                    Text { anchors.centerIn: parent; text: "✕"; color: Renk.yaziSoluk; font.pixelSize: 12 }
                    MouseArea { id: kapatFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: s.kapat(index) }
                }
            }
        }
        Simge { anchors.verticalCenter: parent.verticalCenter; ad: "add"; boy: 20; ipucu: qsTr("Yeni sekme (Ctrl+T)"); onTiklandi: s.yeni() }
    }
}
