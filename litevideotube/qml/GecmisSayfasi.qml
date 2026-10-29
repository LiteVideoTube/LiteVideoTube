import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// İzleme geçmişi: günlere göre, kaldığın yer, tek tek ve onaylı toplu silme (22 Ekim düzeni). Arama kutusu
// (YouTube'daki gibi sayfanın kendi kutusu, üstteki arama kutusu YouTube'da aramaya devam eder):
// yazdıkça liste daralır, bütün geçmişte başlık ve kanal adında arar.
// "Ana sayfaya geri koy" yok; yerine her satırda "Sonra izle'ye ekle".
Item {
    id: g
    readonly property Flickable kaydirmaAlani: kaydirma   // yakınlıkla yeniden açılınca kaydırma yeri (Ana.qml)
    property var gunler: []
    property string arama: ""
    signal sec(var v)
    function yenile() { gunler = kayit.gecmisAra(arama) }
    onAramaChanged: aramaSaati.restart()
    Timer { id: aramaSaati; interval: 200; onTriggered: g.yenile() }
    Connections { target: kayit; function onGecmisDegisti() { if (g.visible) g.yenile() } }

    function zaman(s) {
        s = Math.floor(s); var sa = Math.floor(s / 3600), dk = Math.floor(s % 3600 / 60), sn = s % 60
        return (sa > 0 ? sa + ":" + (dk < 10 ? "0" : "") : "") + dk + ":" + (sn < 10 ? "0" : "") + sn
    }

    Flickable {
        id: kaydirma
        TekerlekHizi { hedef: kaydirma }
        anchors.fill: parent
        contentHeight: sutun.implicitHeight + 48
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        Column {
            id: sutun
            x: Math.max(24, (kaydirma.width - 900) / 2); y: 16
            width: Math.min(900, kaydirma.width - 48)
            spacing: 12
            RowLayout {
                width: parent.width
                Text { text: qsTr("İzleme geçmişi"); color: Renk.yazi; font.pixelSize: 26; font.bold: true; Layout.fillWidth: true; SecimKatmani { } }
                Rectangle {
                    Layout.preferredWidth: Math.min(320, sutun.width * 0.4); Layout.preferredHeight: 36; radius: 18
                    color: Renk.yuzey; border.color: aramaKutu.activeFocus ? Renk.mavi : "transparent"
                    Image { id: aramaSimge; anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; width: 18; height: 18
                        sourceSize: Qt.size(36, 36); source: Renk.simge("search"); opacity: 0.7 }
                    TextField {
                        id: aramaKutu
                        anchors { left: aramaSimge.right; leftMargin: 6; right: temizle.left; top: parent.top; bottom: parent.bottom }
                        placeholderText: qsTr("İzleme geçmişinde ara")
                        placeholderTextColor: Renk.yaziSoluk
                        color: Renk.yazi; font.pixelSize: 14; background: null; selectByMouse: true
                        verticalAlignment: TextInput.AlignVCenter
                        onTextChanged: g.arama = text
                        Keys.onEscapePressed: { if (text) text = ""; else focus = false }
                    }
                    Simge { id: temizle; boy: 16; anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter
                        visible: aramaKutu.text !== ""; ad: "close"; ipucu: qsTr("Aramayı temizle"); onTiklandi: aramaKutu.text = "" }
                }
                Button {
                    id: hepsi
                    visible: g.gunler.length > 0 && g.arama === ''
                    text: qsTr("Tüm geçmişi sil")
                    onClicked: onay.open()
                    contentItem: Text { text: hepsi.text; color: Renk.yazi; font.pixelSize: 14 }
                    background: Rectangle { radius: 18; implicitHeight: 36; color: hepsi.hovered ? Renk.yuzeyAcik : Renk.yuzey }
                }
            }
            Text { anchors.left: parent.left;
                visible: g.gunler.length === 0
                text: g.arama ? qsTr("Aramana uyan video yok.") : qsTr("Henüz izlediğin bir video yok.")
                color: Renk.yaziSoluk; font.pixelSize: 16
                SecimKatmani { }
            }
            Repeater {
                model: g.gunler
                Column {
                    width: sutun.width; spacing: 10
                    Text { anchors.left: parent.left; text: modelData.gun; color: Renk.yazi; font.pixelSize: 18; font.bold: true; topPadding: 12; SecimKatmani { } }
                    Repeater {
                        model: modelData.videolar
                        Item {
                            id: satir
                            width: sutun.width; height: 104
                            // Sayfada bul (Ctrl+F): başlık ve kanal adı.
                            BulKaynagi {
                                hedef: satir
                                function eslesmeler(sorgu) {
                                    return pencere.bulKucuk((modelData.baslik || "") + " " + (modelData.kanal || "")).indexOf(sorgu) >= 0
                                        ? [{ y: satir.mapToItem(null, 0, 0).y }] : []
                                }
                                function goster(m) { pencere.bulunanId = modelData.id; pencere.kaydirGoster(satir, 0) }
                                function birak() { pencere.bulunanId = "" }
                            }
                            Rectangle { anchors.fill: parent; anchors.margins: -4; radius: 10; color: "transparent"
                                border.color: Renk.mavi; border.width: 2; visible: pencere.bulunanId === modelData.id }
                            Rectangle {
                                id: resim
                                anchors.left: parent.left
                                width: 184; height: 104; radius: 8; color: Renk.yuzey
                                Image { anchors.fill: parent; fillMode: Image.PreserveAspectCrop; asynchronous: true
                                    source: modelData.resim; sourceSize.width: 320 }
                                IlerlemeCizgisi { videoId: modelData.id }
                                Rectangle { visible: modelData.sure !== ""; anchors { right: parent.right; bottom: parent.bottom; margins: 6 }
                                    width: sy.implicitWidth + 6; height: 18; radius: 4; color: "#cc000000"
                                    Text { id: sy; anchors.centerIn: parent; color: "white"; font.pixelSize: 11; font.bold: true; text: modelData.sure } }
                            }
                            // Yazılar sürükleyince seçilir (SecimKatmani), tıklayınca satır gibi açar.
                            function solTik(tuslar) { if (tuslar & Qt.ControlModifier) pencere.videoYeniSekmede(modelData); else g.sec(modelData) }
                            Column {
                                z: 1
                                anchors { left: resim.right; leftMargin: 12; right: sil.left; rightMargin: 8; top: parent.top }
                                spacing: 4
                                Text { width: parent.width; text: modelData.baslik || modelData.id; color: Renk.yazi; font.pixelSize: 16
                                    font.weight: Font.Medium; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                                    SecimKatmani { tiklama: satir.solTik } }
                                // Kanal ve son izlenişlerin zamanı (en yenisi önde; kayit.izlenis_yazisi).
                                Text { width: parent.width; elide: Text.ElideRight; color: Renk.yaziSoluk; font.pixelSize: 13
                                    text: [modelData.kanal, modelData.zamanlar].filter(function(x) { return x }).join("  ·  ")
                                    SecimKatmani { tiklama: satir.solTik } }
                                Text { anchors.left: parent.left; visible: modelData.kaldigi > 0; color: Renk.mavi; font.pixelSize: 13
                                    text: qsTr("Kaldığın yer: %1").arg(g.zaman(modelData.kaldigi)); SecimKatmani { tiklama: satir.solTik } }
                            }
                            MouseArea { anchors { left: parent.left; right: sonra.left; top: parent.top; bottom: parent.bottom }
                                cursorShape: Qt.PointingHandCursor
                                // Orta tık ya da Ctrl+tık yeni sekmede, sağ tık menü (video kartlarındaki gibi).
                                acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                                onClicked: function(m) {
                                    if (m.button === Qt.RightButton) pencere.kartMenusu(modelData)
                                    else if (m.button === Qt.MiddleButton) pencere.videoYeniSekmede(modelData)
                                    else satir.solTik(m.modifiers)
                                } }
                            // "Ana sayfaya geri koy" yerine: Sonra izle'ye ekle.
                            Simge { id: sonra; anchors.right: sil.left; anchors.verticalCenter: parent.verticalCenter
                                readonly property bool listede: { listeler.surum; return listeler.sonradaMi(modelData.id) }
                                ad: listede ? "check" : "schedule"; ipucu: listede ? qsTr("Sonra izle'den çıkar") : qsTr("Sonra izle'ye ekle")
                                onTiklandi: listeler.sonraIzleDegistir(modelData) }
                            Simge { id: sil; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                ad: "close"; ipucu: qsTr("Geçmişten sil"); onTiklandi: { silOnay.video = modelData; silOnay.open() } }
                        }
                    }
                }
            }
        }
    }

    // Tek video silmek de sorulur (28 Ekim: yanlışlıkla silinmesin); kaldığı yer de gidiyor.
    Dialog {
        id: silOnay
        property var video: null
        anchors.centerIn: parent
        modal: true
        title: qsTr("Geçmişten silinsin mi?")
        standardButtons: Dialog.Yes | Dialog.No
        Text { width: Math.min(460, g.width - 80); wrapMode: Text.Wrap; color: Renk.yazi; font.pixelSize: 14
            text: qsTr("\"%1\" ve kaldığın yer silinecek.").arg(silOnay.video ? (silOnay.video.baslik || silOnay.video.id) : "") }
        background: Rectangle { color: Renk.pencereZemin; radius: 12 }
        onAccepted: if (video) kayit.sil(video.id)
        onClosed: video = null
        Component.onCompleted: { standardButton(Dialog.Yes).text = qsTr("Evet, sil"); standardButton(Dialog.No).text = qsTr("Vazgeç") }
    }

    Dialog {
        id: onay
        anchors.centerIn: parent
        modal: true
        title: qsTr("Tüm geçmiş silinsin mi?")
        standardButtons: Dialog.Yes | Dialog.No
        Text { text: qsTr("İzlediğin bütün videolar ve kaldığın yerler silinecek. Geri alınamaz."); color: Renk.yazi; font.pixelSize: 14 }
        background: Rectangle { color: Renk.pencereZemin; radius: 12 }
        onAccepted: kayit.hepsiniSil()
        Component.onCompleted: { standardButton(Dialog.Yes).text = qsTr("Evet, sil"); standardButton(Dialog.No).text = qsTr("Vazgeç") }
    }
}
