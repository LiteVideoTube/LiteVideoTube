import QtQuick
import QtQuick.Controls.Basic

// Yenilikler sayfası (lvt://yenilikler; yenilikler.py): bütün sürümlerin notları, en yenisi üstte. Her maddede ana
// başlık ve bir iki cümlelik açıklama; "Güncellendi" penceresindeki başlıklar bunların aynısı.
Item {
    id: ys
    property var surumler: []
    function yenile() { surumler = yenilikler.hepsi() }
    function tarihYaz(t) { return t ? new Date(t + "T12:00:00").toLocaleDateString(Qt.locale(), "d MMMM yyyy") : "" }

    Flickable {
        id: f
        TekerlekHizi { hedef: f }
        anchors.fill: parent
        contentHeight: sutun.implicitHeight + 64
        boundsBehavior: Flickable.StopAtBounds; clip: true
        Column {
            id: sutun
            width: Math.min(760, parent.width - 48); x: (parent.width - width) / 2; y: 24; spacing: 28
            Column {
                anchors.left: parent.left
                spacing: 6
                Text { anchors.left: parent.left; text: qsTr("Yenilikler"); color: Renk.yazi; font.pixelSize: 22; font.bold: true; SecimKatmani { } }
                Text { anchors.left: parent.left; text: qsTr("Şu an kullandığın sürüm: %1").arg(yenilikler.surumAdi); color: Renk.yaziSoluk; font.pixelSize: 13 }
            }
            Repeater {
                model: ys.surumler
                Column {
                    required property var modelData
                    required property int index
                    width: sutun.width; spacing: 14
                    Rectangle { width: parent.width; height: 1; color: Renk.cizgi; visible: index > 0 }
                    Row {
                        anchors.left: parent.left
                        spacing: 10
                        Text { id: surumYazi; text: qsTr("Sürüm %1").arg(modelData.surum); color: Renk.yazi; font.pixelSize: 18; font.weight: Font.Medium }
                        Text { text: ys.tarihYaz(modelData.tarih); color: Renk.yaziSoluk; font.pixelSize: 13; anchors.baseline: surumYazi.baseline }
                    }
                    Repeater {
                        model: modelData.maddeler
                        Column {
                            required property var modelData
                            width: sutun.width; spacing: 4
                            Row {
                                anchors.left: parent.left
                                spacing: 10
                                Rectangle { width: 6; height: 6; radius: 3; color: Renk.maviDolgu; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: modelData.baslik; color: Renk.yazi; font.pixelSize: 15; font.weight: Font.Medium }
                            }
                            Text { anchors.left: parent.left; anchors.leftMargin: 16; width: parent.width - 16; wrapMode: Text.Wrap
                                text: modelData.ayrinti; color: Renk.yaziSoluk; font.pixelSize: 14; lineHeight: 1.25 }
                        }
                    }
                }
            }
        }
    }
}
