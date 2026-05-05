# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.11.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMenuBar, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QStatusBar, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 700)
        MainWindow.setMinimumSize(QSize(600, 400))
        MainWindow.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        icon = QIcon(QIcon.fromTheme(u"emblem-system"))
        MainWindow.setWindowIcon(icon)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.HelpAbout))
        self.actionAbout.setIcon(icon1)
        self.actionAbout.setMenuRole(QAction.MenuRole.AboutRole)
        self.actionQuit = QAction(MainWindow)
        self.actionQuit.setObjectName(u"actionQuit")
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ApplicationExit))
        self.actionQuit.setIcon(icon2)
        self.actionQuit.setMenuRole(QAction.MenuRole.QuitRole)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_main = QVBoxLayout(self.centralwidget)
        self.verticalLayout_main.setSpacing(6)
        self.verticalLayout_main.setObjectName(u"verticalLayout_main")
        self.verticalLayout_main.setContentsMargins(10, 10, 10, 10)
        self.horizontalLayout_topbar = QHBoxLayout()
        self.horizontalLayout_topbar.setObjectName(u"horizontalLayout_topbar")
        self.label_title = QLabel(self.centralwidget)
        self.label_title.setObjectName(u"label_title")
        font = QFont()
        font.setPointSize(16)
        font.setBold(False)
        self.label_title.setFont(font)
        self.label_title.setTextFormat(Qt.TextFormat.PlainText)

        self.horizontalLayout_topbar.addWidget(self.label_title)

        self.horizontalSpacer_topbar = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_topbar.addItem(self.horizontalSpacer_topbar)

        self.pushButton_ServiceStop = QPushButton(self.centralwidget)
        self.pushButton_ServiceStop.setObjectName(u"pushButton_ServiceStop")
        self.pushButton_ServiceStop.setEnabled(False)
        icon3 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.SystemShutdown))
        self.pushButton_ServiceStop.setIcon(icon3)

        self.horizontalLayout_topbar.addWidget(self.pushButton_ServiceStop)

        self.pushButton_ServiceStart = QPushButton(self.centralwidget)
        self.pushButton_ServiceStart.setObjectName(u"pushButton_ServiceStart")
        self.pushButton_ServiceStart.setEnabled(False)
        icon4 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart))
        self.pushButton_ServiceStart.setIcon(icon4)

        self.horizontalLayout_topbar.addWidget(self.pushButton_ServiceStart)


        self.verticalLayout_main.addLayout(self.horizontalLayout_topbar)

        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_overview = QWidget()
        self.tab_overview.setObjectName(u"tab_overview")
        self.verticalLayout_overview = QVBoxLayout(self.tab_overview)
        self.verticalLayout_overview.setSpacing(8)
        self.verticalLayout_overview.setObjectName(u"verticalLayout_overview")
        self.verticalLayout_overview.setContentsMargins(8, 8, 8, 8)
        self.groupBox_Service = QGroupBox(self.tab_overview)
        self.groupBox_Service.setObjectName(u"groupBox_Service")
        self.horizontalLayout_service = QHBoxLayout(self.groupBox_Service)
        self.horizontalLayout_service.setObjectName(u"horizontalLayout_service")
        self.horizontalLayout_service.setContentsMargins(8, 8, 8, 8)
        self.formLayout_service = QFormLayout()
        self.formLayout_service.setObjectName(u"formLayout_service")
        self.formLayout_service.setHorizontalSpacing(20)
        self.formLayout_service.setVerticalSpacing(8)
        self.label_svc_url_lbl = QLabel(self.groupBox_Service)
        self.label_svc_url_lbl.setObjectName(u"label_svc_url_lbl")
        self.label_svc_url_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_service.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_svc_url_lbl)

        self.label_ServiceURL = QLabel(self.groupBox_Service)
        self.label_ServiceURL.setObjectName(u"label_ServiceURL")
        self.label_ServiceURL.setTextFormat(Qt.TextFormat.RichText)
        self.label_ServiceURL.setOpenExternalLinks(True)

        self.formLayout_service.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_ServiceURL)

        self.label_svc_pid_lbl = QLabel(self.groupBox_Service)
        self.label_svc_pid_lbl.setObjectName(u"label_svc_pid_lbl")
        self.label_svc_pid_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_service.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_svc_pid_lbl)

        self.label_ServicePID = QLabel(self.groupBox_Service)
        self.label_ServicePID.setObjectName(u"label_ServicePID")

        self.formLayout_service.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_ServicePID)

        self.label_svc_uptime_lbl = QLabel(self.groupBox_Service)
        self.label_svc_uptime_lbl.setObjectName(u"label_svc_uptime_lbl")
        self.label_svc_uptime_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_service.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_svc_uptime_lbl)

        self.label_ServiceUptime = QLabel(self.groupBox_Service)
        self.label_ServiceUptime.setObjectName(u"label_ServiceUptime")

        self.formLayout_service.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_ServiceUptime)

        self.label_svc_started_lbl = QLabel(self.groupBox_Service)
        self.label_svc_started_lbl.setObjectName(u"label_svc_started_lbl")
        self.label_svc_started_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_service.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_svc_started_lbl)

        self.label_ServiceStarted = QLabel(self.groupBox_Service)
        self.label_ServiceStarted.setObjectName(u"label_ServiceStarted")

        self.formLayout_service.setWidget(3, QFormLayout.ItemRole.FieldRole, self.label_ServiceStarted)


        self.horizontalLayout_service.addLayout(self.formLayout_service)

        self.horizontalSpacer_service = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_service.addItem(self.horizontalSpacer_service)

        self.verticalLayout_serviceStatus = QVBoxLayout()
        self.verticalLayout_serviceStatus.setObjectName(u"verticalLayout_serviceStatus")
        self.label_ServiceStatus = QLabel(self.groupBox_Service)
        self.label_ServiceStatus.setObjectName(u"label_ServiceStatus")
        self.label_ServiceStatus.setStyleSheet(u"QLabel {\n"
"    background-color: #616161;\n"
"    color: white;\n"
"    font-size: 13pt;\n"
"    padding: 4px 14px;\n"
"    border-radius: 6px;\n"
"}")
        self.label_ServiceStatus.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_serviceStatus.addWidget(self.label_ServiceStatus)

        self.pushButton_ServiceOpen = QPushButton(self.groupBox_Service)
        self.pushButton_ServiceOpen.setObjectName(u"pushButton_ServiceOpen")
        self.pushButton_ServiceOpen.setEnabled(False)
        icon5 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.UserAvailable))
        self.pushButton_ServiceOpen.setIcon(icon5)

        self.verticalLayout_serviceStatus.addWidget(self.pushButton_ServiceOpen)

        self.verticalSpacer_serviceStatus = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_serviceStatus.addItem(self.verticalSpacer_serviceStatus)


        self.horizontalLayout_service.addLayout(self.verticalLayout_serviceStatus)


        self.verticalLayout_overview.addWidget(self.groupBox_Service)

        self.horizontalLayout_overview_bottom = QHBoxLayout()
        self.horizontalLayout_overview_bottom.setSpacing(8)
        self.horizontalLayout_overview_bottom.setObjectName(u"horizontalLayout_overview_bottom")
        self.groupBox_Database = QGroupBox(self.tab_overview)
        self.groupBox_Database.setObjectName(u"groupBox_Database")
        self.formLayout_database = QFormLayout(self.groupBox_Database)
        self.formLayout_database.setObjectName(u"formLayout_database")
        self.formLayout_database.setHorizontalSpacing(20)
        self.formLayout_database.setVerticalSpacing(8)
        self.formLayout_database.setContentsMargins(8, 8, 8, 8)
        self.label_db_type_lbl = QLabel(self.groupBox_Database)
        self.label_db_type_lbl.setObjectName(u"label_db_type_lbl")
        self.label_db_type_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_database.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_db_type_lbl)

        self.label_DatabaseType = QLabel(self.groupBox_Database)
        self.label_DatabaseType.setObjectName(u"label_DatabaseType")

        self.formLayout_database.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_DatabaseType)

        self.label_db_location_lbl = QLabel(self.groupBox_Database)
        self.label_db_location_lbl.setObjectName(u"label_db_location_lbl")
        self.label_db_location_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_database.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_db_location_lbl)

        self.label_DatabaseLocation = QLabel(self.groupBox_Database)
        self.label_DatabaseLocation.setObjectName(u"label_DatabaseLocation")

        self.formLayout_database.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_DatabaseLocation)

        self.label_db_exists_lbl = QLabel(self.groupBox_Database)
        self.label_db_exists_lbl.setObjectName(u"label_db_exists_lbl")
        self.label_db_exists_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_database.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_db_exists_lbl)

        self.label_DatabaseFileExists = QLabel(self.groupBox_Database)
        self.label_DatabaseFileExists.setObjectName(u"label_DatabaseFileExists")

        self.formLayout_database.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_DatabaseFileExists)

        self.label_db_size_lbl = QLabel(self.groupBox_Database)
        self.label_db_size_lbl.setObjectName(u"label_db_size_lbl")
        self.label_db_size_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_database.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_db_size_lbl)

        self.label_DatabaseSize = QLabel(self.groupBox_Database)
        self.label_DatabaseSize.setObjectName(u"label_DatabaseSize")

        self.formLayout_database.setWidget(3, QFormLayout.ItemRole.FieldRole, self.label_DatabaseSize)


        self.horizontalLayout_overview_bottom.addWidget(self.groupBox_Database)

        self.groupBox_LLMAPIs = QGroupBox(self.tab_overview)
        self.groupBox_LLMAPIs.setObjectName(u"groupBox_LLMAPIs")
        self.formLayout_llmapis = QFormLayout(self.groupBox_LLMAPIs)
        self.formLayout_llmapis.setObjectName(u"formLayout_llmapis")
        self.formLayout_llmapis.setHorizontalSpacing(20)
        self.formLayout_llmapis.setVerticalSpacing(8)
        self.formLayout_llmapis.setContentsMargins(8, 8, 8, 8)
        self.label_llm_type_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_type_lbl.setObjectName(u"label_llm_type_lbl")
        self.label_llm_type_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_llmapis.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_llm_type_lbl)

        self.label_LLMType = QLabel(self.groupBox_LLMAPIs)
        self.label_LLMType.setObjectName(u"label_LLMType")

        self.formLayout_llmapis.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_LLMType)

        self.label_llm_chat_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_chat_lbl.setObjectName(u"label_llm_chat_lbl")
        self.label_llm_chat_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_llmapis.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_llm_chat_lbl)

        self.label_LLMChatAPIURL = QLabel(self.groupBox_LLMAPIs)
        self.label_LLMChatAPIURL.setObjectName(u"label_LLMChatAPIURL")
        self.label_LLMChatAPIURL.setTextFormat(Qt.TextFormat.RichText)
        self.label_LLMChatAPIURL.setOpenExternalLinks(True)

        self.formLayout_llmapis.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_LLMChatAPIURL)

        self.label_llm_vision_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_vision_lbl.setObjectName(u"label_llm_vision_lbl")
        self.label_llm_vision_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_llmapis.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_llm_vision_lbl)

        self.label_LLMVisionAPIURL = QLabel(self.groupBox_LLMAPIs)
        self.label_LLMVisionAPIURL.setObjectName(u"label_LLMVisionAPIURL")
        self.label_LLMVisionAPIURL.setTextFormat(Qt.TextFormat.RichText)
        self.label_LLMVisionAPIURL.setOpenExternalLinks(True)

        self.formLayout_llmapis.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_LLMVisionAPIURL)

        self.label_llm_vectordb_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_vectordb_lbl.setObjectName(u"label_llm_vectordb_lbl")
        self.label_llm_vectordb_lbl.setStyleSheet(u"color: #888;")

        self.formLayout_llmapis.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_llm_vectordb_lbl)

        self.label_VectorDB = QLabel(self.groupBox_LLMAPIs)
        self.label_VectorDB.setObjectName(u"label_VectorDB")

        self.formLayout_llmapis.setWidget(3, QFormLayout.ItemRole.FieldRole, self.label_VectorDB)


        self.horizontalLayout_overview_bottom.addWidget(self.groupBox_LLMAPIs)


        self.verticalLayout_overview.addLayout(self.horizontalLayout_overview_bottom)

        self.label_DebugLogsPath = QLabel(self.tab_overview)
        self.label_DebugLogsPath.setObjectName(u"label_DebugLogsPath")
        self.label_DebugLogsPath.setVisible(False)

        self.verticalLayout_overview.addWidget(self.label_DebugLogsPath)

        self.label_DatabasePermissions = QLabel(self.tab_overview)
        self.label_DatabasePermissions.setObjectName(u"label_DatabasePermissions")
        self.label_DatabasePermissions.setVisible(False)

        self.verticalLayout_overview.addWidget(self.label_DatabasePermissions)

        self.verticalSpacer_overview = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_overview.addItem(self.verticalSpacer_overview)

        self.tabWidget.addTab(self.tab_overview, "")
        self.tab_setup = QWidget()
        self.tab_setup.setObjectName(u"tab_setup")
        self.verticalLayout_setup = QVBoxLayout(self.tab_setup)
        self.verticalLayout_setup.setSpacing(8)
        self.verticalLayout_setup.setObjectName(u"verticalLayout_setup")
        self.verticalLayout_setup.setContentsMargins(8, 8, 8, 8)
        self.groupBox_Vllm = QGroupBox(self.tab_setup)
        self.groupBox_Vllm.setObjectName(u"groupBox_Vllm")
        self.verticalLayout_vllm = QVBoxLayout(self.groupBox_Vllm)
        self.verticalLayout_vllm.setObjectName(u"verticalLayout_vllm")
        self.verticalLayout_vllm.setContentsMargins(8, 8, 8, 8)
        self.formLayout_vllm_info = QFormLayout()
        self.formLayout_vllm_info.setObjectName(u"formLayout_vllm_info")
        self.formLayout_vllm_info.setHorizontalSpacing(20)
        self.formLayout_vllm_info.setVerticalSpacing(6)
        self.label_vllm_status_lbl = QLabel(self.groupBox_Vllm)
        self.label_vllm_status_lbl.setObjectName(u"label_vllm_status_lbl")

        self.formLayout_vllm_info.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_vllm_status_lbl)

        self.label_VllmVersion = QLabel(self.groupBox_Vllm)
        self.label_VllmVersion.setObjectName(u"label_VllmVersion")

        self.formLayout_vllm_info.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_VllmVersion)


        self.verticalLayout_vllm.addLayout(self.formLayout_vllm_info)

        self.horizontalLayout_vllmInstall = QHBoxLayout()
        self.horizontalLayout_vllmInstall.setObjectName(u"horizontalLayout_vllmInstall")
        self.pushButton_VllmInstall = QPushButton(self.groupBox_Vllm)
        self.pushButton_VllmInstall.setObjectName(u"pushButton_VllmInstall")
        icon6 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.GoDown))
        self.pushButton_VllmInstall.setIcon(icon6)

        self.horizontalLayout_vllmInstall.addWidget(self.pushButton_VllmInstall)

        self.horizontalSpacer_vllmDl = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_vllmInstall.addItem(self.horizontalSpacer_vllmDl)


        self.verticalLayout_vllm.addLayout(self.horizontalLayout_vllmInstall)


        self.verticalLayout_vllm.addWidget()

        self.plainTextEdit_VllmOutput = QPlainTextEdit(self.groupBox_Vllm)
        self.plainTextEdit_VllmOutput.setObjectName(u"plainTextEdit_VllmOutput")
        font1 = QFont()
        font1.setFamilies([u"Courier New"])
        font1.setPointSize(9)
        self.plainTextEdit_VllmOutput.setFont(font1)
        self.plainTextEdit_VllmOutput.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.plainTextEdit_VllmOutput.setReadOnly(True)

        self.verticalLayout_vllm.addWidget(self.plainTextEdit_VllmOutput)


        self.verticalLayout_setup.addWidget(self.groupBox_Vllm)

        self.groupBox_Models = QGroupBox(self.tab_setup)
        self.groupBox_Models.setObjectName(u"groupBox_Models")
        self.verticalLayout_models = QVBoxLayout(self.groupBox_Models)
        self.verticalLayout_models.setObjectName(u"verticalLayout_models")
        self.verticalLayout_models.setContentsMargins(8, 8, 8, 8)
        self.formLayout_models_status = QFormLayout()
        self.formLayout_models_status.setObjectName(u"formLayout_models_status")
        self.formLayout_models_status.setHorizontalSpacing(20)
        self.formLayout_models_status.setVerticalSpacing(6)
        self.label_model_chat_lbl = QLabel(self.groupBox_Models)
        self.label_model_chat_lbl.setObjectName(u"label_model_chat_lbl")

        self.formLayout_models_status.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_model_chat_lbl)

        self.label_ModelChat_Status = QLabel(self.groupBox_Models)
        self.label_ModelChat_Status.setObjectName(u"label_ModelChat_Status")

        self.formLayout_models_status.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_ModelChat_Status)

        self.label_model_vl_lbl = QLabel(self.groupBox_Models)
        self.label_model_vl_lbl.setObjectName(u"label_model_vl_lbl")

        self.formLayout_models_status.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_model_vl_lbl)

        self.label_ModelVL_Status = QLabel(self.groupBox_Models)
        self.label_ModelVL_Status.setObjectName(u"label_ModelVL_Status")

        self.formLayout_models_status.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_ModelVL_Status)

        self.label_model_emb_lbl = QLabel(self.groupBox_Models)
        self.label_model_emb_lbl.setObjectName(u"label_model_emb_lbl")

        self.formLayout_models_status.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_model_emb_lbl)

        self.label_ModelEmbeddings_Status = QLabel(self.groupBox_Models)
        self.label_ModelEmbeddings_Status.setObjectName(u"label_ModelEmbeddings_Status")

        self.formLayout_models_status.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_ModelEmbeddings_Status)


        self.verticalLayout_models.addLayout(self.formLayout_models_status)

        self.horizontalLayout_modelDownload = QHBoxLayout()
        self.horizontalLayout_modelDownload.setObjectName(u"horizontalLayout_modelDownload")
        self.label_model_select_lbl = QLabel(self.groupBox_Models)
        self.label_model_select_lbl.setObjectName(u"label_model_select_lbl")

        self.horizontalLayout_modelDownload.addWidget(self.label_model_select_lbl)

        self.comboBox_ModelSelect = QComboBox(self.groupBox_Models)
        self.comboBox_ModelSelect.addItem("")
        self.comboBox_ModelSelect.addItem("")
        self.comboBox_ModelSelect.addItem("")
        self.comboBox_ModelSelect.setObjectName(u"comboBox_ModelSelect")

        self.horizontalLayout_modelDownload.addWidget(self.comboBox_ModelSelect)

        self.pushButton_ModelDownload = QPushButton(self.groupBox_Models)
        self.pushButton_ModelDownload.setObjectName(u"pushButton_ModelDownload")
        self.pushButton_ModelDownload.setIcon(icon6)

        self.horizontalLayout_modelDownload.addWidget(self.pushButton_ModelDownload)

        self.horizontalSpacer_modelDl = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_modelDownload.addItem(self.horizontalSpacer_modelDl)


        self.verticalLayout_models.addLayout(self.horizontalLayout_modelDownload)

        self.groupBox_ModelsAdvanced = QGroupBox(self.groupBox_Models)
        self.groupBox_ModelsAdvanced.setObjectName(u"groupBox_ModelsAdvanced")
        self.groupBox_ModelsAdvanced.setCheckable(True)
        self.groupBox_ModelsAdvanced.setChecked(False)
        self.horizontalLayout_modelsAdvanced = QHBoxLayout(self.groupBox_ModelsAdvanced)
        self.horizontalLayout_modelsAdvanced.setObjectName(u"horizontalLayout_modelsAdvanced")
        self.label_hf_token_lbl = QLabel(self.groupBox_ModelsAdvanced)
        self.label_hf_token_lbl.setObjectName(u"label_hf_token_lbl")

        self.horizontalLayout_modelsAdvanced.addWidget(self.label_hf_token_lbl)

        self.lineEdit_HFToken = QLineEdit(self.groupBox_ModelsAdvanced)
        self.lineEdit_HFToken.setObjectName(u"lineEdit_HFToken")
        self.lineEdit_HFToken.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)

        self.horizontalLayout_modelsAdvanced.addWidget(self.lineEdit_HFToken)

        self.checkBox_ModelForce = QCheckBox(self.groupBox_ModelsAdvanced)
        self.checkBox_ModelForce.setObjectName(u"checkBox_ModelForce")

        self.horizontalLayout_modelsAdvanced.addWidget(self.checkBox_ModelForce)


        self.verticalLayout_models.addWidget(self.groupBox_ModelsAdvanced)

        self.plainTextEdit_ModelOutput = QPlainTextEdit(self.groupBox_Models)
        self.plainTextEdit_ModelOutput.setObjectName(u"plainTextEdit_ModelOutput")
        self.plainTextEdit_ModelOutput.setFont(font1)
        self.plainTextEdit_ModelOutput.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.plainTextEdit_ModelOutput.setReadOnly(True)

        self.verticalLayout_models.addWidget(self.plainTextEdit_ModelOutput)


        self.verticalLayout_setup.addWidget(self.groupBox_Models)

        self.groupBox_Lightpanda = QGroupBox(self.tab_setup)
        self.groupBox_Lightpanda.setObjectName(u"groupBox_Lightpanda")
        self.verticalLayout_lightpanda = QVBoxLayout(self.groupBox_Lightpanda)
        self.verticalLayout_lightpanda.setObjectName(u"verticalLayout_lightpanda")
        self.verticalLayout_lightpanda.setContentsMargins(8, 8, 8, 8)
        self.formLayout_lightpanda_status = QFormLayout()
        self.formLayout_lightpanda_status.setObjectName(u"formLayout_lightpanda_status")
        self.formLayout_lightpanda_status.setHorizontalSpacing(20)
        self.formLayout_lightpanda_status.setVerticalSpacing(6)
        self.label_lightpanda_bindir_lbl = QLabel(self.groupBox_Lightpanda)
        self.label_lightpanda_bindir_lbl.setObjectName(u"label_lightpanda_bindir_lbl")

        self.formLayout_lightpanda_status.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_lightpanda_bindir_lbl)

        self.label_Lightpanda_BinDir = QLabel(self.groupBox_Lightpanda)
        self.label_Lightpanda_BinDir.setObjectName(u"label_Lightpanda_BinDir")

        self.formLayout_lightpanda_status.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_Lightpanda_BinDir)

        self.label_lightpanda_version_lbl = QLabel(self.groupBox_Lightpanda)
        self.label_lightpanda_version_lbl.setObjectName(u"label_lightpanda_version_lbl")

        self.formLayout_lightpanda_status.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_lightpanda_version_lbl)

        self.label_Lightpanda_Version = QLabel(self.groupBox_Lightpanda)
        self.label_Lightpanda_Version.setObjectName(u"label_Lightpanda_Version")

        self.formLayout_lightpanda_status.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_Lightpanda_Version)

        self.label_lightpanda_status_lbl = QLabel(self.groupBox_Lightpanda)
        self.label_lightpanda_status_lbl.setObjectName(u"label_lightpanda_status_lbl")

        self.formLayout_lightpanda_status.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_lightpanda_status_lbl)

        self.label_Lightpanda_Status = QLabel(self.groupBox_Lightpanda)
        self.label_Lightpanda_Status.setObjectName(u"label_Lightpanda_Status")

        self.formLayout_lightpanda_status.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_Lightpanda_Status)


        self.verticalLayout_lightpanda.addLayout(self.formLayout_lightpanda_status)

        self.horizontalLayout_lightpandaDownload = QHBoxLayout()
        self.horizontalLayout_lightpandaDownload.setObjectName(u"horizontalLayout_lightpandaDownload")
        self.pushButton_LightpandaDownload = QPushButton(self.groupBox_Lightpanda)
        self.pushButton_LightpandaDownload.setObjectName(u"pushButton_LightpandaDownload")
        self.pushButton_LightpandaDownload.setIcon(icon6)

        self.horizontalLayout_lightpandaDownload.addWidget(self.pushButton_LightpandaDownload)

        self.horizontalSpacer_lightpandaDl = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_lightpandaDownload.addItem(self.horizontalSpacer_lightpandaDl)


        self.verticalLayout_lightpanda.addLayout(self.horizontalLayout_lightpandaDownload)

        self.groupBox_LightpandaAdvanced = QGroupBox(self.groupBox_Lightpanda)
        self.groupBox_LightpandaAdvanced.setObjectName(u"groupBox_LightpandaAdvanced")
        self.groupBox_LightpandaAdvanced.setCheckable(True)
        self.groupBox_LightpandaAdvanced.setChecked(False)
        self.horizontalLayout_lightpandaAdvanced = QHBoxLayout(self.groupBox_LightpandaAdvanced)
        self.horizontalLayout_lightpandaAdvanced.setObjectName(u"horizontalLayout_lightpandaAdvanced")
        self.label_lightpanda_version_lbl_2 = QLabel(self.groupBox_LightpandaAdvanced)
        self.label_lightpanda_version_lbl_2.setObjectName(u"label_lightpanda_version_lbl_2")

        self.horizontalLayout_lightpandaAdvanced.addWidget(self.label_lightpanda_version_lbl_2)

        self.lineEdit_LightpandaVersion = QLineEdit(self.groupBox_LightpandaAdvanced)
        self.lineEdit_LightpandaVersion.setObjectName(u"lineEdit_LightpandaVersion")

        self.horizontalLayout_lightpandaAdvanced.addWidget(self.lineEdit_LightpandaVersion)


        self.verticalLayout_lightpanda.addWidget(self.groupBox_LightpandaAdvanced)

        self.plainTextEdit_LightpandaOutput = QPlainTextEdit(self.groupBox_Lightpanda)
        self.plainTextEdit_LightpandaOutput.setObjectName(u"plainTextEdit_LightpandaOutput")
        self.plainTextEdit_LightpandaOutput.setFont(font1)
        self.plainTextEdit_LightpandaOutput.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.plainTextEdit_LightpandaOutput.setReadOnly(True)

        self.verticalLayout_lightpanda.addWidget(self.plainTextEdit_LightpandaOutput)


        self.verticalLayout_setup.addWidget(self.groupBox_Lightpanda)

        self.verticalSpacer_setup = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_setup.addItem(self.verticalSpacer_setup)

        self.tabWidget.addTab(self.tab_setup, "")
        self.tab_users = QWidget()
        self.tab_users.setObjectName(u"tab_users")
        self.horizontalLayout_users = QHBoxLayout(self.tab_users)
        self.horizontalLayout_users.setSpacing(12)
        self.horizontalLayout_users.setObjectName(u"horizontalLayout_users")
        self.horizontalLayout_users.setContentsMargins(8, 8, 8, 8)
        self.groupBox_CreateUser = QGroupBox(self.tab_users)
        self.groupBox_CreateUser.setObjectName(u"groupBox_CreateUser")
        self.formLayout_createUser = QFormLayout(self.groupBox_CreateUser)
        self.formLayout_createUser.setObjectName(u"formLayout_createUser")
        self.formLayout_createUser.setHorizontalSpacing(12)
        self.formLayout_createUser.setVerticalSpacing(8)
        self.formLayout_createUser.setContentsMargins(8, 8, 8, 8)
        self.label_user_name_lbl = QLabel(self.groupBox_CreateUser)
        self.label_user_name_lbl.setObjectName(u"label_user_name_lbl")

        self.formLayout_createUser.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_user_name_lbl)

        self.lineEdit_UserName = QLineEdit(self.groupBox_CreateUser)
        self.lineEdit_UserName.setObjectName(u"lineEdit_UserName")

        self.formLayout_createUser.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserName)

        self.label_user_email_lbl = QLabel(self.groupBox_CreateUser)
        self.label_user_email_lbl.setObjectName(u"label_user_email_lbl")

        self.formLayout_createUser.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_user_email_lbl)

        self.lineEdit_UserEmail = QLineEdit(self.groupBox_CreateUser)
        self.lineEdit_UserEmail.setObjectName(u"lineEdit_UserEmail")

        self.formLayout_createUser.setWidget(1, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserEmail)

        self.label_user_password_lbl = QLabel(self.groupBox_CreateUser)
        self.label_user_password_lbl.setObjectName(u"label_user_password_lbl")

        self.formLayout_createUser.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_user_password_lbl)

        self.lineEdit_UserPassword = QLineEdit(self.groupBox_CreateUser)
        self.lineEdit_UserPassword.setObjectName(u"lineEdit_UserPassword")
        self.lineEdit_UserPassword.setMaxLength(48)
        self.lineEdit_UserPassword.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)

        self.formLayout_createUser.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserPassword)

        self.label_user_confirm_password_lbl = QLabel(self.groupBox_CreateUser)
        self.label_user_confirm_password_lbl.setObjectName(u"label_user_confirm_password_lbl")

        self.formLayout_createUser.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_user_confirm_password_lbl)

        self.lineEdit_UserConfirmPassword = QLineEdit(self.groupBox_CreateUser)
        self.lineEdit_UserConfirmPassword.setObjectName(u"lineEdit_UserConfirmPassword")
        self.lineEdit_UserConfirmPassword.setMaxLength(48)
        self.lineEdit_UserConfirmPassword.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)

        self.formLayout_createUser.setWidget(3, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserConfirmPassword)

        self.label_PasswordStrength = QLabel(self.groupBox_CreateUser)
        self.label_PasswordStrength.setObjectName(u"label_PasswordStrength")

        self.formLayout_createUser.setWidget(4, QFormLayout.ItemRole.FieldRole, self.label_PasswordStrength)

        self.pushButton_CreateUser = QPushButton(self.groupBox_CreateUser)
        self.pushButton_CreateUser.setObjectName(u"pushButton_CreateUser")
        self.pushButton_CreateUser.setEnabled(False)

        self.formLayout_createUser.setWidget(5, QFormLayout.ItemRole.FieldRole, self.pushButton_CreateUser)


        self.horizontalLayout_users.addWidget(self.groupBox_CreateUser)

        self.verticalLayout_userList = QVBoxLayout()
        self.verticalLayout_userList.setObjectName(u"verticalLayout_userList")
        self.listWidget_CurrentUsers = QListWidget(self.tab_users)
        self.listWidget_CurrentUsers.setObjectName(u"listWidget_CurrentUsers")

        self.verticalLayout_userList.addWidget(self.listWidget_CurrentUsers)

        self.horizontalLayout_userButtons = QHBoxLayout()
        self.horizontalLayout_userButtons.setObjectName(u"horizontalLayout_userButtons")
        self.pushButton_EditUser = QPushButton(self.tab_users)
        self.pushButton_EditUser.setObjectName(u"pushButton_EditUser")
        self.pushButton_EditUser.setEnabled(False)

        self.horizontalLayout_userButtons.addWidget(self.pushButton_EditUser)

        self.pushButton_DeleteUser = QPushButton(self.tab_users)
        self.pushButton_DeleteUser.setObjectName(u"pushButton_DeleteUser")
        self.pushButton_DeleteUser.setEnabled(False)
        icon7 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditDelete))
        self.pushButton_DeleteUser.setIcon(icon7)

        self.horizontalLayout_userButtons.addWidget(self.pushButton_DeleteUser)


        self.verticalLayout_userList.addLayout(self.horizontalLayout_userButtons)


        self.horizontalLayout_users.addLayout(self.verticalLayout_userList)

        self.tabWidget.addTab(self.tab_users, "")
        self.tab_logs = QWidget()
        self.tab_logs.setObjectName(u"tab_logs")
        self.verticalLayout_logs = QVBoxLayout(self.tab_logs)
        self.verticalLayout_logs.setSpacing(6)
        self.verticalLayout_logs.setObjectName(u"verticalLayout_logs")
        self.verticalLayout_logs.setContentsMargins(8, 8, 8, 8)
        self.horizontalLayout_logFilter = QHBoxLayout()
        self.horizontalLayout_logFilter.setObjectName(u"horizontalLayout_logFilter")
        self.lineEdit_LogSearch = QLineEdit(self.tab_logs)
        self.lineEdit_LogSearch.setObjectName(u"lineEdit_LogSearch")
        self.lineEdit_LogSearch.setClearButtonEnabled(True)

        self.horizontalLayout_logFilter.addWidget(self.lineEdit_LogSearch)

        self.comboBox_LogFilter = QComboBox(self.tab_logs)
        self.comboBox_LogFilter.addItem("")
        self.comboBox_LogFilter.addItem("")
        self.comboBox_LogFilter.addItem("")
        self.comboBox_LogFilter.addItem("")
        self.comboBox_LogFilter.setObjectName(u"comboBox_LogFilter")
        self.comboBox_LogFilter.setMinimumContentsLength(8)

        self.horizontalLayout_logFilter.addWidget(self.comboBox_LogFilter)


        self.verticalLayout_logs.addLayout(self.horizontalLayout_logFilter)

        self.textEdit_Logs = QTextEdit(self.tab_logs)
        self.textEdit_Logs.setObjectName(u"textEdit_Logs")
        font2 = QFont()
        font2.setFamilies([u"Courier New"])
        font2.setPointSize(10)
        self.textEdit_Logs.setFont(font2)
        self.textEdit_Logs.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.textEdit_Logs.setReadOnly(True)

        self.verticalLayout_logs.addWidget(self.textEdit_Logs)

        self.horizontalLayout_logsToolbar = QHBoxLayout()
        self.horizontalLayout_logsToolbar.setObjectName(u"horizontalLayout_logsToolbar")
        self.pushButton_AutoRefresh = QPushButton(self.tab_logs)
        self.pushButton_AutoRefresh.setObjectName(u"pushButton_AutoRefresh")
        icon8 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause))
        self.pushButton_AutoRefresh.setIcon(icon8)

        self.horizontalLayout_logsToolbar.addWidget(self.pushButton_AutoRefresh)

        self.horizontalSpacer_logsToolbar = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_logsToolbar.addItem(self.horizontalSpacer_logsToolbar)

        self.pushButton_RefreshLogs = QPushButton(self.tab_logs)
        self.pushButton_RefreshLogs.setObjectName(u"pushButton_RefreshLogs")
        icon9 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ViewRefresh))
        self.pushButton_RefreshLogs.setIcon(icon9)

        self.horizontalLayout_logsToolbar.addWidget(self.pushButton_RefreshLogs)


        self.verticalLayout_logs.addLayout(self.horizontalLayout_logsToolbar)

        self.tabWidget.addTab(self.tab_logs, "")
        self.tab_settings = QWidget()
        self.tab_settings.setObjectName(u"tab_settings")
        self.verticalLayout_settings = QVBoxLayout(self.tab_settings)
        self.verticalLayout_settings.setSpacing(8)
        self.verticalLayout_settings.setObjectName(u"verticalLayout_settings")
        self.verticalLayout_settings.setContentsMargins(8, 8, 8, 8)
        self.groupBox_SettingsBasic = QGroupBox(self.tab_settings)
        self.groupBox_SettingsBasic.setObjectName(u"groupBox_SettingsBasic")
        self.formLayout_settingsBasic = QFormLayout(self.groupBox_SettingsBasic)
        self.formLayout_settingsBasic.setObjectName(u"formLayout_settingsBasic")
        self.formLayout_settingsBasic.setHorizontalSpacing(20)
        self.formLayout_settingsBasic.setVerticalSpacing(8)
        self.formLayout_settingsBasic.setContentsMargins(8, 8, 8, 8)
        self.label_ServerHostLbl = QLabel(self.groupBox_SettingsBasic)
        self.label_ServerHostLbl.setObjectName(u"label_ServerHostLbl")

        self.formLayout_settingsBasic.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_ServerHostLbl)

        self.lineEdit_ServerHost = QLineEdit(self.groupBox_SettingsBasic)
        self.lineEdit_ServerHost.setObjectName(u"lineEdit_ServerHost")

        self.formLayout_settingsBasic.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lineEdit_ServerHost)

        self.label_ServerPortLbl = QLabel(self.groupBox_SettingsBasic)
        self.label_ServerPortLbl.setObjectName(u"label_ServerPortLbl")

        self.formLayout_settingsBasic.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_ServerPortLbl)

        self.spinBox_ServerPort = QSpinBox(self.groupBox_SettingsBasic)
        self.spinBox_ServerPort.setObjectName(u"spinBox_ServerPort")
        self.spinBox_ServerPort.setMinimum(1)
        self.spinBox_ServerPort.setMaximum(65535)
        self.spinBox_ServerPort.setValue(9876)

        self.formLayout_settingsBasic.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spinBox_ServerPort)

        self.label_ChatRepoLbl = QLabel(self.groupBox_SettingsBasic)
        self.label_ChatRepoLbl.setObjectName(u"label_ChatRepoLbl")

        self.formLayout_settingsBasic.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_ChatRepoLbl)

        self.lineEdit_ChatRepo = QLineEdit(self.groupBox_SettingsBasic)
        self.lineEdit_ChatRepo.setObjectName(u"lineEdit_ChatRepo")

        self.formLayout_settingsBasic.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lineEdit_ChatRepo)

        self.label_ChatModelLbl = QLabel(self.groupBox_SettingsBasic)
        self.label_ChatModelLbl.setObjectName(u"label_ChatModelLbl")

        self.formLayout_settingsBasic.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_ChatModelLbl)

        self.lineEdit_ChatModel = QLineEdit(self.groupBox_SettingsBasic)
        self.lineEdit_ChatModel.setObjectName(u"lineEdit_ChatModel")

        self.formLayout_settingsBasic.setWidget(3, QFormLayout.ItemRole.FieldRole, self.lineEdit_ChatModel)


        self.verticalLayout_settings.addWidget(self.groupBox_SettingsBasic)

        self.groupBox_SettingsAdvanced = QGroupBox(self.tab_settings)
        self.groupBox_SettingsAdvanced.setObjectName(u"groupBox_SettingsAdvanced")
        self.groupBox_SettingsAdvanced.setCheckable(True)
        self.groupBox_SettingsAdvanced.setChecked(False)
        self.formLayout_settingsAdvanced = QFormLayout(self.groupBox_SettingsAdvanced)
        self.formLayout_settingsAdvanced.setObjectName(u"formLayout_settingsAdvanced")
        self.formLayout_settingsAdvanced.setHorizontalSpacing(20)
        self.formLayout_settingsAdvanced.setVerticalSpacing(8)
        self.formLayout_settingsAdvanced.setContentsMargins(8, 8, 8, 8)
        self.checkBox_Debug = QCheckBox(self.groupBox_SettingsAdvanced)
        self.checkBox_Debug.setObjectName(u"checkBox_Debug")

        self.formLayout_settingsAdvanced.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.checkBox_Debug)

        self.label_ChatQuantLbl = QLabel(self.groupBox_SettingsAdvanced)
        self.label_ChatQuantLbl.setObjectName(u"label_ChatQuantLbl")

        self.formLayout_settingsAdvanced.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_ChatQuantLbl)

        self.comboBox_ChatQuantType = QComboBox(self.groupBox_SettingsAdvanced)
        self.comboBox_ChatQuantType.addItem("")
        self.comboBox_ChatQuantType.addItem("")
        self.comboBox_ChatQuantType.addItem("")
        self.comboBox_ChatQuantType.addItem("")
        self.comboBox_ChatQuantType.addItem("")
        self.comboBox_ChatQuantType.setObjectName(u"comboBox_ChatQuantType")

        self.formLayout_settingsAdvanced.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comboBox_ChatQuantType)

        self.label_ChatCtxLbl = QLabel(self.groupBox_SettingsAdvanced)
        self.label_ChatCtxLbl.setObjectName(u"label_ChatCtxLbl")

        self.formLayout_settingsAdvanced.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_ChatCtxLbl)

        self.comboBox_ChatCtxSize = QComboBox(self.groupBox_SettingsAdvanced)
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.addItem("")
        self.comboBox_ChatCtxSize.setObjectName(u"comboBox_ChatCtxSize")

        self.formLayout_settingsAdvanced.setWidget(2, QFormLayout.ItemRole.FieldRole, self.comboBox_ChatCtxSize)

        self.checkBox_KVCacheOffload = QCheckBox(self.groupBox_SettingsAdvanced)
        self.checkBox_KVCacheOffload.setObjectName(u"checkBox_KVCacheOffload")
        self.checkBox_KVCacheOffload.setChecked(True)

        self.formLayout_settingsAdvanced.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.checkBox_KVCacheOffload)


        self.verticalLayout_settings.addWidget(self.groupBox_SettingsAdvanced)

        self.horizontalLayout_settingsButtons = QHBoxLayout()
        self.horizontalLayout_settingsButtons.setObjectName(u"horizontalLayout_settingsButtons")
        self.pushButton_SettingsRevert = QPushButton(self.tab_settings)
        self.pushButton_SettingsRevert.setObjectName(u"pushButton_SettingsRevert")

        self.horizontalLayout_settingsButtons.addWidget(self.pushButton_SettingsRevert)

        self.horizontalSpacer_settingsButtons = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_settingsButtons.addItem(self.horizontalSpacer_settingsButtons)

        self.label_restart = QLabel(self.tab_settings)
        self.label_restart.setObjectName(u"label_restart")

        self.horizontalLayout_settingsButtons.addWidget(self.label_restart)

        self.pushButton_SettingsSave = QPushButton(self.tab_settings)
        self.pushButton_SettingsSave.setObjectName(u"pushButton_SettingsSave")

        self.horizontalLayout_settingsButtons.addWidget(self.pushButton_SettingsSave)


        self.verticalLayout_settings.addLayout(self.horizontalLayout_settingsButtons)

        self.verticalSpacer_settings = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_settings.addItem(self.verticalSpacer_settings)

        self.tabWidget.addTab(self.tab_settings, "")

        self.verticalLayout_main.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 800, 30))
        self.menuApplication = QMenu(self.menuBar)
        self.menuApplication.setObjectName(u"menuApplication")
        self.menuHelp = QMenu(self.menuBar)
        self.menuHelp.setObjectName(u"menuHelp")
        MainWindow.setMenuBar(self.menuBar)
        self.statusBar = QStatusBar(MainWindow)
        self.statusBar.setObjectName(u"statusBar")
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
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Aria", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"&About", None))
        self.actionQuit.setText(QCoreApplication.translate("MainWindow", u"&Quit", None))
#if QT_CONFIG(shortcut)
        self.actionQuit.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.label_title.setText(QCoreApplication.translate("MainWindow", u"Aria Service Manager", None))
        self.pushButton_ServiceStop.setText(QCoreApplication.translate("MainWindow", u"Stop", None))
        self.pushButton_ServiceStart.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.groupBox_Service.setTitle(QCoreApplication.translate("MainWindow", u"Service", None))
        self.label_svc_url_lbl.setText(QCoreApplication.translate("MainWindow", u"URL", None))
        self.label_ServiceURL.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_svc_pid_lbl.setText(QCoreApplication.translate("MainWindow", u"Process", None))
        self.label_ServicePID.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_svc_uptime_lbl.setText(QCoreApplication.translate("MainWindow", u"Uptime", None))
        self.label_ServiceUptime.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_svc_started_lbl.setText(QCoreApplication.translate("MainWindow", u"Started", None))
        self.label_ServiceStarted.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_ServiceStatus.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.pushButton_ServiceOpen.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.groupBox_Database.setTitle(QCoreApplication.translate("MainWindow", u"Database", None))
        self.label_db_type_lbl.setText(QCoreApplication.translate("MainWindow", u"Type", None))
        self.label_DatabaseType.setText(QCoreApplication.translate("MainWindow", u"SQLite", None))
        self.label_db_location_lbl.setText(QCoreApplication.translate("MainWindow", u"Location", None))
        self.label_DatabaseLocation.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_db_exists_lbl.setText(QCoreApplication.translate("MainWindow", u"Exists", None))
        self.label_DatabaseFileExists.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_db_size_lbl.setText(QCoreApplication.translate("MainWindow", u"Size", None))
        self.label_DatabaseSize.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.groupBox_LLMAPIs.setTitle(QCoreApplication.translate("MainWindow", u"AI Services", None))
        self.label_llm_type_lbl.setText(QCoreApplication.translate("MainWindow", u"Engine", None))
        self.label_LLMType.setText(QCoreApplication.translate("MainWindow", u"Local AI", None))
        self.label_llm_chat_lbl.setText(QCoreApplication.translate("MainWindow", u"Chat", None))
        self.label_LLMChatAPIURL.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_llm_vision_lbl.setText(QCoreApplication.translate("MainWindow", u"Vision/OCR", None))
        self.label_LLMVisionAPIURL.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_llm_vectordb_lbl.setText(QCoreApplication.translate("MainWindow", u"Knowledge Base", None))
        self.label_VectorDB.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_DebugLogsPath.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_DatabasePermissions.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_overview), QCoreApplication.translate("MainWindow", u"Home", None))
        self.groupBox_Vllm.setTitle(QCoreApplication.translate("MainWindow", u"AI Engine", None))
        self.label_vllm_status_lbl.setText(QCoreApplication.translate("MainWindow", u"Status", None))
        self.label_VllmVersion.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.pushButton_VllmInstall.setText(QCoreApplication.translate("MainWindow", u"Install vLLM", None))
        self.plainTextEdit_VllmOutput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Install output will appear here...", None))
        self.groupBox_Models.setTitle(QCoreApplication.translate("MainWindow", u"AI Model Files", None))
        self.label_model_chat_lbl.setText(QCoreApplication.translate("MainWindow", u"Chat", None))
        self.label_ModelChat_Status.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_model_vl_lbl.setText(QCoreApplication.translate("MainWindow", u"Vision/VL", None))
        self.label_ModelVL_Status.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_model_emb_lbl.setText(QCoreApplication.translate("MainWindow", u"Embeddings", None))
        self.label_ModelEmbeddings_Status.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_model_select_lbl.setText(QCoreApplication.translate("MainWindow", u"Model:", None))
        self.comboBox_ModelSelect.setItemText(0, QCoreApplication.translate("MainWindow", u"chat", None))
        self.comboBox_ModelSelect.setItemText(1, QCoreApplication.translate("MainWindow", u"vl", None))
        self.comboBox_ModelSelect.setItemText(2, QCoreApplication.translate("MainWindow", u"embeddings", None))

        self.pushButton_ModelDownload.setText(QCoreApplication.translate("MainWindow", u"Download Model", None))
        self.groupBox_ModelsAdvanced.setTitle(QCoreApplication.translate("MainWindow", u"Advanced", None))
        self.label_hf_token_lbl.setText(QCoreApplication.translate("MainWindow", u"Access Token (optional):", None))
        self.lineEdit_HFToken.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Access Token", None))
        self.checkBox_ModelForce.setText(QCoreApplication.translate("MainWindow", u"Force re-download", None))
        self.plainTextEdit_ModelOutput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Download output will appear here...", None))
        self.groupBox_Lightpanda.setTitle(QCoreApplication.translate("MainWindow", u"Lightpanda Browser", None))
        self.label_lightpanda_bindir_lbl.setText(QCoreApplication.translate("MainWindow", u"Install Location", None))
        self.label_Lightpanda_BinDir.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_lightpanda_version_lbl.setText(QCoreApplication.translate("MainWindow", u"Configured Version", None))
        self.label_Lightpanda_Version.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_lightpanda_status_lbl.setText(QCoreApplication.translate("MainWindow", u"Status", None))
        self.label_Lightpanda_Status.setText(QCoreApplication.translate("MainWindow", u"\u2717 Not installed", None))
        self.pushButton_LightpandaDownload.setText(QCoreApplication.translate("MainWindow", u"Download", None))
        self.groupBox_LightpandaAdvanced.setTitle(QCoreApplication.translate("MainWindow", u"Advanced", None))
        self.label_lightpanda_version_lbl_2.setText(QCoreApplication.translate("MainWindow", u"Version (optional):", None))
        self.lineEdit_LightpandaVersion.setPlaceholderText(QCoreApplication.translate("MainWindow", u"nightly", None))
        self.plainTextEdit_LightpandaOutput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Download output will appear here...", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_setup), QCoreApplication.translate("MainWindow", u"Setup", None))
        self.groupBox_CreateUser.setTitle(QCoreApplication.translate("MainWindow", u"Create User", None))
        self.label_user_name_lbl.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.label_user_email_lbl.setText(QCoreApplication.translate("MainWindow", u"E-Mail", None))
        self.label_user_password_lbl.setText(QCoreApplication.translate("MainWindow", u"Password", None))
        self.label_user_confirm_password_lbl.setText(QCoreApplication.translate("MainWindow", u"Confirm Password", None))
        self.label_PasswordStrength.setText("")
        self.pushButton_CreateUser.setText(QCoreApplication.translate("MainWindow", u"Create", None))
        self.pushButton_EditUser.setText(QCoreApplication.translate("MainWindow", u"Edit", None))
        self.pushButton_DeleteUser.setText(QCoreApplication.translate("MainWindow", u"Delete", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_users), QCoreApplication.translate("MainWindow", u"Users", None))
        self.lineEdit_LogSearch.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search logs\u2026", None))
        self.comboBox_LogFilter.setItemText(0, QCoreApplication.translate("MainWindow", u"All", None))
        self.comboBox_LogFilter.setItemText(1, QCoreApplication.translate("MainWindow", u"ERROR", None))
        self.comboBox_LogFilter.setItemText(2, QCoreApplication.translate("MainWindow", u"WARNING", None))
        self.comboBox_LogFilter.setItemText(3, QCoreApplication.translate("MainWindow", u"INFO", None))

        self.pushButton_AutoRefresh.setText(QCoreApplication.translate("MainWindow", u"Pause Auto-Refresh", None))
        self.pushButton_RefreshLogs.setText(QCoreApplication.translate("MainWindow", u"Refresh", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_logs), QCoreApplication.translate("MainWindow", u"Logs", None))
        self.groupBox_SettingsBasic.setTitle(QCoreApplication.translate("MainWindow", u"Basic", None))
        self.label_ServerHostLbl.setText(QCoreApplication.translate("MainWindow", u"Server host", None))
        self.label_ServerPortLbl.setText(QCoreApplication.translate("MainWindow", u"Server port", None))
        self.label_ChatRepoLbl.setText(QCoreApplication.translate("MainWindow", u"Model Source", None))
        self.label_ChatModelLbl.setText(QCoreApplication.translate("MainWindow", u"Model filename", None))
        self.groupBox_SettingsAdvanced.setTitle(QCoreApplication.translate("MainWindow", u"Advanced", None))
        self.checkBox_Debug.setText(QCoreApplication.translate("MainWindow", u"Enable debug logging", None))
        self.label_ChatQuantLbl.setText(QCoreApplication.translate("MainWindow", u"Quality / Size", None))
        self.comboBox_ChatQuantType.setItemText(0, QCoreApplication.translate("MainWindow", u"Q4_0", None))
        self.comboBox_ChatQuantType.setItemText(1, QCoreApplication.translate("MainWindow", u"Q4_K_M", None))
        self.comboBox_ChatQuantType.setItemText(2, QCoreApplication.translate("MainWindow", u"Q5_K_M", None))
        self.comboBox_ChatQuantType.setItemText(3, QCoreApplication.translate("MainWindow", u"Q6_K", None))
        self.comboBox_ChatQuantType.setItemText(4, QCoreApplication.translate("MainWindow", u"Q8_0", None))

        self.label_ChatCtxLbl.setText(QCoreApplication.translate("MainWindow", u"Memory Limit", None))
        self.comboBox_ChatCtxSize.setItemText(0, QCoreApplication.translate("MainWindow", u"2048", None))
        self.comboBox_ChatCtxSize.setItemText(1, QCoreApplication.translate("MainWindow", u"4096", None))
        self.comboBox_ChatCtxSize.setItemText(2, QCoreApplication.translate("MainWindow", u"8192", None))
        self.comboBox_ChatCtxSize.setItemText(3, QCoreApplication.translate("MainWindow", u"16384", None))
        self.comboBox_ChatCtxSize.setItemText(4, QCoreApplication.translate("MainWindow", u"32768", None))
        self.comboBox_ChatCtxSize.setItemText(5, QCoreApplication.translate("MainWindow", u"65536", None))
        self.comboBox_ChatCtxSize.setItemText(6, QCoreApplication.translate("MainWindow", u"131072", None))
        self.comboBox_ChatCtxSize.setItemText(7, QCoreApplication.translate("MainWindow", u"262144", None))

        self.checkBox_KVCacheOffload.setText(QCoreApplication.translate("MainWindow", u"KV cache offloading (RAM)", None))
#if QT_CONFIG(tooltip)
        self.checkBox_KVCacheOffload.setToolTip(QCoreApplication.translate("MainWindow", u"When enabled, the KV cache is loaded into system RAM instead of GPU VRAM. Disable to keep the KV cache on GPU (uses more VRAM but may be faster).", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_SettingsRevert.setText(QCoreApplication.translate("MainWindow", u"Revert", None))
        self.label_restart.setText(QCoreApplication.translate("MainWindow", u"Changes require a service restart to take effect.", None))
        self.pushButton_SettingsSave.setText(QCoreApplication.translate("MainWindow", u"Save Settings", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_settings), QCoreApplication.translate("MainWindow", u"Config", None))
        self.menuApplication.setTitle(QCoreApplication.translate("MainWindow", u"&File", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"&Help", None))
    # retranslateUi

