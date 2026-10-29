import QtQuick
import QtQuick.Controls.Basic

// Dil seçme penceresi (ceviri.py, kisi.py). 29 Ekim: dil tek tıkla seçilir, uzun listede aranmaz.
// Program ilk açıldığında çıkar, sonra kişi menüsündeki "Dil" satırından açılır. Üstte programın şu anki dili tek düğme
// (ilk açılışta bilgisayarın dili, çevirisi varsa): çoğu kişi tek tıkla geçer. Başka dil için önce bölge (haritalı
// kutular; emoji küreler Kuzey Amerika'yı Latin Amerika'dan ayırmıyordu), sonra o bölgenin dilleri, her biri kendi
// dilinde yazılı. Dil değişince program yeniden açılır. Esc ya da dışarı tıklamak şu anki dille devam etmektir.
Popup {
    id: p
    property string bolge: ""
    readonly property var bolgeler: [
        { ad: "avrupa", yazi: qsTr("Avrupa") },
        { ad: "asya", yazi: qsTr("Asya") },
        { ad: "afrika", yazi: qsTr("Afrika") },
        { ad: "kuzey_amerika", yazi: qsTr("Kuzey Amerika") },
        { ad: "latin_amerika", yazi: qsTr("Latin Amerika") }
    ]
    function dilAdi(kod) { var d = kisiler.diller.find(function(x) { return x.kod === kod }); return d ? d.ad : kod }
    function sec(kod) {
        kisiler.dilSec(kod)
        close()
        if (kod !== kisiler.dil) pencere.durumlaYenidenAc()
    }
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(862, parent.width - 48)
    padding: 32
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Renk.pencereZemin; radius: 16; border.color: Renk.cizgi }
    onClosed: {
        if (!kisiler.dilSecildi) kisiler.dilSec(kisiler.dil)
        bolge = ""
        pencere.tuslariVideoyaVer()
    }

    contentItem: Column {
        spacing: 20
        Text { anchors.left: parent.left; text: qsTr("Programın dili"); color: Renk.yazi; font.pixelSize: 26; font.bold: true }
        Button { anchors.left: parent.left;
            id: devam
            text: qsTr("%1 ile devam et").arg(p.dilAdi(kisiler.dil))
            onClicked: p.sec(kisiler.dil)
            contentItem: Text { text: devam.text; color: "black"; font.pixelSize: 17; font.weight: Font.Medium
                horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { implicitWidth: Math.max(320, devam.contentItem.implicitWidth + 48); implicitHeight: 50
                radius: 25; color: devam.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu }
        }
        Text { anchors.left: parent.left; text: qsTr("Başka bir dil: önce bölgeni seç"); color: Renk.yaziSoluk; font.pixelSize: 14 }
        Flow {
            width: parent.width
            spacing: 12
            Repeater {
                model: p.bolgeler
                Rectangle {
                    id: kutu
                    readonly property bool secili: p.bolge === modelData.ad
                    width: 146; height: 106; radius: 14
                    color: secili ? Renk.k("#1d3446", "#e3f1fc") : kutuFare.containsMouse ? Renk.yuzeyAcik : Renk.k("#333333", "#f2f2f2")
                    border.color: secili ? Renk.mavi : "transparent"; border.width: 2
                    Column {
                        anchors.centerIn: parent
                        spacing: 8
                        Image { anchors.horizontalCenter: parent.horizontalCenter; width: 126; height: 49
                            sourceSize: Qt.size(252, 98); source: Qt.resolvedUrl("../simgeler/bolge_" + modelData.ad + ".svg") }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.yazi; color: Renk.yazi
                            font.pixelSize: 14; font.weight: Font.Medium }
                    }
                    MouseArea { id: kutuFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: p.bolge = kutu.secili ? "" : modelData.ad }
                }
            }
        }
        Flow {
            visible: p.bolge !== ""
            width: parent.width
            spacing: 10
            Repeater {
                model: kisiler.diller.filter(function(d) { return d.bolgeler.indexOf(p.bolge) >= 0 })
                Rectangle {
                    id: dil
                    readonly property bool simdiki: modelData.kod === kisiler.dil
                    width: dilYazi.implicitWidth + 36; height: 44; radius: 22
                    color: dilFare.containsMouse ? Renk.yuzeyAcik : Renk.k("#333333", "#f2f2f2")
                    border.color: dil.simdiki ? Renk.mavi : Renk.cizgi
                    Text { id: dilYazi; anchors.centerIn: parent; text: (dil.simdiki ? "✓ " : "") + modelData.ad
                        color: Renk.yazi; font.pixelSize: 17 }
                    MouseArea { id: dilFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: p.sec(modelData.kod) }
                }
            }
        }
    }
}
