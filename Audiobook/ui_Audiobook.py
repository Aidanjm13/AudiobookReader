# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Audiobook.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QScrollArea,
    QSizePolicy, QTabWidget, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(992, 628)
        MainWindow.setAnimated(True)
        MainWindow.setTabShape(QTabWidget.TabShape.Triangular)
        MainWindow.setDockNestingEnabled(False)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.centralwidget.setAutoFillBackground(False)
        self.horizontalLayout_2 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.Books = QWidget()
        self.Books.setObjectName(u"Books")
        self.horizontalLayout_3 = QHBoxLayout(self.Books)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.booksScrollArea = QScrollArea(self.Books)
        self.booksScrollArea.setObjectName(u"booksScrollArea")
        self.booksScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.booksScrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 946, 558))
        self.booksScrollArea.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout_3.addWidget(self.booksScrollArea)

        self.tabWidget.addTab(self.Books, "")
        self.Settings = QWidget()
        self.Settings.setObjectName(u"Settings")
        self.horizontalLayout = QHBoxLayout(self.Settings)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.tabWidget.addTab(self.Settings, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Books), QCoreApplication.translate("MainWindow", u"Books", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Settings), QCoreApplication.translate("MainWindow", u"Settings", None))
    # retranslateUi

