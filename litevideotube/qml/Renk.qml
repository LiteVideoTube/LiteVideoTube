pragma Singleton
import QtQuick

// Programın renkleri, koyu ve açık görünüm. Görünüm kişi menüsünden seçilir (Ana.qml, kisiler.gorunum): "cihaz"
// bilgisayarın açık/koyu ayarına uyar (ayar okunamazsa koyu), "koyu", "acik". Video alanı, oynatıcı çubuğu ve
// küçük resimlerin üstündekiler her görünümde koyu zeminde durur; onların renkleri aşağıda "video" adlı olanlar.
QtObject {
    property string secim: "cihaz"
    // Izgaralı sayfalarda (abonelikler, arama, kanal) yan yana en çok kaç video: %100'de 5; arayüz küçültülünce
    // (yakınlık) artar ki daha çok video görünsün (Ana.qml bağlar).
    property int enCokSutun: 5
    readonly property bool acik: secim === "acik" || (secim === "cihaz" && Qt.styleHints.colorScheme === Qt.ColorScheme.Light)
    // Tek yerde kullanılan tonlar için: koyu görünümdeki değer, açık görünümdeki değer.
    function k(koyu, acik_) { return acik ? acik_ : koyu }

    readonly property color zemin: acik ? "#ffffff" : "#0f0f0f"
    readonly property color yuzey: acik ? "#f2f2f2" : "#272727"
    readonly property color yuzeyAcik: acik ? "#e5e5e5" : "#3f3f3f"
    readonly property color yazi: acik ? "#0f0f0f" : "#f1f1f1"
    readonly property color yaziSoluk: acik ? "#606060" : "#aaaaaa"
    // Programın kendi rengi bebe mavisi: addaki "Lite", seçim işaretleri, bağlantılar. Açık zeminde okunsun diye koyulaşır.
    readonly property color mavi: acik ? "#1170c0" : "#7cc4ff"
    // Mavi düğmeler (Abonelikleri getir, kişi düğmesi, YENİ): her görünümde bebe mavisi, üstündeki yazı siyah.
    readonly property color maviDolgu: "#7cc4ff"
    readonly property color maviDolguVurgu: "#a6d8ff"
    // Çerçeveler ve ayırma çizgileri; yazı kutularının içi; hata yazısı; onay pencerelerinin zemini.
    readonly property color cizgi: acik ? "#d9d9d9" : "#3a3a3a"
    readonly property color kutu: acik ? "#ffffff" : "#121212"
    readonly property color hata: acik ? "#c5221f" : "#ff8a80"
    readonly property color pencereZemin: acik ? "#ffffff" : "#272727"
    // Açılır menüler (MenuKutusu, MenuSatiri: modern, hepsi aynı görünüş): kutu, üstüne gelinen
    // satırın vurgusu, ayırma çizgisi, köşe yuvarlaklığı.
    readonly property color menu: acik ? "#ffffff" : "#282828"
    readonly property color menuVurgu: acik ? "#ececec" : "#3d3d3d"
    readonly property color menuCizgi: acik ? "#e5e5e5" : "#3a3a3a"
    readonly property int menuKose: 12

    // Video alanında, oynatıcı çubuğunda, küçük resimlerin üstünde (görünümden bağımsız).
    readonly property color videoYazi: "#f1f1f1"
    readonly property color videoSoluk: "#aaaaaa"
    readonly property color videoMavi: "#7cc4ff"
    // Zaman çubuğu: izlenen mavi, inmiş beyaza yakın açık gri, inmemiş orta gri.
    readonly property color inmis: "#e0e0e0"
    readonly property color inmemis: "#808080"

    // Simgeler beyaz çizilmiş (simgeler/*.svg); açık görünümde koyusu (uygulama.py, KoyuSimgeler).
    // Video alanındaki simgeler bunu kullanmaz, hep beyaz kalır.
    function simge(ad) { return acik ? "image://koyu/" + ad : Qt.resolvedUrl("../simgeler/" + ad + ".svg") }
    // Bölüm başlıklarının renkli simgeleri (29 Ekim, dört seçenekten "her bölüm kendi renginde"):
    // renk [koyu görünümde, açık görünümde], "#"siz; açık görünümde aynı rengin koyusu.
    function simgeRenkli(ad, renk) { return "image://koyu/" + ad + "/" + (acik ? renk[1] : renk[0]) }
    // Küçük resmin yüklenirken küçültüleceği genişlik (sourceSize.width): videoların küçük resmi 320 piksel
    // (mqdefault). JPEG yalnız yarıya, çeyreğe... temiz küçülüyor; 320'den 240'a gibi ara boyda harf kenarları basamak
    // basamak çıkıyordu (30 Ekim, Windows'ta %150 ekran ölçeğinde görüldü). Gösterilen boydan küçük olmayan en küçük temiz
    // bölüme inilir, kalanını ekran kartı düzgün küçültür. fiziksel: gösterilen genişlik * Screen.devicePixelRatio.
    function resimBoyu(fiziksel) {
        var b = 320
        while (b > 40 && b / 2 >= fiziksel * 0.99) b /= 2
        return b
    }
}
