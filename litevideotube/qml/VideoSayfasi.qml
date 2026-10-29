import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// YouTube düzeni: solda video, altında başlık, kanal ve açıklama; sağda öneriler.
Item {
    id: vs
    readonly property Flickable kaydirmaAlani: kaydirma   // yakınlıkla yeniden açılınca kaydırma yeri (Ana.qml)
    property var bilgi: ({})
    // Öneriler ListModel'de: yeni parti gelince yalnız yeniler eklenir (dizi modelinde her partide bütün satırlar
    // resimleriyle baştan kuruluyordu; 23 Ekim, tur 3).
    ListModel { id: oneriModeli }
    readonly property int oneriSayisi: oneriModeli.count
    function onerileriKoy(liste) { oneriModeli.clear(); onerileriEkle(liste) }
    // ListModel'in alanları ilk eklenen öğeden belirleniyor: eksik alan (kanalı bilinmeyen öneri) sonrakilerde de
    // kayboluyordu; her alan hep yazılır.
    function onerileriEkle(liste) {
        for (var i = 0; i < liste.length; i++) {
            var v = liste[i]
            oneriModeli.append({ id: v.id || "", baslik: v.baslik || "", kanal: v.kanal || "", kanal_id: v.kanal_id || "",
                                 sure: v.sure || "", izlenme: v.izlenme || "", tarih: v.tarih || "", canli: !!v.canli,
                                 resim: v.resim || "" })
        }
    }
    // Satıra modelin canlı öğesi değil düz bir kopya verilir: video açılınca liste boşalıyor, öğe geçersiz kalırdı.
    function kopya(m) {
        return { id: m.id, baslik: m.baslik, kanal: m.kanal, kanal_id: m.kanal_id, sure: m.sure, izlenme: m.izlenme,
                 tarih: m.tarih, canli: m.canli, resim: m.resim }
    }
    property bool oneriDevamVar: false
    property bool devamIstendi: false
    // "normal": video solda, öneriler yanında; "sinema": video sayfa genişliğinde, altında iki sütun.
    property string kip: "normal"
    // "yorum" (4. ilke: yorumlar için izleyenler): video sağ sütunun üstünde, solda başlık, açıklama ve geniş
    // yorumlar; öneriler videonun altında. Dar pencerede (sağ sütun yokken) normal düzen.
    readonly property string duzen: kip === "yorum" && width < 1000 ? "normal" : kip
    property real videoOrani: 0   // oynayan videonun en/boy oranı (0: bilinmiyor, 16:9 sayılır)
    property int elleBoy: 0     // kullanıcının videoya köşesinden çekerek verdiği genişlik (Ana.qml, gorunum.yanBoy)
    // Videonun sayfadaki yeri (yer tutucu); oynatıcı bunun üstüne yerleşir ya da aşağı kaydırınca yana geçer.
    readonly property Item videoYeri: duzen === "sinema" ? sinemaYeri : duzen === "yorum" ? yorumYeri : normalYeri
    readonly property alias sagSutun: sag
    readonly property alias solSutun: sol
    readonly property alias kaydirma: kaydirma
    // Video yana geçince yer tutucuda boş siyah alan kalmasın diye ufak bir not (Ana.qml verir).
    property bool videoYanda: false
    property bool videoSolda: false
    // Aşağı kaydırınca "en büyük" video: video önerilerin sütunundan geniş olunca, yer tutucunun
    // altındaki yazılar (başlık, açıklama, yorumlar) videonun altında kalmasın diye o kadar daralır (Ana.qml verir;
    // video yerindeyken 0). Yer tutucu daralmaz: değişen her şey onun altında, sayfa okunan yerden kaymaz.
    property int yanVideoEn: 0
    readonly property int yaziEn: sol.width - (yanVideoEn > sagGenislik && sagGenislik > 0 ? yanVideoEn - sagGenislik : 0)
    // Fare öneriler sütununun üstünde mi (kişi önerilere bakıyor; Ana.qml satır hizalaması için).
    readonly property bool sagUstunde: sagFare.hovered
    // Bir liste oynuyorsa (Ana.qml): {ad, videolar, sira}; yoksa null.
    property var calanListe: null
    property var oynatici   // indirme menüsü kaliteleri ve altyazıları buradan okur
    signal listeSec(int i)
    signal listeKapat()
    signal sec(var v)
    signal dahaFazla()
    signal yerDegisti()
    function basaDon() { kaydirma.contentY = 0 }
    readonly property alias yorumlar: yorumBolumu
    // Yorumlar kişi bölüme yaklaşınca istenir, sonu görünmeye yaklaşınca devamı (YorumBolumu.qml).
    onVisibleChanged: if (visible) Qt.callLater(yorumlariDenetle)
    function yorumlariDenetle() {
        if (!vs.visible) return   // Shorts görünümündeyken video sayfası gizli: yorum istenmez
        var y = yorumBolumu.mapToItem(kaydirma.contentItem, 0, 0).y
        var alt = kaydirma.contentY + kaydirma.height
        if (y < alt + 400) yorumBolumu.baslat()
        if (y + yorumBolumu.height < alt + 800) yorumBolumu.dahaFazla()
    }

    // Sağ sütun 402 px (öneri satırı 160 px resim + yazı); yorum düzeninde videonun boyu: varsayılan sayfanın
    // %40'ı, elle verilmişse o (en çok %60, yorumlara yer kalsın).
    readonly property int sagGenislik: width < 1000 ? 0 : duzen !== "yorum" ? 402
        : Math.round(Math.max(402, Math.min(elleBoy || width * 0.4, width * 0.6)))
    readonly property int bosluk: 24
    // Sağdan sola kipte (LayoutMirroring, Ana.qml) öneriler sütunu soldadır, ana sütun sağda; x'ler elle yerleştirildiği
    // için burada çevrilir.
    readonly property bool ters: LayoutMirroring.enabled
    readonly property int solX: ters && sagGenislik > 0 ? bosluk + sagGenislik + bosluk : bosluk
    readonly property int sagX: ters ? bosluk : kaydirma.width - bosluk - sagGenislik
    // Öneri satırları 90 px, aralarında 12 px: 102 pikselde bir (OneriSatiri.qml).
    readonly property int satirAdimi: 102

    Flickable {
        id: kaydirma
        objectName: "videoKaydirma"
        TekerlekHizi { hedef: kaydirma }
        anchors.fill: parent
        contentWidth: width
        contentHeight: sinemaYeri.height + Math.max(sol.implicitHeight, sag.y - sinemaYeri.height + sag.implicitHeight) + 48
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        onContentYChanged: {
            vs.yerDegisti()
            vs.yorumlariDenetle()
            // Önerilerin devamı öneri sütununun sonu yaklaşınca gelir (sayfanın sonu değil: yorumlar uzayınca
            // sütun yarıda kalıyordu). Dar pencerede öneriler yorumların üstünde: devamları kendiliğinden gelmez,
            // yoksa yorumlara hiç inilemezdi (ikisi de aşağı indikçe uzuyor).
            if (vs.sagGenislik > 0 && vs.oneriDevamVar && !vs.devamIstendi && sag.y + sag.height < contentY + height + 800) {
                vs.devamIstendi = true; vs.dahaFazla()
            }
        }
        onWidthChanged: Qt.callLater(vs.yerDegisti)

        // Sinema: video sayfanın bütün genişliğinde, kenardan kenara (YouTube'un sinema kipi gibi).
        Rectangle {
            id: sinemaYeri
            width: kaydirma.width
            // Kutu videonun şekline uyar (29 Ekim): 4:3 klip daha büyük, geniş film daha az siyah şeritle; en çok
            // sayfanın %85'i (oynatıcı çubuğu ekranda kalsın).
            height: vs.duzen === "sinema" ? Math.round(Math.min(width / (vs.videoOrani > 0 ? vs.videoOrani : 16 / 9), vs.height * 0.85)) : 0
            visible: height > 0
            color: "black"
            onHeightChanged: Qt.callLater(vs.yerDegisti)
            onWidthChanged: Qt.callLater(vs.yerDegisti)
            YanNotu { anchors.fill: parent; visible: vs.videoYanda && vs.duzen === "sinema" }
        }
        Column {
            id: sol
            x: vs.solX; y: sinemaYeri.height + vs.bosluk
            width: kaydirma.width - 2 * vs.bosluk - (vs.sagGenislik ? vs.sagGenislik + vs.bosluk : 0)
            spacing: 12
            Rectangle {
                id: normalYeri
                width: parent.width
                height: vs.duzen !== "normal" ? 0 : Math.round(Math.min(width * 9 / 16, vs.height * 0.75))
                visible: height > 0
                color: "black"
                onHeightChanged: Qt.callLater(vs.yerDegisti)
                onWidthChanged: Qt.callLater(vs.yerDegisti)
                YanNotu { anchors.fill: parent; visible: vs.videoYanda && vs.duzen === "normal" }
            }
            SecilirYazi { anchors.left: parent.left;
                width: vs.yaziEn
                text: vs.bilgi.baslik || ""; textFormat: TextEdit.PlainText
                color: Renk.yazi; font.pixelSize: 20; font.bold: true
            }
            // Kanal (adı, abone sayısı, "Abone ol" ve zil) solda, düğmeler sağda; sığmazsa düğmeler alt satıra iner
            // (YouTube'daki gibi; video yandayken yazı sütunu dar).
            GridLayout { anchors.left: parent.left;
                id: kanalSatiri
                width: vs.yaziEn; columnSpacing: 12; rowSpacing: 10
                readonly property bool genis: kanalGrubu.implicitWidth + dugmeGrubu.implicitWidth + 24 <= width
                columns: genis ? 3 : 1
                Row {
                    id: kanalGrubu
                    spacing: 16
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { anchors.left: parent.left; text: vs.bilgi.kanal || ""; color: Renk.yazi; font.pixelSize: 16; font.weight: Font.Medium
                            font.underline: kanalSecim.ustunde && !!vs.bilgi.kanal_id
                            SecimKatmani { id: kanalSecim
                                tiklama: vs.bilgi.kanal_id ? function(tuslar) { pencere.kanalAc(vs.bilgi.kanal_id, vs.bilgi.kanal) } : null } }
                        Text { anchors.left: parent.left; text: vs.bilgi.abone || ""; color: Renk.yaziSoluk; font.pixelSize: 12; SecimKatmani { } }
                    }
                    AboneDugmeleri { anchors.verticalCenter: parent.verticalCenter; kanalId: vs.bilgi.kanal_id || ""; kanalAd: vs.bilgi.kanal || "" }
                }
                Item { visible: kanalSatiri.genis; Layout.fillWidth: true }
                Row {
                    id: dugmeGrubu
                    spacing: 12
                    // İndirme programın içinde (5. ilke: YouTube'un yapmadığı yerde fark).
                    Button {
                        id: indirDugme
                        text: indirici.isler.some(function(x) { return x.vid === vs.bilgi.id && x.suruyor }) ? qsTr("İndiriliyor…") : qsTr("İndir")
                        enabled: !!vs.bilgi.id && vs.bilgi.id.indexOf("://") < 0
                        onClicked: indirMenu.opened ? indirMenu.close() : indirMenu.open()
                        contentItem: Row {
                            spacing: 6
                            Image { source: Renk.simge("download"); width: 20; height: 20; sourceSize: Qt.size(40, 40); anchors.verticalCenter: parent.verticalCenter }
                            Text { text: indirDugme.text; color: Renk.yazi; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                        }
                        background: Rectangle { radius: 18; color: indirDugme.hovered ? Renk.yuzeyAcik : Renk.yuzey; implicitHeight: 36 }
                        IndirMenusu { id: indirMenu; v: vs.bilgi; oynatici: vs.oynatici }
                    }
                    FavoriDugmesi { v: vs.bilgi }
                    // Sonra izle ve listeler: programın kendi listeleri.
                    Button {
                        id: kaydet
                        text: qsTr("Kaydet")
                        enabled: !!vs.bilgi.id && vs.bilgi.id.indexOf("://") < 0
                        onClicked: kaydetMenu.opened ? kaydetMenu.close() : kaydetMenu.open()
                        contentItem: Row {
                            spacing: 6
                            Image { source: Renk.simge("playlist_add"); width: 20; height: 20; sourceSize: Qt.size(40, 40); anchors.verticalCenter: parent.verticalCenter }
                            Text { text: kaydet.text; color: Renk.yazi; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                        }
                        background: Rectangle { radius: 18; color: kaydet.hovered ? Renk.yuzeyAcik : Renk.yuzey; implicitHeight: 36 }
                        KaydetMenusu { id: kaydetMenu; v: vs.bilgi }
                    }
                    // Beğenmek ve yorum yazmak hesap ister: video kullanıcının normal tarayıcısında açılır (5. ilke).
                    Button {
                        id: tarayici
                        text: qsTr("YouTube'da aç")
                        onClicked: Qt.openUrlExternally("https://www.youtube.com/watch?v=" + (vs.bilgi.id || ""))
                        contentItem: Row {
                            spacing: 6
                            Image { source: Renk.simge("thumb_up"); width: 18; height: 18; sourceSize: Qt.size(36, 36); anchors.verticalCenter: parent.verticalCenter }
                            Text { text: tarayici.text; color: Renk.yazi; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                            Image { source: Renk.simge("open_in_new"); width: 16; height: 16; sourceSize: Qt.size(32, 32); anchors.verticalCenter: parent.verticalCenter }
                        }
                        background: Rectangle { radius: 18; color: tarayici.hovered ? Renk.yuzeyAcik : Renk.yuzey; implicitHeight: 36 }
                    }
                }
            }
            Rectangle { anchors.left: parent.left;
                width: vs.yaziEn; radius: 12; color: Renk.yuzey
                height: aciklama.implicitHeight + 24
                Column {
                    id: aciklama
                    anchors.left: parent.left; anchors.leftMargin: 12; y: 12; width: parent.width - 24; spacing: 6
                    property bool acik: false
                    Text { anchors.left: parent.left; color: Renk.yazi; font.pixelSize: 14; font.weight: Font.Medium
                        text: [vs.bilgi.izlenme, vs.bilgi.tarih].filter(function(x) { return x }).join("   ")
                        SecimKatmani { } }
                    SecilirYazi {
                        width: parent.width; color: Renk.yazi; font.pixelSize: 14
                        text: vs.bilgi.aciklama || ""; textFormat: TextEdit.PlainText
                        satirSiniri: 3; acik: aciklama.acik
                        onAcilmali: aciklama.acik = true   // sayfada bul açıklamanın gizli kısmında buldu
                    }
                    Text { color: Renk.yaziSoluk; font.pixelSize: 14; font.weight: Font.Medium
                        text: aciklama.acik ? qsTr("Daha az göster") : qsTr("…devamı")
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: aciklama.acik = !aciklama.acik } }
                }
            }
            // Dar pencerede liste ve öneriler videonun altına iner.
            ListePaneli {
                visible: vs.sagGenislik === 0 && vs.calanListe !== null
                width: parent.width
                ad: vs.calanListe ? vs.calanListe.ad : ""; videolar: vs.calanListe ? vs.calanListe.videolar : []
                sira: vs.calanListe ? vs.calanListe.sira : -1
                onSec: function(i) { vs.listeSec(i) }
                onKapat: vs.listeKapat()
            }
            Column {
                visible: vs.sagGenislik === 0
                width: parent.width; spacing: 12
                Repeater {
                    model: vs.sagGenislik === 0 ? oneriModeli : null
                    OneriSatiri { width: parent.width; v: vs.kopya(model); onSec: vs.sec(v) }
                }
                Text {
                    visible: vs.oneriDevamVar && !vs.devamIstendi && vs.oneriSayisi > 0
                    text: qsTr("Daha fazla öneri"); color: Renk.mavi; font.pixelSize: 14; font.weight: Font.Medium
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: { vs.devamIstendi = true; vs.dahaFazla() } }
                }
            }
            Item { width: 1; height: 12 }
            YorumBolumu { anchors.left: parent.left;
                id: yorumBolumu
                width: vs.yaziEn
                videoId: vs.bilgi.id || ""
                ilkDevam: vs.bilgi.yorum_devam || ""
                mesaj: vs.bilgi.yorum_mesaji || ""
                onIlkDevamChanged: Qt.callLater(vs.yorumlariDenetle)
                // Yorumdaki "6:23" videonun o anına götürür; video yanda oynuyorsa sayfa yerinde kalır.
                onZamanaGit: function(sn) { if (vs.oynatici) vs.oynatici.git(sn) }
            }
        }
        // Yorum düzeninde videonun yeri: sağ sütunun üstü.
        Rectangle {
            id: yorumYeri
            x: vs.sagX; y: vs.bosluk
            width: vs.sagGenislik
            height: vs.duzen === "yorum" ? Math.round(width * 9 / 16) : 0
            visible: height > 0
            color: "black"
            onHeightChanged: Qt.callLater(vs.yerDegisti)
            onWidthChanged: Qt.callLater(vs.yerDegisti)
            onXChanged: Qt.callLater(vs.yerDegisti)
            YanNotu { anchors.fill: parent; visible: vs.videoYanda && vs.duzen === "yorum" }
        }
        // Liste oynarken önerilerin üstünde listenin kutusu (öneri satırlarının hizası bozulmasın diye ayrı).
        ListePaneli {
            id: listeKutusu
            visible: vs.sagGenislik > 0 && vs.calanListe !== null
            x: vs.sagX; y: sinemaYeri.height + vs.bosluk + (yorumYeri.visible ? yorumYeri.height + 16 : 0)
            width: vs.sagGenislik
            ad: vs.calanListe ? vs.calanListe.ad : ""; videolar: vs.calanListe ? vs.calanListe.videolar : []
            sira: vs.calanListe ? vs.calanListe.sira : -1
            onSec: function(i) { vs.listeSec(i) }
            onKapat: vs.listeKapat()
            onHeightChanged: Qt.callLater(vs.yerDegisti)
        }
        Column {
            id: sag
            visible: vs.sagGenislik > 0
            x: vs.sagX
            y: sinemaYeri.height + vs.bosluk + (yorumYeri.visible ? yorumYeri.height + 16 : 0)
               + (listeKutusu.visible ? listeKutusu.height + 16 : 0)
            width: vs.sagGenislik
            spacing: 12
            HoverHandler { id: sagFare }
            Repeater {
                model: vs.sagGenislik > 0 ? oneriModeli : null
                OneriSatiri { width: sag.width; v: vs.kopya(model); onSec: vs.sec(v) }
            }
        }
    }

    // Yer tutucuda, video yanda oynarken: siyah boşluk yerine nerede olduğunu söyleyen not.
    component YanNotu: Item {
        Text {
            anchors.centerIn: parent
            text: vs.videoSolda ? qsTr("Video sol üstte oynuyor") : qsTr("Video sağ üstte oynuyor")
            color: Renk.videoSoluk; font.pixelSize: 14
        }
    }
}
