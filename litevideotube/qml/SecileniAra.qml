import QtQuick

// Seçili yazının sağ tık menüsünde (SecilirYazi, SecimKatmani): seçilen yazıyı tarayıcıda Google'da ya da programın
// kendi aramasında arar (29 Ekim; tarayıcıdaki "Google'da ara" gibi). Yalnız yazı seçiliyken görünür.
Column {
    id: s
    property string secilen: ""
    signal secildi()
    readonly property string metin: secilen.replace(/\s+/g, " ").trim()
    readonly property string kisa: metin.length > 24 ? metin.slice(0, 24).trim() + "…" : metin
    visible: metin !== ""
    spacing: 2
    MenuCizgisi { anchors.left: parent.left; width: 300 }
    MenuSatiri { anchors.left: parent.left; width: 300; yazi: qsTr("Google'da ara: “%1”").arg(s.kisa)
        onTiklandi: { Qt.openUrlExternally("https://www.google.com/search?q=" + encodeURIComponent(s.metin)); s.secildi() } }
    MenuSatiri { anchors.left: parent.left; width: 300; yazi: qsTr("YouTube'da ara"); ipucu: qsTr("bu programda")
        onTiklandi: { pencere.secileniAra(s.metin); s.secildi() } }
}
