from __future__ import annotations

import hashlib

from PySide6.QtCore import QObject, QStandardPaths, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceManager(QObject):
    """Pastikan hanya satu Bagi Layar berjalan per akun pengguna."""

    show_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._accept_connections)
        self._clients: list[QLocalSocket] = []
        self.name = self._server_name()
        self._primary = False
        self._pending_show = False

    @staticmethod
    def _server_name() -> str:
        config_path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        digest = hashlib.sha1(config_path.encode("utf-8", errors="ignore")).hexdigest()[:12]
        return f"ToniTools.BagiLayar.{digest}"

    def acquire_or_notify(self, show_existing: bool = True) -> bool:
        """Return True untuk instance primer; instance kedua memberi sinyal lalu keluar."""
        probe = QLocalSocket(self)
        probe.connectToServer(self.name)
        if probe.waitForConnected(180):
            command = b"SHOW\n" if show_existing else b"PING\n"
            probe.write(command)
            probe.flush()
            probe.waitForBytesWritten(180)
            probe.disconnectFromServer()
            return False

        probe.abort()
        # Bersihkan endpoint yatim setelah crash. Jika sebenarnya ada race dengan
        # instance lain, percobaan listen akan gagal dan kita coba connect sekali lagi.
        QLocalServer.removeServer(self.name)
        if self.server.listen(self.name):
            self._primary = True
            return True

        retry = QLocalSocket(self)
        retry.connectToServer(self.name)
        if retry.waitForConnected(180):
            command = b"SHOW\n" if show_existing else b"PING\n"
            retry.write(command)
            retry.flush()
            retry.waitForBytesWritten(180)
            retry.disconnectFromServer()
            return False
        retry.abort()
        return False

    def _accept_connections(self) -> None:
        while self.server.hasPendingConnections():
            client = self.server.nextPendingConnection()
            if client is None:
                continue
            self._clients.append(client)
            client.readyRead.connect(lambda c=client: self._read_client(c))
            client.disconnected.connect(lambda c=client: self._drop_client(c))
            if client.bytesAvailable():
                self._read_client(client)

    def _read_client(self, client: QLocalSocket) -> None:
        payload = bytes(client.readAll()).decode("utf-8", errors="ignore").strip().upper()
        if "SHOW" in payload:
            self._pending_show = True
            self.show_requested.emit()
        client.disconnectFromServer()

    def consume_pending_show(self) -> bool:
        value = self._pending_show
        self._pending_show = False
        return value

    def _drop_client(self, client: QLocalSocket) -> None:
        try:
            self._clients.remove(client)
        except ValueError:
            pass
        client.deleteLater()

    @property
    def is_primary(self) -> bool:
        return self._primary

    def close(self) -> None:
        for client in list(self._clients):
            try:
                client.abort()
            except Exception:
                pass
        self._clients.clear()
        if self.server.isListening():
            self.server.close()
        if self._primary:
            QLocalServer.removeServer(self.name)
        self._primary = False
