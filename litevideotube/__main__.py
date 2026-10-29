import sys

# Arka plan yoklaması (program kapalıyken) Qt yüklemeden çalışır: pencere modülü hiç içe alınmaz.
if "--arkada" in sys.argv:
    from .arkada import calistir
else:
    from .uygulama import calistir

sys.exit(calistir())
