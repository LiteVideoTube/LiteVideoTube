import QtQuick
import QtQuick.Controls.Basic

// "Görünüm" düğmesinin menüsü: video açılınca nasıl görünsün, aşağı kaydırınca nereye
// geçsin; varsayılana dön. Seçim hemen uygulanır ve kalıcıdır (Ana.qml, gorunum). Menü seçimden sonra
// açık kalır, işaret yeni seçime geçer.
MenuKutusu {
    id: m
    property var gorunum
    y: -height - 8
    x: mirrored ? Math.max(0, parent.width - width) : Math.min(0, -width + parent.width)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
    onOpened: c.menuAcik = true
    onClosed: c.menuAcik = false
    contentItem: Column {
        id: kolon
        spacing: 2
        // Satırlar en uzun yazıya göre genişler (Rusçada ve yeni satırda yazılar kesiliyordu; 29 Ekim), en çok 600 px.
        readonly property real satirEn: {
            var e = 300
            for (var i = 0; i < children.length; i++)
                if (children[i].visible && children[i].gereken) e = Math.max(e, children[i].gereken)
            return Math.min(Math.ceil(e), 600)
        }
        MenuBasligi { anchors.left: parent.left; text: qsTr("Video açılınca") }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Normal"); ipucu: qsTr("varsayılan"); secili: m.gorunum.sayfa === "normal"; onTiklandi: m.gorunum.sayfa = "normal" }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Sinema"); ipucu: qsTr("sayfa genişliğinde"); secili: m.gorunum.sayfa === "sinema"; onTiklandi: m.gorunum.sayfa = "sinema" }
        // 4. ilke: yorumlar için izleyenlerin düzeni (yorumlar büyük, video yanda).
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Yorumlarla yan yana"); ipucu: qsTr("video sağda"); secili: m.gorunum.sayfa === "yorum"; onTiklandi: m.gorunum.sayfa = "yorum" }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Tam ekran"); ipucu: qsTr("Esc ile çıkılır"); secili: m.gorunum.sayfa === "tam"; onTiklandi: m.gorunum.sayfa = "tam" }
        MenuBasligi { anchors.left: parent.left; text: qsTr("Aşağı kaydırınca") }
        // Aşağı inince de video büyük kalsın, yazılar daralsın; ok düğmesiyle sola alınır.
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Önerilerin üstünde, en büyük"); ipucu: qsTr("varsayılan")
            secili: m.gorunum.yan === "buyuk" && !m.gorunum.yanBoy; onTiklandi: { m.gorunum.yan = "buyuk"; m.gorunum.yanBoy = 0 } }
        // Yorumları okurken video olabildiğince büyük; öneriler altında kalır (29 Ekim).
        // İpucu ("öneriler kapanır") satıra sığmıyordu, yazı kesiliyordu; seçince görünüyor.
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Yorumların yanında, en büyük")
            secili: m.gorunum.yan === "yorumlar" && !m.gorunum.yanBoy; onTiklandi: { m.gorunum.yan = "yorumlar"; m.gorunum.yanBoy = 0 } }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Önerilerin üstünde, sütun genişliğinde")
            secili: m.gorunum.yan === "genis" && !m.gorunum.yanBoy; onTiklandi: { m.gorunum.yan = "genis"; m.gorunum.yanBoy = 0 } }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Sağ üstte, küçük")
            secili: m.gorunum.yan === "kucuk" && !m.gorunum.yanBoy; onTiklandi: { m.gorunum.yan = "kucuk"; m.gorunum.yanBoy = 0 } }
        MenuSatiri { anchors.left: parent.left; visible: m.gorunum.yanBoy > 0; tiklanir: false; secili: true
            yazi: qsTr("Elle verdiğin boy"); ipucu: m.gorunum.yanBoy + " × " + Math.round(m.gorunum.yanBoy * 9 / 16) }
        MenuCizgisi { anchors.left: parent.left; width: kolon.satirEn }
        MenuSatiri { anchors.left: parent.left; yazi: qsTr("Hepsini varsayılana döndür"); onTiklandi: m.gorunum.varsayilan() }
    }
}
