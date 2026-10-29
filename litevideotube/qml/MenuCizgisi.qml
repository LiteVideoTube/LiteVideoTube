import QtQuick

// Açılır menüde bölümleri ayıran ince çizgi.
Item {
    width: 300; height: 9
    Rectangle { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 4; width: parent.width - 8; height: 1; color: Renk.menuCizgi }
}
