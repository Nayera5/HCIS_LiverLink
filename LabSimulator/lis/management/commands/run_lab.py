"""python manage.py run_lab : start the simulator (HL7 listener + web page). Stop with Ctrl+C."""
import threading

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from lis.mllp import MLLPServer
from lis.services import handle_inbound


def _handle(raw):
    try:
        return handle_inbound(raw)
    finally:
        close_old_connections()


class Command(BaseCommand):
    help = 'Start the External Laboratory Simulator.'

    def handle(self, *args, **opts):
        call_command('migrate', verbosity=0)  # the simulator's own SQLite file
        try:
            server = MLLPServer(settings.HL7_HOST, settings.HL7_PORT, _handle)
        except OSError as e:
            raise CommandError(f'Cannot listen on {settings.HL7_HOST}:{settings.HL7_PORT}: {e}')
        threading.Thread(target=server.serve_forever, daemon=True, name='hl7-listener').start()
        self.stdout.write(self.style.SUCCESS(
            f'HL7 listener on {settings.HL7_HOST}:{settings.HL7_PORT}. '
            f'Open http://127.0.0.1:{settings.WEB_PORT}/'))
        call_command('runserver', f'127.0.0.1:{settings.WEB_PORT}', use_reloader=False)
