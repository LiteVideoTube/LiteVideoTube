import QtQuick
import QtQuick.Controls.Basic

// Bir yorum ya da yanıt (YouTube düzeninde): solda yuvarlak resim, sağda ad, zaman, metin, beğeni ve yanıtlar.
// Yüzlerce yorum yüklenebildiği için satır hafif tutulur: nadiren gereken parçalar (sabitlenmiş notu, kalp,
// "Devamını oku", yanıtlar) yalnız gerektiğinde kurulur (23 Ekim ölçümü: 140 yorum ~40 MB'tı).
Item {
    id: ys
    property var yrm: ({})
    property bool yanit: false
    property var bolum          // YorumBolumu: yanıt istemek ve bağlantıları açmak için
    readonly property int resimBoy: yanit ? 24 : 40
    implicitHeight: Math.max(resimBoy, govde.implicitHeight)
    // Bölüm yanıtları buraya iletir (etiket "yanit:<id>").
    function yanitGeldi(parti) { if (yanitlarYeri.item) yanitlarYeri.item.geldi(parti) }

    // Resmin altında gri daire: resim gelene kadar ya da hiç yoksa görünür.
    Rectangle { anchors.left: parent.left; width: ys.resimBoy; height: ys.resimBoy; radius: width / 2; color: Renk.k("#4a4a4a", "#d9d9d9") }
    Image {
        anchors.left: parent.left
        width: ys.resimBoy; height: ys.resimBoy
        // Sunucu yuvarlak kesilmiş resim veriyor (youtube.py, "=s48-cc").
        source: ys.yrm.resim || ""; sourceSize: Qt.size(48, 48); asynchronous: true
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; enabled: !!ys.yrm.yazar_id
            onClicked: pencere.kanalAc(ys.yrm.yazar_id, ys.yrm.yazar) }
    }
    Column {
        id: govde
        anchors { left: parent.left; leftMargin: ys.resimBoy + (ys.yanit ? 10 : 14); right: parent.right }
        spacing: 4
        // Sabitlenmiş yorum (YouTube'daki gibi üstte küçük not).
        Loader { anchors.left: parent.left;
            active: !!ys.yrm.sabit
            visible: active
            sourceComponent: Row {
                spacing: 4
                Image { source: Renk.simge("push_pin"); width: 14; height: 14; sourceSize: Qt.size(28, 28); opacity: 0.7
                    anchors.verticalCenter: parent.verticalCenter }
                Text { text: ys.yrm.sabit; color: Renk.yaziSoluk; font.pixelSize: 12; SecimKatmani { } }
            }
        }
        Row { anchors.left: parent.left;
            spacing: 6
            // Kanal sahibinin yorumu gri bir zeminle ayrılır (YouTube'daki gibi).
            Rectangle {
                width: ad.implicitWidth + (ys.yrm.sahip ? 12 : 0); height: ad.implicitHeight + (ys.yrm.sahip ? 4 : 0)
                radius: height / 2; color: ys.yrm.sahip ? Renk.k("#555555", "#e5e5e5") : "transparent"
                anchors.verticalCenter: parent.verticalCenter
                Text { id: ad; anchors.centerIn: parent; text: ys.yrm.yazar || ""; color: Renk.yazi
                    font.pixelSize: 13; font.weight: Font.Medium; font.underline: adSecim.ustunde && !!ys.yrm.yazar_id
                    // Sürükleyince seçilir, tıklayınca yazarın kanalı (SecimKatmani).
                    SecimKatmani { id: adSecim
                        tiklama: ys.yrm.yazar_id ? function(tuslar) { pencere.kanalAc(ys.yrm.yazar_id, ys.yrm.yazar) } : null } }
            }
            Text { text: (ys.yrm.dogrulanmis ? "✓  " : "") + (ys.yrm.tarih || ""); color: Renk.yaziSoluk; font.pixelSize: 12
                anchors.verticalCenter: parent.verticalCenter; SecimKatmani { } }
        }
        // Seçilip kopyalanabilir (SecilirYazi). Bağlantı rengi HTML'de verilir: TextEdit'in linkColor'u yok.
        SecilirYazi {
            id: metin
            property bool acikMi: false
            width: parent.width
            text: (ys.yrm.metin || "").replace(/<a /g, '<a style="color:' + Renk.mavi + '; text-decoration:none" ')
            textFormat: TextEdit.RichText
            color: Renk.yazi
            font.pixelSize: 14
            // Uzun yorum dört satırda kesilir (YouTube'daki gibi), "Devamını oku" ile açılır.
            satirSiniri: 4; acik: acikMi
            onAcilmali: acikMi = true
            onLinkActivated: function(adres) { ys.bolum.baglantiAc(adres) }
        }
        Loader { anchors.left: parent.left;
            active: metin.kesik || metin.acikMi
            visible: active
            sourceComponent: Text {
                text: metin.acikMi ? qsTr("Daha az göster") : qsTr("Devamını oku")
                color: Renk.yaziSoluk; font.pixelSize: 13; font.weight: Font.Medium
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: metin.acikMi = !metin.acikMi }
            }
        }
        Row { anchors.left: parent.left;
            spacing: 14
            height: 24
            Row {
                spacing: 6; anchors.verticalCenter: parent.verticalCenter
                Image { source: Renk.simge("thumb_up"); width: 16; height: 16; sourceSize: Qt.size(32, 32); opacity: 0.8
                    anchors.verticalCenter: parent.verticalCenter }
                Text { text: ys.yrm.begeni && ys.yrm.begeni !== "0" ? ys.yrm.begeni : ""; color: Renk.yaziSoluk; font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter }
            }
            // Kanal sahibi kalp bıraktıysa (YouTube'daki gibi kırmızı kalp; ipucunda kimin bıraktığı).
            Loader {
                active: !!ys.yrm.kalp
                anchors.verticalCenter: parent.verticalCenter
                sourceComponent: Image {
                    source: "../simgeler/favorite_kirmizi.svg"; width: 16; height: 16; sourceSize: Qt.size(32, 32)
                    HoverHandler { id: kalpFare }
                    ToolTip.visible: kalpFare.hovered; ToolTip.text: ys.yrm.kalp_ipucu || qsTr("Kanal sahibi kalp bıraktı"); ToolTip.delay: 400
                }
            }
        }
        // "4 yanıt": yanıtlar ilk açılışta istenir; kapatıp açmak yeniden istemez.
        Loader {
            id: yanitlarYeri
            active: !ys.yanit && !!ys.yrm.yanit_devam
            visible: active
            width: parent.width
            sourceComponent: Yanitlar { }
        }
    }

    component Yanitlar: Column {
        id: yc
        property bool acik: false
        property bool yukleniyor: false
        property string hata: ""
        property string devam: ""
        spacing: 14
        function iste(anahtar) { yukleniyor = true; hata = ""; ys.bolum.yanitIste(ys.yrm.id, anahtar) }
        function geldi(parti) {
            yukleniyor = false
            if (parti.hata) { hata = parti.hata; return }
            for (var i = 0; i < parti.yorumlar.length; i++) liste.append(parti.yorumlar[i])
            devam = parti.devam || ""
        }
        ListModel { id: liste }
        Text { anchors.left: parent.left;
            // Sayı YouTube'dan yazı olarak geliyor: düz sayıysa dilin tekil ve çoğul biçimiyle ("1 reply", "3 replies").
            text: (yc.acik ? "▴ " : "▾ ") + (!ys.yrm.yanit_sayisi ? qsTr("Yanıtlar")
                  : /^\d+$/.test(ys.yrm.yanit_sayisi) ? qsTr("%n yanıt", "", parseInt(ys.yrm.yanit_sayisi))
                  : qsTr("%1 yanıt").arg(ys.yrm.yanit_sayisi))
            color: Renk.mavi; font.pixelSize: 14; font.weight: Font.Medium
            MouseArea {
                anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor
                onClicked: {
                    yc.acik = !yc.acik
                    if (yc.acik && liste.count === 0 && !yc.yukleniyor) yc.iste(ys.yrm.yanit_devam)
                }
            }
        }
        // Yanıt satırı bu dosyanın kendisi; kendini doğrudan içeremediği için Loader ile.
        Repeater {
            model: yc.acik ? liste : null
            Loader {
                width: yc.width
                height: item ? item.implicitHeight : 0
                Component.onCompleted: setSource("YorumSatiri.qml", { yanit: true, bolum: ys.bolum, yrm: model })
            }
        }
        Text { anchors.left: parent.left; visible: yc.acik && yc.yukleniyor; text: qsTr("Yanıtlar geliyor…"); color: Renk.yaziSoluk; font.pixelSize: 13 }
        Text { anchors.left: parent.left;
            visible: yc.acik && !yc.yukleniyor && (yc.devam !== "" || yc.hata !== "")
            text: yc.hata ? qsTr("Yanıtlar alınamadı. Yeniden dene") : qsTr("↳ Daha fazla yanıt göster")
            color: Renk.mavi; font.pixelSize: 14; font.weight: Font.Medium
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onClicked: yc.iste(yc.hata ? (yc.devam || ys.yrm.yanit_devam) : yc.devam) }
        }
    }
}
