import QtQuick

// Sayfada bul (Ctrl+F) için bir kaynak. Kaydı kendisi yapar; görünmeyen sayfadakiler aranmaz (hedef.visible).
// Kullanan, şu üç işlevi yazar: eslesmeler(sorgu) -> [{y, ...}] (y: sayfadaki sıra için), goster(m), birak().
// Sorgu küçük harfe çevrilmiş gelir (pencere.bulKucuk).
QtObject {
    id: b
    property Item hedef
    Component.onCompleted: pencere.bulKaynaklari.push(b)
    Component.onDestruction: {
        var i = pencere.bulKaynaklari.indexOf(b)
        if (i >= 0) pencere.bulKaynaklari.splice(i, 1)
    }
}
