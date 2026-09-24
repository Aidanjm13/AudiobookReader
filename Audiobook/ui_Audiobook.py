# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Audiobook.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
    QLayout, QMainWindow, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
    QWidget)

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
        self.verticalLayout_2 = QVBoxLayout(self.Books)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.topbar = QHBoxLayout()
        self.topbar.setObjectName(u"topbar")
        self.topbar.setContentsMargins(0, 0, 0, -1)
        self.uploadFilesButton = QPushButton(self.Books)
        self.uploadFilesButton.setObjectName(u"uploadFilesButton")
        self.uploadFilesButton.setBaseSize(QSize(0, 0))
        self.uploadFilesButton.setIconSize(QSize(16, 16))

        self.topbar.addWidget(self.uploadFilesButton)

        self.widget = QWidget(self.Books)
        self.widget.setObjectName(u"widget")

        self.topbar.addWidget(self.widget)

        self.topbar.setStretch(0, 1)
        self.topbar.setStretch(1, 8)

        self.verticalLayout_2.addLayout(self.topbar)

        self.booksScrollArea = QScrollArea(self.Books)
        self.booksScrollArea.setObjectName(u"booksScrollArea")
        self.booksScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.booksScrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 948, 522))
        self.booksScrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.booksScrollArea)

        self.verticalLayout_2.setStretch(0, 1)
        self.verticalLayout_2.setStretch(1, 16)
        self.tabWidget.addTab(self.Books, "")
        self.Settings = QWidget()
        self.Settings.setObjectName(u"Settings")
        self.horizontalLayout = QHBoxLayout(self.Settings)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.SettingsColumn1 = QVBoxLayout()
        self.SettingsColumn1.setObjectName(u"SettingsColumn1")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.label = QLabel(self.Settings)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMaximumSize(QSize(16777215, 16777215))

        self.horizontalLayout_3.addWidget(self.label)

        self.voicesComboBox = QComboBox(self.Settings)
        self.voicesComboBox.setObjectName(u"voicesComboBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.voicesComboBox.sizePolicy().hasHeightForWidth())
        self.voicesComboBox.setSizePolicy(sizePolicy1)
        self.voicesComboBox.setInsertPolicy(QComboBox.InsertPolicy.InsertAfterCurrent)

        self.horizontalLayout_3.addWidget(self.voicesComboBox)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.RefreshVoiceButton = QPushButton(self.Settings)
        self.RefreshVoiceButton.setObjectName(u"RefreshVoiceButton")

        self.verticalLayout.addWidget(self.RefreshVoiceButton)

        self.DownloadDeleteVoiceButton = QPushButton(self.Settings)
        self.DownloadDeleteVoiceButton.setObjectName(u"DownloadDeleteVoiceButton")

        self.verticalLayout.addWidget(self.DownloadDeleteVoiceButton)


        self.horizontalLayout_3.addLayout(self.verticalLayout)


        self.SettingsColumn1.addLayout(self.horizontalLayout_3)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.SettingsColumn1.addItem(self.verticalSpacer)


        self.horizontalLayout.addLayout(self.SettingsColumn1)

        self.horizontalSpacer = QSpacerItem(90, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.tabWidget.addTab(self.Settings, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"AudiobookLibrary", None))
        self.uploadFilesButton.setText(QCoreApplication.translate("MainWindow", u"Upload Files", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Books), QCoreApplication.translate("MainWindow", u"Books", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Voice Download:", None))
        self.RefreshVoiceButton.setText(QCoreApplication.translate("MainWindow", u"Refresh Options", None))
        self.DownloadDeleteVoiceButton.setText(QCoreApplication.translate("MainWindow", u"Download/Delete", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Settings), QCoreApplication.translate("MainWindow", u"Settings", None))
    # retranslateUi

