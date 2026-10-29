import QtQuick
import QtQuick.Controls.Basic

// Bir Text'i fareyle seçilip kopyalanabilir yapar (yazı seçmek her sayfada olsun, tarayıcıdaki
// gibi). Text'in içine konur: Text { ...; SecimKatmani { } }. Text görünür kalır ("…" kısaltması ve satır sınırı
// bozulmasın); üstünde aynı yazıyı aynı yerde taşıyan görünmez bir TextEdit seçimi çizer. Kopyalanan yazı tam
// yazıdır, "…" ile gizlenen kısım da (tarayıcıdaki gibi). Ctrl+C ve sağ tık "Kopyala" SecilirYazi'daki gibi.
// TextEdit yalnız fare yazının üstündeyken ya da seçim varken kurulur: sayfalarda yüzlerce yazı var, bilgisayar eski.
// tiklama: yazı tıklanan bir şeyin üstündeyse (video kartı, kanal adı) sürüklemeden yapılan sol tık ona gider,
// function(tuslar); sürükleyince seçer. Orta tık Ctrl+tık olarak ona gider. Sağ tık alttakine geçer; seçim varken ya
// da yazı tıklanmıyorsa sağ tık "Kopyala" menüsünü açar.
Item {
    id: k
    property var tiklama: null
    readonly property bool ustunde: uzerinde.hovered
    property bool secimVar: false
    property bool menuAcik: false    // sağ tık menüsü açıkken fare yazıdan çıksa da TextEdit (ve menü) kalsın
    readonly property Text yazi: parent
    width: parent ? parent.width : 0; height: parent ? parent.height : 0   // kanal adında yalnız yazının eni
    HoverHandler { id: uzerinde; cursorShape: k.tiklama ? Qt.PointingHandCursor : Qt.IBeamCursor }
    Loader {
        id: yukleyici
        anchors.fill: parent
        active: uzerinde.hovered || k.secimVar || k.menuAcik
        sourceComponent: TextEdit {
            id: y
            text: k.yazi.text
            font: k.yazi.font
            wrapMode: k.yazi.wrapMode
            // Text'in ekrandaki hizası (sağdan sola dilde yazıya göre sağa ya da sola dönmüş hâli) olduğu gibi alınır,
            // TextEdit kendisi bir daha aynalamasın: yoksa Farsça ve Arapça yazıda seçim yazının yanına düşüyordu.
            LayoutMirroring.enabled: false
            horizontalAlignment: k.yazi.effectiveHorizontalAlignment
            verticalAlignment: k.yazi.verticalAlignment
            topPadding: k.yazi.topPadding; bottomPadding: k.yazi.bottomPadding
            leftPadding: k.yazi.leftPadding; rightPadding: k.yazi.rightPadding
            textFormat: k.yazi.textFormat === Text.RichText || k.yazi.textFormat === Text.StyledText ? TextEdit.RichText : TextEdit.PlainText
            color: "transparent"
            selectedTextColor: "transparent"   // alttaki Text görünür; seçim rengi yarı saydam
            selectionColor: "#663ea6ff"
            clip: true
            readOnly: true
            selectByMouse: true
            activeFocusOnPress: false
            onSelectedTextChanged: { k.secimVar = selectedText !== ""; if (k.secimVar) pencere.yaziSecildi(y) }
            // TextEdit orta tıkı da yutuyor: orta tık Ctrl+tık sayılır (tarayıcıda ikisi de yeni sekme).
            TapHandler {
                acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                enabled: k.tiklama !== null
                onTapped: function(nokta, dugme) { k.tiklama(point.modifiers | (dugme === Qt.MiddleButton ? Qt.ControlModifier : 0)) }
            }
            // Seçim varken sağ tık alttakine (kartın menüsüne) gitmesin: basışı bu tutar. Tıklanmayan yazıda hep menü.
            TapHandler {
                acceptedButtons: Qt.RightButton
                enabled: y.selectedText !== "" || k.tiklama === null
                gesturePolicy: TapHandler.ReleaseWithinBounds
                onTapped: menu.popup()
            }
            MenuKutusu {
                id: menu
                onOpened: k.menuAcik = true
                onClosed: k.menuAcik = false
                contentItem: Column {
                    spacing: 2
                    MenuSatiri { anchors.left: parent.left; width: 300; yazi: qsTr("Kopyala"); tiklanir: y.selectedText !== ""; opacity: tiklanir ? 1 : 0.5
                        onTiklandi: { y.copy(); menu.close() } }
                    MenuSatiri { anchors.left: parent.left; width: 300; yazi: qsTr("Hepsini seç"); onTiklandi: { y.selectAll(); menu.close() } }
                    SecileniAra { anchors.left: parent.left; secilen: y.selectedText; onSecildi: menu.close() }
                }
            }
        }
    }
}
