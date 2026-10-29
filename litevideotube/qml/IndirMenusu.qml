import QtQuick
import QtQuick.Controls.Basic

// Video sayfasındaki "İndir" düğmesinin menüsü (22-23 Ekim düzeninden): video boyutları (her boyutta
// önce H.264), yalnız ses (m4a, MP3), metin dökümü; altında bu videonun indirmeleri. Dosyalar
// İndirilenler klasörüne iner; indirmeyi bilgisayarda yt-dlp yapar, sırayla.
MenuKutusu {
    id: m
    property var v: ({})
    property var oynatici
    y: parent.height + 6
    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

    // Boyutlar oynatıcının kalite listesinden: her yükseklik bir kez; yalnız büyütülmüş kopyası olan
    // boyut ve AV1 açıkça söylenir.
    readonly property var boyutlar: {
        var g = {}, sira = []
        var liste = m.oynatici ? m.oynatici.kaliteler : []
        for (var i = 0; i < liste.length; i++) {
            var k = liste[i], h = parseInt(k.ad)
            if (!(h > 0)) continue
            if (!(h in g)) { g[h] = { h: h, bicim: k.bicim, buyutulmus: k.buyutulmus }; sira.push(h) }
            else if (g[h].buyutulmus && !k.buyutulmus) g[h] = { h: h, bicim: k.bicim, buyutulmus: false }
        }
        return sira.map(function(h) { return g[h] })
    }
    readonly property var buVideo: { var l = indirici.isler; return l.filter(function(x) { return x.vid === m.v.id }) }
    readonly property bool altyaziVar: m.oynatici ? m.oynatici.altyaziElle.length + m.oynatici.altyaziOtomatik.length > 0 : false
    contentItem: Column {
        spacing: 2
        MenuBasligi { anchors.left: parent.left; text: qsTr("Video") }
        Text { anchors.left: parent.left; visible: m.boyutlar.length === 0; leftPadding: 32; color: Renk.yaziSoluk; font.pixelSize: 13; text: qsTr("Boyutlar yükleniyor…") }
        Repeater {
            model: m.boyutlar
            MenuSatiri { anchors.left: parent.left;
                width: 320
                yazi: modelData.h + "p"
                ipucu: modelData.buyutulmus ? qsTr("YouTube'un büyüttüğü kopya")
                       : modelData.bicim === "AV1" ? qsTr("AV1: eski bilgisayarda takılabilir")
                       : modelData.bicim === "VP9" ? "VP9" : ""
                isaret: "↓"
                onTiklandi: indirici.indir(m.v.id, m.v.baslik || m.v.id, modelData.h + "")
            }
        }
        MenuBasligi { anchors.left: parent.left; text: qsTr("Yalnız ses") }
        MenuSatiri { anchors.left: parent.left; width: 320; yazi: qsTr("Ses (m4a)"); isaret: "↓"; onTiklandi: indirici.indir(m.v.id, m.v.baslik || m.v.id, "ses") }
        MenuSatiri { anchors.left: parent.left; width: 320; yazi: qsTr("Ses (MP3)"); ipucu: qsTr("eski çalarlar için"); isaret: "↓"; onTiklandi: indirici.indir(m.v.id, m.v.baslik || m.v.id, "mp3") }
        MenuBasligi { anchors.left: parent.left; text: qsTr("Yazı") }
        MenuSatiri { anchors.left: parent.left; width: 320; yazi: qsTr("Metin dökümü (.txt)"); ipucu: m.altyaziVar ? qsTr("altyazıdan") : qsTr("altyazı yok"); isaret: "↓"
            tiklanir: m.altyaziVar; opacity: m.altyaziVar ? 1 : 0.5
            onTiklandi: { m.oynatici.dokumKaydet(); m.close() } }
        Rectangle { anchors.left: parent.left; visible: m.buVideo.length > 0; width: 320; height: 1; color: Renk.menuCizgi }
        Repeater {
            model: m.buVideo
            IndirmeSatiri { anchors.left: parent.left; is_: modelData }
        }
        MenuCizgisi { anchors.left: parent.left; width: 320 }
        MenuSatiri { anchors.left: parent.left; width: 320; yazi: qsTr("İndirilenler klasörünü aç"); isaret: ""; onTiklandi: { indirici.klasoruAc(); m.close() } }
    }
}
