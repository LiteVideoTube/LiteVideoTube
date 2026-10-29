import QtQuick
import QtQuick.Controls.Basic

// Altyazı menüsü: Kapalı; elle yazılmışlar; otomatik (konuşmanın
// kendi dili); "Makine çevirisi" ayrı sayfada. Dil adları ekran dilinde, kullanıcının dili başta, öbürleri
// abece sırasıyla (cozumle.altyazilar, diller.py). Altyazı YouTube'daki gibi kapalı başlar.
MenuKutusu {
    id: m
    property var oynatici
    property bool ceviriSayfasi: false
    property real ustBosluk: 600   // düğmenin üstünde pencerede kalan yer; açılırken ölçülür
    y: -height - 8
    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
    onAboutToShow: ustBosluk = parent.mapToItem(null, 0, 0).y
    onOpened: { c.menuAcik = true; ceviriSayfasi = m.oynatici.seciliAltyazi.indexOf("ceviri:") === 0 }
    onClosed: c.menuAcik = false
    function sec(anahtar) { m.oynatici.altyaziSec(anahtar) }
    readonly property string secili: oynatici.seciliAltyazi
    readonly property string bekleyen: oynatici.bekleyenAltyazi
    readonly property string durum: oynatici.altyaziDurum

    onCeviriSayfasiChanged: liste.contentY = 0
    contentItem: Flickable {
        id: liste
        implicitWidth: 300
        // Pencereye sığmayan uzun liste kaydırılır (makine çevirisinde ~155 dil).
        // Menü düğmenin üstünde açılır; liste oraya sığmazsa kaydırılır (makine çevirisinde ~155 dil).
        implicitHeight: Math.min(sutun.implicitHeight, Math.max(160, m.ustBosluk - 40))
        contentHeight: sutun.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        Column {
            id: sutun
            width: 300
            spacing: 2
            // Makine çevirisi giriş istiyorsa ya da altyazı inmediyse düz açıklama (kullanıcıdan saklanmaz).
            Rectangle { anchors.left: parent.left;
                visible: m.durum !== "" && m.durum !== "iniyor"
                width: 300; radius: 8; color: Renk.k("#303030", "#f2f2f2")
                height: visible ? durumSutun.implicitHeight + 20 : 0
                Column {
                    id: durumSutun
                    anchors.left: parent.left; anchors.leftMargin: 10; y: 10; width: 280; spacing: 8
                    Text { width: parent.width; wrapMode: Text.Wrap; color: Renk.yazi; font.pixelSize: 13
                        text: m.durum === "giris"
                              ? qsTr("YouTube makine çevirisini yalnız YouTube'a giriş yapmış kişiye veriyor.")
                              : m.durum === "oturum" ? qsTr("Tarayıcıda YouTube oturumu bulunamadı.") : qsTr("Altyazı inmedi.") }
                    Button { anchors.left: parent.left;
                        id: oturumDugme
                        visible: m.durum === "giris"
                        text: qsTr("Tarayıcımdaki YouTube oturumuyla indir")
                        onClicked: m.oynatici.altyaziOturumla(m.bekleyen)
                        contentItem: Text { text: oturumDugme.text; color: "black"; font.pixelSize: 13; font.weight: Font.Medium
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        background: Rectangle { implicitHeight: 32; radius: 16; color: oturumDugme.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu }
                    }
                    Text { visible: m.durum === "giris"; width: parent.width; wrapMode: Text.Wrap; color: Renk.yaziSoluk; font.pixelSize: 12
                        text: qsTr("Oturumun yalnız bu altyazı için okunur, saklanmaz.") }
                }
            }
            Column { anchors.left: parent.left;
                visible: !m.ceviriSayfasi
                width: 300; spacing: 2
                MenuBasligi { anchors.left: parent.left; text: qsTr("Altyazı") }
                MenuSatiri { anchors.left: parent.left; yazi: qsTr("Kapalı"); secili: m.secili === "" && m.bekleyen === ""; onTiklandi: m.sec("") }
                MenuBasligi { anchors.left: parent.left; text: qsTr("Elle yazılmış"); visible: m.oynatici.altyaziElle.length > 0 }
                Repeater {
                    model: m.ceviriSayfasi ? [] : m.oynatici.altyaziElle
                    MenuSatiri { anchors.left: parent.left; yazi: modelData; secili: m.secili === "elle:" + index; bekliyor: m.bekleyen === "elle:" + index
                        onTiklandi: m.sec("elle:" + index) }
                }
                MenuBasligi { anchors.left: parent.left; text: qsTr("Otomatik (konuşmadan)"); visible: m.oynatici.altyaziOtomatik.length > 0 }
                Repeater {
                    model: m.ceviriSayfasi ? [] : m.oynatici.altyaziOtomatik
                    MenuSatiri { anchors.left: parent.left; yazi: modelData; ipucu: qsTr("otomatik"); secili: m.secili === "otomatik:" + index
                        bekliyor: m.bekleyen === "otomatik:" + index; onTiklandi: m.sec("otomatik:" + index) }
                }
                MenuSatiri { anchors.left: parent.left; visible: m.oynatici.altyaziCeviri.length > 0; yazi: qsTr("Makine çevirisi"); ipucu: Qt.application.layoutDirection === Qt.RightToLeft ? "‹" : "›"
                    secili: m.secili.indexOf("ceviri:") === 0; onTiklandi: m.ceviriSayfasi = true }
                Text { anchors.left: parent.left; visible: m.oynatici.altyaziElle.length + m.oynatici.altyaziOtomatik.length === 0
                    leftPadding: 32; bottomPadding: 6; color: Renk.yaziSoluk; font.pixelSize: 13; text: qsTr("Bu videoda altyazı yok") }
            }
            Column { anchors.left: parent.left;
                visible: m.ceviriSayfasi
                width: 300; spacing: 2
                MenuSatiri { anchors.left: parent.left; yazi: qsTr("Makine çevirisi"); isaret: Qt.application.layoutDirection === Qt.RightToLeft ? "›" : "‹"; onTiklandi: m.ceviriSayfasi = false }
                Text { anchors.left: parent.left; width: 300; leftPadding: 32; rightPadding: 10; bottomPadding: 4; wrapMode: Text.Wrap
                    color: Renk.yaziSoluk; font.pixelSize: 12
                    text: qsTr("YouTube'un otomatik çevirisi; yanlışları olabilir.") }
                Repeater {
                    model: m.ceviriSayfasi ? m.oynatici.altyaziCeviri : []
                    MenuSatiri { anchors.left: parent.left; yazi: modelData; secili: m.secili === "ceviri:" + index; bekliyor: m.bekleyen === "ceviri:" + index
                        onTiklandi: m.sec("ceviri:" + index) }
                }
            }
        }
    }
}
