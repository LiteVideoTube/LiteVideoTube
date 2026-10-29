import QtQuick
import QtQuick.Controls.Basic

// Üst şeritteki indirme düğmesinin menüsü: bütün indirmeler (en yeni üstte).
MenuKutusu {
    id: m
    y: parent.height + 4
    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
    contentItem: Column {
        spacing: 2
        MenuBasligi { anchors.left: parent.left; text: qsTr("İndirmeler") }
        Text { anchors.left: parent.left; visible: indirici.isler.length === 0; leftPadding: 10; bottomPadding: 6; color: Renk.yaziSoluk; font.pixelSize: 13
            text: qsTr("Henüz bir şey indirmedin.") }
        Repeater {
            model: indirici.isler.slice(0, 8)
            IndirmeSatiri { anchors.left: parent.left; width: 360; is_: modelData; baslikGoster: true }
        }
        MenuCizgisi { anchors.left: parent.left; width: 360 }
        MenuSatiri { anchors.left: parent.left; width: 360; yazi: qsTr("İndirilenler klasörünü aç"); onTiklandi: { indirici.klasoruAc(); m.close() } }
        MenuSatiri { anchors.left: parent.left; visible: indirici.isler.length > indirici.suruyor; width: 360; yazi: qsTr("Bitenleri listeden kaldır")
            ipucu: qsTr("dosyalar kalır"); onTiklandi: indirici.bitenleriTemizle() }
    }
}
