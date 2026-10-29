import QtQuick

// YouTube kısayolları: k, boşluk, j, l, oklar, f, m, c, 0-9, Home, End, <, >. mpv'nin d tuşu yok
// (görüntü düzeltme işlemciyi %170'e çıkarıyordu, 21 Ekim).
Item {
    id: k
    property bool etkin: true
    property var oynatici
    property bool shortsKipi: false   // Shorts görünümünde ↑ ↓ önceki ve sıradaki Shorts (sesi değil)
    signal shortsGec(int adim)
    signal tamEkranIstendi()
    signal cikis()
    signal sonraki()
    signal geri()
    focus: etkin

    Keys.enabled: etkin
    Keys.onPressed: function(e) {
        var o = k.oynatici
        // Alt ya da Ctrl'li tuşlar YouTube kısayolu değil; Alt+Sol geri gider (tarayıcı alışkanlığı).
        if (e.modifiers & (Qt.AltModifier | Qt.ControlModifier)) {
            if (e.key === Qt.Key_Left && (e.modifiers & Qt.AltModifier)) { k.geri(); e.accepted = true }
            return
        }
        switch (e.key) {
        case Qt.Key_K: case Qt.Key_Space: o.durdurOynat(); break
        case Qt.Key_J: o.ileriGeri(-10); break
        case Qt.Key_L: o.ileriGeri(10); break
        case Qt.Key_Left: o.ileriGeri(-5); break
        case Qt.Key_Right: o.ileriGeri(5); break
        case Qt.Key_Up: if (k.shortsKipi) k.shortsGec(-1); else o.sesAyarla(o.ses + 5); break
        case Qt.Key_Down: if (k.shortsKipi) k.shortsGec(1); else o.sesAyarla(o.ses - 5); break
        case Qt.Key_F: k.tamEkranIstendi(); break
        case Qt.Key_Escape: k.cikis(); break
        case Qt.Key_M: o.sessizDegistir(); break
        case Qt.Key_C: o.altyaziAcKapa(); break
        case Qt.Key_N: if (e.modifiers & Qt.ShiftModifier) k.sonraki(); else return; break
        case Qt.Key_Home: o.git(0); break
        case Qt.Key_End: o.git(Math.max(0, o.sure - 1)); break
        case Qt.Key_Less: o.hizAyarla(o.hiz - 0.25); break
        case Qt.Key_Greater: o.hizAyarla(o.hiz + 0.25); break
        default:
            if (e.key >= Qt.Key_0 && e.key <= Qt.Key_9) o.git(o.sure * (e.key - Qt.Key_0) / 10)
            else return
        }
        e.accepted = true
    }
}
