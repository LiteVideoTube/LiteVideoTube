import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Oynatma listeleri ve "Sonra izle" (YouTube'daki gibi). Solda listeler, sağda seçili
// listenin videoları: tıklanan videodan başlayarak liste sırayla oynar. Listeler programın kendi
// kaydında (liste.py), YouTube hesabına yazılmaz.
Item {
    id: ls
    property var listeler_: []
    property int secili: 1
    property var videolar: []
    property bool adYaziliyor: false
    signal oynat(int listeId, int sira)
    function yenile() {
        listeler_ = listeler.listeler()
        if (!listeler_.some(function(l) { return l.id === secili })) secili = 1
        videolar = listeler.videolar(secili)
    }
    function sec(id) { secili = id; adYaziliyor = false; videolar = listeler.videolar(id) }
    readonly property var seciliListe: { for (var i = 0; i < listeler_.length; i++) if (listeler_[i].id === secili) return listeler_[i]; return null }
    Connections { target: listeler; function onDegisti() { if (ls.visible) ls.yenile() } }

    // Solda listeler
    Flickable {
        id: sol
        TekerlekHizi { hedef: sol }
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: 300
        contentHeight: solSutun.implicitHeight + 32
        boundsBehavior: Flickable.StopAtBounds; clip: true
        Column {
            id: solSutun
            anchors.left: parent.left; anchors.leftMargin: 16; y: 16; width: 268; spacing: 4
            Text { anchors.left: parent.left; text: qsTr("Listeler"); color: Renk.yazi; font.pixelSize: 22; font.bold: true; bottomPadding: 8; SecimKatmani { } }
            Repeater {
                model: ls.listeler_
                Rectangle { anchors.left: parent.left;
                    width: 268; height: 64; radius: 10
                    color: modelData.id === ls.secili ? Renk.yuzeyAcik : satirUstunde.hovered ? Renk.yuzey : "transparent"
                    HoverHandler { id: satirUstunde }
                    Rectangle {
                        id: kucukResim
                        anchors.left: parent.left; anchors.leftMargin: 8; anchors.verticalCenter: parent.verticalCenter
                        width: 85; height: 48; radius: 6; color: Renk.yuzey
                        Image { anchors.fill: parent; fillMode: Image.PreserveAspectCrop; asynchronous: true
                            source: modelData.resim; sourceSize.width: Renk.resimBoyu(85 * Screen.devicePixelRatio) }
                        Image { visible: modelData.resim === ""; anchors.centerIn: parent; width: 24; height: 24; sourceSize: Qt.size(48, 48)
                            source: Renk.simge(modelData.favori ? "favorite" : modelData.sabit ? "schedule" : "playlist_play"); opacity: 0.6 }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: ls.sec(modelData.id) }
                    // Yazılar sürükleyince seçilir, tıklayınca listeyi açar (SecimKatmani).
                    Column {
                        anchors { left: kucukResim.right; leftMargin: 10; right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                        Text { width: parent.width; text: modelData.ad; color: Renk.yazi; font.pixelSize: 15; font.weight: Font.Medium; elide: Text.ElideRight
                            SecimKatmani { tiklama: function(tuslar) { ls.sec(modelData.id) } } }
                        Text { anchors.left: parent.left; text: qsTr("%n video", "", modelData.sayi); color: Renk.yaziSoluk; font.pixelSize: 12
                            SecimKatmani { tiklama: function(tuslar) { ls.sec(modelData.id) } } }
                    }
                }
            }
            // Yeni liste: ad yazılıp Enter'a basılır.
            Rectangle { anchors.left: parent.left;
                width: 268; height: 44; radius: 10; color: yeniFare.containsMouse && !yeniAd.visible ? Renk.yuzey : "transparent"
                Row {
                    visible: !yeniAd.visible
                    anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                    Image { source: Renk.simge("add"); width: 22; height: 22; sourceSize: Qt.size(44, 44); anchors.verticalCenter: parent.verticalCenter }
                    Text { text: qsTr("Yeni liste"); color: Renk.yazi; font.pixelSize: 15; anchors.verticalCenter: parent.verticalCenter }
                }
                MouseArea { id: yeniFare; anchors.fill: parent; hoverEnabled: true; visible: !yeniAd.visible
                    cursorShape: Qt.PointingHandCursor; onClicked: { yeniAd.visible = true; yeniAd.forceActiveFocus() } }
                TextField {
                    id: yeniAd
                    visible: false
                    anchors.fill: parent; anchors.margins: 4
                    placeholderText: qsTr("Listenin adı"); placeholderTextColor: Renk.yaziSoluk
                    color: Renk.yazi; font.pixelSize: 15
                    background: Rectangle { radius: 8; color: Renk.kutu; border.color: Renk.mavi }
                    onAccepted: { var id = listeler.yeniListe(text); text = ""; visible = false; ls.yenile(); ls.sec(id) }
                    Keys.onEscapePressed: { text = ""; visible = false }
                    onActiveFocusChanged: if (!activeFocus) { text = ""; visible = false }
                }
            }
        }
    }
    Rectangle { anchors { left: sol.right; top: parent.top; bottom: parent.bottom } width: 1; color: Renk.k("#272727", "#e5e5e5") }

    // Sağda seçili liste
    Flickable {
        id: sag
        TekerlekHizi { hedef: sag }
        anchors { left: sol.right; leftMargin: 1; right: parent.right; top: parent.top; bottom: parent.bottom }
        contentHeight: sagSutun.implicitHeight + 32
        boundsBehavior: Flickable.StopAtBounds; clip: true
        ScrollBar.vertical: ScrollBar { }
        Column {
            id: sagSutun
            anchors.left: parent.left; anchors.leftMargin: 24; y: 16; width: Math.min(900, sag.width - 48); spacing: 8
            RowLayout {
                width: parent.width; spacing: 8
                Text {
                    visible: !adKutusu.visible
                    text: ls.seciliListe ? ls.seciliListe.ad : ""; color: Renk.yazi; font.pixelSize: 24; font.bold: true
                    Layout.fillWidth: true; elide: Text.ElideRight
                    SecimKatmani { }
                }
                TextField {
                    id: adKutusu
                    visible: ls.adYaziliyor
                    Layout.fillWidth: true
                    color: Renk.yazi; font.pixelSize: 20
                    background: Rectangle { radius: 8; color: Renk.kutu; border.color: Renk.mavi }
                    onAccepted: { listeler.adDegistir(ls.secili, text); ls.adYaziliyor = false }
                    Keys.onEscapePressed: ls.adYaziliyor = false
                }
                Button {
                    id: oynatDugme
                    visible: ls.videolar.length > 0
                    text: qsTr("Hepsini oynat")
                    onClicked: ls.oynat(ls.secili, 0)
                    contentItem: Row { spacing: 6
                        Text { text: "▶"; color: "black"; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: oynatDugme.text; color: "black"; font.pixelSize: 14; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter } }
                    background: Rectangle { radius: 18; implicitHeight: 36; color: oynatDugme.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu }
                }
                Simge { visible: ls.seciliListe && !ls.seciliListe.sabit; ad: "edit"; ipucu: qsTr("Adını değiştir")
                    onTiklandi: { adKutusu.text = ls.seciliListe.ad; ls.adYaziliyor = true; adKutusu.forceActiveFocus(); adKutusu.selectAll() } }
                Simge { visible: ls.seciliListe && !ls.seciliListe.sabit; ad: "delete"; ipucu: qsTr("Listeyi sil"); onTiklandi: silOnay.open() }
            }
            Text { anchors.left: parent.left; text: qsTr("%n video", "", ls.videolar.length); color: Renk.yaziSoluk; font.pixelSize: 13; SecimKatmani { } }
            Text {
                visible: ls.videolar.length === 0
                width: parent.width; wrapMode: Text.Wrap; topPadding: 24
                color: Renk.yaziSoluk; font.pixelSize: 15
                text: ls.secili === 1
                      ? qsTr("Sonra izle listen boş. Videonun resmindeki saat düğmesiyle ekleyebilirsin.")
                      : qsTr("Bu liste boş. Video sayfasındaki \"Kaydet\" düğmesiyle video ekleyebilirsin.")
                SecimKatmani { }
            }
            Repeater {
                model: ls.videolar
                Rectangle {
                    id: videoSatiri
                    width: sagSutun.width; height: 102; radius: 10
                    color: videoUstunde.hovered ? Renk.yuzey : "transparent"
                    HoverHandler { id: videoUstunde }
                    function solTik(tuslar) { if (tuslar & Qt.ControlModifier) pencere.videoYeniSekmede(modelData); else ls.oynat(ls.secili, index) }
                    Text { anchors.left: parent.left; anchors.leftMargin: 4; width: 24; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter
                        text: index + 1; color: Renk.yaziSoluk; font.pixelSize: 13 }
                    Rectangle {
                        id: resim
                        anchors.left: parent.left; anchors.leftMargin: 32; anchors.verticalCenter: parent.verticalCenter
                        width: 160; height: 90; radius: 8; color: Renk.yuzey
                        Image { anchors.fill: parent; fillMode: Image.PreserveAspectCrop; asynchronous: true
                            source: modelData.resim; sourceSize.width: 320 }
                        IlerlemeCizgisi { videoId: modelData.id }
                        Rectangle { visible: modelData.sure !== ""; anchors { right: parent.right; bottom: parent.bottom; margins: 4 }
                            width: sy.implicitWidth + 6; height: 18; radius: 4; color: "#cc000000"
                            Text { id: sy; anchors.centerIn: parent; color: "white"; font.pixelSize: 11; font.bold: true; text: modelData.sure } }
                    }
                    Column {
                        z: 1   // yazılar sürükleyince seçilir, tıklayınca satır gibi (SecimKatmani)
                        anchors { left: resim.right; leftMargin: 12; right: dugmeler.left; rightMargin: 8; verticalCenter: parent.verticalCenter }
                        spacing: 4
                        Text { width: parent.width; text: modelData.baslik || modelData.id; color: Renk.yazi; font.pixelSize: 15
                            font.weight: Font.Medium; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                            SecimKatmani { tiklama: videoSatiri.solTik } }
                        Text { anchors.left: parent.left; text: modelData.kanal; color: Renk.yaziSoluk; font.pixelSize: 13; SecimKatmani { tiklama: videoSatiri.solTik } }
                    }
                    // Orta tık ya da Ctrl+tık videoyu tek başına yeni sekmede açar, sağ tık menü.
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                        onClicked: function(m) {
                            if (m.button === Qt.RightButton) pencere.kartMenusu(modelData)
                            else if (m.button === Qt.MiddleButton) pencere.videoYeniSekmede(modelData)
                            else videoSatiri.solTik(m.modifiers)
                        } }
                    Row {
                        id: dugmeler
                        anchors { right: parent.right; rightMargin: 4; verticalCenter: parent.verticalCenter }
                        Simge { ad: "arrow_upward"; ipucu: qsTr("Yukarı taşı"); opacity: index > 0 ? 1 : 0.3
                            onTiklandi: listeler.tasi(ls.secili, modelData.id, -1) }
                        Simge { ad: "arrow_downward"; ipucu: qsTr("Aşağı taşı"); opacity: index < ls.videolar.length - 1 ? 1 : 0.3
                            onTiklandi: listeler.tasi(ls.secili, modelData.id, 1) }
                        Simge { ad: "close"; ipucu: qsTr("Listeden çıkar"); onTiklandi: { cikarOnay.video = modelData; cikarOnay.open() } }
                    }
                }
            }
        }
    }

    // Tek videoyu listeden çıkarmak da sorulur (28 Ekim: yanlışlıkla silinmesin).
    Dialog {
        id: cikarOnay
        property var video: null
        anchors.centerIn: parent
        modal: true
        title: qsTr("Listeden çıkarılsın mı?")
        standardButtons: Dialog.Yes | Dialog.No
        Text { width: Math.min(460, ls.width - 80); wrapMode: Text.Wrap; color: Renk.yazi; font.pixelSize: 14
            text: qsTr("\"%1\" %2 listesinden çıkarılacak.")
                  .arg(cikarOnay.video ? (cikarOnay.video.baslik || cikarOnay.video.id) : "").arg(ls.seciliListe ? ls.seciliListe.ad : "") }
        background: Rectangle { color: Renk.pencereZemin; radius: 12 }
        onAccepted: if (video) listeler.cikar(ls.secili, video.id)
        onClosed: video = null
        Component.onCompleted: { standardButton(Dialog.Yes).text = qsTr("Evet, çıkar"); standardButton(Dialog.No).text = qsTr("Vazgeç") }
    }

    Dialog {
        id: silOnay
        anchors.centerIn: parent
        modal: true
        title: qsTr("\"%1\" silinsin mi?").arg(ls.seciliListe ? ls.seciliListe.ad : "")
        standardButtons: Dialog.Yes | Dialog.No
        Text { text: qsTr("Liste silinecek. İzleme geçmişin kalır."); color: Renk.yazi; font.pixelSize: 14 }
        background: Rectangle { color: Renk.pencereZemin; radius: 12 }
        onAccepted: { listeler.listeSil(ls.secili); ls.secili = 1; ls.yenile() }
        Component.onCompleted: { standardButton(Dialog.Yes).text = qsTr("Evet, sil"); standardButton(Dialog.No).text = qsTr("Vazgeç") }
    }
}
