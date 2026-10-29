import QtQuick
import QtQuick.Controls.Basic

// Bir indirmenin satırı: ne indiği, durumu, ilerleme çizgisi ve düğmeleri (iptal, aç, yeniden).
Item {
    id: s
    property var is_
    property bool baslikGoster: false
    width: 320; height: sutun.implicitHeight + 10
    Column {
        id: sutun
        anchors.left: parent.left; anchors.leftMargin: 10; y: 5; width: parent.width - 20 - dugmeler.width; spacing: 3
        Text { visible: s.baslikGoster; width: parent.width; text: s.is_.baslik; color: Renk.yazi; font.pixelSize: 13; elide: Text.ElideRight }
        Text { width: parent.width; text: s.is_.turAdi; color: s.baslikGoster ? Renk.yaziSoluk : Renk.yazi; font.pixelSize: 13 }
        Text { width: parent.width; text: s.is_.yazi; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
            color: s.is_.durum === "hata" ? Renk.hata : Renk.yaziSoluk; font.pixelSize: 12 }
        Rectangle { visible: s.is_.suruyor; width: parent.width; height: 4; radius: 2; color: Renk.inmemis
            Rectangle { anchors.left: parent.left; width: parent.width * s.is_.oran; height: parent.height; radius: 2; color: Renk.mavi } }
    }
    Row {
        id: dugmeler
        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
        Simge { visible: s.is_.suruyor; ad: "close"; boy: 20; ipucu: qsTr("İptal"); onTiklandi: indirici.iptal(s.is_.no) }
        Simge { visible: s.is_.durum === "bitti" && s.is_.var; ad: "open_in_new"; boy: 20; ipucu: qsTr("Dosyayı aç"); onTiklandi: indirici.dosyayiAc(s.is_.no) }
        Simge { visible: !s.is_.suruyor && s.is_.tur !== "dokum" && (s.is_.durum !== "bitti" || !s.is_.var); ad: "replay"; boy: 20
            ipucu: qsTr("Yeniden indir"); onTiklandi: indirici.yeniden(s.is_.no) }
    }
}
