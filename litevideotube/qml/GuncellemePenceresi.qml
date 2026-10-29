import QtQuick
import QtQuick.Controls.Basic

// "Yeni sürüm var" penceresi (guncelleme.py): yeni sürüm arka planda indirildikten sonra çıkar.
// "Şimdi yükle": program kapanır, güncelleme kurulur, program yeni sürümle yeniden açılır. "Sonra yükle": pencere
// kapanır, güncelleme program kapanınca kurulur. Görünüşü geri bildirim penceresiyle aynı.
Popup {
    id: p
    property string surum: ""
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: 420
    padding: 22
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape      // Esc "Sonra yükle" ile aynı
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Renk.pencereZemin; radius: 12; border.color: Renk.cizgi }
    onClosed: pencere.tuslariVideoyaVer()

    function ac(yeni) { surum = yeni; open() }
    function simdi() {
        // Program her zamanki gibi kapanır (sekmeler, kaldığın yer kaydedilir); Velopack kapanmayı bekleyip kurar.
        if (guncelleme.simdiYukle()) pencere.close()
        else close()
    }
    function sonra() { close() }   // kurulum program kapanırken (guncelleme.kapanirken)

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
        Text { anchors.left: parent.left; text: qsTr("Yeni sürüm var"); color: Renk.yazi; font.pixelSize: 18; font.weight: Font.Medium }
        Text { width: parent.width; wrapMode: Text.Wrap; color: Renk.yaziSoluk; font.pixelSize: 13
            text: qsTr("LiteVideoTube %1 indirildi.").arg(p.surum) }
        Row {
            anchors.right: parent.right
            spacing: 8
            Dugme { text: qsTr("Sonra yükle"); onClicked: p.sonra() }
            Dugme { text: qsTr("Şimdi yükle"); ana: true; onClicked: p.simdi() }
        }
    }
}
