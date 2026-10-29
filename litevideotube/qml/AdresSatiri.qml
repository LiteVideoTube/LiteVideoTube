import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Tarayıcının adres satırı (program tarayıcıya alışık birine tanıdık gelsin, eksik gedik olmasın):
// geri, ileri, yenile ve bulunulan sayfanın adresi. Adrese bağlantı yazılırsa açılır, söz yazılırsa aranır
// (Ana.qml, adresAc). Tıklayınca adresin hepsi seçilir; vazgeçince (Esc, başka yere tıklama) eski adres geri gelir.
// Geri ve ileri, gidilecek yer yokken soluk durur (tarayıcıdaki gibi; düğmeler yer değiştirmesin).
Rectangle {
    id: a
    property string adres: ""
    property bool geriVar: false
    property bool ileriVar: false
    property alias yaziyor: kutu.activeFocus
    signal geri()
    signal ileri()
    signal yenile()
    signal git(string metin)
    color: Renk.zemin
    onAdresChanged: if (!kutu.activeFocus) kutu.text = adres
    function yazmayaBasla() { kutu.forceActiveFocus(); kutu.selectAll() }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8; anchors.rightMargin: 16
        spacing: 0
        Simge { ad: "arrow_back"; yonlu: true; ipucu: qsTr("Geri (Alt+Sol)"); opacity: a.geriVar ? 1 : 0.35; onTiklandi: if (a.geriVar) a.geri() }
        Simge { ad: "arrow_forward"; yonlu: true; ipucu: qsTr("İleri (Alt+Sağ)"); opacity: a.ileriVar ? 1 : 0.35; onTiklandi: if (a.ileriVar) a.ileri() }
        Simge { ad: "refresh"; ipucu: qsTr("Yenile (F5)"); onTiklandi: a.yenile() }
        Rectangle {
            Layout.fillWidth: true; Layout.leftMargin: 8; Layout.preferredHeight: 32
            radius: 16; color: Renk.k("#1c1c1c", "#f2f2f2"); border.color: kutu.activeFocus ? Renk.mavi : "transparent"
            TextField {
                id: kutu
                anchors { fill: parent; leftMargin: 14; rightMargin: 14 + yakinlikDugmesi.width }
                placeholderText: qsTr("Adres ya da arama")
                placeholderTextColor: Renk.yaziSoluk
                color: kutu.activeFocus ? Renk.yazi : Renk.yaziSoluk; font.pixelSize: 14
                background: null
                selectByMouse: true
                verticalAlignment: TextInput.AlignVCenter
                onAccepted: { var t = text.trim(); focus = false; if (t) a.git(t) }
                Keys.onEscapePressed: focus = false
                onActiveFocusChanged: if (activeFocus) Qt.callLater(kutu.selectAll); else text = a.adres
            }
            // Yakınlık (Chrome'daki gibi adres satırının sağ ucunda, hep görünür; herkesin gözü farklı, Ctrl+tekerleği
            // kimse kendiliğinden bulmaz): büyüteç ve yüzde; tıklayınca altında − / + açılır.
            Rectangle {
                id: yakinlikDugmesi
                anchors { right: parent.right; rightMargin: 4; verticalCenter: parent.verticalCenter }
                width: yakinlikSira.implicitWidth + 16; height: 28; radius: 14
                color: yakinlikFare.containsMouse || yakinlikMenu.opened ? Renk.k("#3a3a3a", "#e0e0e0") : "transparent"
                Row {
                    id: yakinlikSira
                    anchors.centerIn: parent
                    spacing: 3
                    Image { anchors.verticalCenter: parent.verticalCenter; width: 22; height: 22; sourceSize: Qt.size(44, 44)
                        source: Renk.simge("zoom_in"); opacity: 0.9 }
                    Text { anchors.verticalCenter: parent.verticalCenter; text: qsTr("%%1").arg(kisiler.yakinlik)
                        color: Renk.yaziSoluk; font.pixelSize: 14 }
                }
                MouseArea {
                    id: yakinlikFare
                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: yakinlikMenu.opened ? yakinlikMenu.close() : yakinlikMenu.open()
                }
                ToolTip.visible: yakinlikFare.containsMouse && !yakinlikMenu.opened; ToolTip.delay: 600
                ToolTip.text: qsTr("Yakınlık (Ctrl + tekerlek, Ctrl + / −)")
                MenuKutusu {
                    id: yakinlikMenu
                    y: parent.height + 6; x: parent.width - width
                    contentItem: Row {
                        spacing: 6; padding: 4
                        Repeater {
                            model: [{ y: "−", yon: -1 }, { y: "", yon: 0 }, { y: "+", yon: 1 }]
                            Rectangle {
                                width: modelData.yon === 0 ? 64 : 32; height: 32; radius: 16
                                color: modelData.yon !== 0 && dFare.containsMouse ? Renk.menuVurgu : "transparent"
                                border.width: modelData.yon !== 0 ? 1 : 0; border.color: Renk.cizgi
                                Text { anchors.centerIn: parent; color: Renk.yazi; font.pixelSize: modelData.yon === 0 ? 14 : 18
                                    text: modelData.yon === 0 ? qsTr("%%1").arg(kisiler.yakinlik) : modelData.y }
                                MouseArea { id: dFare; anchors.fill: parent; hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    // Ortadaki yüzde: %100'e döner (Ctrl+0 gibi).
                                    onClicked: pencere.yakinlikDegistir(modelData.yon) }
                            }
                        }
                    }
                }
            }
        }
    }
}
