import QtQuick
import QtQuick.Window

// Video sayfasının sağındaki öneri satırı: sabit 90 px yükseklik, başlık en çok iki satır (22 Ekim).
// Yazıların satır yüksekliği piksel olarak sabit (22, 17, 17): Arapça ve Tayca yazı tiplerinin satırı Latin
// harflerinden uzun, iki satırlık başlıkta izlenme satırı bir sonraki önerinin üstüne biniyordu (29 Ekim).
// Sayılar Latin harfli yazının kendi yüksekliği; Türkçede görünüş değişmedi.
Item {
    id: o
    property var v
    signal sec()
    height: 90

    Rectangle {
        id: resimKutu
        anchors.left: parent.left   // sağdan sola kipte sağa geçsin (LayoutMirroring)
        z: 1   // içindeki "Sonra izle" düğmesi kartın tıklama alanının üstünde kalsın
        width: 160; height: 90; radius: 8; color: Renk.yuzey
        Image {
            anchors.fill: parent; fillMode: Image.PreserveAspectCrop
            source: o.v ? o.v.resim : ""; asynchronous: true
            // Gösterildiği boya yakın tutulur: sayfa aşağı indikçe yüzlerce öneri birikiyor, 320 piksellik resim
            // her birinde dört kat bellek tutuyordu (23 Ekim, tur 3). Ara boyda değil, temiz bölümde (Renk.resimBoyu).
            sourceSize.width: Renk.resimBoyu(160 * Screen.devicePixelRatio)
        }
        IlerlemeCizgisi { videoId: o.v ? o.v.id : "" }
        SonraIzleDugmesi { v: o.v; goster: kartFare.hovered }
        Rectangle {
            visible: o.v && (o.v.sure || o.v.canli)
            anchors { right: parent.right; bottom: parent.bottom; margins: 4 }
            width: sy.implicitWidth + 6; height: 18; radius: 4
            color: o.v && o.v.canli ? "#cc0000" : "#cc000000"
            Text { id: sy; anchors.centerIn: parent; color: "white"; font.pixelSize: 11; font.bold: true
                text: o.v ? (o.v.canli ? qsTr("CANLI") : o.v.sure) : "" }
        }
    }
    Column {
        anchors { left: resimKutu.right; leftMargin: 8; right: parent.right; top: parent.top }
        z: 1   // kanal adının tıklama alanı kartınkinin üstünde kalsın
        spacing: 2
        // Yazılar sürükleyince seçilir (SecimKatmani), tıklayınca kart gibi açar.
        Text { width: parent.width; text: o.v ? o.v.baslik : ""; color: Renk.yazi; font.pixelSize: 14; font.weight: Font.Medium
            wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight; lineHeightMode: Text.FixedHeight; lineHeight: 22
            SecimKatmani { tiklama: o.solTik } }
        Text { width: parent.width; text: o.v ? o.v.kanal : ""; color: Renk.yaziSoluk; font.pixelSize: 12; elide: Text.ElideRight
            lineHeightMode: Text.FixedHeight; lineHeight: 17
            // Kanal adına tıklayınca kanal sayfası (YouTube'daki gibi).
            font.underline: kanalSecim.ustunde && !!(o.v && o.v.kanal_id)
            SecimKatmani { id: kanalSecim; width: Math.min(parent.width, parent.contentWidth)
                x: parent.effectiveHorizontalAlignment === Text.AlignRight ? parent.width - width : 0   // sağa yaslı yazıda (Arapça)
                tiklama: o.v && o.v.kanal_id ? function(tuslar) { if (tuslar & Qt.ControlModifier) o.solTik(tuslar); else pencere.kanalAc(o.v.kanal_id, o.v.kanal) }
                                              : o.solTik } }
        Text { width: parent.width; color: Renk.yaziSoluk; font.pixelSize: 12; elide: Text.ElideRight
            lineHeightMode: Text.FixedHeight; lineHeight: 17
            text: o.v ? [o.v.izlenme, o.v.tarih].filter(function(x) { return x }).join(" • ") : ""
            SecimKatmani { tiklama: o.solTik } }
    }
    HoverHandler { id: kartFare }
    // Sol tık açar; orta tık ya da Ctrl+tık yeni sekmede (arkada), sağ tık menü (tarayıcı alışkanlığı).
    function solTik(tuslar) { if (tuslar & Qt.ControlModifier) pencere.videoYeniSekmede(o.v); else o.sec() }
    MouseArea {
        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        onClicked: function(m) {
            if (m.button === Qt.RightButton) pencere.kartMenusu(o.v)
            else if (m.button === Qt.MiddleButton) pencere.videoYeniSekmede(o.v)
            else o.solTik(m.modifiers)
        }
    }
}
