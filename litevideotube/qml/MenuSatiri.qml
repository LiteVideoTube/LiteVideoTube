import QtQuick

// Açılır menülerde (MenuKutusu) bir satır: solda seçim işareti, sağda soluk ipucu; üstüne gelince yuvarlak köşeli vurgu.
Rectangle {
    id: sat
    property string yazi
    property string ipucu
    property bool secili: false
    property bool bekliyor: false   // seçildi, iniyor
    property bool tiklanir: true
    property string isaret: secili ? "✓" : bekliyor ? "…" : ""
    property color yaziRenk: Renk.yazi
    signal tiklandi()
    // Yazı ve ipucunun kesilmeden sığdığı genişlik; menü bunu satırlarına ortak genişlik olarak verebilir (satirEn).
    readonly property real gereken: 42 + yaziMetni.implicitWidth + (ipucu ? ipucuYazi.implicitWidth + 16 : 0)
    width: parent && parent.satirEn ? parent.satirEn : 300; height: 34; radius: 8
    color: fare.containsMouse && tiklanir ? Renk.menuVurgu : "transparent"
    Text { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: sat.isaret; color: Renk.mavi; font.pixelSize: 14 }
    Text { id: yaziMetni; anchors.left: parent.left; anchors.leftMargin: 32; width: parent.width - 42 - ipucuYazi.implicitWidth; anchors.verticalCenter: parent.verticalCenter
        // Hizalama açıkça verilir: sağdan sola dilde aynalanır, İngilizce altyazı adları da sağa yaslanır.
        horizontalAlignment: Text.AlignLeft
        text: sat.yazi; color: sat.yaziRenk; font.pixelSize: 14; elide: Text.ElideRight }
    Text { id: ipucuYazi; anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
        text: sat.ipucu; color: Renk.yaziSoluk; font.pixelSize: 12 }
    MouseArea { id: fare; anchors.fill: parent; hoverEnabled: true; enabled: sat.tiklanir
        cursorShape: Qt.PointingHandCursor; onClicked: sat.tiklandi() }
}
