import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic

// Bir liste oynarken video sayfasında önerilerin üstünde duran kutu (YouTube'daki gibi): listenin adı,
// kaçıncı video, sıradaki videolar. Tıklanan videoya geçilir; ✕ listeden çıkar (video sürer).
Rectangle {
    id: p
    property string ad
    property var videolar: []
    property int sira: -1
    signal sec(int i)
    signal kapat()
    radius: 12; color: Renk.yuzey; clip: true
    height: baslik.height + Math.min(liste.contentHeight, 330) + 12
    Item {
        id: baslik
        width: parent.width; height: 56
        Column {
            anchors.left: parent.left; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 70
            Text { width: parent.width; text: p.ad; color: Renk.yazi; font.pixelSize: 16; font.bold: true; elide: Text.ElideRight; SecimKatmani { } }
            Text { anchors.left: parent.left; text: (p.sira + 1) + " / " + p.videolar.length; color: Renk.yaziSoluk; font.pixelSize: 12; SecimKatmani { } }
        }
        Simge { anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter
            ad: "close"; ipucu: qsTr("Listeden çık (video sürer)"); onTiklandi: p.kapat() }
    }
    ListView {
        id: liste
        anchors { top: baslik.bottom; left: parent.left; right: parent.right; bottom: parent.bottom; bottomMargin: 6 }
        model: p.videolar
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        Component.onCompleted: positionViewAtIndex(Math.max(0, p.sira), ListView.Beginning)
        Connections { target: p; function onSiraChanged() { liste.positionViewAtIndex(Math.max(0, p.sira), ListView.Contain) } }
        delegate: Rectangle {
            width: liste.width; height: 62
            color: index === p.sira ? Renk.k("#3a3a3a", "#e0e0e0") : satirUstunde.hovered ? Renk.k("#313131", "#e8e8e8") : "transparent"
            HoverHandler { id: satirUstunde }
            Text { anchors.left: parent.left; anchors.leftMargin: 4; width: 22; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter
                text: index === p.sira ? "▶" : index + 1; color: index === p.sira ? Renk.mavi : Renk.yaziSoluk; font.pixelSize: 12 }
            Rectangle {
                id: r
                anchors.left: parent.left; anchors.leftMargin: 28; anchors.verticalCenter: parent.verticalCenter
                width: 96; height: 54; radius: 6; color: Renk.k("#1f1f1f", "#e5e5e5")
                Image { anchors.fill: parent; fillMode: Image.PreserveAspectCrop; asynchronous: true
                    source: modelData.resim; sourceSize.width: Renk.resimBoyu(96 * Screen.devicePixelRatio) }
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: p.sec(index) }
            // Yazılar sürükleyince seçilir, tıklayınca o videoya geçer (SecimKatmani).
            Column {
                anchors { left: r.right; leftMargin: 8; right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                Text { width: parent.width; text: modelData.baslik || modelData.id; color: Renk.yazi; font.pixelSize: 13
                    font.weight: Font.Medium; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                    SecimKatmani { tiklama: function(tuslar) { p.sec(index) } } }
                Text { width: parent.width; text: modelData.kanal; color: Renk.yaziSoluk; font.pixelSize: 11; elide: Text.ElideRight
                    SecimKatmani { tiklama: function(tuslar) { p.sec(index) } } }
            }
        }
    }
}
