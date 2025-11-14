from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from PyQt6.QtWidgets import QApplication


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)
    result = pyqtSignal(object)


class FunctionWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        # Parent signals to the QApplication instance to keep the underlying
        # C++ QObject alive for the duration of the application. This prevents
        # 'wrapped C/C++ object ... has been deleted' when emitting from threads.
        app = QApplication.instance()
        if app is not None:
            self.signals = WorkerSignals(parent=app)
        else:
            # Fallback: if QApplication isn't created yet, keep an unparented
            # WorkerSignals. In practice the UI creates the QApplication before
            # workers are used.
            self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            try:
                self.signals.error.emit(e)
            except RuntimeError:
                # signals QObject was deleted during shutdown; ignore
                pass
        else:
            try:
                self.signals.result.emit(res)
            except RuntimeError:
                pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass
