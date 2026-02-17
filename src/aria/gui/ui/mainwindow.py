# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindowffUWtU.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    Qt,
    QTime,
    QUrl,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(750, 695)
        MainWindow.setMinimumSize(QSize(750, 695))
        MainWindow.setMaximumSize(QSize(750, 695))
        MainWindow.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        icon = QIcon(QIcon.fromTheme("emblem-system"))
        MainWindow.setWindowIcon(icon)
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.HelpAbout))
        self.actionAbout.setIcon(icon1)
        self.actionQuit = QAction(MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ApplicationExit))
        self.actionQuit.setIcon(icon2)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayoutWidget = QWidget(self.centralwidget)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(10, 10, 731, 631))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName("label")
        font = QFont()
        font.setPointSize(16)
        font.setBold(False)
        self.label.setFont(font)
        self.label.setTextFormat(Qt.TextFormat.PlainText)

        self.horizontalLayout.addWidget(self.label)

        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton_ServiceControl = QPushButton(self.verticalLayoutWidget)
        self.pushButton_ServiceControl.setObjectName(
            "pushButton_ServiceControl"
        )
        self.pushButton_ServiceControl.setEnabled(True)
        icon3 = QIcon(QIcon.fromTheme("media-playback-start"))
        self.pushButton_ServiceControl.setIcon(icon3)
        self.pushButton_ServiceControl.setFlat(False)

        self.horizontalLayout.addWidget(self.pushButton_ServiceControl)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tabWidget = QTabWidget(self.verticalLayoutWidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tabWidget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_overview = QWidget()
        self.tab_overview.setObjectName("tab_overview")
        self.verticalLayoutWidget_3 = QWidget(self.tab_overview)
        self.verticalLayoutWidget_3.setObjectName("verticalLayoutWidget_3")
        self.verticalLayoutWidget_3.setGeometry(QRect(9, 9, 2988, 541))
        self.verticalLayout_3 = QVBoxLayout(self.verticalLayoutWidget_3)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.groupBox_3 = QGroupBox(self.verticalLayoutWidget_3)
        self.groupBox_3.setObjectName("groupBox_3")
        self.formLayoutWidget_3 = QWidget(self.groupBox_3)
        self.formLayoutWidget_3.setObjectName("formLayoutWidget_3")
        self.formLayoutWidget_3.setGeometry(QRect(9, 29, 361, 141))
        self.formLayout_3 = QFormLayout(self.formLayoutWidget_3)
        self.formLayout_3.setObjectName("formLayout_3")
        self.formLayout_3.setHorizontalSpacing(20)
        self.formLayout_3.setVerticalSpacing(10)
        self.formLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label_8 = QLabel(self.formLayoutWidget_3)
        self.label_8.setObjectName("label_8")
        self.label_8.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_3.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_8
        )

        self.label_9 = QLabel(self.formLayoutWidget_3)
        self.label_9.setObjectName("label_9")
        self.label_9.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_3.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_9
        )

        self.label_12 = QLabel(self.formLayoutWidget_3)
        self.label_12.setObjectName("label_12")
        self.label_12.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_3.setWidget(
            3, QFormLayout.ItemRole.LabelRole, self.label_12
        )

        self.label_13 = QLabel(self.formLayoutWidget_3)
        self.label_13.setObjectName("label_13")
        self.label_13.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_3.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_13
        )

        self.label_ServiceURL = QLabel(self.formLayoutWidget_3)
        self.label_ServiceURL.setObjectName("label_ServiceURL")

        self.formLayout_3.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_ServiceURL
        )

        self.label_ServicePID = QLabel(self.formLayoutWidget_3)
        self.label_ServicePID.setObjectName("label_ServicePID")

        self.formLayout_3.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_ServicePID
        )

        self.label_ServiceUptime = QLabel(self.formLayoutWidget_3)
        self.label_ServiceUptime.setObjectName("label_ServiceUptime")

        self.formLayout_3.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.label_ServiceUptime
        )

        self.label_ServiceStarted = QLabel(self.formLayoutWidget_3)
        self.label_ServiceStarted.setObjectName("label_ServiceStarted")

        self.formLayout_3.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self.label_ServiceStarted
        )

        self.label_13.raise_()
        self.label_8.raise_()
        self.label_9.raise_()
        self.label_12.raise_()
        self.label_ServiceURL.raise_()
        self.label_ServicePID.raise_()
        self.label_ServiceUptime.raise_()
        self.label_ServiceStarted.raise_()
        self.pushButton_ServiceOpen = QPushButton(self.groupBox_3)
        self.pushButton_ServiceOpen.setObjectName("pushButton_ServiceOpen")
        self.pushButton_ServiceOpen.setGeometry(QRect(380, 30, 96, 27))
        icon4 = QIcon(QIcon.fromTheme("applications-internet"))
        self.pushButton_ServiceOpen.setIcon(icon4)

        self.verticalLayout_3.addWidget(self.groupBox_3)

        self.groupBox_2 = QGroupBox(self.verticalLayoutWidget_3)
        self.groupBox_2.setObjectName("groupBox_2")
        self.formLayoutWidget = QWidget(self.groupBox_2)
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(10, 30, 361, 141))
        self.formLayout = QFormLayout(self.formLayoutWidget)
        self.formLayout.setObjectName("formLayout")
        self.formLayout.setHorizontalSpacing(20)
        self.formLayout.setVerticalSpacing(10)
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.formLayoutWidget)
        self.label_2.setObjectName("label_2")
        self.label_2.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_2
        )

        self.label_DatabaseType = QLabel(self.formLayoutWidget)
        self.label_DatabaseType.setObjectName("label_DatabaseType")

        self.formLayout.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_DatabaseType
        )

        self.label_3 = QLabel(self.formLayoutWidget)
        self.label_3.setObjectName("label_3")
        self.label_3.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_3
        )

        self.label_DatabaseLocation = QLabel(self.formLayoutWidget)
        self.label_DatabaseLocation.setObjectName("label_DatabaseLocation")

        self.formLayout.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_DatabaseLocation
        )

        self.label_6 = QLabel(self.formLayoutWidget)
        self.label_6.setObjectName("label_6")
        self.label_6.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_6
        )

        self.label_DatabasePermissions = QLabel(self.formLayoutWidget)
        self.label_DatabasePermissions.setObjectName(
            "label_DatabasePermissions"
        )

        self.formLayout.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.label_DatabasePermissions
        )

        self.label_10 = QLabel(self.formLayoutWidget)
        self.label_10.setObjectName("label_10")
        self.label_10.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout.setWidget(
            3, QFormLayout.ItemRole.LabelRole, self.label_10
        )

        self.label_DatabaseSize = QLabel(self.formLayoutWidget)
        self.label_DatabaseSize.setObjectName("label_DatabaseSize")

        self.formLayout.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self.label_DatabaseSize
        )

        self.verticalLayout_3.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(self.verticalLayoutWidget_3)
        self.groupBox.setObjectName("groupBox")
        self.formLayoutWidget_2 = QWidget(self.groupBox)
        self.formLayoutWidget_2.setObjectName("formLayoutWidget_2")
        self.formLayoutWidget_2.setGeometry(QRect(10, 30, 361, 141))
        self.formLayout_2 = QFormLayout(self.formLayoutWidget_2)
        self.formLayout_2.setObjectName("formLayout_2")
        self.formLayout_2.setHorizontalSpacing(20)
        self.formLayout_2.setVerticalSpacing(10)
        self.formLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_18 = QLabel(self.formLayoutWidget_2)
        self.label_18.setObjectName("label_18")
        self.label_18.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_2.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_18
        )

        self.label_19 = QLabel(self.formLayoutWidget_2)
        self.label_19.setObjectName("label_19")
        self.label_19.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_2.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_19
        )

        self.label_20 = QLabel(self.formLayoutWidget_2)
        self.label_20.setObjectName("label_20")
        self.label_20.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_2.setWidget(
            3, QFormLayout.ItemRole.LabelRole, self.label_20
        )

        self.label_LLMChatAPIURL = QLabel(self.formLayoutWidget_2)
        self.label_LLMChatAPIURL.setObjectName("label_LLMChatAPIURL")

        self.formLayout_2.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_LLMChatAPIURL
        )

        self.label_LLMVisionAPIURL = QLabel(self.formLayoutWidget_2)
        self.label_LLMVisionAPIURL.setObjectName("label_LLMVisionAPIURL")

        self.formLayout_2.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.label_LLMVisionAPIURL
        )

        self.label_LLMEmbeddingsAPIURL = QLabel(self.formLayoutWidget_2)
        self.label_LLMEmbeddingsAPIURL.setObjectName(
            "label_LLMEmbeddingsAPIURL"
        )

        self.formLayout_2.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self.label_LLMEmbeddingsAPIURL
        )

        self.label_24 = QLabel(self.formLayoutWidget_2)
        self.label_24.setObjectName("label_24")
        self.label_24.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout_2.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_24
        )

        self.label_LLMType = QLabel(self.formLayoutWidget_2)
        self.label_LLMType.setObjectName("label_LLMType")

        self.formLayout_2.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_LLMType
        )

        self.verticalLayout_3.addWidget(self.groupBox)

        self.tabWidget.addTab(self.tab_overview, "")
        self.tab_users = QWidget()
        self.tab_users.setObjectName("tab_users")
        self.verticalLayoutWidget_4 = QWidget(self.tab_users)
        self.verticalLayoutWidget_4.setObjectName("verticalLayoutWidget_4")
        self.verticalLayoutWidget_4.setGeometry(QRect(9, 9, 711, 541))
        self.verticalLayout_4 = QVBoxLayout(self.verticalLayoutWidget_4)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.groupBox_5 = QGroupBox(self.verticalLayoutWidget_4)
        self.groupBox_5.setObjectName("groupBox_5")
        self.listWidget_CurrentUsers = QListWidget(self.groupBox_5)
        self.listWidget_CurrentUsers.setObjectName("listWidget_CurrentUsers")
        self.listWidget_CurrentUsers.setGeometry(QRect(5, 31, 581, 231))
        self.pushButton_ResetPassword = QPushButton(self.groupBox_5)
        self.pushButton_ResetPassword.setObjectName("pushButton_ResetPassword")
        self.pushButton_ResetPassword.setGeometry(QRect(600, 60, 96, 27))
        self.pushButton_EditUser = QPushButton(self.groupBox_5)
        self.pushButton_EditUser.setObjectName("pushButton_EditUser")
        self.pushButton_EditUser.setGeometry(QRect(600, 30, 96, 27))
        self.pushButton_DeleteUser = QPushButton(self.groupBox_5)
        self.pushButton_DeleteUser.setObjectName("pushButton_DeleteUser")
        self.pushButton_DeleteUser.setGeometry(QRect(600, 90, 96, 27))

        self.verticalLayout_4.addWidget(self.groupBox_5)

        self.groupBox_4 = QGroupBox(self.verticalLayoutWidget_4)
        self.groupBox_4.setObjectName("groupBox_4")
        self.formLayoutWidget_4 = QWidget(self.groupBox_4)
        self.formLayoutWidget_4.setObjectName("formLayoutWidget_4")
        self.formLayoutWidget_4.setGeometry(QRect(9, 29, 531, 211))
        self.formLayout_4 = QFormLayout(self.formLayoutWidget_4)
        self.formLayout_4.setObjectName("formLayout_4")
        self.formLayout_4.setHorizontalSpacing(20)
        self.formLayout_4.setVerticalSpacing(10)
        self.formLayout_4.setContentsMargins(0, 0, 0, 0)
        self.label_26 = QLabel(self.formLayoutWidget_4)
        self.label_26.setObjectName("label_26")

        self.formLayout_4.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_26
        )

        self.label_27 = QLabel(self.formLayoutWidget_4)
        self.label_27.setObjectName("label_27")

        self.formLayout_4.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_27
        )

        self.label_28 = QLabel(self.formLayoutWidget_4)
        self.label_28.setObjectName("label_28")

        self.formLayout_4.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_28
        )

        self.pushButton_CreateUser = QPushButton(self.formLayoutWidget_4)
        self.pushButton_CreateUser.setObjectName("pushButton_CreateUser")

        self.formLayout_4.setWidget(
            3, QFormLayout.ItemRole.LabelRole, self.pushButton_CreateUser
        )

        self.lineEdit_UserName = QLineEdit(self.formLayoutWidget_4)
        self.lineEdit_UserName.setObjectName("lineEdit_UserName")

        self.formLayout_4.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserName
        )

        self.lineEdit_UserEmail = QLineEdit(self.formLayoutWidget_4)
        self.lineEdit_UserEmail.setObjectName("lineEdit_UserEmail")

        self.formLayout_4.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserEmail
        )

        self.lineEdit_UserPassword = QLineEdit(self.formLayoutWidget_4)
        self.lineEdit_UserPassword.setObjectName("lineEdit_UserPassword")
        self.lineEdit_UserPassword.setMaxLength(48)
        self.lineEdit_UserPassword.setEchoMode(
            QLineEdit.EchoMode.PasswordEchoOnEdit
        )

        self.formLayout_4.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserPassword
        )

        self.verticalLayout_4.addWidget(self.groupBox_4)

        self.tabWidget.addTab(self.tab_users, "")
        self.tab_logs = QWidget()
        self.tab_logs.setObjectName("tab_logs")
        self.verticalLayoutWidget_2 = QWidget(self.tab_logs)
        self.verticalLayoutWidget_2.setObjectName("verticalLayoutWidget_2")
        self.verticalLayoutWidget_2.setGeometry(QRect(9, 9, 711, 541))
        self.verticalLayout_2 = QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.plainTextEdit_Logs = QPlainTextEdit(self.verticalLayoutWidget_2)
        self.plainTextEdit_Logs.setObjectName("plainTextEdit_Logs")
        self.plainTextEdit_Logs.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.plainTextEdit_Logs.setReadOnly(True)
        self.plainTextEdit_Logs.setMaximumBlockCount(1000)

        self.verticalLayout_2.addWidget(self.plainTextEdit_Logs)

        self.tabWidget.addTab(self.tab_logs, "")

        self.verticalLayout.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName("menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 750, 24))
        self.menuApplication = QMenu(self.menuBar)
        self.menuApplication.setObjectName("menuApplication")
        self.menuHelp = QMenu(self.menuBar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menuBar)
        self.statusBar = QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)

        self.menuBar.addAction(self.menuApplication.menuAction())
        self.menuBar.addAction(self.menuHelp.menuAction())
        self.menuApplication.addAction(self.actionQuit)
        self.menuHelp.addAction(self.actionAbout)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QCoreApplication.translate("MainWindow", "Aria", None)
        )
        self.actionAbout.setText(
            QCoreApplication.translate("MainWindow", "&About", None)
        )
        self.actionQuit.setText(
            QCoreApplication.translate("MainWindow", "&Quit", None)
        )
        # if QT_CONFIG(shortcut)
        self.actionQuit.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+Q", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.label.setText(
            QCoreApplication.translate(
                "MainWindow", "Aria Service Manager", None
            )
        )
        self.pushButton_ServiceControl.setText(
            QCoreApplication.translate("MainWindow", "Start", None)
        )
        self.groupBox_3.setTitle(
            QCoreApplication.translate("MainWindow", "Service", None)
        )
        self.label_8.setText(
            QCoreApplication.translate("MainWindow", "URL", None)
        )
        self.label_9.setText(
            QCoreApplication.translate("MainWindow", "Uptime", None)
        )
        self.label_12.setText(
            QCoreApplication.translate("MainWindow", "Started", None)
        )
        self.label_13.setText(
            QCoreApplication.translate("MainWindow", "PID", None)
        )
        self.label_ServiceURL.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_ServicePID.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_ServiceUptime.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_ServiceStarted.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.pushButton_ServiceOpen.setText(
            QCoreApplication.translate("MainWindow", "Open", None)
        )
        self.groupBox_2.setTitle(
            QCoreApplication.translate("MainWindow", "Database", None)
        )
        self.label_2.setText(
            QCoreApplication.translate("MainWindow", "Type", None)
        )
        self.label_DatabaseType.setText(
            QCoreApplication.translate("MainWindow", "SQLite", None)
        )
        self.label_3.setText(
            QCoreApplication.translate("MainWindow", "Location", None)
        )
        self.label_DatabaseLocation.setText(
            QCoreApplication.translate("MainWindow", "/path", None)
        )
        self.label_6.setText(
            QCoreApplication.translate("MainWindow", "Permissions", None)
        )
        self.label_DatabasePermissions.setText(
            QCoreApplication.translate("MainWindow", "RW", None)
        )
        self.label_10.setText(
            QCoreApplication.translate("MainWindow", "Size", None)
        )
        self.label_DatabaseSize.setText(
            QCoreApplication.translate("MainWindow", "8MB", None)
        )
        self.groupBox.setTitle(
            QCoreApplication.translate(
                "MainWindow", "LLM Inference APIs", None
            )
        )
        self.label_18.setText(
            QCoreApplication.translate("MainWindow", "Chat", None)
        )
        self.label_19.setText(
            QCoreApplication.translate("MainWindow", "Vision/OCR", None)
        )
        self.label_20.setText(
            QCoreApplication.translate("MainWindow", "Embeddings", None)
        )
        self.label_LLMChatAPIURL.setText(
            QCoreApplication.translate(
                "MainWindow", "http://127.0.0.1:7070/v1", None
            )
        )
        self.label_LLMVisionAPIURL.setText(
            QCoreApplication.translate(
                "MainWindow", "http://127.0.0.1:7071/v1", None
            )
        )
        self.label_LLMEmbeddingsAPIURL.setText(
            QCoreApplication.translate(
                "MainWindow", "http://127.0.0.1:7072/v1", None
            )
        )
        self.label_24.setText(
            QCoreApplication.translate("MainWindow", "Type", None)
        )
        self.label_LLMType.setText(
            QCoreApplication.translate("MainWindow", "llama.cpp", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_overview),
            QCoreApplication.translate("MainWindow", "Overview", None),
        )
        self.groupBox_5.setTitle(
            QCoreApplication.translate("MainWindow", "Current Users", None)
        )
        self.pushButton_ResetPassword.setText(
            QCoreApplication.translate("MainWindow", "Reset", None)
        )
        self.pushButton_EditUser.setText(
            QCoreApplication.translate("MainWindow", "Edit", None)
        )
        self.pushButton_DeleteUser.setText(
            QCoreApplication.translate("MainWindow", "Delete", None)
        )
        self.groupBox_4.setTitle(
            QCoreApplication.translate("MainWindow", "New", None)
        )
        self.label_26.setText(
            QCoreApplication.translate("MainWindow", "Name", None)
        )
        self.label_27.setText(
            QCoreApplication.translate("MainWindow", "E-Mail", None)
        )
        self.label_28.setText(
            QCoreApplication.translate("MainWindow", "Password", None)
        )
        self.pushButton_CreateUser.setText(
            QCoreApplication.translate("MainWindow", "Create", None)
        )
        self.lineEdit_UserPassword.setInputMask("")
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_users),
            QCoreApplication.translate("MainWindow", "Users", None),
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_logs),
            QCoreApplication.translate("MainWindow", "Logs", None),
        )
        self.menuApplication.setTitle(
            QCoreApplication.translate("MainWindow", "&Application", None)
        )
        self.menuHelp.setTitle(
            QCoreApplication.translate("MainWindow", "&Help", None)
        )

    # retranslateUi
