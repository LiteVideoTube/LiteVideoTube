import QtQuick

// Arama sonuçlarında bir video: küçük resim üstte, başlık ve bilgiler altta.
// Küçük resmin üstüne gelince önizleme oynamaz (eski bilgisayarı yormasın).
Item {
    id: k
    property var v
    signal sec()
    implicitHeight: resimKutu.height + 8 + yazilar.implicitHeight + 16

    // Sayfada bul (Ctrl+F) bu videoyu bulduysa bütün kart (resim ve yazı) mavi zeminle işaretlenir. Önceden yalnız
    // resmin kenarında ince çizgi vardı; kırmızı çerçeveli resimlerde seçilmiyordu, aranan söz de çoğu zaman başlığın
    // "…" ile kesilen yerindeydi (28 Ekim).
    Rectangle { anchors.fill: parent; anchors.margins: -6; anchors.bottomMargin: 0; radius: 14
        color: "#403ea6ff"; border.color: Renk.mavi; border.width: 3
        visible: !!k.v && pencere.bulunanId === k.v.id }

    Rectangle {
        id: resimKutu
        z: 1   // içindeki "Sonra izle" düğmesi kartın tıklama alanının üstünde kalsın
        // clip yok: PreserveAspectCrop resmi Qt kendisi kırpıyor, içindekiler kutudan taşmıyor. clip her kartı ayrı
        // çizdiriyordu (karede ~220 yerine ~120 çizim; abonelik sayfasını kaydırırken işlemci %38 → %32, 28 Ekim).
        // Öbür küçük resim kutuları da (OneriSatiri, ShortsKarti, geçmiş, listeler) aynı sebeple clip'siz.
        width: parent.width; height: width * 9 / 16; radius: 10; color: Renk.yuzey
        Image {
            anchors.fill: parent; fillMode: Image.PreserveAspectCrop
            source: k.v ? k.v.resim : ""; asynchronous: true; sourceSize.width: 320
        }
        IlerlemeCizgisi { videoId: k.v ? k.v.id : "" }
        // Abonelik sayfasında son bakıştan beri gelen video (abonelik.py, akis).
        Rectangle { visible: !!k.v && !!k.v.yeni; anchors { left: parent.left; top: parent.top; margins: 6 }
            width: yeniYazi.implicitWidth + 10; height: 20; radius: 4; color: Renk.maviDolgu
            Text { id: yeniYazi; anchors.centerIn: parent; text: qsTr("YENİ"); color: "black"; font.pixelSize: 11; font.bold: true } }
        SonraIzleDugmesi { v: k.v; goster: kartFare.hovered }
        // Sağ altta süre; canlı yayında kırmızı CANLI, başlamamış yayında YAKINDA.
        Rectangle {
            visible: !!k.v && !!(k.v.sure || k.v.canli || k.v.yakinda)
            anchors { right: parent.right; bottom: parent.bottom; margins: 6 }
            width: sureYazi.implicitWidth + 8; height: 20; radius: 4
            color: k.v && k.v.canli ? "#cc0000" : "#cc000000"
            Text { id: sureYazi; anchors.centerIn: parent; color: "white"; font.pixelSize: 12; font.bold: true
                text: k.v ? (k.v.canli ? qsTr("CANLI") : k.v.yakinda ? qsTr("YAKINDA") : k.v.sure) : "" }
        }
    }
    Column {
        id: yazilar
        z: 1   // kanal adının tıklama alanı kartınkinin üstünde kalsın
        anchors { left: parent.left; right: parent.right; top: resimKutu.bottom; topMargin: 8 }
        spacing: 4
        // Yazılar sürükleyince seçilir (SecimKatmani), tıklayınca kart gibi açar.
        Text { width: parent.width; text: k.v ? k.v.baslik : ""; color: Renk.yazi; font.pixelSize: 15; font.weight: Font.Medium
            wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
            SecimKatmani { tiklama: k.solTik } }
        Text { width: parent.width; text: k.v ? k.v.kanal : ""; color: Renk.yaziSoluk; font.pixelSize: 13; elide: Text.ElideRight
            // Kanal adına tıklayınca kanal sayfası (YouTube'daki gibi).
            font.underline: kanalSecim.ustunde && !!(k.v && k.v.kanal_id)
            SecimKatmani { id: kanalSecim; width: Math.min(parent.width, parent.contentWidth)
                x: parent.effectiveHorizontalAlignment === Text.AlignRight ? parent.width - width : 0   // sağa yaslı yazıda (Arapça)
                tiklama: k.v && k.v.kanal_id ? function(tuslar) { if (tuslar & Qt.ControlModifier) k.solTik(tuslar); else pencere.kanalAc(k.v.kanal_id, k.v.kanal) }
                                              : k.solTik } }
        Text { width: parent.width; color: Renk.yaziSoluk; font.pixelSize: 13; elide: Text.ElideRight
            text: k.v ? [k.v.izlenme, k.v.tarih].filter(function(x) { return x }).join(" • ") : ""
            SecimKatmani { tiklama: k.solTik } }
    }
    HoverHandler { id: kartFare }
    // Sol tık açar; orta tık ya da Ctrl+tık yeni sekmede (arkada), sağ tık menü (tarayıcı alışkanlığı).
    function solTik(tuslar) { if (tuslar & Qt.ControlModifier) pencere.videoYeniSekmede(k.v); else k.sec() }
    MouseArea {
        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        onClicked: function(m) {
            if (m.button === Qt.RightButton) pencere.kartMenusu(k.v)
            else if (m.button === Qt.MiddleButton) pencere.videoYeniSekmede(k.v)
            else k.solTik(m.modifiers)
        }
    }
}
