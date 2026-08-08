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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QPushButton,
    QSizePolicy, QTextEdit, QVBoxLayout, QWidget)

class Ui_BookWindow(object):
    def setupUi(self, BookWindow):
        if not BookWindow.objectName():
            BookWindow.setObjectName(u"BookWindow")
        BookWindow.resize(836, 827)
        self.centralwidget = QWidget(BookWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.TextArea = QTextEdit(self.centralwidget)
        self.TextArea.setObjectName(u"TextArea")

        self.verticalLayout.addWidget(self.TextArea)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.prevPageButton = QPushButton(self.centralwidget)
        self.prevPageButton.setObjectName(u"prevPageButton")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.prevPageButton.sizePolicy().hasHeightForWidth())
        self.prevPageButton.setSizePolicy(sizePolicy)
        self.prevPageButton.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.horizontalLayout_2.addWidget(self.prevPageButton)

        self.nextPageButton = QPushButton(self.centralwidget)
        self.nextPageButton.setObjectName(u"nextPageButton")
        self.nextPageButton.setEnabled(True)
        sizePolicy.setHeightForWidth(self.nextPageButton.sizePolicy().hasHeightForWidth())
        self.nextPageButton.setSizePolicy(sizePolicy)
        self.nextPageButton.setIconSize(QSize(16, 16))

        self.horizontalLayout_2.addWidget(self.nextPageButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.verticalLayout.setStretch(0, 12)
        self.verticalLayout.setStretch(1, 1)

        self.horizontalLayout.addLayout(self.verticalLayout)

        self.widget = QWidget(self.centralwidget)
        self.widget.setObjectName(u"widget")

        self.horizontalLayout.addWidget(self.widget)

        self.horizontalLayout.setStretch(0, 5)
        self.horizontalLayout.setStretch(1, 2)
        BookWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(BookWindow)

        QMetaObject.connectSlotsByName(BookWindow)
    # setupUi

    def retranslateUi(self, BookWindow):
        BookWindow.setWindowTitle(QCoreApplication.translate("BookWindow", u"BookWindow", None))
        self.prevPageButton.setText(QCoreApplication.translate("BookWindow", u"Previous Page", None))
        self.nextPageButton.setText(QCoreApplication.translate("BookWindow", u"Next Page", None))
    # retranslateUi

