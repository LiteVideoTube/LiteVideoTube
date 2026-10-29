import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects

// Tıklanabilir simge. Videonun üstündeyken parlak sahnede de seçilsin diye koyu kenarlı.
Item {
    id: s
    property string ad
    property int boy: 24
    property string ipucu: ""
    property bool golge: false
    property var renk: null   // [koyu görünümde, açık görünümde] (Renk.simgeRenkli); yoksa yazı renginde
    // Çizimi kutusunda aşağı kaydırır: çizimi kutusunun üstünde toplanan simgeler (feedback) yanındakilerden yukarıda dursun diye.
    property real kaydir: 0
    // Yön gösteren simge (geri, ileri): sağdan sola kipte (LayoutMirroring) aynalanır.
    property bool yonlu: false
    signal tiklandi()
    signal sagTiklandi()
    signal ortaTiklandi()     // tekerleğe basarak; yeni sekmede açan düğmeler kullanır
    signal tekerlek(real adim)
    implicitWidth: boy + 16; implicitHeight: boy + 16

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height); height: width; radius: width / 2
        color: fare.containsMouse && !s.golge ? Renk.k("#3a3a3a", "#e5e5e5") : "transparent"
    }
    Image {
        id: resim
        anchors.centerIn: parent
        anchors.verticalCenterOffset: s.kaydir
        width: s.boy; height: s.boy; sourceSize: Qt.size(s.boy * 2, s.boy * 2)
        mirror: s.yonlu && s.LayoutMirroring.enabled
        source: s.golge ? "../simgeler/" + s.ad + ".svg" : s.renk ? Renk.simgeRenkli(s.ad, s.renk) : Renk.simge(s.ad)   // videonun üstündekiler (gölgeli) hep beyaz
        layer.enabled: s.golge
        layer.effect: MultiEffect {
            shadowEnabled: true; shadowColor: "#000000"; shadowBlur: 0.25
            shadowScale: 1.12; shadowOpacity: 0.9; shadowHorizontalOffset: 0; shadowVerticalOffset: 0
        }
    }
    MouseArea {
        id: fare
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        cursorShape: Qt.PointingHandCursor
        onClicked: function(m) {
            if (m.button === Qt.RightButton) s.sagTiklandi()
            else if (m.button === Qt.MiddleButton) s.ortaTiklandi()
            else s.tiklandi()
        }
        onWheel: function(w) { s.tekerlek(w.angleDelta.y / 120); w.accepted = true }
    }
    ToolTip.visible: s.ipucu !== "" && fare.containsMouse
    ToolTip.text: s.ipucu
    ToolTip.delay: 600
}
