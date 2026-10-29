import QtQuick
import QtQuick.Controls.Basic

// Fareyle seçilip kopyalanabilen yazı (tarayıcı alışkanlığı): Ctrl+C ya da sağ tık "Kopyala".
// Klavye odağını almaz, tuşlar videoda kalır; Ctrl+C'yi Ana.qml'deki kısayol son seçilen yazıya iletir.
// Sayfada bul (Ctrl+F) bu yazılarda da arar. Uzun yazı satirSiniri satırda kesilir; açık olup olmadığını (acik)
// kullanan bağlar, bul gizli kısımda bir şey bulunca acilmali() ile açmasını ister.
TextEdit {
    id: y
    property int satirSiniri: 0
    property bool acik: false
    signal acilmali()
    readonly property real sinirBoy: satirSiniri * olcu.lineSpacing
    readonly property bool kesik: satirSiniri > 0 && contentHeight > sinirBoy + 2
    height: satirSiniri > 0 && !acik ? Math.min(contentHeight, sinirBoy) : contentHeight
    clip: satirSiniri > 0 && !acik
    readOnly: true
    selectByMouse: true
    activeFocusOnPress: false
    wrapMode: TextEdit.Wrap
    selectionColor: "#663ea6ff"
    selectedTextColor: Renk.yazi
    FontMetrics { id: olcu; font: y.font }
    onSelectedTextChanged: if (selectedText !== "") pencere.yaziSecildi(y)
    HoverHandler { cursorShape: y.hoveredLink ? Qt.PointingHandCursor : Qt.IBeamCursor }
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: function(nokta) { menu.popup() }
    }
    MenuKutusu {
        id: menu
        contentItem: Column {
            spacing: 2
            MenuSatiri { anchors.left: parent.left; width: 300; yazi: qsTr("Kopyala"); tiklanir: y.selectedText !== ""; opacity: tiklanir ? 1 : 0.5
                onTiklandi: { y.copy(); menu.close() } }
            MenuSatiri { anchors.left: parent.left; width: 300; yazi: qsTr("Hepsini seç"); onTiklandi: { y.selectAll(); menu.close() } }
            SecileniAra { anchors.left: parent.left; secilen: y.selectedText; onSecildi: menu.close() }
        }
    }

    // Sayfada bul: eşleşmeler ve gösterme.
    BulKaynagi {
        hedef: y
        function eslesmeler(sorgu) {
            var metin = pencere.bulKucuk(y.getText(0, y.length)), l = [], i = metin.indexOf(sorgu)
            while (i >= 0 && sorgu.length) {
                l.push({ y: y.mapToItem(null, 0, y.positionToRectangle(i).y).y, bas: i, son: i + sorgu.length })
                i = metin.indexOf(sorgu, i + sorgu.length)
            }
            return l
        }
        function goster(m) {
            if (y.satirSiniri > 0 && !y.acik && y.positionToRectangle(m.bas).y + olcu.lineSpacing > y.height) y.acilmali()
            y.select(m.bas, m.son)
            Qt.callLater(function() { pencere.kaydirGoster(y, y.positionToRectangle(m.bas).y) })   // açıldıysa yeni boyla
        }
        function birak() { y.deselect() }
    }
}
