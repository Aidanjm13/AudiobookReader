# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'BookWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QSizePolicy, QWidget)

class Ui_BookWindow(object):
    def setupUi(self, BookWindow):
        if not BookWindow.objectName():
            BookWindow.setObjectName(u"BookWindow")
        BookWindow.resize(800, 600)
        self.centralwidget = QWidget(BookWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        BookWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(BookWindow)

        QMetaObject.connectSlotsByName(BookWindow)
    # setupUi

    def retranslateUi(self, BookWindow):
        BookWindow.setWindowTitle(QCoreApplication.translate("BookWindow", u"BookWindow", None))
    # retranslateUi

