# External Laboratory Simulator

A small stand-in for an external lab system (LIS). It receives lab orders from LiverLink as HL7 ORM^O01,
lets lab staff process the sample and enter results, and sends them back as HL7 ORU^R01.

It is a separate Django project with its own SQLite database. It exchanges HL7 messages with LiverLink and
never touches LiverLink's code or database.

```powershell
pip install -r requirements.txt    # or reuse Backend\venv, which already has both packages
python manage.py run_lab           # creates its database on the first run
```

Open http://127.0.0.1:8100. For results to be accepted, LiverLink's `python manage.py hl7_listener` must be running.

| Tab | What it shows |
|---|---|
| Incoming orders | Orders, MRN, internal order ID, Accession Number, sample status, result entry, send |
| HL7 message monitor | Every message received or sent, with its ACK |

Tests: `python manage.py test`

Messages, rules, settings and a demo script: [HL7_INTEGRATION.md](../HL7_INTEGRATION.md).
