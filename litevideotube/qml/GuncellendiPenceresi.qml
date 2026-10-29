import QtQuick
import QtQuick.Controls.Basic

// "Güncellendi" penceresi (29 Ekim; yenilikler.py): program yeni sürümle ilk açılınca o sürümün ana başlıkları.
// Ayrıntı vermez; "Ayrıntılı notlar" Yenilikler sayfasını açar. Görünüşü güncelleme penceresiyle aynı.
Popup {
    id: p
    property var basliklar: []
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: 440
    padding: 22
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Renk.pencereZemin; radius: 12; border.color: Renk.cizgi }
    onClosed: pencere.tuslariVideoyaVer()

    function ac() { basliklar = yenilikler.yeniBasliklar(); open() }

    component Dugme: Button {
        id: d
        property bool ana: false
        contentItem: Text { text: d.text; font.pixelSize: 14; font.weight: Font.Medium
            color: d.ana ? "black" : Renk.yazi
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { implicitHeight: 36; implicitWidth: 96; radius: 18
            color: d.ana ? (d.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu) : (d.hovered ? Renk.yuzeyAcik : "transparent") }
    }

    contentItem: Column {
        spacing: 14
        Text { anchors.left: parent.left; width: parent.width; wrapMode: Text.Wrap
            text: qsTr("LiteVideoTube güncellendi: %1").arg(yenilikler.surumAdi); color: Renk.yazi; font.pixelSize: 18; font.weight: Font.Medium }
        Text { anchors.left: parent.left; visible: p.basliklar.length > 0; text: qsTr("Bu sürümde:"); color: Renk.yaziSoluk; font.pixelSize: 13 }
        Column {
            width: parent.width; spacing: 8
            Repeater {
                model: p.basliklar
                Row {
                    required property string modelData
                    anchors.left: parent.left
                    spacing: 10
                    Rectangle { width: 6; height: 6; radius: 3; color: Renk.maviDolgu; anchors.verticalCenter: parent.verticalCenter }
                    Text { width: 380; wrapMode: Text.Wrap; text: modelData; color: Renk.yazi; font.pixelSize: 14 }
                }
            }
        }
        Item { width: 1; height: 2 }
        Row {
            anchors.right: parent.right
            spacing: 8
            Dugme { text: qsTr("Ayrıntılı notlar"); onClicked: { p.close(); pencere.yenilikleriAc() } }
            Dugme { text: qsTr("Tamam"); ana: true; onClicked: p.close() }
        }
    }
}
