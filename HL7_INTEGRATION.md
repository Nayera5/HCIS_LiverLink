# HL7 Integration: LiverLink and the External Laboratory Simulator

LiverLink sends lab orders to an external lab and receives the results back, using HL7 v2.5 messages.
The lab is played by the **LabSimulator**, a separate project with its own database and web page.

## How it works

```text
LiverLink (Backend + Frontend)                      LabSimulator
own database (Neon)                                 own database (SQLite file)

1. doctor places an order   ── ORM^O01 (NW) ──►     order created + Accession Number
                            ◄─────── ACK ─────      port 2576
2.                                                  staff: Received → Processing → Completed
                                                    and enter values, units, ranges, flags
3. results saved            ◄──── ORU^R01 ────      "Send results to LiverLink"
   port 2575                ─────── ACK ─────►
4. doctor is notified, checks and releases the results to the patient

   doctor cancels an order  ── ORM^O01 (CA) ──►     order marked Cancelled
                            ◄─────── ACK ─────
```

- Messages travel over **MLLP** (TCP): each message is wrapped as `<VT> message <FS><CR>`.
- Neither system reads the other's database or imports the other's code. Messages are the only contact.
- Messages are built and parsed with **HL7apy**, as named in the project specification.

## Run the demo

First time (after pulling this feature):

```powershell
cd Backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt      # adds hl7apy
python manage.py migrate             # REQUIRED: adds the HL7 tables and LabResult.hl7_message
python manage.py seed_lab_tests      # only if the test catalog is empty
```

The shared Neon database has its own rules for `migrate`: see *Working safely on a shared database* in
[README.md](README.md).

Then four terminals. The first three activate `Backend\venv` as above.

| # | Folder | Command | What it is |
|---|---|---|---|
| 1 | `Backend` | `python manage.py runserver` | LiverLink API (port 8000) |
| 2 | `Backend` | `python manage.py hl7_listener` | Receives results (port 2575) |
| 3 | `LabSimulator` | `python manage.py run_lab` | The lab: page on port 8100, orders on port 2576 |
| 4 | `Frontend` | `npm run dev` | LiverLink portal (port 5173) |

LiverLink is at http://localhost:5173 and the lab at http://127.0.0.1:8100.

### Demo script

1. In LiverLink, sign in as a **hepatologist** or **transplant surgeon** and place a lab order.
2. In the lab, the order appears within a few seconds with its Accession Number. Open it.
3. Click **Processing**, enter the values (the flag is suggested from the range), then click **Completed**.
4. Click **Send results to LiverLink**. The green message shows that LiverLink answered AA.
5. In LiverLink, open the order: values and flags are there. Click **Release to patient**.
6. Show the **HL7 message monitor** in both: the lab's second tab, and in LiverLink
   **Administration → HL7 messages** (super admin).

To show error handling:

- **Refused result:** change the unit of a test to `umol/L` and send. LiverLink answers AE and saves nothing.
- **Lab offline:** stop terminal 3 and place an order. The order is saved and its message shows *Error*.
  Start the lab again, open the message in LiverLink's monitor and click **Resend**.

## The messages

| Message | Direction | Segments | Carries |
|---|---|---|---|
| ORM^O01 | LiverLink → lab | MSH, PID, (ORC, OBR) per test | New order (`ORC-1 = NW`) or cancellation (`CA`) |
| ORU^R01 | lab → LiverLink | MSH, PID, (ORC, OBR, OBX) per test | Results |
| ACK | both ways | MSH, MSA | Answer to every message |

| Data | Field |
|---|---|
| Message control ID | MSH-10 (repeated in MSA-2 of the ACK) |
| Patient MRN | PID-3 |
| LiverLink's internal order ID | ORC-2 / OBR-2 |
| Accession Number | ORC-3 / OBR-3 (in ORU) |
| Test (LOINC code and name) | OBR-4, OBX-3 |
| Priority (R routine, A urgent) | OBR-5 |
| Value / unit / range / flag | OBX-5 / OBX-6 / OBX-7 / OBX-8 |
| Result status (F final, C corrected) | OBX-11 |

| ACK | Meaning | When |
|---|---|---|
| AA | Accepted | Processed, or the same message was already processed |
| AE | Error | The content breaks a rule; nothing is saved |
| AR | Rejected | Not HL7, unsupported type, no control ID, unknown or inactive sender |

## Rules

**LiverLink** (`Backend/apps/hl7/services.py`)

- An order is never blocked by the lab. The message is sent in the background after the order is saved.
- Failed messages can be resent with the same control ID, so an order is never created twice.
- A *new order* message is not sent once its order has been cancelled.
- Results are saved all together or not at all. Refused with AE: unknown order, MRN that does not match,
  cancelled order, test not ordered, wrong unit, value that is not a number, not final.
- A result that is already recorded changes only if the lab marks it corrected (`OBX-11 = C`).
- The stored flag is computed by LiverLink from its own ranges (specification 4.17). The lab's flag, unit and
  range stay readable in the logged message.
- Received results go through `labs.services.record_result()`, the same function as manual entry. So
  notification, automatic invoice and the release step work as before.
- Manual entry is still available. If no external lab is active, no message is sent.

**Lab** (`LabSimulator/lis/services.py`)

- Received → Processing → Completed, one step at a time. Completed needs a value for every test.
- Results can be edited only while Processing, and sent only when Completed.
- After LiverLink accepts, the order is locked. If it refuses, go back to Processing, correct and send again.

## Where the code is

| LiverLink `Backend/apps/hl7/` | Lab `LabSimulator/lis/` | Job |
|---|---|---|
| `message.py` | `hl7.py` | Build and parse messages (HL7apy) |
| `mllp.py` | `mllp.py` | Send and receive over TCP |
| `services.py` | `services.py` | The rules above |
| `models.py` | `models.py` | `ExternalSystem`, `HL7Message` / `Order`, `OrderTest`, `Message` |
| `views.py`, `serializers.py`, `urls.py` | `views.py` | JSON API |
| `management/commands/hl7_listener.py` | `management/commands/run_lab.py` | Start command |
| `tests.py` | `tests.py` | Automated tests |

- **LiverLink page:** `Frontend/src/pages/HL7/HL7MonitorPage.jsx`
- **Lab page:** `LabSimulator/lis/templates/lis/index.html` with `static/lis/app.js` and `style.css`

LiverLink API (capability `hl7.monitor`, super admin only; opening and resending are audited):

| Method | URL |
|---|---|
| GET | `/api/hl7/messages/?direction=&status=&type=&search=` |
| GET | `/api/hl7/messages/<id>/` |
| POST | `/api/hl7/messages/<id>/resend/` |

## Settings

| Setting | Where | Default |
|---|---|---|
| Where LiverLink sends orders | `ExternalSystem` record (Django admin) | `127.0.0.1:2576` |
| Where LiverLink receives results | `HL7_LISTEN_HOST`, `HL7_LISTEN_PORT` in `Backend/.env` | `127.0.0.1:2575` |
| Lab page / lab HL7 port | `LIS_WEB_PORT`, `LIS_HL7_PORT` (environment) | `8100`, `2576` |
| Where the lab sends results | `LIVERLINK_HL7_HOST`, `LIVERLINK_HL7_PORT` (environment) | `127.0.0.1:2575` |

The lab's name, `EXTERNAL_LAB`, is its MSH-3 and must match the `ExternalSystem` name.

## Tests

```powershell
cd Backend
$env:DATABASE_URL="sqlite:///:memory:"; python manage.py test apps.hl7 apps.labs
Remove-Item Env:DATABASE_URL
cd ..\LabSimulator; python manage.py test
```

## Known limits

- The simulator has no login and MLLP is not encrypted. Both listen on `127.0.0.1` only. A real connection
  would need TLS or a VPN.
- Each developer's LiverLink sends to the simulator on their own computer, even though Neon is shared.
- Order IDs from different LiverLink databases can repeat. To reset the lab, stop it and delete
  `LabSimulator/db.sqlite3`.
- Accession Numbers are shown in the lab and in the messages; LiverLink does not store them in a column.
- Only lab orders and results are covered. ADT, SIU and imaging messages are not.
