"""
MLLP: how HL7 v2 travels over TCP. Each message is wrapped as  <VT> message <FS><CR>.

    send()         client: send one message, return the answer (the ACK)
    MLLPServer     server: calls `handler(raw_message) -> ack` for every message received
"""
import logging
import socket
import socketserver

logger = logging.getLogger(__name__)

START = b'\x0b'
END = b'\x1c\x0d'
MAX_SIZE = 1024 * 1024  # 1 MB
TIMEOUT = 10            # seconds


class MLLPError(Exception):
    """The other system could not be reached, or did not answer properly."""


def _wrap(text):
    return START + text.encode('utf-8') + END


def _receive(sock, buffer):
    """Read one framed message. Returns (text, rest of the buffer), or (None, b'') on disconnect."""
    while END not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            return None, b''
        buffer += chunk
        if len(buffer) > MAX_SIZE:
            raise MLLPError('Message too large.')
    frame, rest = buffer.split(END, 1)
    if START not in frame:
        raise MLLPError('Message has no MLLP start character.')
    # 'replace' keeps a badly encoded message readable in the log instead of losing it.
    return frame.split(START, 1)[1].decode('utf-8', errors='replace'), rest


def send(host, port, text, timeout=TIMEOUT):
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(_wrap(text))
            answer, _ = _receive(sock, b'')
    except OSError as e:  # refused, timed out, unknown host…
        raise MLLPError(f'No answer from {host}:{port} ({e}).') from e
    if answer is None:
        raise MLLPError(f'{host}:{port} closed the connection without an ACK.')
    return answer


class _Connection(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(60)
        buffer = b''
        try:
            while True:
                text, buffer = _receive(self.request, buffer)
                if text is None:
                    return
                self.request.sendall(_wrap(self.server.handler(text)))
        except (MLLPError, OSError) as e:
            logger.warning('MLLP connection from %s closed: %s', self.client_address[0], e)


class MLLPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True

    def __init__(self, host, port, handler):
        self.handler = handler
        super().__init__((host, port), _Connection)
