"""History management tab"""

import csv
import io as _io

from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.history import HistoryEntry


class HistoryTab(QWidget):
    def __init__(self, history_manager, text_tab, clone_tab):
        super().__init__()
        self.history_manager = history_manager
        self.text_tab = text_tab
        self.clone_tab = clone_tab

        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("篩選："))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "文字合成", "語音克隆", "潤稿翻譯"])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        left_layout.addLayout(filter_layout)

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self._on_item_clicked)
        left_layout.addWidget(self.history_list)

        list_button_layout = QHBoxLayout()
        self.retry_btn = QPushButton("重新執行")
        self.retry_btn.clicked.connect(self._on_retry)
        self.retry_btn.setEnabled(False)
        list_button_layout.addWidget(self.retry_btn)

        self.copy_text_btn = QPushButton("複製文字")
        self.copy_text_btn.clicked.connect(self._on_copy_text)
        self.copy_text_btn.setEnabled(False)
        list_button_layout.addWidget(self.copy_text_btn)

        self.delete_btn = QPushButton("刪除")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setEnabled(False)
        list_button_layout.addWidget(self.delete_btn)

        left_layout.addLayout(list_button_layout)

        # ── Export row ──
        export_row = QHBoxLayout()
        self.export_csv_btn = QPushButton("📊 匯出 CSV")
        self.export_csv_btn.setToolTip("將目前篩選的歷史記錄匯出為 CSV 檔案")
        self.export_csv_btn.clicked.connect(self._on_export_csv)
        export_row.addWidget(self.export_csv_btn)
        export_row.addStretch()
        left_layout.addLayout(export_row)

        main_layout.addWidget(left_panel, stretch=1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        detail_group = QGroupBox("詳細資訊")
        detail_layout = QVBoxLayout(detail_group)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumHeight(300)
        detail_layout.addWidget(self.detail_text)

        clear_all_btn = QPushButton("清空全部歷史")
        clear_all_btn.clicked.connect(self._on_clear_all)
        detail_layout.addWidget(clear_all_btn)

        right_layout.addWidget(detail_group)
        main_layout.addWidget(right_panel, stretch=2)

    def _load_history(self):
        self.history_list.clear()
        filter_mode = self.filter_combo.currentIndex()

        for entry in self.history_manager.get_all():
            if not self._matches_filter(entry, filter_mode):
                continue

            op_type = self._get_operation_type_label(entry.operation)
            timestamp = entry.timestamp.split("T")[1][:8]
            preview = entry.text[:30] + "..." if len(entry.text) > 30 else entry.text
            item_text = f"[{timestamp}] {op_type} - {preview}"
            self.history_list.addItem(item_text)

    def _matches_filter(self, entry: HistoryEntry, filter_mode: int) -> bool:
        if filter_mode == 0:
            return True
        elif filter_mode == 1:
            return entry.operation == "tts"
        elif filter_mode == 2:
            return entry.operation.startswith("clone")
        elif filter_mode == 3:
            return entry.operation.startswith("edit")
        return True

    def _get_operation_type_label(self, operation: str) -> str:
        labels = {
            "tts": "文字合成",
            "clone_text": "語音克隆(文字)",
            "clone_audio": "語音克隆(音檔)",
            "edit_mode_0": "潤稿",
            "edit_mode_1": "簡→繁",
            "edit_mode_2": "繁→簡",
            "edit_mode_3": "英→中",
            "edit_mode_4": "中→英",
            "edit_mode_5": "日→中",
            "edit_mode_6": "自訂處理",
        }
        return labels.get(operation, operation)

    def _on_filter_changed(self):
        self._load_history()

    def _on_item_clicked(self, item):
        index = self.history_list.row(item)
        entries = [
            e
            for e in self.history_manager.get_all()
            if self._matches_filter(e, self.filter_combo.currentIndex())
        ]

        if 0 <= index < len(entries):
            self.selected_entry = entries[index]
            self._show_detail(entries[index])
            self.retry_btn.setEnabled(True)
            self.copy_text_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

    def _show_detail(self, entry: HistoryEntry):
        detail = f"""操作類型：{self._get_operation_type_label(entry.operation)}
時間：{entry.timestamp}

原文：
{entry.text}
"""
        if entry.ref_text:
            detail += f"\n參考文字：\n{entry.ref_text}"
        if entry.ref_audio_name:
            detail += f"\n參考音檔：{entry.ref_audio_name}"
        if entry.config:
            detail += f"\n參數：{entry.config}"
        if entry.audio_duration:
            detail += f"\n音訊時長：{entry.audio_duration:.2f} 秒"

        self.detail_text.setPlainText(detail)

    def _on_retry(self):
        if not hasattr(self, "selected_entry"):
            return

        entry = self.selected_entry

        if entry.operation == "tts":
            self.text_tab.text_input.setPlainText(entry.text)
            self._switch_to_tab(0)
        elif entry.operation.startswith("clone"):
            self.clone_tab.text_input.setPlainText(entry.text)
            if entry.ref_text:
                self.clone_tab.mode_combo.setCurrentIndex(0)
                self.clone_tab.ref_text_input.setPlainText(entry.ref_text)
            self._switch_to_tab(1)

    def _switch_to_tab(self, index: int):
        parent = self.parent()
        while parent and not isinstance(parent, QtWidgets.QTabWidget):
            parent = parent.parent()
        if parent:
            parent.setCurrentIndex(index)

    def _on_copy_text(self):
        if hasattr(self, "selected_entry"):
            QtWidgets.QApplication.clipboard().setText(self.selected_entry.text)

    def _on_delete(self):
        if not hasattr(self, "selected_entry"):
            return

        reply = QMessageBox.question(
            self,
            "確認刪除",
            "確定要刪除這筆歷史記錄嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.delete(self.selected_entry.id)
            self._load_history()
            self.detail_text.clear()
            self.retry_btn.setEnabled(False)
            self.copy_text_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def _on_clear_all(self):
        reply = QMessageBox.question(
            self,
            "確認清空",
            "確定要清空全部歷史記錄嗎？此操作無法復原。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear()
            self._load_history()
            self.detail_text.clear()
            self.retry_btn.setEnabled(False)
            self.copy_text_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def _on_export_csv(self) -> None:
        """Export currently filtered history to a CSV file."""
        filter_mode = self.filter_combo.currentIndex()
        entries = [
            e for e in self.history_manager.get_all()
            if self._matches_filter(e, filter_mode)
        ]
        if not entries:
            QMessageBox.information(self, "無記錄", "目前沒有可匯出的歷史記錄。")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "儲存 CSV", "history.csv", "CSV 檔案 (*.csv)"
        )
        if not path:
            return

        try:
            buf = _io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=["id", "timestamp", "operation", "text",
                            "ref_text", "ref_audio_name", "audio_duration"],
                extrasaction="ignore",
            )
            writer.writeheader()
            for e in entries:
                writer.writerow(e.to_dict())
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(buf.getvalue())
            QMessageBox.information(self, "匯出成功", f"已匯出 {len(entries)} 筆記錄到：\n{path}")
        except OSError as exc:
            QMessageBox.critical(self, "匯出失敗", str(exc))

    def refresh(self):
        self._load_history()
