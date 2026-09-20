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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QHBoxLayout, QMainWindow,
    QPushButton, QSizePolicy, QTextEdit, QVBoxLayout,
    QWidget)

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
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.TextArea.sizePolicy().hasHeightForWidth())
        self.TextArea.setSizePolicy(sizePolicy)
        font = QFont()
        font.setPointSize(16)
        self.TextArea.setFont(font)
        self.TextArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.TextArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.TextArea.setReadOnly(True)

        self.verticalLayout.addWidget(self.TextArea)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.prevPageButton = QPushButton(self.centralwidget)
        self.prevPageButton.setObjectName(u"prevPageButton")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.prevPageButton.sizePolicy().hasHeightForWidth())
        self.prevPageButton.setSizePolicy(sizePolicy1)
        self.prevPageButton.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.horizontalLayout_2.addWidget(self.prevPageButton)

        self.nextPageButton = QPushButton(self.centralwidget)
        self.nextPageButton.setObjectName(u"nextPageButton")
        self.nextPageButton.setEnabled(True)
        sizePolicy1.setHeightForWidth(self.nextPageButton.sizePolicy().hasHeightForWidth())
        self.nextPageButton.setSizePolicy(sizePolicy1)
        self.nextPageButton.setIconSize(QSize(16, 16))

        self.horizontalLayout_2.addWidget(self.nextPageButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.verticalLayout.setStretch(0, 12)
        self.verticalLayout.setStretch(1, 1)

        self.horizontalLayout.addLayout(self.verticalLayout)

        self.ControlsArea = QVBoxLayout()
        self.ControlsArea.setObjectName(u"ControlsArea")
        self.FontEntry = QDoubleSpinBox(self.centralwidget)
        self.FontEntry.setObjectName(u"FontEntry")
        self.FontEntry.setMinimum(1.000000000000000)
        self.FontEntry.setMaximum(100.000000000000000)
        self.FontEntry.setValue(16.000000000000000)

        self.ControlsArea.addWidget(self.FontEntry)

        self.volume = QDoubleSpinBox(self.centralwidget)
        self.volume.setObjectName(u"volume")
        self.volume.setSingleStep(0.100000000000000)
        self.volume.setValue(1.000000000000000)

        self.ControlsArea.addWidget(self.volume)

        self.AudioStart = QPushButton(self.centralwidget)
        self.AudioStart.setObjectName(u"AudioStart")

        self.ControlsArea.addWidget(self.AudioStart)


        self.horizontalLayout.addLayout(self.ControlsArea)

        self.horizontalLayout.setStretch(0, 5)
        self.horizontalLayout.setStretch(1, 1)
        BookWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(BookWindow)

        QMetaObject.connectSlotsByName(BookWindow)
    # setupUi

    def retranslateUi(self, BookWindow):
        BookWindow.setWindowTitle(QCoreApplication.translate("BookWindow", u"BookWindow", None))
        self.TextArea.setPlaceholderText(QCoreApplication.translate("BookWindow", u"hello", None))
        self.prevPageButton.setText(QCoreApplication.translate("BookWindow", u"Previous Page", None))
        self.nextPageButton.setText(QCoreApplication.translate("BookWindow", u"Next Page", None))
        self.FontEntry.setPrefix(QCoreApplication.translate("BookWindow", u"Font Size: ", None))
        self.AudioStart.setText(QCoreApplication.translate("BookWindow", u"Start / Stop Audio", None))
    # retranslateUi

