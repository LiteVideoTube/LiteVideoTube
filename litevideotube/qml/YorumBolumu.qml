import QtQuick
import QtQuick.Controls.Basic

// Video sayfasının yorumları (YouTube düzeninde). Sayfayla gelmez: kişi bölüme yaklaşınca istenir (baslat),
// aşağı indikçe devamı gelir (dahaFazla). Aşağı inmeyen için boşuna veri ve bellek harcanmaz; gelmesi
// 0,3-0,9 sn sürdüğü için (23 Ekim ölçümü) bölüme varınca beklemek hissedilmez.
// Yorum yazmak ve beğenmek hesap ister: tarayıcıda açılır (5. ilke).
Column {
    id: yb
    property string videoId
    property string ilkDevam      // video sayfasıyla gelen ilk partinin anahtarı
    property string mesaj         // "Yorumlar kapalı." gibi; anahtar yoksa
    property string sayi: ""
    property var siralar: []
    property string devam: ""
    property bool yukleniyor: false
    property bool istendi: false
    property string hata: ""
    property int istekNo: 0       // sıralama değişince eski isteğin cevabı listeye karışmasın
    property string sonAnahtar: "" // hata olursa "Yeniden dene" aynı partiyi ister
    readonly property alias liste: yorumlar
    signal zamanaGit(real saniye)
    spacing: 18

    ListModel { id: yorumlar }

    function sifirla() {
        yorumlar.clear(); sayi = ""; siralar = []; devam = ""; yukleniyor = false; istendi = false; hata = ""
        istekNo++
    }
    function baslat() {
        if (istendi || !ilkDevam) return
        istendi = true
        iste(ilkDevam)
    }
    function iste(anahtar) {
        yukleniyor = true; hata = ""; sonAnahtar = anahtar
        veri.yorumlar(videoId, anahtar, "ana:" + istekNo)
    }
    function dahaFazla() { if (istendi && devam && !yukleniyor && !hata) iste(devam) }
    function sirala(i) {
        if (!siralar[i] || siralar[i].secili || !siralar[i].devam) return
        var yeni = siralar.map(function(s, j) { return { ad: s.ad, devam: s.devam, secili: j === i } })
        var anahtar = yeni[i].devam
        yorumlar.clear(); devam = ""; istekNo++
        siralar = yeni
        iste(anahtar)
    }
    function yanitIste(yorumId, anahtar) { veri.yorumlar(videoId, anahtar, "yanit:" + yorumId) }
    // Yorumdaki bağlantılar (youtube.py, _yorum_metni): bu videonun bir anı, başka video, kanal, dış adres.
    function baglantiAc(adres) {
        if (adres.indexOf("t:") === 0) yb.zamanaGit(parseFloat(adres.slice(2)))
        else if (adres.indexOf("v:") === 0) pencere.videoAc(adres.split(":")[1])
        else if (adres.indexOf("c:") === 0) pencere.kanalAc(adres.slice(2), "")
        else if (/^https?:/.test(adres)) Qt.openUrlExternally(adres)
    }
    onVideoIdChanged: sifirla()

    Connections {
        target: veri
        function onYorumlarGeldi(vid, etiket, parti) {
            if (vid !== yb.videoId) return
            if (etiket.indexOf("yanit:") === 0) {
                var id = etiket.slice(6)
                for (var k = 0; k < satirlar.count; k++) {
                    var s = satirlar.itemAt(k)
                    if (s && s.yrm.id === id) { s.yanitGeldi(parti); break }
                }
                return
            }
            if (etiket !== "ana:" + yb.istekNo) return
            yb.yukleniyor = false
            if (parti.hata) { yb.hata = parti.hata; return }
            if (parti.sayi) yb.sayi = parti.sayi
            if (parti.siralar && parti.siralar.length && !yb.siralar.length) yb.siralar = parti.siralar
            for (var i = 0; i < parti.yorumlar.length; i++) yorumlar.append(parti.yorumlar[i])
            yb.devam = parti.devam || ""
        }
    }

    // Başlık: yorum sayısı, sıralama, yorum yazmak için tarayıcı.
    Row { anchors.left: parent.left;
        spacing: 24
        height: 36
        Text { text: yb.sayi || qsTr("Yorumlar"); color: Renk.yazi; font.pixelSize: 20; font.bold: true
            anchors.verticalCenter: parent.verticalCenter; SecimKatmani { } }
        Button {
            id: siraDugme
            visible: yb.siralar.length > 1
            anchors.verticalCenter: parent.verticalCenter
            onClicked: siraMenu.opened ? siraMenu.close() : siraMenu.open()
            contentItem: Row {
                spacing: 8
                Image { source: Renk.simge("sort"); width: 22; height: 22; sourceSize: Qt.size(44, 44); anchors.verticalCenter: parent.verticalCenter }
                Text { text: qsTr("Sırala"); color: Renk.yazi; font.pixelSize: 14; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter }
            }
            background: Rectangle { radius: 18; color: siraDugme.hovered ? Renk.yuzeyAcik : "transparent"; implicitHeight: 36 }
            MenuKutusu {
                id: siraMenu
                x: mirrored ? parent.width - width : 0   // sağdan sola dilde sağ kenarı düğmeninkiyle hizalı
                y: parent.height + 4
                contentItem: Column {
                    spacing: 2
                    Repeater {
                        model: yb.siralar
                        MenuSatiri { anchors.left: parent.left; width: 220; yazi: modelData.ad; secili: modelData.secili
                            onTiklandi: { siraMenu.close(); yb.sirala(index) } }
                    }
                }
            }
        }
    }
    // Yorum kutusunun yerinde: yazmak hesap ister, video tarayıcıda açılır.
    Rectangle {
        visible: yb.istendi && !yb.mesaj
        width: parent.width; height: 40; radius: 20; color: "transparent"; border.color: yazFare.containsMouse ? Renk.k("#717171", "#909090") : Renk.k("#3f3f3f", "#d0d0d0")
        Row {
            anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter }
            spacing: 8
            Text { text: qsTr("Yorum yaz…"); color: Renk.yaziSoluk; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
        }
        Image { source: Renk.simge("open_in_new"); width: 16; height: 16; sourceSize: Qt.size(32, 32); opacity: 0.7
            anchors { right: parent.right; rightMargin: 16; verticalCenter: parent.verticalCenter } }
        MouseArea { id: yazFare; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: Qt.openUrlExternally("https://www.youtube.com/watch?v=" + yb.videoId) }
    }
    Text {
        visible: !!yb.mesaj
        text: yb.mesaj
        color: Renk.yaziSoluk; font.pixelSize: 14
        SecimKatmani { }
    }
    Repeater {
        id: satirlar
        model: yorumlar
        YorumSatiri { width: yb.width; bolum: yb; yrm: model }
    }
    Row {
        visible: yb.yukleniyor
        spacing: 10
        BusyIndicator { width: 28; height: 28; running: yb.yukleniyor }
        Text { text: qsTr("Yorumlar geliyor…"); color: Renk.yaziSoluk; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
    }
    Text {
        visible: !!yb.hata
        text: qsTr("Yorumlar alınamadı (%1). <a href=\"x\">Yeniden dene</a>").arg(yb.hata)
        textFormat: Text.StyledText; linkColor: Renk.mavi
        color: Renk.yaziSoluk; font.pixelSize: 14
        onLinkActivated: yb.iste(yb.sonAnahtar)
    }
}
