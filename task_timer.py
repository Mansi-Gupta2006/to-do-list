import sys, os, time, base64
from dataclasses import dataclass
from typing import List

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QCheckBox, QSystemTrayIcon, QMenu
)

APP_NAME = "Task Timer"
REMINDER_SECONDS = 5 * 60   # Fixed 5 minutes

ICON_B64 = (
    b"iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAASElEQVR4nO3PMQEAAAgDIN8/9K0h"
    b"YQAFu8y8CwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4M8B0wABk2sHn1wAAAABJRU5ErkJggg=="
)

@dataclass
class Task:
    title: str
    done: bool = False

class TaskItem(QWidget):
    def __init__(self, task: Task, on_toggle, on_remove):
        super().__init__()
        self.task = task
        self.on_toggle = on_toggle
        self.on_remove = on_remove

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self.chk = QCheckBox()
        self.chk.setChecked(self.task.done)
        self.chk.stateChanged.connect(self.toggle)

        self.lbl = QLabel(self.task.title)
        self.lbl.setWordWrap(True)
        self.update_style()

        self.btn_remove = QPushButton("✕")
        self.btn_remove.setFixedSize(26, 26)
        self.btn_remove.clicked.connect(self.remove)

        layout.addWidget(self.chk)
        layout.addWidget(self.lbl, 1)
        layout.addWidget(self.btn_remove)

    def toggle(self):
        self.on_toggle(self)
        self.update_style()

    def remove(self):
        self.on_remove(self)

    def update_style(self):
        if self.task.done:
            self.lbl.setText(f"<span style='color:#7aa97a;text-decoration:line-through'>✓ {self.task.title}</span>")
        else:
            self.lbl.setText(self.task.title)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(420, 560)

        self.icon = self.load_icon()
        self.setWindowIcon(self.icon)

        self.tasks: List[Task] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("<h2>Task Timer</h2>")
        subtitle = QLabel("Fixed 5-minute reminder • Minimizes to tray • Enter to add")

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a task and press Enter…")
        self.input.returnPressed.connect(self.add_task)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_task)
        row.addWidget(self.input, 1)
        row.addWidget(self.btn_add)

        self.timer_label = QLabel("05:00")
        self.timer_hint = QLabel("Timer starts with the first task. Stops when all are done/removed.")

        self.list = QListWidget()

        foot = QHBoxLayout()
        self.count_label = QLabel("")
        self.btn_clear_done = QPushButton("Clear Done")
        self.btn_clear_done.clicked.connect(self.clear_done)
        foot.addWidget(self.count_label, 1)
        foot.addWidget(self.btn_clear_done)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addLayout(row)
        root.addWidget(self.timer_label)
        root.addWidget(self.timer_hint)
        root.addWidget(self.list, 1)
        root.addLayout(foot)

        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip(APP_NAME)
        tray_menu = QMenu()
        act_show = QAction("Show")
        act_show.triggered.connect(self.show_window)
        act_quit = QAction("Quit")
        act_quit.triggered.connect(QApplication.quit)
        tray_menu.addAction(act_show)
        tray_menu.addAction(act_quit)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        self.seconds_left = REMINDER_SECONDS
        self.tick = QTimer(self)
        self.tick.setInterval(1000)
        self.tick.timeout.connect(self.on_tick)

        self.refresh_list()
        self.update_counter()
        self.reset_or_start()

    def load_icon(self) -> QIcon:
        try:
            from PyQt6.QtGui import QPixmap
            pix = QPixmap()
            pix.loadFromData(base64.b64decode(ICON_B64))
            return QIcon(pix)
        except Exception:
            return QIcon()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(APP_NAME, "Still running in the tray.", QSystemTrayIcon.MessageIcon.Information, 2500)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden():
                self.show_window()
            else:
                self.hide()

    def add_task(self):
        text = self.input.text().strip()
        if not text:
            return
        self.tasks.append(Task(title=text))
        self.input.clear()
        self.refresh_list()
        self.update_counter()
        self.reset_or_start(start_if_any=True)

    def toggle_task(self, item_widget: TaskItem):
        item_widget.task.done = not item_widget.task.done
        self.update_counter()
        self.reset_or_start()

    def remove_task(self, item_widget: TaskItem):
        self.tasks = [t for t in self.tasks if t is not item_widget.task]
        self.refresh_list()
        self.update_counter()
        self.reset_or_start()

    def clear_done(self):
        self.tasks = [t for t in self.tasks if not t.done]
        self.refresh_list()
        self.update_counter()
        self.reset_or_start()

    def refresh_list(self):
        self.list.clear()
        for t in self.tasks:
            item = QListWidgetItem()
            w = TaskItem(t, on_toggle=self.toggle_task, on_remove=self.remove_task)
            item.setSizeHint(QSize(0, 46))
            self.list.addItem(item)
            self.list.setItemWidget(item, w)

    def update_counter(self):
        remaining = sum(1 for t in self.tasks if not t.done)
        total = len(self.tasks)
        self.count_label.setText(f"Pending: {remaining} / Total: {total}")

    def reset_or_start(self, start_if_any=False):
        has_pending = any(not t.done for t in self.tasks)
        if has_pending:
            if start_if_any or not self.tick.isActive():
                self.seconds_left = REMINDER_SECONDS
                self.tick.start()
        else:
            self.tick.stop()
            self.seconds_left = REMINDER_SECONDS
        self.render_timer()

    def on_tick(self):
        if not any(not t.done for t in self.tasks):
            self.tick.stop()
            self.seconds_left = REMINDER_SECONDS
            self.render_timer()
            return

        self.seconds_left -= 1
        if self.seconds_left <= 0:
            self.fire_reminder()
            self.seconds_left = REMINDER_SECONDS
        self.render_timer()

    def render_timer(self):
        m = self.seconds_left // 60
        s = self.seconds_left % 60
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    def fire_reminder(self):
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                "Task Reminder",
                "You have pending tasks! Stay focused.",
                duration=10,
                threaded=True
            )
        except:
            self.tray.showMessage("Task Reminder", "You have pending tasks! Stay focused.", QSystemTrayIcon.MessageIcon.Information, 6000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
