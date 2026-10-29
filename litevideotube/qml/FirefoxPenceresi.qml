import QtQuick
import QtQuick.Controls.Basic

// Abonelikleri getirirken hiçbir tarayıcıda YouTube girişi bulunamayınca (tarayici.py, FirefoxYardimi): tek soru,
// "Kur / Hayır" ya da "Giriş yap / Hayır". Sonrası kendiliğinden yürür: Firefox iner ve kurulur, YouTube'un giriş
// sayfası Firefox'ta açılır, giriş görülünce abonelikler gelir ve pencere kapanır. Görünüşü güncelleme penceresiyle aynı.
Popup {
    id: p
    readonly property string durum: firefox ? firefox.durum : ""
    readonly property bool calisiyor: durum === "kuruluyor" || durum === "aliniyor"   // bu arada kapatılamaz
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: 440
    padding: 22
    modal: true
    focus: true
    closePolicy: calisiyor ? Popup.NoAutoClose : Popup.CloseOnEscape   // Esc "Hayır" ya da "Vazgeç" ile aynı
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Renk.pencereZemin; radius: 12; border.color: Renk.cizgi }
    onDurumChanged: durum === "" ? close() : open()
    onClosed: { if (p.durum !== "") firefox.hayir(); pencere.tuslariVideoyaVer() }

    Connections {
        target: firefox
        // Abonelikler geldi: kişi Firefox'taysa program öne gelsin, sonucu görsün.
        function onGeldi() { pencere.raise(); pencere.requestActivate() }
    }

    readonly property string baslik: ({
        "sor": !firefox || !firefox.kurulu ? qsTr("Firefox kurulsun mu?")
               : firefox.kip === "yeniden" ? qsTr("Firefox'ta YouTube'a yeniden gir") : qsTr("Firefox'ta YouTube'a gir"),
        "indiriliyor": qsTr("Firefox indiriliyor"),
        "kuruluyor": qsTr("Firefox kuruluyor"),
        "bekliyor": firefox && firefox.kip === "baska" ? qsTr("Firefox'ta başka hesapla gir") : qsTr("Firefox'ta YouTube'a giriş yap"),
        "bos": qsTr("Bu hesapta abonelik yok"),
        "aliniyor": qsTr("Giriş yapıldı"),
        "hata": qsTr("Abonelikler getirilemedi") })[durum] || ""
    readonly property string metin: {
        if (!firefox) return ""
        var neden = firefox.neden ? " " + firefox.neden : ""
        switch (durum) {
        case "sor": if (firefox.kurulu && firefox.kip === "yeniden")
            return qsTr("Firefox'taki YouTube girişi artık geçerli değil (çıkış yapılmış ya da süresi dolmuş). Aboneliklerini"
                + " getirmek için Firefox'ta yeniden gir; abonelikler kendiliğinden gelir.")
            // neden (firefox.py) boş ya da boşlukla başlayan ayrı bir cümle; %1 cümlelerin arasına girer.
            return firefox.kurulu
            ? qsTr("Aboneliklerini getirmek için Firefox'ta YouTube hesabına bir kez giriş yapman yeterli.%1"
              + " Giriş yapınca abonelikler kendiliğinden gelir.").arg(neden)
            : qsTr("Aboneliklerini getirmek için Firefox gerekiyor.%1"
              + " Firefox ücretsiz, Mozilla'nın kendi sitesinden iner. Kurulunca YouTube'a bir kez giriş yaparsın,"
              + " abonelikler kendiliğinden gelir.").arg(neden)
        case "indiriliyor": return firefox.toplam
            ? qsTr("%1 / %2 MB").arg(Math.round(firefox.inen / 1048576)).arg(Math.round(firefox.toplam / 1048576)) : qsTr("Başlıyor…")
        case "kuruluyor": return firefox.windows ? qsTr("Windows izin sorarsa Evet'e bas.") : qsTr("Parolan sorulursa gir.")
        case "bos": return qsTr("Firefox'ta girdiğin YouTube hesabında abone olunan kanal görünmüyor. Aboneliklerin başka bir"
            + " hesaptaysa onunla gir; abonelikler kendiliğinden gelir.")
        case "bekliyor": if (firefox.kip === "yeniden") return qsTr("Firefox'ta açılan sayfada hesabını seç ya da yeniden"
            + " giriş yap. Giriş yapınca abonelikler kendiliğinden gelir; buraya dönmen gerekmez.")
            if (firefox.kip === "baska") return qsTr("Firefox'ta açılan sayfada aboneliklerinin olduğu hesabı seç ya da"
            + " onunla giriş yap. Giriş yapınca abonelikler kendiliğinden gelir; buraya dönmen gerekmez.")
            return firefox.yeniKuruldu
            ? qsTr("Firefox açıldı. “Hoş geldiniz” çıkarsa Devam et'e bas, sonra Google hesabınla giriş yap."
              + " Giriş yapınca abonelikler kendiliğinden gelir; buraya dönmen gerekmez.")
            : qsTr("Firefox açıldı. Orada Google hesabınla giriş yap."
              + " Giriş yapınca abonelikler kendiliğinden gelir; buraya dönmen gerekmez.")
        case "aliniyor": return qsTr("Abonelikler getiriliyor…")
        case "hata": return firefox.aciklama
        }
        return ""
    }

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
        Text { anchors.left: parent.left; text: p.baslik; color: Renk.yazi; font.pixelSize: 18; font.weight: Font.Medium }
        Text { width: parent.width; wrapMode: Text.Wrap; color: Renk.yaziSoluk; font.pixelSize: 14; lineHeight: 1.15
            text: p.metin }
        // İlerleme: inerken dolan çizgi; kurulurken ve beklerken gidip gelen parça (süresi belli değil).
        Rectangle {
            id: cizgi
            visible: p.durum === "indiriliyor" || p.durum === "kuruluyor" || p.durum === "bekliyor" || p.durum === "aliniyor"
            readonly property bool belli: p.durum === "indiriliyor" && firefox && firefox.toplam > 0
            width: parent.width; height: 4; radius: 2; color: Renk.yuzeyAcik; clip: true
            Rectangle {
                visible: cizgi.belli
                height: parent.height; radius: 2; color: Renk.mavi
                width: cizgi.belli ? parent.width * Math.min(1, firefox.inen / firefox.toplam) : 0
            }
            Rectangle {
                id: parca
                visible: !cizgi.belli
                height: parent.height; radius: 2; color: Renk.mavi; width: parent.width / 4
                NumberAnimation on x {
                    running: cizgi.visible && !cizgi.belli
                    from: -parca.width; to: cizgi.width; duration: 1400; loops: Animation.Infinite
                }
            }
        }
        Row {
            anchors.right: parent.right
            spacing: 8
            visible: !p.calisiyor
            Dugme { text: p.durum === "sor" ? qsTr("Hayır") : p.durum === "hata" || p.durum === "bos" ? qsTr("Kapat") : qsTr("Vazgeç")
                onClicked: { firefox.hayir(); p.close() } }
            Dugme { visible: p.durum === "hata" && firefox.tekrar === "kur"; text: qsTr("Firefox'un sitesi")
                onClicked: firefox.siteyiAc() }
            Dugme { visible: p.durum === "bekliyor"; text: qsTr("Firefox'u yeniden aç"); onClicked: firefox.firefoxuAc() }
            Dugme { visible: p.durum === "bos"; ana: true; text: qsTr("Başka hesapla gir"); onClicked: firefox.baskaHesapla() }
            Dugme { visible: p.durum === "sor" || p.durum === "hata"; ana: true
                text: p.durum === "hata" ? qsTr("Yeniden dene") : firefox && firefox.kurulu ? qsTr("Giriş yap") : qsTr("Kur")
                onClicked: p.durum === "hata" ? firefox.yenidenDene() : firefox.evet() }
        }
    }
}
