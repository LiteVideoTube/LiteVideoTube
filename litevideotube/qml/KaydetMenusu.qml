import QtQuick
import QtQuick.Controls.Basic

// Video sayfasındaki "Kaydet" düğmesinin menüsü (YouTube'daki gibi): "Sonra izle" ve kullanıcının
// listeleri, işaretli olanlarda video var; tıklamak ekler ya da çıkarır. En altta yeni liste.
MenuKutusu {
    id: m
    property var v: ({})
    property var listeler_: []
    y: parent.height + 6
    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
    onAboutToShow: { listeler_ = listeler.listeler(); yeniAd.visible = false }
    Connections { target: listeler; function onDegisti() { if (m.visible) m.listeler_ = listeler.listeler() } }
    contentItem: Column {
        spacing: 2
        MenuBasligi { anchors.left: parent.left; text: qsTr("Kaydet") }
        Repeater {
            model: m.listeler_
            MenuSatiri { anchors.left: parent.left;
                yazi: modelData.ad
                ipucu: modelData.sayi + ""
                secili: { listeler.surum; return m.v.id ? listeler.icinde(modelData.id, m.v.id) : false }
                onTiklandi: secili ? listeler.cikar(modelData.id, m.v.id) : listeler.ekle(modelData.id, m.v)
            }
        }
        MenuCizgisi { anchors.left: parent.left; width: 300 }
        MenuSatiri { anchors.left: parent.left; visible: !yeniAd.visible; yazi: qsTr("Yeni liste"); isaret: "+"
            onTiklandi: { yeniAd.visible = true; yeniAd.forceActiveFocus() } }
        TextField { anchors.left: parent.left;
            id: yeniAd
            visible: false
            width: 300; height: 36
            placeholderText: qsTr("Listenin adı"); placeholderTextColor: Renk.yaziSoluk
            color: Renk.yazi; font.pixelSize: 14
            background: Rectangle { radius: 8; color: Renk.kutu; border.color: Renk.mavi }
            onAccepted: { var id = listeler.yeniListe(text); listeler.ekle(id, m.v); text = ""; visible = false }
            Keys.onEscapePressed: { text = ""; visible = false }
        }
    }
}
