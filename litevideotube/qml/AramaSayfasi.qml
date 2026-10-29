import QtQuick
import QtQuick.Controls.Basic

Item {
    id: a
    readonly property Flickable kaydirmaAlani: izgara   // yakınlıkla yeniden açılınca kaydırma yeri (Ana.qml)
    property var sonuclar: []
    property bool devamVar: false
    property bool yukleniyor: false
    signal sec(var v)
    signal dahaFazla()
    function basaDon() { izgara.contentY = 0 }

    readonly property int sutun: Math.max(1, Math.min(Renk.enCokSutun, Math.floor((width - 32) / 300)))

    GridView {
        id: izgara
        TekerlekHizi { hedef: izgara }
        IzgaraBul { izgara: izgara; liste: a.sonuclar }
        anchors.fill: parent; anchors.leftMargin: 24; anchors.topMargin: 16
        cellWidth: (width - 8) / a.sutun; cellHeight: cellWidth * 9 / 16 + 112
        model: a.sonuclar
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        // Kart hücrenin başında, aradaki 16 px sonunda; sağdan sola dilde kart hücrenin sağına geçer (anchors.left
        // aynalanır), iki yandaki boşluk Türkçedeki gibi eşit kalır.
        delegate: Item {
            width: izgara.cellWidth; height: izgara.cellHeight
            VideoKarti {
                anchors.left: parent.left
                width: izgara.cellWidth - 16
                v: modelData
                onSec: a.sec(modelData)
            }
        }
        // Devamı sayfanın sonu yaklaşınca istenir; ilk sonuçlar ekrana sığıyorsa (geniş pencere) kaydıracak yer
        // olmadığından içerik boyu değişince de bakılır (24 Ekim: 1920 px'te 7 sonuçta kalıyordu).
        function devamBak() { if (a.devamVar && !a.yukleniyor && contentY + height > contentHeight - 600) { a.yukleniyor = true; a.dahaFazla() } }
        onContentYChanged: devamBak()
        onContentHeightChanged: Qt.callLater(devamBak)
        Connections { target: a; function onYukleniyorChanged() { if (!a.yukleniyor) Qt.callLater(izgara.devamBak) } }
    }
    Text {
        anchors.centerIn: parent
        visible: a.sonuclar.length === 0
        color: Renk.yaziSoluk; font.pixelSize: 18
        text: a.yukleniyor ? qsTr("Aranıyor…") : qsTr("Bir şey ara ya da bir YouTube bağlantısı yapıştır.")
        SecimKatmani { }
    }
}
