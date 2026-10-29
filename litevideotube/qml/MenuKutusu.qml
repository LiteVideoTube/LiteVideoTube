import QtQuick
import QtQuick.Controls.Basic

// Programdaki bütün açılır menülerin ortak kutusu (menüler modern görünsün, hepsi aynı görünüşte
// olsun, sonradan hepsi birlikte değişsin): yuvarlak köşe, çerçeve yerine hafif gölge, programın renkleri (Renk.qml).
// İçine MenuSatiri, MenuBasligi ve MenuCizgisi konur (contentItem: Column { ... }).
// popup(): sağ tık menüsü için; menü farenin son bastığı yerde açılır (pencere.sonBasis, uygulama.py OdakBekcisi),
// sağdan sola dilde farenin soluna doğru.
Popup {
    id: m
    padding: 6
    margins: 8          // pencerenin dışına taşmasın
    modal: false
    // Esc menüyü ancak klavye odağı menüdeyse kapatır (Qt); odaksız menüler Esc'le kapanmıyordu. Kapanınca odak
    // videoya döner (uygulama.py, OdakBekcisi).
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    function popup() {
        var p = parent.mapFromItem(null, pencere.sonBasis.x, pencere.sonBasis.y)
        // mirrored açılmadan önce hep false; uygulamanın yönüne bakılır.
        x = Qt.application.layoutDirection === Qt.RightToLeft ? p.x - implicitWidth : p.x; y = p.y
        open()
    }
    // Gölge: kutunun arkasında, dışa doğru açılan saydam katmanlar (bulanıklaştırma efektinden ucuz; eski
    // bilgisayarda da iş yapmaz). Biraz aşağıda durur, menü sayfanın üstünde duruyormuş gibi görünür.
    background: Item {
        implicitWidth: 120
        Repeater {
            model: 6
            Rectangle {
                required property int index
                anchors { fill: parent; leftMargin: -index - 1; rightMargin: -index - 1; topMargin: -index + 1; bottomMargin: -index - 4 }
                radius: Renk.menuKose + index + 1
                color: Qt.rgba(0, 0, 0, Renk.k(0.09, 0.035))   // beyaz zeminde koyu kenar gibi durmasın
            }
        }
        Rectangle { anchors.fill: parent; radius: Renk.menuKose; color: Renk.menu }
    }
}
