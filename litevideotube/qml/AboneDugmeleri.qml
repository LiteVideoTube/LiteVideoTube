import QtQuick
import QtQuick.Controls.Basic

// "Abone ol" ve zil (YouTube'daki gibi): kanal sayfasında ve video sayfasında kanal adının yanında
// (insan kanalın sayfasına nadiren girer, zil izlediği videodan takılabilmeli). Abonelik yalnız programda kalır,
// YouTube hesabına yazılmaz. Zil yalnız abone olunca görünür: zilli kanala 15 dakikada bir bakılır (program
// kapalıyken de), yeni videoları abonelik sayfasının başında ayrı durur.
Row {
    id: d
    property string kanalId
    property string kanalAd
    readonly property bool abone: { abonelik.kanalSayisi; return d.kanalId ? abonelik.aboneMi(d.kanalId) : false }
    readonly property bool zilli: { abonelik.kanalSayisi; return d.abone && abonelik.zilli(d.kanalId) }
    spacing: 8
    visible: d.kanalId !== ""

    Button {
        id: aboneDugme
        objectName: "aboneDugme"
        text: d.abone ? qsTr("Abone olundu") : qsTr("Abone ol")
        onClicked: d.abone ? birakOnay.open() : abonelik.aboneOl(d.kanalId, d.kanalAd)
        contentItem: Text { text: (d.abone ? "✓ " : "") + aboneDugme.text; font.pixelSize: 14; font.weight: Font.Medium
            color: d.abone ? Renk.yazi : "black"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { implicitHeight: 36; implicitWidth: 140; radius: 18
            color: d.abone ? (aboneDugme.hovered ? Renk.yuzeyAcik : Renk.yuzey) : (aboneDugme.hovered ? Renk.maviDolguVurgu : Renk.maviDolgu) }
    }
    Button {
        id: zilDugme
        visible: d.abone
        onClicked: abonelik.zilDegistir(d.kanalId)
        contentItem: Row {
            spacing: 6
            Image { source: d.zilli ? "../simgeler/notifications_active_mavi.svg" : Renk.simge("notifications_bos")
                width: 22; height: 22; sourceSize: Qt.size(44, 44); anchors.verticalCenter: parent.verticalCenter }
            Text { text: d.zilli ? qsTr("Zil açık") : qsTr("Zil"); color: Renk.yazi; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
        }
        background: Rectangle { implicitHeight: 36; radius: 18; color: zilDugme.hovered ? Renk.yuzeyAcik : Renk.yuzey }
    }

    Dialog {
        id: birakOnay
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        title: qsTr("\"%1\" aboneliğinden çıkılsın mı?").arg(d.kanalAd)
        standardButtons: Dialog.Yes | Dialog.No
        Text { text: qsTr("YouTube hesabındaki aboneliğin değişmez."); color: Renk.yazi; font.pixelSize: 14 }
        background: Rectangle { color: Renk.pencereZemin; radius: 12 }
        onAccepted: abonelik.abonelikBirak(d.kanalId)
        Component.onCompleted: { standardButton(Dialog.Yes).text = qsTr("Abonelikten çık"); standardButton(Dialog.No).text = qsTr("Vazgeç") }
    }
}
