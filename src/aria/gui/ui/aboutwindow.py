# -*- coding: utf-8 -*-
# About dialog — proper QVBoxLayout (no absolute positioning).
# Replaces the .ui-generated version with hardcoded geometry rects.

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)


class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName("AboutDialog")
        AboutDialog.resize(480, 300)
        AboutDialog.setMinimumSize(QSize(400, 260))
        AboutDialog.setSizeGripEnabled(True)
        AboutDialog.setWindowTitle("About")

        # Main layout on the dialog itself
        main_layout = QVBoxLayout(AboutDialog)
        main_layout.setContentsMargins(24, 24, 24, 20)
        main_layout.setSpacing(16)

        # --- Header: App name + version ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.label_2 = QLabel(AboutDialog)
        self.label_2.setObjectName("label_2")
        font_title = QFont()
        font_title.setPointSize(18)
        font_title.setWeight(QFont.Weight.DemiBold)
        self.label_2.setFont(font_title)
        self.label_2.setText("Aria")
        header_layout.addWidget(self.label_2)

        self.label_Version = QLabel(AboutDialog)
        self.label_Version.setObjectName("label_Version")
        font_version = QFont()
        font_version.setPointSize(14)
        self.label_Version.setFont(font_version)
        self.label_Version.setText("v")
        self.label_Version.setProperty("muted", True)
        header_layout.addWidget(self.label_Version)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- Tagline ---
        self.label_Tagline = QLabel(AboutDialog)
        self.label_Tagline.setObjectName("label_Tagline")
        font_tagline = QFont()
        font_tagline.setPointSize(12)
        font_tagline.setItalic(True)
        self.label_Tagline.setFont(font_tagline)
        self.label_Tagline.setWordWrap(True)
        self.label_Tagline.setText(
            "AI Assistant with web UI, CLI management, and local LLM support"
        )
        main_layout.addWidget(self.label_Tagline)

        # --- Details ---
        self.label_Details = QLabel(AboutDialog)
        self.label_Details.setObjectName("label_Details")
        self.label_Details.setTextFormat(Qt.TextFormat.RichText)
        self.label_Details.setOpenExternalLinks(True)
        self.label_Details.setWordWrap(True)
        self.label_Details.setText(
            "<b>Stack</b>: Chainlit, LlamaIndex, PySide6<br/>"
            "<b>License</b>: See repository for project details"
        )
        main_layout.addWidget(self.label_Details)

        # --- Source link ---
        self.label = QLabel(AboutDialog)
        self.label.setObjectName("label")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setOpenExternalLinks(True)
        self.label.setText(
            '<a href="https://github.com/malvavisc0/aria">GitHub Repository</a>'
        )
        main_layout.addWidget(self.label)

        # --- Copyright ---
        self.label_Copyright = QLabel(AboutDialog)
        self.label_Copyright.setObjectName("label_Copyright")
        self.label_Copyright.setWordWrap(True)
        self.label_Copyright.setProperty("muted", True)
        self.label_Copyright.setText(
            "Built for local-first workflows with multi-agent orchestration."
        )
        main_layout.addWidget(self.label_Copyright)

        # --- Spacer + OK button ---
        main_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addItem(
            QSpacerItem(
                40,
                20,
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
        )
        self.pushButton_Ok = QPushButton(AboutDialog)
        self.pushButton_Ok.setObjectName("pushButton_Ok")
        self.pushButton_Ok.setText("OK")
        button_layout.addWidget(self.pushButton_Ok)
        main_layout.addLayout(button_layout)
