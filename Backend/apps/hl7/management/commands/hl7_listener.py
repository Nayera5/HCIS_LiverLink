"""python manage.py hl7_listener : receive HL7 messages (lab results) over MLLP. Stop with Ctrl+C."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.hl7.mllp import MLLPServer
from apps.hl7.services import handle_inbound


def _handle(raw):
    close_old_connections()  # drop connections the database closed while the listener was idle
    try:
        return handle_inbound(raw)
    finally:
        close_old_connections()


class Command(BaseCommand):
    help = 'Receive HL7 messages from external systems over MLLP.'

    def handle(self, *args, **opts):
        host, port = settings.HL7_LISTEN_HOST, settings.HL7_LISTEN_PORT
        try:
            server = MLLPServer(host, port, _handle)
        except OSError as e:
            raise CommandError(f'Cannot listen on {host}:{port}: {e}')
        self.stdout.write(self.style.SUCCESS(f'LiverLink HL7 listener on {host}:{port} (Ctrl+C to stop)'))
        with server:
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                self.stdout.write('Listener stopped.')
