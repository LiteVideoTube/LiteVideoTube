import QtQuick
import QtQuick.Controls.Basic

// Küçük resmin sağ üstünde, fare kartın üstündeyken görünen "Sonra izle" düğmesi (YouTube'daki gibi).
// Video listedeyse onay işareti gösterir; tıklamak ekler ya da çıkarır.
Rectangle {
    id: d
    property var v
    property bool goster: false
    readonly property bool listede: { listeler.surum; return d.v ? listeler.sonradaMi(d.v.id) : false }
    visible: d.v && d.v.id && d.v.id.indexOf("://") < 0 && (d.goster || fare.containsMouse)
    anchors { top: parent.top; right: parent.right; margins: 6 }
    width: 30; height: 30; radius: 6; color: fare.containsMouse ? "#e0000000" : "#b0000000"
    z: 2
    Image { anchors.centerIn: parent; width: 20; height: 20; sourceSize: Qt.size(40, 40)
        source: "../simgeler/" + (d.listede ? "check" : "schedule") + ".svg" }
    MouseArea { id: fare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
        onClicked: listeler.sonraIzleDegistir(d.v) }
    ToolTip.visible: fare.containsMouse; ToolTip.delay: 400
    ToolTip.text: d.listede ? qsTr("Sonra izle'den çıkar") : qsTr("Sonra izle")
}
