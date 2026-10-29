import QtQuick
import QtQuick.Controls.Basic

// Üst şeritteki kişi düğmesinin menüsü (kisi.py): kişiler, yeni kişi, adını değiştirme, silme; programın görünümü
// (açık, koyu). Kişi değişince program o kişinin kayıtlarıyla yeniden açılır.
MenuKutusu {
    id: m
    property string yazilan: ""     // "yeni" ya da "ad": hangi yazı kutusu açık; "sil": silme onayı
    y: parent.height + 4
    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
    onClosed: yazilan = ""
    contentItem: Column {
        spacing: 2
        Text { anchors.left: parent.left; width: 300; leftPadding: 10; rightPadding: 10; topPadding: 6; bottomPadding: 6; wrapMode: Text.Wrap
            color: Renk.yaziSoluk; font.pixelSize: 12
            text: qsTr("Kişi değişince program yeniden açılır.") }
        Repeater {
            model: kisiler.liste
            MenuSatiri { anchors.left: parent.left; yazi: modelData.ad; secili: modelData.id === kisiler.secili
                onTiklandi: { m.close(); kisiler.sec(modelData.id) } }
        }
        MenuCizgisi { anchors.left: parent.left; width: 300 }
        MenuSatiri { anchors.left: parent.left; visible: m.yazilan !== "yeni" && m.yazilan !== "sil"; yazi: qsTr("Yeni kişi ekle"); isaret: "+"
            onTiklandi: { m.yazilan = "yeni"; kutu.text = ""; kutu.forceActiveFocus() } }
        MenuSatiri { anchors.left: parent.left; visible: m.yazilan !== "ad" && m.yazilan !== "sil"; yazi: qsTr("Bu kişinin adını değiştir")
            onTiklandi: { m.yazilan = "ad"; kutu.text = kisiler.seciliAd; kutu.forceActiveFocus(); kutu.selectAll() } }
        // Son kişi silinmez. Silinince program kalan ilk kişiyle yeniden açılır.
        MenuSatiri { anchors.left: parent.left; visible: m.yazilan === "" && kisiler.liste.length > 1; yazi: qsTr("Bu kişiyi sil")
            onTiklandi: m.yazilan = "sil" }
        TextField { anchors.left: parent.left;
            id: kutu
            visible: m.yazilan === "yeni" || m.yazilan === "ad"
            width: 300
            placeholderText: m.yazilan === "yeni" ? qsTr("Yeni kişinin adı") : qsTr("Yeni ad")
            placeholderTextColor: Renk.yaziSoluk
            color: Renk.yazi; font.pixelSize: 14; selectByMouse: true
            background: Rectangle { radius: 6; color: Renk.kutu; border.color: Renk.mavi }
            onAccepted: {
                if (m.yazilan === "yeni") { m.close(); kisiler.sec(kisiler.ekle(text)) }
                else { kisiler.adDegistir(kisiler.secili, text); m.yazilan = "" }
            }
            Keys.onEscapePressed: m.yazilan = ""
        }
        Text { anchors.left: parent.left; visible: m.yazilan === "sil"; width: 300; leftPadding: 10; rightPadding: 10; topPadding: 4; bottomPadding: 4
            wrapMode: Text.Wrap; color: Renk.yazi; font.pixelSize: 13
            text: qsTr("“%1” silinsin mi? Abonelikleri, zili, geçmişi ve listeleri de silinir; geri alınamaz. Program “%2” ile yeniden açılır.")
                  .arg(kisiler.seciliAd).arg((kisiler.liste.find(function(x) { return x.id !== kisiler.secili }) || {}).ad) }
        MenuSatiri { anchors.left: parent.left; visible: m.yazilan === "sil"; yazi: qsTr("Sil"); yaziRenk: Renk.hata
            onTiklandi: { m.close(); kisiler.sil(kisiler.secili) } }
        MenuSatiri { anchors.left: parent.left; visible: m.yazilan === "sil"; yazi: qsTr("Vazgeç"); onTiklandi: m.yazilan = "" }
        MenuCizgisi { anchors.left: parent.left; width: 300 }
        // Programın görünümü; seçilince hemen değişir, menü açık kalır.
        MenuBasligi { anchors.left: parent.left; text: qsTr("Görünüm") }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Cihaz teması"); ipucu: qsTr("varsayılan"); secili: kisiler.gorunum === "cihaz"; onTiklandi: kisiler.gorunumSec("cihaz") }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Koyu"); secili: kisiler.gorunum === "koyu"; onTiklandi: kisiler.gorunumSec("koyu") }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Açık"); secili: kisiler.gorunum === "acik"; onTiklandi: kisiler.gorunumSec("acik") }
        // Dil (DilPenceresi): satırda şu anki dil kendi dilinde yazılı.
        MenuCizgisi { anchors.left: parent.left; width: 300 }
        MenuBasligi { anchors.left: parent.left; text: qsTr("Dil") }
        MenuSatiri { anchors.left: parent.left; width: 300; yazi: (kisiler.diller.find(function(d) { return d.kod === kisiler.dil }) || {}).ad || kisiler.dil
            ipucu: qsTr("değiştir"); onTiklandi: { m.close(); pencere.dilPenceresiniAc() } }
        // Yakınlık: bütün arayüz birlikte büyür ya da küçülür (Ctrl+artı, Ctrl+eksi, Ctrl+0, Ctrl+tekerlek). Değiştirmek
        // bitince program kendiliğinden bir kez yeniden açılır (Ana.qml, yakinlikDegistir).
        MenuCizgisi { anchors.left: parent.left; width: 300 }
        MenuBasligi { anchors.left: parent.left; text: qsTr("Yakınlık") }
        Item {
            width: 300; height: 40
            Row {
                anchors.left: parent.left; anchors.leftMargin: 10; spacing: 6; anchors.verticalCenter: parent.verticalCenter
                Repeater {
                    model: [{ y: "−", yon: -1 }, { y: "", yon: 0 }, { y: "+", yon: 1 }]
                    Rectangle {
                        width: modelData.yon === 0 ? 64 : 32; height: 32; radius: 16
                        color: modelData.yon !== 0 && yakFare.containsMouse ? Renk.menuVurgu : "transparent"
                        border.width: modelData.yon !== 0 ? 1 : 0; border.color: Renk.cizgi
                        Text { anchors.centerIn: parent; color: Renk.yazi; font.pixelSize: modelData.yon === 0 ? 14 : 18
                            text: modelData.yon === 0 ? qsTr("%%1").arg(kisiler.yakinlik) : modelData.y }
                        MouseArea { id: yakFare; anchors.fill: parent; hoverEnabled: true; enabled: modelData.yon !== 0
                            cursorShape: Qt.PointingHandCursor; onClicked: pencere.yakinlikDegistir(modelData.yon) }
                    }
                }
            }
            Text { anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                text: "Ctrl + / −"; color: Renk.yaziSoluk; font.pixelSize: 12 }
        }
        // Yenilikler (sürüm notları, yenilikler.py): kurulu sürüm de burada görünür.
        MenuCizgisi { anchors.left: parent.left; width: 300 }
        MenuSatiri { anchors.left: parent.left; width: 300; yazi: qsTr("Yenilikler"); ipucu: qsTr("sürüm %1").arg(yenilikler.surumAdi)
            onTiklandi: { m.close(); pencere.yenilikleriAc() } }
    }
}
