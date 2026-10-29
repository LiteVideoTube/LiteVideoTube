import QtQuick
import QtQuick.Controls.Basic

// Videoya sağ tıklayınca açılan menü (YouTube alışkanlığı). YouTube'un menüsünden döngü,
// bağlantı kopyalama ve istatistikler alındı; yerleştirme kodu, hata ayıklama bilgisi ve sorun bildirme
// YouTube'un kendi işleri olduğu için alınmadı. Programa özgü iki satır: tarayıcıda aç, kareyi kaydet.
MenuKutusu {
    id: m
    property var oynatici
    property string baslik
    signal istatistikIstendi()
    // Tıklanan yerde (sağdan sola dilde farenin solunda); videonun dışına taşacaksa içeri alınır. Popup'ın
    // mirrored'ı açılmadan önce hep false, o yüzden uygulamanın yönüne bakılır.
    function ac(x, y) {
        m.x = Math.max(0, Math.min(Qt.application.layoutDirection === Qt.RightToLeft ? x - width : x, parent.width - width))
        m.y = Math.max(0, Math.min(y, parent.height - height))
        open()
    }
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    onOpened: c.menuAcik = true
    onClosed: c.menuAcik = false
    contentItem: Column {
        spacing: 2
        MenuSatiri { anchors.left: parent.left; width: 380; yazi: qsTr("Döngü"); ipucu: qsTr("bitince baştan"); secili: m.oynatici.dongu; visible: !m.oynatici.canli
            onTiklandi: { m.close(); m.oynatici.donguDegistir() } }
        MenuSatiri { anchors.left: parent.left; width: 380; yazi: qsTr("Bağlantıyı kopyala"); onTiklandi: { m.close(); m.oynatici.baglantiKopyala(false) } }
        MenuSatiri { anchors.left: parent.left; width: 380; yazi: qsTr("Bu andaki bağlantıyı kopyala"); ipucu: qsTr("bu saniyeden açılır"); visible: !m.oynatici.canli
            onTiklandi: { m.close(); m.oynatici.baglantiKopyala(true) } }
        MenuSatiri { anchors.left: parent.left; width: 380; yazi: qsTr("İstatistikler"); ipucu: qsTr("kalite, takılma"); onTiklandi: { m.close(); m.istatistikIstendi() } }
        MenuCizgisi { anchors.left: parent.left; width: 380 }
        // Tarayıcıda açınca burada duraklar, iki ses üst üste binmesin.
        MenuSatiri { anchors.left: parent.left; width: 380; yazi: qsTr("Tarayıcıda aç"); ipucu: qsTr("bu saniyeden")
            onTiklandi: {
                m.close()
                if (!m.oynatici.durakli) m.oynatici.durdurOynat()
                Qt.openUrlExternally(m.oynatici.baglanti(true))
            } }
        MenuSatiri { anchors.left: parent.left; width: 380; yazi: qsTr("Bu kareyi resim olarak kaydet"); ipucu: qsTr("İndirilenler")
            onTiklandi: { m.close(); m.oynatici.kareKaydet(m.baslik) } }
    }
}
