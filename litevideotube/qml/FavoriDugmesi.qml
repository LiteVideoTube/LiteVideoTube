import QtQuick
import QtQuick.Controls.Basic

// Favorilere ekleme: video sayfasında Kaydet'in yanında, Shorts görünümünde kanalın altında.
// Favoriler programın kendi listesi (liste.py); YouTube hesabına yazılmaz.
Button {
    id: f
    property var v
    readonly property bool favoride: { listeler.surum; return f.v && f.v.id ? listeler.favoriMi(f.v.id) : false }
    enabled: !!f.v && !!f.v.id && f.v.id.indexOf("://") < 0
    text: f.favoride ? qsTr("Favorilerde") : qsTr("Favori")
    onClicked: listeler.favoriDegistir(f.v)
    contentItem: Row {
        spacing: 6
        Image { source: f.favoride ? "../simgeler/favorite_kirmizi.svg" : Renk.simge("favorite")
            width: 18; height: 18; sourceSize: Qt.size(36, 36); anchors.verticalCenter: parent.verticalCenter
            opacity: f.favoride ? 1 : 0.85 }
        Text { text: f.text; color: Renk.yazi; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
    }
    background: Rectangle { radius: 18; implicitHeight: 36; color: f.hovered ? Renk.yuzeyAcik : Renk.yuzey }
    ToolTip.visible: hovered; ToolTip.delay: 500
    ToolTip.text: f.favoride ? qsTr("Favorilerden çıkar") : qsTr("Favorilere ekle")
}
