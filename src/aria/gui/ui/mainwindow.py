# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindowmNDagG.ui'
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
    QCheckBox,
    QComboBox,
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
        MainWindow.resize(800, 700)
        MainWindow.setMinimumSize(QSize(750, 650))
        MainWindow.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        icon = QIcon(QIcon.fromTheme("emblem-system"))
        MainWindow.setWindowIcon(icon)
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
        self.verticalLayout_main = QVBoxLayout(self.centralwidget)
        self.verticalLayout_main.setSpacing(6)
        self.verticalLayout_main.setObjectName("verticalLayout_main")
        self.verticalLayout_main.setContentsMargins(10, 10, 10, 10)
        self.horizontalLayout_topbar = QHBoxLayout()
        self.horizontalLayout_topbar.setObjectName("horizontalLayout_topbar")
        self.label_title = QLabel(self.centralwidget)
        self.label_title.setObjectName("label_title")
        font = QFont()
        font.setPointSize(16)
        font.setBold(False)
        self.label_title.setFont(font)
        self.label_title.setTextFormat(Qt.TextFormat.PlainText)

        self.horizontalLayout_topbar.addWidget(self.label_title)

        self.horizontalSpacer_topbar = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_topbar.addItem(self.horizontalSpacer_topbar)

        self.pushButton_ServiceStop = QPushButton(self.centralwidget)
        self.pushButton_ServiceStop.setObjectName("pushButton_ServiceStop")
        self.pushButton_ServiceStop.setEnabled(False)
        icon3 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.SystemShutdown))
        self.pushButton_ServiceStop.setIcon(icon3)

        self.horizontalLayout_topbar.addWidget(self.pushButton_ServiceStop)

        self.pushButton_ServiceStart = QPushButton(self.centralwidget)
        self.pushButton_ServiceStart.setObjectName("pushButton_ServiceStart")
        self.pushButton_ServiceStart.setEnabled(False)
        icon4 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart))
        self.pushButton_ServiceStart.setIcon(icon4)

        self.horizontalLayout_topbar.addWidget(self.pushButton_ServiceStart)

        self.verticalLayout_main.addLayout(self.horizontalLayout_topbar)

        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tabWidget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_overview = QWidget()
        self.tab_overview.setObjectName("tab_overview")
        self.verticalLayout_overview = QVBoxLayout(self.tab_overview)
        self.verticalLayout_overview.setSpacing(8)
        self.verticalLayout_overview.setObjectName("verticalLayout_overview")
        self.verticalLayout_overview.setContentsMargins(8, 8, 8, 8)
        self.groupBox_Service = QGroupBox(self.tab_overview)
        self.groupBox_Service.setObjectName("groupBox_Service")
        self.horizontalLayout_service = QHBoxLayout(self.groupBox_Service)
        self.horizontalLayout_service.setObjectName("horizontalLayout_service")
        self.horizontalLayout_service.setContentsMargins(8, 8, 8, 8)
        self.formLayout_service = QFormLayout()
        self.formLayout_service.setObjectName("formLayout_service")
        self.formLayout_service.setHorizontalSpacing(20)
        self.formLayout_service.setVerticalSpacing(8)
        self.label_svc_url_lbl = QLabel(self.groupBox_Service)
        self.label_svc_url_lbl.setObjectName("label_svc_url_lbl")
        self.label_svc_url_lbl.setStyleSheet("color: #888;")

        self.formLayout_service.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_svc_url_lbl
        )

        self.label_ServiceURL = QLabel(self.groupBox_Service)
        self.label_ServiceURL.setObjectName("label_ServiceURL")
        self.label_ServiceURL.setTextFormat(Qt.TextFormat.RichText)
        self.label_ServiceURL.setOpenExternalLinks(True)

        self.formLayout_service.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_ServiceURL
        )

        self.label_svc_pid_lbl = QLabel(self.groupBox_Service)
        self.label_svc_pid_lbl.setObjectName("label_svc_pid_lbl")
        self.label_svc_pid_lbl.setStyleSheet("color: #888;")

        self.formLayout_service.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_svc_pid_lbl
        )

        self.label_ServicePID = QLabel(self.groupBox_Service)
        self.label_ServicePID.setObjectName("label_ServicePID")

        self.formLayout_service.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_ServicePID
        )

        self.label_svc_uptime_lbl = QLabel(self.groupBox_Service)
        self.label_svc_uptime_lbl.setObjectName("label_svc_uptime_lbl")
        self.label_svc_uptime_lbl.setStyleSheet("color: #888;")

        self.formLayout_service.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_svc_uptime_lbl
        )

        self.label_ServiceUptime = QLabel(self.groupBox_Service)
        self.label_ServiceUptime.setObjectName("label_ServiceUptime")

        self.formLayout_service.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.label_ServiceUptime
        )

        self.label_svc_started_lbl = QLabel(self.groupBox_Service)
        self.label_svc_started_lbl.setObjectName("label_svc_started_lbl")
        self.label_svc_started_lbl.setStyleSheet("color: #888;")

        self.formLayout_service.setWidget(
            3, QFormLayout.ItemRole.LabelRole, self.label_svc_started_lbl
        )

        self.label_ServiceStarted = QLabel(self.groupBox_Service)
        self.label_ServiceStarted.setObjectName("label_ServiceStarted")

        self.formLayout_service.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self.label_ServiceStarted
        )

        self.horizontalLayout_service.addLayout(self.formLayout_service)

        self.horizontalSpacer_service = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_service.addItem(self.horizontalSpacer_service)

        self.verticalLayout_serviceStatus = QVBoxLayout()
        self.verticalLayout_serviceStatus.setObjectName("verticalLayout_serviceStatus")
        self.label_ServiceStatus = QLabel(self.groupBox_Service)
        self.label_ServiceStatus.setObjectName("label_ServiceStatus")
        self.label_ServiceStatus.setStyleSheet(
            "QLabel {\n"
            "    background-color: #616161;\n"
            "    color: white;\n"
            "    font-size: 13pt;\n"
            "    padding: 4px 14px;\n"
            "    border-radius: 6px;\n"
            "}"
        )
        self.label_ServiceStatus.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_serviceStatus.addWidget(self.label_ServiceStatus)

        self.pushButton_ServiceOpen = QPushButton(self.groupBox_Service)
        self.pushButton_ServiceOpen.setObjectName("pushButton_ServiceOpen")
        self.pushButton_ServiceOpen.setEnabled(False)
        icon5 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.UserAvailable))
        self.pushButton_ServiceOpen.setIcon(icon5)

        self.verticalLayout_serviceStatus.addWidget(self.pushButton_ServiceOpen)

        self.verticalSpacer_serviceStatus = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.verticalLayout_serviceStatus.addItem(self.verticalSpacer_serviceStatus)

        self.horizontalLayout_service.addLayout(self.verticalLayout_serviceStatus)

        self.verticalLayout_overview.addWidget(self.groupBox_Service)

        self.horizontalLayout_overview_bottom = QHBoxLayout()
        self.horizontalLayout_overview_bottom.setSpacing(8)
        self.horizontalLayout_overview_bottom.setObjectName(
            "horizontalLayout_overview_bottom"
        )
        self.groupBox_Database = QGroupBox(self.tab_overview)
        self.groupBox_Database.setObjectName("groupBox_Database")
        self.formLayout_database = QFormLayout(self.groupBox_Database)
        self.formLayout_database.setObjectName("formLayout_database")
        self.formLayout_database.setHorizontalSpacing(20)
        self.formLayout_database.setVerticalSpacing(8)
        self.formLayout_database.setContentsMargins(8, 8, 8, 8)
        self.label_db_type_lbl = QLabel(self.groupBox_Database)
        self.label_db_type_lbl.setObjectName("label_db_type_lbl")
        self.label_db_type_lbl.setStyleSheet("color: #888;")

        self.formLayout_database.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_db_type_lbl
        )

        self.label_DatabaseType = QLabel(self.groupBox_Database)
        self.label_DatabaseType.setObjectName("label_DatabaseType")

        self.formLayout_database.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_DatabaseType
        )

        self.label_db_location_lbl = QLabel(self.groupBox_Database)
        self.label_db_location_lbl.setObjectName("label_db_location_lbl")
        self.label_db_location_lbl.setStyleSheet("color: #888;")

        self.formLayout_database.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_db_location_lbl
        )

        self.label_DatabaseLocation = QLabel(self.groupBox_Database)
        self.label_DatabaseLocation.setObjectName("label_DatabaseLocation")

        self.formLayout_database.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_DatabaseLocation
        )

        self.label_db_exists_lbl = QLabel(self.groupBox_Database)
        self.label_db_exists_lbl.setObjectName("label_db_exists_lbl")
        self.label_db_exists_lbl.setStyleSheet("color: #888;")

        self.formLayout_database.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_db_exists_lbl
        )

        self.label_DatabaseFileExists = QLabel(self.groupBox_Database)
        self.label_DatabaseFileExists.setObjectName("label_DatabaseFileExists")

        self.formLayout_database.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.label_DatabaseFileExists
        )

        self.label_db_size_lbl = QLabel(self.groupBox_Database)
        self.label_db_size_lbl.setObjectName("label_db_size_lbl")
        self.label_db_size_lbl.setStyleSheet("color: #888;")

        self.formLayout_database.setWidget(
            3, QFormLayout.ItemRole.LabelRole, self.label_db_size_lbl
        )

        self.label_DatabaseSize = QLabel(self.groupBox_Database)
        self.label_DatabaseSize.setObjectName("label_DatabaseSize")

        self.formLayout_database.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self.label_DatabaseSize
        )

        self.horizontalLayout_overview_bottom.addWidget(self.groupBox_Database)

        self.groupBox_LLMAPIs = QGroupBox(self.tab_overview)
        self.groupBox_LLMAPIs.setObjectName("groupBox_LLMAPIs")
        self.formLayout_llmapis = QFormLayout(self.groupBox_LLMAPIs)
        self.formLayout_llmapis.setObjectName("formLayout_llmapis")
        self.formLayout_llmapis.setHorizontalSpacing(20)
        self.formLayout_llmapis.setVerticalSpacing(8)
        self.formLayout_llmapis.setContentsMargins(8, 8, 8, 8)
        self.label_llm_type_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_type_lbl.setObjectName("label_llm_type_lbl")
        self.label_llm_type_lbl.setStyleSheet("color: #888;")

        self.formLayout_llmapis.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_llm_type_lbl
        )

        self.label_LLMType = QLabel(self.groupBox_LLMAPIs)
        self.label_LLMType.setObjectName("label_LLMType")

        self.formLayout_llmapis.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_LLMType
        )

        self.label_llm_chat_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_chat_lbl.setObjectName("label_llm_chat_lbl")
        self.label_llm_chat_lbl.setStyleSheet("color: #888;")

        self.formLayout_llmapis.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_llm_chat_lbl
        )

        self.label_LLMChatAPIURL = QLabel(self.groupBox_LLMAPIs)
        self.label_LLMChatAPIURL.setObjectName("label_LLMChatAPIURL")

        self.formLayout_llmapis.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_LLMChatAPIURL
        )

        self.label_llm_vision_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_vision_lbl.setObjectName("label_llm_vision_lbl")
        self.label_llm_vision_lbl.setStyleSheet("color: #888;")

        self.formLayout_llmapis.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_llm_vision_lbl
        )

        self.label_LLMVisionAPIURL = QLabel(self.groupBox_LLMAPIs)
        self.label_LLMVisionAPIURL.setObjectName("label_LLMVisionAPIURL")

        self.formLayout_llmapis.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.label_LLMVisionAPIURL
        )

        self.label_llm_embeddings_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_embeddings_lbl.setObjectName("label_llm_embeddings_lbl")
        self.label_llm_embeddings_lbl.setStyleSheet("color: #888;")

        self.formLayout_llmapis.setWidget(
            3, QFormLayout.ItemRole.LabelRole, self.label_llm_embeddings_lbl
        )

        self.label_LLMEmbeddingsAPIURL = QLabel(self.groupBox_LLMAPIs)
        self.label_LLMEmbeddingsAPIURL.setObjectName("label_LLMEmbeddingsAPIURL")

        self.formLayout_llmapis.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self.label_LLMEmbeddingsAPIURL
        )

        self.label_llm_vectordb_lbl = QLabel(self.groupBox_LLMAPIs)
        self.label_llm_vectordb_lbl.setObjectName("label_llm_vectordb_lbl")
        self.label_llm_vectordb_lbl.setStyleSheet("color: #888;")

        self.formLayout_llmapis.setWidget(
            4, QFormLayout.ItemRole.LabelRole, self.label_llm_vectordb_lbl
        )

        self.label_VectorDB = QLabel(self.groupBox_LLMAPIs)
        self.label_VectorDB.setObjectName("label_VectorDB")

        self.formLayout_llmapis.setWidget(
            4, QFormLayout.ItemRole.FieldRole, self.label_VectorDB
        )

        self.horizontalLayout_overview_bottom.addWidget(self.groupBox_LLMAPIs)

        self.verticalLayout_overview.addLayout(self.horizontalLayout_overview_bottom)

        self.label_DebugLogsPath = QLabel(self.tab_overview)
        self.label_DebugLogsPath.setObjectName("label_DebugLogsPath")
        self.label_DebugLogsPath.setVisible(False)

        self.verticalLayout_overview.addWidget(self.label_DebugLogsPath)

        self.label_DatabasePermissions = QLabel(self.tab_overview)
        self.label_DatabasePermissions.setObjectName("label_DatabasePermissions")
        self.label_DatabasePermissions.setVisible(False)

        self.verticalLayout_overview.addWidget(self.label_DatabasePermissions)

        self.verticalSpacer_overview = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.verticalLayout_overview.addItem(self.verticalSpacer_overview)

        self.tabWidget.addTab(self.tab_overview, "")
        self.tab_setup = QWidget()
        self.tab_setup.setObjectName("tab_setup")
        self.verticalLayout_setup = QVBoxLayout(self.tab_setup)
        self.verticalLayout_setup.setSpacing(8)
        self.verticalLayout_setup.setObjectName("verticalLayout_setup")
        self.verticalLayout_setup.setContentsMargins(8, 8, 8, 8)
        self.groupBox_LlamaCpp = QGroupBox(self.tab_setup)
        self.groupBox_LlamaCpp.setObjectName("groupBox_LlamaCpp")
        self.verticalLayout_llamacpp = QVBoxLayout(self.groupBox_LlamaCpp)
        self.verticalLayout_llamacpp.setObjectName("verticalLayout_llamacpp")
        self.verticalLayout_llamacpp.setContentsMargins(8, 8, 8, 8)
        self.formLayout_llamacpp_info = QFormLayout()
        self.formLayout_llamacpp_info.setObjectName("formLayout_llamacpp_info")
        self.formLayout_llamacpp_info.setHorizontalSpacing(20)
        self.formLayout_llamacpp_info.setVerticalSpacing(6)
        self.label_llama_bindir_lbl = QLabel(self.groupBox_LlamaCpp)
        self.label_llama_bindir_lbl.setObjectName("label_llama_bindir_lbl")

        self.formLayout_llamacpp_info.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_llama_bindir_lbl
        )

        self.label_LlamaBinDir = QLabel(self.groupBox_LlamaCpp)
        self.label_LlamaBinDir.setObjectName("label_LlamaBinDir")

        self.formLayout_llamacpp_info.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_LlamaBinDir
        )

        self.label_llama_version_lbl = QLabel(self.groupBox_LlamaCpp)
        self.label_llama_version_lbl.setObjectName("label_llama_version_lbl")

        self.formLayout_llamacpp_info.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_llama_version_lbl
        )

        self.label_LlamaVersion = QLabel(self.groupBox_LlamaCpp)
        self.label_LlamaVersion.setObjectName("label_LlamaVersion")

        self.formLayout_llamacpp_info.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_LlamaVersion
        )

        self.verticalLayout_llamacpp.addLayout(self.formLayout_llamacpp_info)

        self.horizontalLayout_llamabins = QHBoxLayout()
        self.horizontalLayout_llamabins.setObjectName("horizontalLayout_llamabins")
        self.label_LlamaBin_cli = QLabel(self.groupBox_LlamaCpp)
        self.label_LlamaBin_cli.setObjectName("label_LlamaBin_cli")

        self.horizontalLayout_llamabins.addWidget(self.label_LlamaBin_cli)

        self.label_LlamaBin_server = QLabel(self.groupBox_LlamaCpp)
        self.label_LlamaBin_server.setObjectName("label_LlamaBin_server")

        self.horizontalLayout_llamabins.addWidget(self.label_LlamaBin_server)

        self.label_LlamaBin_bench = QLabel(self.groupBox_LlamaCpp)
        self.label_LlamaBin_bench.setObjectName("label_LlamaBin_bench")

        self.horizontalLayout_llamabins.addWidget(self.label_LlamaBin_bench)

        self.label_LlamaBin_quantize = QLabel(self.groupBox_LlamaCpp)
        self.label_LlamaBin_quantize.setObjectName("label_LlamaBin_quantize")

        self.horizontalLayout_llamabins.addWidget(self.label_LlamaBin_quantize)

        self.horizontalSpacer_llamabins = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_llamabins.addItem(self.horizontalSpacer_llamabins)

        self.verticalLayout_llamacpp.addLayout(self.horizontalLayout_llamabins)

        self.horizontalLayout_llamaDownload = QHBoxLayout()
        self.horizontalLayout_llamaDownload.setObjectName(
            "horizontalLayout_llamaDownload"
        )
        self.label_llama_dl_version_lbl = QLabel(self.groupBox_LlamaCpp)
        self.label_llama_dl_version_lbl.setObjectName("label_llama_dl_version_lbl")

        self.horizontalLayout_llamaDownload.addWidget(self.label_llama_dl_version_lbl)

        self.lineEdit_LlamaVersion = QLineEdit(self.groupBox_LlamaCpp)
        self.lineEdit_LlamaVersion.setObjectName("lineEdit_LlamaVersion")

        self.horizontalLayout_llamaDownload.addWidget(self.lineEdit_LlamaVersion)

        self.pushButton_LlamaDownload = QPushButton(self.groupBox_LlamaCpp)
        self.pushButton_LlamaDownload.setObjectName("pushButton_LlamaDownload")
        icon6 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.GoDown))
        self.pushButton_LlamaDownload.setIcon(icon6)

        self.horizontalLayout_llamaDownload.addWidget(self.pushButton_LlamaDownload)

        self.horizontalSpacer_llamaDl = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_llamaDownload.addItem(self.horizontalSpacer_llamaDl)

        self.verticalLayout_llamacpp.addLayout(self.horizontalLayout_llamaDownload)

        self.plainTextEdit_LlamaOutput = QPlainTextEdit(self.groupBox_LlamaCpp)
        self.plainTextEdit_LlamaOutput.setObjectName("plainTextEdit_LlamaOutput")
        font1 = QFont()
        font1.setFamilies(["Courier New"])
        font1.setPointSize(9)
        self.plainTextEdit_LlamaOutput.setFont(font1)
        self.plainTextEdit_LlamaOutput.setReadOnly(True)

        self.verticalLayout_llamacpp.addWidget(self.plainTextEdit_LlamaOutput)

        self.verticalLayout_setup.addWidget(self.groupBox_LlamaCpp)

        self.groupBox_Models = QGroupBox(self.tab_setup)
        self.groupBox_Models.setObjectName("groupBox_Models")
        self.verticalLayout_models = QVBoxLayout(self.groupBox_Models)
        self.verticalLayout_models.setObjectName("verticalLayout_models")
        self.verticalLayout_models.setContentsMargins(8, 8, 8, 8)
        self.formLayout_models_status = QFormLayout()
        self.formLayout_models_status.setObjectName("formLayout_models_status")
        self.formLayout_models_status.setHorizontalSpacing(20)
        self.formLayout_models_status.setVerticalSpacing(6)
        self.label_model_chat_lbl = QLabel(self.groupBox_Models)
        self.label_model_chat_lbl.setObjectName("label_model_chat_lbl")

        self.formLayout_models_status.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_model_chat_lbl
        )

        self.label_ModelChat_Status = QLabel(self.groupBox_Models)
        self.label_ModelChat_Status.setObjectName("label_ModelChat_Status")

        self.formLayout_models_status.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.label_ModelChat_Status
        )

        self.label_model_vl_lbl = QLabel(self.groupBox_Models)
        self.label_model_vl_lbl.setObjectName("label_model_vl_lbl")

        self.formLayout_models_status.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_model_vl_lbl
        )

        self.label_ModelVL_Status = QLabel(self.groupBox_Models)
        self.label_ModelVL_Status.setObjectName("label_ModelVL_Status")

        self.formLayout_models_status.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.label_ModelVL_Status
        )

        self.label_model_emb_lbl = QLabel(self.groupBox_Models)
        self.label_model_emb_lbl.setObjectName("label_model_emb_lbl")

        self.formLayout_models_status.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_model_emb_lbl
        )

        self.label_ModelEmbeddings_Status = QLabel(self.groupBox_Models)
        self.label_ModelEmbeddings_Status.setObjectName("label_ModelEmbeddings_Status")

        self.formLayout_models_status.setWidget(
            2,
            QFormLayout.ItemRole.FieldRole,
            self.label_ModelEmbeddings_Status,
        )

        self.verticalLayout_models.addLayout(self.formLayout_models_status)

        self.horizontalLayout_modelDownload = QHBoxLayout()
        self.horizontalLayout_modelDownload.setObjectName(
            "horizontalLayout_modelDownload"
        )
        self.label_model_select_lbl = QLabel(self.groupBox_Models)
        self.label_model_select_lbl.setObjectName("label_model_select_lbl")

        self.horizontalLayout_modelDownload.addWidget(self.label_model_select_lbl)

        self.comboBox_ModelSelect = QComboBox(self.groupBox_Models)
        self.comboBox_ModelSelect.addItem("")
        self.comboBox_ModelSelect.addItem("")
        self.comboBox_ModelSelect.addItem("")
        self.comboBox_ModelSelect.setObjectName("comboBox_ModelSelect")

        self.horizontalLayout_modelDownload.addWidget(self.comboBox_ModelSelect)

        self.label_hf_token_lbl = QLabel(self.groupBox_Models)
        self.label_hf_token_lbl.setObjectName("label_hf_token_lbl")

        self.horizontalLayout_modelDownload.addWidget(self.label_hf_token_lbl)

        self.lineEdit_HFToken = QLineEdit(self.groupBox_Models)
        self.lineEdit_HFToken.setObjectName("lineEdit_HFToken")
        self.lineEdit_HFToken.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)

        self.horizontalLayout_modelDownload.addWidget(self.lineEdit_HFToken)

        self.checkBox_ModelForce = QCheckBox(self.groupBox_Models)
        self.checkBox_ModelForce.setObjectName("checkBox_ModelForce")

        self.horizontalLayout_modelDownload.addWidget(self.checkBox_ModelForce)

        self.pushButton_ModelDownload = QPushButton(self.groupBox_Models)
        self.pushButton_ModelDownload.setObjectName("pushButton_ModelDownload")
        self.pushButton_ModelDownload.setIcon(icon6)

        self.horizontalLayout_modelDownload.addWidget(self.pushButton_ModelDownload)

        self.verticalLayout_models.addLayout(self.horizontalLayout_modelDownload)

        self.plainTextEdit_ModelOutput = QPlainTextEdit(self.groupBox_Models)
        self.plainTextEdit_ModelOutput.setObjectName("plainTextEdit_ModelOutput")
        self.plainTextEdit_ModelOutput.setFont(font1)
        self.plainTextEdit_ModelOutput.setReadOnly(True)

        self.verticalLayout_models.addWidget(self.plainTextEdit_ModelOutput)

        self.verticalLayout_setup.addWidget(self.groupBox_Models)

        self.verticalSpacer_setup = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.verticalLayout_setup.addItem(self.verticalSpacer_setup)

        self.tabWidget.addTab(self.tab_setup, "")
        self.tab_users = QWidget()
        self.tab_users.setObjectName("tab_users")
        self.horizontalLayout_users = QHBoxLayout(self.tab_users)
        self.horizontalLayout_users.setSpacing(12)
        self.horizontalLayout_users.setObjectName("horizontalLayout_users")
        self.horizontalLayout_users.setContentsMargins(8, 8, 8, 8)
        self.groupBox_CreateUser = QGroupBox(self.tab_users)
        self.groupBox_CreateUser.setObjectName("groupBox_CreateUser")
        self.formLayout_createUser = QFormLayout(self.groupBox_CreateUser)
        self.formLayout_createUser.setObjectName("formLayout_createUser")
        self.formLayout_createUser.setHorizontalSpacing(12)
        self.formLayout_createUser.setVerticalSpacing(8)
        self.formLayout_createUser.setContentsMargins(8, 8, 8, 8)
        self.label_user_name_lbl = QLabel(self.groupBox_CreateUser)
        self.label_user_name_lbl.setObjectName("label_user_name_lbl")

        self.formLayout_createUser.setWidget(
            0, QFormLayout.ItemRole.LabelRole, self.label_user_name_lbl
        )

        self.lineEdit_UserName = QLineEdit(self.groupBox_CreateUser)
        self.lineEdit_UserName.setObjectName("lineEdit_UserName")

        self.formLayout_createUser.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserName
        )

        self.label_user_email_lbl = QLabel(self.groupBox_CreateUser)
        self.label_user_email_lbl.setObjectName("label_user_email_lbl")

        self.formLayout_createUser.setWidget(
            1, QFormLayout.ItemRole.LabelRole, self.label_user_email_lbl
        )

        self.lineEdit_UserEmail = QLineEdit(self.groupBox_CreateUser)
        self.lineEdit_UserEmail.setObjectName("lineEdit_UserEmail")

        self.formLayout_createUser.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserEmail
        )

        self.label_user_password_lbl = QLabel(self.groupBox_CreateUser)
        self.label_user_password_lbl.setObjectName("label_user_password_lbl")

        self.formLayout_createUser.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.label_user_password_lbl
        )

        self.lineEdit_UserPassword = QLineEdit(self.groupBox_CreateUser)
        self.lineEdit_UserPassword.setObjectName("lineEdit_UserPassword")
        self.lineEdit_UserPassword.setMaxLength(48)
        self.lineEdit_UserPassword.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)

        self.formLayout_createUser.setWidget(
            2, QFormLayout.ItemRole.FieldRole, self.lineEdit_UserPassword
        )

        self.pushButton_CreateUser = QPushButton(self.groupBox_CreateUser)
        self.pushButton_CreateUser.setObjectName("pushButton_CreateUser")
        self.pushButton_CreateUser.setEnabled(False)

        self.formLayout_createUser.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self.pushButton_CreateUser
        )

        self.horizontalLayout_users.addWidget(self.groupBox_CreateUser)

        self.verticalLayout_userList = QVBoxLayout()
        self.verticalLayout_userList.setObjectName("verticalLayout_userList")
        self.listWidget_CurrentUsers = QListWidget(self.tab_users)
        self.listWidget_CurrentUsers.setObjectName("listWidget_CurrentUsers")

        self.verticalLayout_userList.addWidget(self.listWidget_CurrentUsers)

        self.horizontalLayout_userButtons = QHBoxLayout()
        self.horizontalLayout_userButtons.setObjectName("horizontalLayout_userButtons")
        self.pushButton_EditUser = QPushButton(self.tab_users)
        self.pushButton_EditUser.setObjectName("pushButton_EditUser")
        self.pushButton_EditUser.setEnabled(False)

        self.horizontalLayout_userButtons.addWidget(self.pushButton_EditUser)

        self.pushButton_DeleteUser = QPushButton(self.tab_users)
        self.pushButton_DeleteUser.setObjectName("pushButton_DeleteUser")
        self.pushButton_DeleteUser.setEnabled(False)
        icon7 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditDelete))
        self.pushButton_DeleteUser.setIcon(icon7)

        self.horizontalLayout_userButtons.addWidget(self.pushButton_DeleteUser)

        self.verticalLayout_userList.addLayout(self.horizontalLayout_userButtons)

        self.horizontalLayout_users.addLayout(self.verticalLayout_userList)

        self.tabWidget.addTab(self.tab_users, "")
        self.tab_logs = QWidget()
        self.tab_logs.setObjectName("tab_logs")
        self.verticalLayout_logs = QVBoxLayout(self.tab_logs)
        self.verticalLayout_logs.setSpacing(6)
        self.verticalLayout_logs.setObjectName("verticalLayout_logs")
        self.verticalLayout_logs.setContentsMargins(8, 8, 8, 8)
        self.plainTextEdit_Logs = QPlainTextEdit(self.tab_logs)
        self.plainTextEdit_Logs.setObjectName("plainTextEdit_Logs")
        font2 = QFont()
        font2.setFamilies(["Courier New"])
        font2.setPointSize(10)
        self.plainTextEdit_Logs.setFont(font2)
        self.plainTextEdit_Logs.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.plainTextEdit_Logs.setReadOnly(True)
        self.plainTextEdit_Logs.setMaximumBlockCount(1000)

        self.verticalLayout_logs.addWidget(self.plainTextEdit_Logs)

        self.pushButton_RefreshLogs = QPushButton(self.tab_logs)
        self.pushButton_RefreshLogs.setObjectName("pushButton_RefreshLogs")
        icon8 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ViewRefresh))
        self.pushButton_RefreshLogs.setIcon(icon8)

        self.verticalLayout_logs.addWidget(self.pushButton_RefreshLogs)

        self.tabWidget.addTab(self.tab_logs, "")

        self.verticalLayout_main.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName("menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 800, 22))
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
        self.actionQuit.setText(QCoreApplication.translate("MainWindow", "&Quit", None))
        # if QT_CONFIG(shortcut)
        self.actionQuit.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+Q", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.label_title.setText(
            QCoreApplication.translate("MainWindow", "Aria Service Manager", None)
        )
        self.pushButton_ServiceStop.setText(
            QCoreApplication.translate("MainWindow", "Stop", None)
        )
        self.pushButton_ServiceStart.setText(
            QCoreApplication.translate("MainWindow", "Start", None)
        )
        self.groupBox_Service.setTitle(
            QCoreApplication.translate("MainWindow", "Service", None)
        )
        self.label_svc_url_lbl.setText(
            QCoreApplication.translate("MainWindow", "URL", None)
        )
        self.label_ServiceURL.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_svc_pid_lbl.setText(
            QCoreApplication.translate("MainWindow", "PID", None)
        )
        self.label_ServicePID.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_svc_uptime_lbl.setText(
            QCoreApplication.translate("MainWindow", "Uptime", None)
        )
        self.label_ServiceUptime.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_svc_started_lbl.setText(
            QCoreApplication.translate("MainWindow", "Started", None)
        )
        self.label_ServiceStarted.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_ServiceStatus.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.pushButton_ServiceOpen.setText(
            QCoreApplication.translate("MainWindow", "Open", None)
        )
        self.groupBox_Database.setTitle(
            QCoreApplication.translate("MainWindow", "Database", None)
        )
        self.label_db_type_lbl.setText(
            QCoreApplication.translate("MainWindow", "Type", None)
        )
        self.label_DatabaseType.setText(
            QCoreApplication.translate("MainWindow", "SQLite", None)
        )
        self.label_db_location_lbl.setText(
            QCoreApplication.translate("MainWindow", "Location", None)
        )
        self.label_DatabaseLocation.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_db_exists_lbl.setText(
            QCoreApplication.translate("MainWindow", "Exists", None)
        )
        self.label_DatabaseFileExists.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_db_size_lbl.setText(
            QCoreApplication.translate("MainWindow", "Size", None)
        )
        self.label_DatabaseSize.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.groupBox_LLMAPIs.setTitle(
            QCoreApplication.translate("MainWindow", "LLM Inference APIs", None)
        )
        self.label_llm_type_lbl.setText(
            QCoreApplication.translate("MainWindow", "Type", None)
        )
        self.label_LLMType.setText(
            QCoreApplication.translate("MainWindow", "llama.cpp", None)
        )
        self.label_llm_chat_lbl.setText(
            QCoreApplication.translate("MainWindow", "Chat", None)
        )
        self.label_LLMChatAPIURL.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_llm_vision_lbl.setText(
            QCoreApplication.translate("MainWindow", "Vision/OCR", None)
        )
        self.label_LLMVisionAPIURL.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_llm_embeddings_lbl.setText(
            QCoreApplication.translate("MainWindow", "Embeddings", None)
        )
        self.label_LLMEmbeddingsAPIURL.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_llm_vectordb_lbl.setText(
            QCoreApplication.translate("MainWindow", "VectorDB", None)
        )
        self.label_VectorDB.setText(QCoreApplication.translate("MainWindow", "-", None))
        self.label_DebugLogsPath.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_DatabasePermissions.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_overview),
            QCoreApplication.translate("MainWindow", "Overview", None),
        )
        self.groupBox_LlamaCpp.setTitle(
            QCoreApplication.translate("MainWindow", "LlamaCpp Binaries", None)
        )
        self.label_llama_bindir_lbl.setText(
            QCoreApplication.translate("MainWindow", "Binary Dir", None)
        )
        self.label_LlamaBinDir.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_llama_version_lbl.setText(
            QCoreApplication.translate("MainWindow", "Version", None)
        )
        self.label_LlamaVersion.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_LlamaBin_cli.setText(
            QCoreApplication.translate("MainWindow", "llama-cli: -", None)
        )
        self.label_LlamaBin_server.setText(
            QCoreApplication.translate("MainWindow", "llama-server: -", None)
        )
        self.label_LlamaBin_bench.setText(
            QCoreApplication.translate("MainWindow", "llama-bench: -", None)
        )
        self.label_LlamaBin_quantize.setText(
            QCoreApplication.translate("MainWindow", "llama-quantize: -", None)
        )
        self.label_llama_dl_version_lbl.setText(
            QCoreApplication.translate("MainWindow", "Version (optional):", None)
        )
        self.lineEdit_LlamaVersion.setPlaceholderText(
            QCoreApplication.translate(
                "MainWindow", "e.g. b4500 (leave blank for latest)", None
            )
        )
        self.pushButton_LlamaDownload.setText(
            QCoreApplication.translate("MainWindow", "Download Binaries", None)
        )
        self.plainTextEdit_LlamaOutput.setPlaceholderText(
            QCoreApplication.translate(
                "MainWindow", "Download output will appear here...", None
            )
        )
        self.groupBox_Models.setTitle(
            QCoreApplication.translate("MainWindow", "GGUF Models", None)
        )
        self.label_model_chat_lbl.setText(
            QCoreApplication.translate("MainWindow", "Chat", None)
        )
        self.label_ModelChat_Status.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_model_vl_lbl.setText(
            QCoreApplication.translate("MainWindow", "Vision/VL", None)
        )
        self.label_ModelVL_Status.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_model_emb_lbl.setText(
            QCoreApplication.translate("MainWindow", "Embeddings", None)
        )
        self.label_ModelEmbeddings_Status.setText(
            QCoreApplication.translate("MainWindow", "-", None)
        )
        self.label_model_select_lbl.setText(
            QCoreApplication.translate("MainWindow", "Model:", None)
        )
        self.comboBox_ModelSelect.setItemText(
            0, QCoreApplication.translate("MainWindow", "chat", None)
        )
        self.comboBox_ModelSelect.setItemText(
            1, QCoreApplication.translate("MainWindow", "vl", None)
        )
        self.comboBox_ModelSelect.setItemText(
            2, QCoreApplication.translate("MainWindow", "embeddings", None)
        )

        self.label_hf_token_lbl.setText(
            QCoreApplication.translate("MainWindow", "HF Token (optional):", None)
        )
        self.lineEdit_HFToken.setPlaceholderText(
            QCoreApplication.translate("MainWindow", "HuggingFace token", None)
        )
        self.checkBox_ModelForce.setText(
            QCoreApplication.translate("MainWindow", "Force re-download", None)
        )
        self.pushButton_ModelDownload.setText(
            QCoreApplication.translate("MainWindow", "Download Model", None)
        )
        self.plainTextEdit_ModelOutput.setPlaceholderText(
            QCoreApplication.translate(
                "MainWindow", "Download output will appear here...", None
            )
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_setup),
            QCoreApplication.translate("MainWindow", "Setup", None),
        )
        self.groupBox_CreateUser.setTitle(
            QCoreApplication.translate("MainWindow", "Create User", None)
        )
        self.label_user_name_lbl.setText(
            QCoreApplication.translate("MainWindow", "Name", None)
        )
        self.label_user_email_lbl.setText(
            QCoreApplication.translate("MainWindow", "E-Mail", None)
        )
        self.label_user_password_lbl.setText(
            QCoreApplication.translate("MainWindow", "Password", None)
        )
        self.pushButton_CreateUser.setText(
            QCoreApplication.translate("MainWindow", "Create", None)
        )
        self.pushButton_EditUser.setText(
            QCoreApplication.translate("MainWindow", "Edit", None)
        )
        self.pushButton_DeleteUser.setText(
            QCoreApplication.translate("MainWindow", "Delete", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_users),
            QCoreApplication.translate("MainWindow", "Users", None),
        )
        self.pushButton_RefreshLogs.setText(
            QCoreApplication.translate("MainWindow", "Refresh", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_logs),
            QCoreApplication.translate("MainWindow", "Logs", None),
        )
        self.menuApplication.setTitle(
            QCoreApplication.translate("MainWindow", "&Application", None)
        )
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", "&Help", None))

    # retranslateUi
