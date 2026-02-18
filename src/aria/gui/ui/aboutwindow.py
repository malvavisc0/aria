# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'aboutwindowMbHxyP.ui'
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
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName("AboutDialog")
        AboutDialog.resize(400, 240)
        AboutDialog.setMinimumSize(QSize(400, 240))
        AboutDialog.setMaximumSize(QSize(400, 240))
        self.horizontalLayoutWidget = QWidget(AboutDialog)
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayoutWidget.setGeometry(QRect(9, 190, 381, 41))
        self.horizontalLayout = QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton_Ok = QPushButton(self.horizontalLayoutWidget)
        self.pushButton_Ok.setObjectName("pushButton_Ok")

        self.horizontalLayout.addWidget(self.pushButton_Ok)

        self.formLayoutWidget = QWidget(AboutDialog)
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(10, 20, 381, 71))
        self.formLayout = QFormLayout(self.formLayoutWidget)
        self.formLayout.setObjectName("formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.formLayoutWidget)
        self.label_2.setObjectName("label_2")
        font = QFont()
        font.setPointSize(18)
        self.label_2.setFont(font)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.label_Version = QLabel(self.formLayoutWidget)
        self.label_Version.setObjectName("label_Version")
        font1 = QFont()
        font1.setPointSize(16)
        self.label_Version.setFont(font1)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_Version)

        self.label_3 = QLabel(self.formLayoutWidget)
        self.label_3.setObjectName("label_3")
        self.label_3.setStyleSheet("color: rgb(61, 56, 70)")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.label = QLabel(self.formLayoutWidget)
        self.label.setObjectName("label")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label)

        self.verticalLayoutWidget = QWidget(AboutDialog)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(9, 100, 381, 80))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.retranslateUi(AboutDialog)

        QMetaObject.connectSlotsByName(AboutDialog)

    # setupUi

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(
            QCoreApplication.translate("AboutDialog", "About", None)
        )
        self.pushButton_Ok.setText(
            QCoreApplication.translate("AboutDialog", "OK", None)
        )
        self.label_2.setText(QCoreApplication.translate("AboutDialog", "Aria", None))
        self.label_Version.setText(QCoreApplication.translate("AboutDialog", "v", None))
        self.label_3.setText(QCoreApplication.translate("AboutDialog", "Source", None))
        self.label.setText(
            QCoreApplication.translate(
                "AboutDialog",
                '<a href="https://github.com/malvavisc0/aria">GitHub Repository</a>',
                None,
            )
        )

    # retranslateUi
