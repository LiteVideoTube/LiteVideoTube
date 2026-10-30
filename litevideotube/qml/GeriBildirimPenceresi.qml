import QtQuick
import QtQuick.Controls.Basic

// Hata bildirme ve öneri penceresi: üst şeritteki düğmeden, her sayfadan açılır. Hata mı
// öneri mi seçilir, yazılır, "Gönder"e basılır. Bildirim önce bu bilgisayara yazılır, sonra arka planda geliştiricilere
// (Sentry) gider; internet yoksa diskte bekler, program sonra kendisi gönderir (geribildirim.py). Pencere bunu
// beklemez: diske yazıldıysa "Gönderildi." der (ara hâl, klasör yolu ve "Klasörü aç" olmasın).
// Yalnız diske yazılamazsa hata yazısı çıkar.
Popup {
    id: p
    property string tur: "hata"
    property string sayfa: ""          // açıldığı sayfanın adresi
    property string kaydedilen: ""     // diske yazılan bildirim; doluysa pencere "Gönderildi." hâlinde
    property bool hataOldu: false
    property string resimAdresi: ""    // pencere açılmadan hemen önce alınan pencere resmi (geribildirim.resimAl)
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: 540
    padding: 22
    margins: 12
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Renk.pencereZemin; radius: 12; border.color: Renk.cizgi }

    function ac(adres) {
        // Resim pencere açılmadan alınır: bildirme penceresi resimde görünmesin.
        resimAdresi = geriBildirim.resimAl(pencere)
        resimEkle.checked = false
        tur = "hata"
        sayfa = adres
        kaydedilen = ""
        hataOldu = false
        yazi.text = ""
        adresEkle.checked = true
        kayitEkle.checked = true
        open()
        yazi.forceActiveFocus()
    }
    function gonder() {
        if (!yazi.text.trim()) return
        var yol = geriBildirim.gonder(p.tur, yazi.text, adresEkle.checked ? p.sayfa : "", resimEkle.checked && p.resimAdresi !== "",
                                       p.tur === "hata" && kayitEkle.checked)
        if (yol) p.kaydedilen = yol
        else p.hataOldu = true
    }
    // Ctrl+Enter pencerenin her yerinde gönderir (yazı alanında yalnız Enter yeni satır); işarete tıklayınca odak
    // yazı alanından çıkıyordu.
    Shortcut { sequences: ["Ctrl+Return", "Ctrl+Enter"]; enabled: p.opened && !p.kaydedilen; onActivated: p.gonder() }
    onClosed: { geriBildirim.resimBirak(); resimAdresi = ""; pencere.tuslariVideoyaVer() }

    component Hap: Rectangle {
        id: h
        property string yazi
        property bool secili: false
        signal tiklandi()
        width: hYazi.implicitWidth + 32; height: 34; radius: 17
        color: secili ? Renk.maviDolgu : hFare.containsMouse ? Renk.k("#4a4a4a", "#d9d9d9") : Renk.yuzeyAcik
        Text { id: hYazi; anchors.centerIn: parent; text: h.yazi; font.pixelSize: 14; font.weight: Font.Medium
            color: h.secili ? "black" : Renk.yazi }
        MouseArea { id: hFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: h.tiklandi() }
    }
    component Isaret: CheckBox {
        id: c
        property string yazi
        padding: 0
        indicator: Rectangle {
            implicitWidth: 18; implicitHeight: 18; radius: 4; y: (c.height - height) / 2; x: c.mirrored ? c.width - width : 0
            color: c.checked ? Renk.maviDolgu : "transparent"; border.color: c.checked ? Renk.maviDolgu : Renk.yaziSoluk
            Text { anchors.centerIn: parent; text: "✓"; visible: c.checked; color: "black"; font.pixelSize: 13; font.bold: true }
        }
        contentItem: Text { leftPadding: c.mirrored ? 0 : 26; rightPadding: c.mirrored ? 26 : 0; text: c.yazi; color: Renk.yazi; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter }
    }
    component Dugme: Button {
        id: d
        property bool ana: false
        contentItem: Text { text: d.text; font.pixelSize: 14; font.weight: Font.Medium
            color: d.ana ? (d.enabled ? "black" : Renk.k("#555555", "#8a8a8a")) : Renk.yazi
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { implicitHeight: 36; implicitWidth: 96; radius: 18
            color: d.ana ? (d.enabled ? (d.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu) : Renk.k("#3a4a58", "#cfe3f5")) : (d.hovered ? Renk.yuzeyAcik : "transparent") }
    }

    contentItem: Column {
        spacing: 14

        // Başlık ve sağ üstte kapatma çarpısı (Vazgeç ile aynı iş; pencerelerin alışılmış yerinde).
        Item {
            id: baslikSatiri
            width: parent.width; height: baslik.implicitHeight
            Text { id: baslik; anchors.left: parent.left; text: qsTr("Hata bildir ya da öneri yaz"); color: Renk.yazi; font.pixelSize: 18; font.weight: Font.Medium }
            Simge { objectName: "geriBildirimKapat"; ad: "close"; boy: 20; ipucu: qsTr("Kapat (Esc)")
                anchors { right: parent.right; rightMargin: -12; verticalCenter: baslik.verticalCenter }
                onTiklandi: p.close() }
        }

        // Yazma hâli. Ortası pencereye sığmazsa kayar, Vazgeç ve Gönder hep altta görünür: %110 yakınlıkta resim
        // eklenince pencere ekrandan taşıyor, Gönder ekranın altında kalıyordu (Eren'in bildirimi, 30 Ekim).
        Flickable {
            id: kaydir
            visible: !p.kaydedilen
            width: parent.width
            // Pencerenin sığabileceği boydan başlık, düğmeler, aralıklar ve kenar boşlukları çıkar. Bu boylar kaydir'a
            // bağlı değil; pencerenin kendi boyu kullanılsaydı döngü olurdu.
            height: Math.min(icerik.implicitHeight, (p.parent ? p.parent.height : 768) - 2 * p.margins
                             - p.topPadding - p.bottomPadding - baslikSatiri.height - dugmeler.height - 2 * 14)
            contentHeight: icerik.implicitHeight
            clip: true
            interactive: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: kaydir.interactive ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }
        Column {
            id: icerik
            width: kaydir.width
            spacing: 14
            Row { anchors.left: parent.left;
                spacing: 8
                Hap { yazi: qsTr("Hata"); secili: p.tur === "hata"; onTiklandi: { p.tur = "hata"; yazi.forceActiveFocus() } }
                Hap { yazi: qsTr("Öneri"); secili: p.tur === "oneri"; onTiklandi: { p.tur = "oneri"; yazi.forceActiveFocus() } }
            }
            ScrollView {
                // Resim gösterilirken yazı alanı kısalır: pencere 768 piksellik ekrana da sığsın.
                width: parent.width; height: resimEkle.checked ? 110 : 170
                TextArea {
                    id: yazi
                    wrapMode: TextArea.Wrap
                    selectByMouse: true
                    color: Renk.yazi; font.pixelSize: 14
                    placeholderTextColor: Renk.yaziSoluk
                    placeholderText: p.tur === "hata" ? qsTr("Ne oldu? Ne yaparken oldu? Ne olmasını bekliyordun?")
                                                       : qsTr("Programda ne olsun ya da ne değişsin istersin?")
                    background: Rectangle { radius: 8; color: Renk.kutu; border.color: yazi.activeFocus ? Renk.mavi : Renk.cizgi }
                }
            }
            Isaret { anchors.left: parent.left; id: adresEkle; visible: p.sayfa !== ""; yazi: qsTr("Açık sayfanın adresini de ekle") }
            Isaret { anchors.left: parent.left; id: kayitEkle; visible: p.tur === "hata"; yazi: qsTr("Program kayıtlarını da gönder") }
            Isaret { anchors.left: parent.left; id: resimEkle; visible: p.resimAdresi !== ""; yazi: qsTr("Pencerenin resmini de ekle") }
            Column {
                visible: resimEkle.checked && p.resimAdresi !== ""
                width: parent.width
                spacing: 6
                Text { width: parent.width; wrapMode: Text.Wrap; color: Renk.yaziSoluk; font.pixelSize: 13
                    text: qsTr("Eklenecek resim bu. Bu pencereyi açmadan önce ekranda ne varsa resimde o görünür.") }
                Image { width: parent.width; height: Math.round(width * 0.45); fillMode: Image.PreserveAspectFit
                    horizontalAlignment: Image.AlignLeft; asynchronous: true; cache: false; source: p.resimAdresi
                    sourceSize.width: 500 }
            }
            Text {
                width: parent.width; wrapMode: Text.Wrap; color: Renk.yaziSoluk; font.pixelSize: 13; lineHeight: 1.15
                text: qsTr("Yazdığın mesaj, sistemin ve programın bilgisiyle birlikte geliştiricilere gönderilir.")
            }
            Text {
                visible: p.hataOldu
                width: parent.width; wrapMode: Text.Wrap; color: Renk.hata; font.pixelSize: 13
                text: qsTr("Kaydedilemedi. Klasöre yazılamadı: %1").arg(geriBildirim.klasor())
            }
        }
        }
        Row {
            id: dugmeler
            visible: !p.kaydedilen
            anchors.right: parent.right
            spacing: 8
            Dugme { text: qsTr("Vazgeç"); onClicked: p.close() }
            Dugme { text: qsTr("Gönder"); ana: true; enabled: yazi.text.trim() !== ""; onClicked: p.gonder() }
        }

        // Gönderildi hâli
        Text {
            visible: !!p.kaydedilen
            width: parent.width; color: Renk.yazi; font.pixelSize: 14; topPadding: 4; bottomPadding: 8
            text: qsTr("Gönderildi.")
        }
    }
}
