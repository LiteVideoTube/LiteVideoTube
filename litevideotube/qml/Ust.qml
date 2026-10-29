import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: ust
    color: Renk.zemin
    signal ara(string metin)
    signal anaSayfa()
    signal gecmis()
    signal abonelikler()
    signal kitaplik()
    signal kesfet()
    signal geriBildirim()   // hata bildirme ve öneri penceresi
    signal menu()
    function sayfada(s) { return pencere.sayfa === s }
    readonly property var mavi: ["7cc4ff", "1170c0"]   // Renk.mavi, açık sayfanın düğmesi      // sol kenardaki abonelik listesini açar ya da kapatır (Ana.qml, kenarDegistir)
    // Arama kutusu yalnız arama kutusu (adres ayrı satırda, AdresSatiri.qml): arama sayfasında
    // aranan söz durur, öbür sayfalarda boş; yazıp vazgeçince eski yazı geri gelir. Silik yazısı yalnız "Ara"
    // (bağlantı yeri adres çubuğu), ama yapıştırılan bağlantı yine açılır: kişi tuhaf bir arama sonucu görmesin.
    property string kutuYazisi: ""
    onKutuYazisiChanged: if (!kutu.activeFocus) kutu.text = kutuYazisi
    property alias yaziyor: kutu.activeFocus
    // Pencere daralınca (eski bilgisayarların küçük ekranı): önce arama kutusunun tam ortada durması bırakılır, sonra
    // kutu daralır, en son adın yazısı gizlenir, simge kalır. 27 Ekim'e kadar sağdaki düğmeler kutunun üstüne biniyor,
    // 800 pikselde pencerenin dışına taşıyordu (sağ taraf adın genişliğine sabitti).
    readonly property real sabitBosluk: 8 + 10 + 16 * 5   // iki kenar payı ve altı parça arasındaki beş aralık
    readonly property real sagTaraf: sagSatir.implicitWidth
    readonly property real solSimgeli: menuDugme.implicitWidth + 48 - 12   // ad alanı 12 piksel sola kayık
    readonly property bool adYazili: width - sabitBosluk - solSimgeli - 8 - ad.implicitWidth - sagTaraf >= 160
    readonly property real solTaraf: solSimgeli + (adYazili ? 8 + ad.implicitWidth : 0)
    readonly property real kalan: width - sabitBosluk - solTaraf - sagTaraf
    readonly property real fark: sagTaraf - solTaraf
    readonly property bool ortada: kalan - Math.abs(fark) >= 280
    readonly property real kutuGenisligi: Math.max(120, Math.min(640, width * 0.5, ortada ? kalan - Math.abs(fark) : kalan))

    RowLayout {
        anchors.fill: parent
        // Sağ pay 10: kişi yuvarlağının kutusundaki 9 piksellik boşlukla pencere kenarına uzaklığı soldaki menü çizgileriyle aynı
        // (19 piksel; 16'yken sağda 25'ti).
        anchors.leftMargin: 8; anchors.rightMargin: 10
        spacing: 16
        Simge { id: menuDugme; objectName: "menuDugme"; ad: "menu"; ipucu: qsTr("Abonelikler listesi"); onTiklandi: ust.menu() }
        // Ad ana sayfaya (Abonelikler) götürür; tarayıcıdaki logo gibi orta tık ve Ctrl+tık yeni sekmede açar, sağ tık
        // "Yeni sekmede aç" menüsü (sağ tık yapılmıyordu).
        MouseArea {
            id: adAlani
            Layout.leftMargin: -12
            Layout.rightMargin: ust.ortada && ust.fark > 0 ? ust.fark : 0
            Layout.preferredWidth: adSatiri.implicitWidth; Layout.fillHeight: true
            cursorShape: Qt.PointingHandCursor
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onClicked: function(m) {
                if (m.button === Qt.RightButton) pencere.yeniSekmeMenusu(function() { pencere.sayfaYeniSekmede("abonelik") }, adAlani)
                else if (m.button === Qt.MiddleButton || (m.modifiers & Qt.ControlModifier)) pencere.sayfaYeniSekmede("abonelik")
                else ust.anaSayfa()
            }
            // Adın solunda programın simgesi, damarlı yapraklı büyük çizim (48 piksel).
            Row {
                id: adSatiri
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    source: "../simgeler/litevideotube.svg"; width: 48; height: 48; sourceSize: Qt.size(48, 48)
                }
                Text {
                    id: ad
                    visible: ust.adYazili
                    anchors.verticalCenter: parent.verticalCenter
                    textFormat: Text.StyledText
                    text: "<font color='" + Renk.mavi + "'>Lite</font>VideoTube"
                    color: Renk.yazi; font.pixelSize: 20; font.bold: true
                }
            }
        }
        Item { Layout.fillWidth: true }
        Rectangle {
            id: cerceve
            Layout.preferredWidth: ust.kutuGenisligi; Layout.preferredHeight: 40
            radius: 20; color: Renk.kutu; border.color: kutu.activeFocus ? Renk.mavi : Renk.k("#303030", "#c6c6c6")
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 4; spacing: 4
                TextField {
                    id: kutu
                    Layout.fillWidth: true
                    placeholderText: qsTr("Ara")
                    placeholderTextColor: Renk.yaziSoluk
                    color: Renk.yazi; font.pixelSize: 16
                    background: null
                    selectByMouse: true
                    onAccepted: { ust.ara(text); focus = false }
                    Keys.onEscapePressed: focus = false
                    onActiveFocusChanged: if (!activeFocus) text = ust.kutuYazisi
                    // Kutunun çerçevesi (✕ dahil) kutunun içi sayılır: ✕'a basınca odak kutuda kalsın (uygulama.py,
                    // OdakBekcisi), yoksa odak gidince silinen yazı geri gelirdi.
                    property Item tiklamaAlani: cerceve
                }
                // Yazıyı tek tıkla silen ✕: yalnız yazı varken; büyüteçten ince bir çizgiyle
                // ayrı, yanlışlıkla aranmasın. Geçmiş sayfasındaki "Aramayı temizle" ile aynı görünüm.
                Simge {
                    visible: kutu.text !== ""
                    ad: "close"; boy: 18; ipucu: qsTr("Temizle")
                    onTiklandi: { kutu.text = ""; kutu.forceActiveFocus() }
                }
                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; Layout.leftMargin: 8; color: Renk.k("#303030", "#d9d9d9") }
                Simge {
                    ad: "search"; boy: 22
                    Layout.preferredWidth: 48; Layout.preferredHeight: 36
                    ipucu: qsTr("Ara")
                    onTiklandi: { ust.ara(kutu.text); kutu.focus = false }
                }
            }
        }
        Item { Layout.fillWidth: true }
        Item {
            Layout.leftMargin: ust.ortada && ust.fark < 0 ? -ust.fark : 0
            Layout.preferredWidth: sagSatir.implicitWidth; Layout.fillHeight: true
            // 29 Ekim (dört seçenekten D): simgeler ince çizgili ve aralıklı (dolu ve sık dururken "iç içe, aynı
            // karalıkta"ydılar). Açık sayfanın düğmesi dolu ve mavi; hata bildirme hafif turuncu (kırmızı "bir şey bozuldu"
            // gibi okunurdu).
            Row {
                id: sagSatir
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                // İndirmeler: yalnız bir şey indirilmişse görünür; sürerken üstünde sayı.
                Item {
                    visible: indirici.isler.length > 0
                    width: indirSimge.implicitWidth; height: indirSimge.implicitHeight
                    Simge { id: indirSimge; ad: "download"; ipucu: qsTr("İndirmeler"); onTiklandi: indirmeler.opened ? indirmeler.close() : indirmeler.open() }
                    Rectangle { visible: indirici.suruyor > 0; anchors { right: parent.right; top: parent.top; margins: 4 }
                        width: 16; height: 16; radius: 8; color: Renk.maviDolgu
                        Text { anchors.centerIn: parent; text: indirici.suruyor; color: "black"; font.pixelSize: 10; font.bold: true } }
                    IndirmelerMenusu { id: indirmeler }
                }
                // Hata bildir ya da öneri yaz: her sayfada görünsün diye üst şeritte, Keşfet'in solunda.
                Simge { id: geriBildirimDugme; objectName: "geriBildirimDugme"; ad: "feedback_ince"; renk: ["ffb74d", "f29900"]; kaydir: 2; ipucu: qsTr("Hata bildir ya da öneri yaz")
                    onTiklandi: ust.geriBildirim() }
                // Sağ tık menüsü düğmenin tam altında açılır (farenin yerinde düğmenin üstüne biniyordu).
                // Keşfet: izlediklerine göre abone olmadığın kanallar; YouTube'daki gibi Aboneliklerin solunda.
                Simge { id: kesfetDugme; ad: ust.sayfada("kesfet") ? "explore" : "explore_ince"; renk: ust.sayfada("kesfet") ? ust.mavi : null; ipucu: qsTr("Keşfet"); onTiklandi: ust.kesfet()
                    onOrtaTiklandi: pencere.sayfaYeniSekmede("kesfet")
                    onSagTiklandi: pencere.yeniSekmeMenusu(function() { pencere.sayfaYeniSekmede("kesfet") }, kesfetDugme) }
                Simge { id: abonelikDugme; ad: ust.sayfada("abonelik") ? "subscriptions" : "subscriptions_ince"; renk: ust.sayfada("abonelik") ? ust.mavi : null; ipucu: qsTr("Abonelikler"); onTiklandi: ust.abonelikler()
                    onOrtaTiklandi: pencere.sayfaYeniSekmede("abonelik")
                    onSagTiklandi: pencere.yeniSekmeMenusu(function() { pencere.sayfaYeniSekmede("abonelik") }, abonelikDugme) }
                Simge { id: listeDugme; ad: ust.sayfada("liste") ? "video_library" : "video_library_ince"; renk: ust.sayfada("liste") ? ust.mavi : null; ipucu: qsTr("Listeler ve Sonra izle"); onTiklandi: ust.kitaplik()
                    onOrtaTiklandi: pencere.sayfaYeniSekmede("liste")
                    onSagTiklandi: pencere.yeniSekmeMenusu(function() { pencere.sayfaYeniSekmede("liste") }, listeDugme) }
                Simge { id: gecmisDugme; ad: "history"; renk: ust.sayfada("gecmis") ? ust.mavi : null; ipucu: qsTr("Geçmiş"); onTiklandi: ust.gecmis()
                    onOrtaTiklandi: pencere.sayfaYeniSekmede("gecmis")
                    onSagTiklandi: pencere.yeniSekmeMenusu(function() { pencere.sayfaYeniSekmede("gecmis") }, gecmisDugme) }
                // Kişi (kisi.py): adının ilk harfi; menüden kişi değiştirilir, yeni kişi eklenir. Boyu simgelerle aynı (40):
                // Row çocukları üstten dizer, 48'ken simgeler yuvarlaktan 4 piksel yukarıda duruyordu.
                Item {
                    width: 48; height: 40
                    Rectangle {
                        anchors.centerIn: parent; width: 30; height: 30; radius: 15
                        color: kisiFare.containsMouse ? Renk.maviDolguVurgu : Renk.maviDolgu
                        Text { anchors.centerIn: parent; text: (kisiler.seciliAd || "?").charAt(0).toLocaleUpperCase()
                            color: "black"; font.pixelSize: 15; font.bold: true }
                    }
                    MouseArea { id: kisiFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: kisiMenu.opened ? kisiMenu.close() : kisiMenu.open()
                        ToolTip.visible: containsMouse && !kisiMenu.opened; ToolTip.delay: 600; ToolTip.text: qsTr("Kişi: %1").arg(kisiler.seciliAd) }
                    KisiMenusu { id: kisiMenu }
                }
            }
        }
    }
    // Sayfanın boş bir yerine tıklayınca yazı kutusu bırakılır, tuşlar videoya döner.
    function birak() { kutu.focus = false }
}
