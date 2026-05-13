from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from .loading_overlay import LoadingOverlay


class _TaskSignals(QObject):
    succeeded = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)
    finished = pyqtSignal(int)


class _TaskRunnable(QRunnable):
    def __init__(self, token, task):
        super().__init__()
        self._token = token
        self._task = task
        self.signals = _TaskSignals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if self._is_cancelled:
            self.signals.finished.emit(self._token)
            return

        try:
            result = self._task()
        except Exception as exc:
            if not self._is_cancelled:
                self.signals.failed.emit(self._token, str(exc))
        else:
            if not self._is_cancelled:
                self.signals.succeeded.emit(self._token, result)
        finally:
            self.signals.finished.emit(self._token)


class AsyncLoadMixin:
    def setup_async_loader(self, blur_target=None):
        self._thread_pool = QThreadPool.globalInstance()
        self._async_jobs = {}
        self._async_token = 0
        self._async_disposed = False
        self.loading_overlay = LoadingOverlay(self, blur_target=blur_target)

    def run_loading_task(
        self,
        task,
        on_success,
        *,
        loading_text="Đang tải dữ liệu...",
        error_title="Không thể tải dữ liệu",
    ):
        if self._async_disposed:
            return

        # Cancel any previous job to avoid conflicts and unnecessary processing
        if self._async_token in self._async_jobs:
            self._async_jobs[self._async_token]["runnable"].cancel()
            self._async_jobs.pop(self._async_token, None)

        self._async_token += 1
        token = self._async_token
        runnable = _TaskRunnable(token, task)
        self._async_jobs[token] = {
            "runnable": runnable,
            "on_success": on_success,
            "error_title": error_title,
        }

        runnable.signals.succeeded.connect(self._handle_async_success)
        runnable.signals.failed.connect(self._handle_async_error)
        runnable.signals.finished.connect(self._handle_async_finished)

        self.loading_overlay.show_overlay(loading_text)
        self._thread_pool.start(runnable)

    def teardown_async_loader(self):
        self._async_disposed = True
        
        # Cancel all pending/running jobs on teardown
        for job in self._async_jobs.values():
            job["runnable"].cancel()

        if hasattr(self, "loading_overlay"):
            self.loading_overlay.hide_overlay()
        self._async_jobs.clear()

    def _handle_async_success(self, token, payload):
        if self._async_disposed or token != self._async_token:
            return

        job = self._async_jobs.get(token)
        if not job:
            return

        try:
            job["on_success"](payload)
        except Exception as exc:
            QMessageBox.critical(self, "Không thể cập nhật giao diện", str(exc))

    def _handle_async_error(self, token, message):
        if self._async_disposed or token != self._async_token:
            return

        title = self._async_jobs.get(token, {}).get("error_title", "Không thể tải dữ liệu")
        QMessageBox.critical(self, title, message or "Đã xảy ra lỗi không xác định.")

    def _handle_async_finished(self, token):
        self._async_jobs.pop(token, None)
        if self._async_disposed:
            return
        if token == self._async_token:
            self.loading_overlay.hide_overlay()
