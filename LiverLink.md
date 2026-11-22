# **LiverLink – Phase 01**

# **System Modules and Features**

## **1\. User & Access Management**

**Purpose:** Manage accounts, login, roles and permissions for the whole system. 

| Feature | Description |
| ----- | ----- |
| Login & Authentication | Secure login with hashed passwords and tokens, logout, password reset, automatic logout after inactivity. |
| Account Creation | Patients and donors register themselves; staff accounts are created by the Admin. |
| Role-Based Access Control (RBAC) | Each user has a role and sub-role (see Section "User Roles"); every page and API checks permissions. |
| User Management | Admin creates, edits, activates and deactivates accounts and assigns roles. |
| Profile & Password | Users update their own contact details and password. |
| Audit Log | Records who viewed, created or changed which patient record, and when. |

## **2\. Patient & Donor Registry**

**Purpose:** Register every person who receives care: liver patients, transplant recipients and living donors.  

| Feature | Description |
| ----- | ----- |
| Registration | Self-registration through the portal, or registration by the Transplant Coordinator. |
| MRN Generation | Generate a unique Medical Record Number for every patient and donor. |
| Demographic Profile | Name, national ID, date of birth, sex, contact, emergency contact, blood group, height and weight (weight is needed for GRWR). |
| Patient Category | Mark the person as: liver patient, transplant candidate (recipient) or living donor. One person can change category over time. |
| Donor Application | A potential donor applies, states the intended recipient and relationship, and the Coordinator screens the application. |
| Consent Management | Record and upload signed informed consent (donor surgery, CT/contrast, data use). |

## **3\. Appointment & Scheduling**

**Purpose:** Schedule and manage all visits.  

| Feature | Description |
| ----- | ----- |
| Doctor Availability | Doctors (or Admin) define working days and time slots. |
| Appointment Booking | Patients and donors book online; the Coordinator can book on their behalf. |
| Appointment Types | Consultation, CT scan, lab visit, donor evaluation, recipient evaluation, post-transplant follow-up. (Replaces separate donor and recipient appointment features.) |
| Appointment Management | Reschedule and cancel; status: booked, checked-in, completed, no-show, cancelled. |
| Appointment Calendar | Day and week view per doctor and per patient. |

## **4\. Electronic Medical Records (EMR)**

**Purpose:** Store each patient's and donor's clinical record.   

| Feature | Description |
| ----- | ----- |
| Medical History | Past conditions, cause of liver disease (HBV, HCV, fatty liver, alcohol, other), previous surgeries, allergies, family history. |
| Encounters | A visit record linked to the appointment, with the treating doctor. |
| Diagnoses | Record diagnoses using ICD-10 codes. |
| Clinical Notes | Doctors write notes for each encounter. |
| Vital Signs | Blood pressure, pulse, weight, height and BMI per visit. |
| Documents & Reports | Upload external reports; view approved radiology reports. |
| Patient Record Access | Patients and donors see their own released records (read-only). |

## **5\. Laboratory Orders & Results**

**Purpose:** Order lab tests and store their results for liver assessment and transplant evaluation.   

| Feature | Description |
| ----- | ----- |
| Lab Orders | Order tests such as liver panel (ALT, AST, bilirubin, albumin), INR, creatinine, sodium, HBV/HCV markers, AFP and blood group. |
| Result Entry | Results are received from an external lab. |
| Abnormal Flags | Highlight results outside the normal range. |
| Pending Tests | List tests that are ordered but have no result yet. |
| Patient Result View | Patients see results after the doctor releases them. |
| Result Trends | Chart of a lab value over time (e.g., bilirubin, AFP). |

## **6\. Prescriptions & Treatment Plans**

**Purpose:** Manage medications and treatment plans (required in the Patient Portal).

| Feature | Description |
| ----- | ----- |
| E-Prescription | Doctor prescribes drug, dose, route, frequency and duration. |
| Active Medication List | Current and past medications for each patient. |
| Treatment Plans | Plan with goals, steps and review date (e.g., surveillance, ablation, chemoembolization, resection, transplant referral). |

## **7\. Radiology & PACS**

**Purpose:** Manage CT orders, DICOM studies and radiology reports.  

| Feature | Description |
| ----- | ----- |
| Imaging Orders | Request a CT (e.g., multiphase liver CT, donor volumetry CT). |
| DICOM Upload | Upload DICOM studies; they are stored in Orthanc PACS and read through DICOMweb. |
| Study Linking | Link each study to the patient (MRN) and the imaging order. |
| Radiology Worklist | Studies waiting for reading or for AI review. |
| Radiology Report | Structured findings and impression, including the LI-RADS category chosen by the radiologist; approve and sign. |
| Prior Studies | List of the patient's previous studies. |

## **8\. DICOM Viewer**

**Purpose:** Interactive web viewer for CT images (built on OHIF / Cornerstone3D).

| Feature | Description |
| ----- | ----- |
| Image Display & Scrolling | Display CT series and scroll through slices. |
| Zoom, Pan & Rotate | Basic image navigation tools. |
| Window / Level | Contrast adjustment with presets (abdomen, liver, bone). |
| Image Filters | Sharpening, smoothing and noise reduction. |
| MPR | Axial, sagittal and coronal views. |
| 3D Volume Rendering | 3D view of the CT volume. |
| Measurements | Length, area and region-of-interest density (HU). |
| Segmentation Overlay | Show AI liver and tumor masks on the images; show/hide each label. |
| Study Comparison | Side-by-side view of current and prior study. |

## **9\. AI Image Analysis & Volumetry**

**Purpose:** Segment the liver and lesions on CT and calculate measurements. The AI only measures; it does not decide.

| Feature | Description |
| ----- | ----- |
| Liver Segmentation | Automatic segmentation of the liver. |
| Lesion Segmentation | Automatic segmentation of liver tumors / lesions. |
| Lesion Measurements | Number of lesions, longest diameter and volume of each. |
| Total Liver Volume | Volume (mL) from the liver mask. |
| Graft & Remnant Volume | On donor CT: volume of the planned graft (right or left lobe) and of the liver that stays with the donor. The radiologist or surgeon confirms the split. |
| Review & Correction | Radiologist accepts, edits or rejects the AI result; both the AI values and the confirmed values are saved. |
| Lesion Location | Liver segment (Couinaud) of each lesion. |

## **10\. Clinical Decision Support (CDSS)**

**Purpose:**CDSS provides clinical insights, scores, and alerts based on radiology findings and patient data to support the doctor's decision without replacing clinical judgment. 

| Feature | Description |
| ----- | ----- |
| Patient Summary Panel | One screen with key labs, confirmed imaging measurements and the radiology report. |
| Imaging-Based Clinical Assessment  | Use confirmed DICOM image analysis results from Module 9 to evaluate relevant clinical criteria and generate imaging-based insights.  |
| MELD Score | Calculate MELD from bilirubin, INR, creatinine and sodium to show liver disease severity. |
| Milan Criteria Check | From confirmed lesion measurements: one tumor up to 5 cm, or up to 3 tumors each up to 3 cm, with no vascular invasion. Shows "within" or "outside" criteria for transplant. |
| Donor Suitability Check | GRWR and donor remnant liver, plus donor age/BMI. Thresholds are set by the Admin, not hard-coded. |
| Clinical Alerts | Specific alerts: abnormal labs, rising AFP, criteria not met, required tests missing. |
| Decision Documentation | The doctor accepts or overrides the suggestion and writes the reason. |

## **11\. Transplant Case Management**

**Purpose:** Manage the living donor transplant process from referral to surgery.

| Feature | Description |
| ----- | ----- |
| Transplant Referral | The hepatologist refers a patient for transplant evaluation. |
| Transplant Case | A case links one recipient with one or more candidate donors. |
| Blood Group Compatibility | Check ABO compatibility between donor and recipient. |
| Evaluation Checklist | Required tests and visits for donor and recipient; missing items are shown as pending. |
| Case Status Tracking | Referred \> Under evaluation \> Committee review \> Approved / Rejected \> Surgery scheduled \> Transplanted \> Follow-up. |
| Committee Decision | Record the transplant team's decision, participants, reasons and any extra tests requested. |
| Surgery Scheduling | Surgery date, operating room and surgical team. |
| Surgery Record | Operative notes, graft type (right/left lobe), duration and complications. |

## **12\. Post-Transplant Follow-up**

**Purpose:** Monitor the recipient and the donor after surgery.

| Feature | Description |
| ----- | ----- |
| Follow-up Plan | Generate the follow-up visit schedule automatically after surgery. |
| Recipient Monitoring | Labs, immunosuppressant levels, rejection episodes and complications. |
| Donor Recovery Tracking | Liver function recovery, complications, return to normal activity, and liver regrowth on follow-up CT. |
| Recovery Charts | Trend charts of recovery for each patient. |

## **13\. Billing & Payments**

**Purpose:** Bill services and process payments

| Feature | Description |
| ----- | ----- |
| Service Catalog | Services and prices (consultation, CT, lab tests, AI analysis, evaluation package). |
| Invoice Generation | Create invoices automatically from completed appointments, scans and tests. |
| Online Payment | Patients pay through the portal using a payment gateway in test (sandbox) mode. |
| Desk Payment | Billing staff record cash or card payments. |
| Receipts | PDF receipt for each payment. |
| Balances & History | Unpaid invoices and payment history per patient. |

## **14\. Notifications**

**Purpose:** Keep users informed, in-app and by email. 

| Feature | Description |
| ----- | ----- |
| Appointment Reminders | Before upcoming appointments. |
| Result Notifications | When lab results, imaging reports or AI results are ready. |
| Case Status Updates | When a transplant case changes stage. |
| Pending Task Alerts | Tell the coordinator about missing tests or documents. |
| Follow-up Reminders | Remind patients and donors about follow-up visits. |

## **15\. Reporting & Analytics**

**Purpose:** Reports and charts on patients, transplants, imaging, finance and system use.   

| Feature | Description |
| ----- | ----- |
| Dashboards | Charts for each role (data visualization requirement). |
| Patient & Donor Statistics | Patients by diagnosis, donors by application status. |
| Transplant Reports | Cases by stage, approval rate, time from referral to surgery. |
| Imaging & AI Reports | Studies per period, AI runs, average processing time, % of AI results edited by radiologists. |
| Financial Reports | Revenue by service and period, unpaid invoices. |
| System Usage Reports | Logins, active users, appointment no-show rate. |
| Export | Export reports to PDF or CSV. |

## **16\. HL7 Interoperability**

**Purpose:** Exchange data with external systems using HL7, through client applications.   

| Feature | Description |
| ----- | ----- |
| HL7 Interface (Server) | Receive and send HL7 v2 messages (e.g., using HAPI or Mirth Connect). |
| Patient Messages (ADT) | Send/receive patient registration and updates. |
| Appointment Messages (SIU) | Send/receive appointment booking, change and cancellation. |
| Order & Result Messages (ORM / ORU) | Lab and imaging orders out; lab results and radiology reports in. |
| Client Application | A separate app (e.g., a simulated external lab or clinic) that queries patient records and appointments and sends results. |
| Message Log | Store every message with its acknowledgement (ACK/NACK) and errors. |
| FHIR API | Optional FHIR REST endpoint for Patient and Appointment. |

---

**System Design**

## LiverLink uses a layered, modular architecture. A React frontend talks to a single Django REST backend that is split into functional modules and shares one PostgreSQL database. Imaging, AI, decision support, HL7 messaging and background jobs run as separate services around this core, and the whole system is deployed with Docker.

* **Users & Roles:** Admin, Clinical Staff and Patient, with sub-roles. Role-based access control (RBAC) decides what each user can see and do.  
* **Presentation Layer:** a React web portal with role-based dashboards, a patient portal, and an embedded DICOM viewer (OHIF / Cornerstone3D).  
* **Application Layer:** a Django \+ Django REST Framework API organized into modules (registry, scheduling, EMR, lab, prescriptions, radiology, AI, CDSS, transplant, billing, reporting, HL7, and others).  
* **Medical Imaging Layer:** CT studies are stored in Orthanc PACS and sent to the viewer through DICOMweb.  
* **AI Processing Layer:** segments the liver and lesions and calculates volumes. The radiologist reviews and confirms the results.  
* **Clinical Decision Support:** applies clinical rules (MELD, Milan criteria, GRWR, remnant liver volume) to the confirmed results and raises alerts. The doctor makes the final decision.  
* **Database Layer:** PostgreSQL stores all structured data. Images stay in Orthanc, and the database keeps only references to them.  
* **HL7 Interoperability:** HL7apy exchanges ADT, SIU, ORM and ORU messages with external labs and hospital systems.  
* **Background Services:** Celery workers with Redis handle notifications, reminders, invoices and AI jobs outside the main request.  
* **Security & Infrastructure:** HTTPS, authentication, RBAC, data encryption, audit logging, and Docker deployment.

**![][image1]**

*Figure 1\. System Design*

# **ER Diagram**

**Each figure shows the full attributes of its entities. Dashed boxes are entities shown in full in another figure.**

![][image2]

*Figure 2\. Users, patient & donor registry, and appointments*

 

*Figure 3\. Electronic medical records, labs and prescriptions*

   
![][image3]

*Figure 4\. Radiology, AI image analysis and clinical decision support*

   
*Figure 5\. Transplant cases, surgery and follow-up*

   
![][image4]

*Figure 6\. Billing, payments and HL7 integration*

# **Entity dictionary**

Each entity with a short description, its attributes and its relationships. 

| \# | Entity | Description |
| :---- | :---- | :---- |
| **Users & Access** |  |  |
| 1 | **User** | Login account for every person who uses the system. Holds the role used for access control. *Role \= admin, clinical\_staff or patient* |
| 2 | **Staff** | Profile of a staff member (clinical or admin). The job title sets the sub-role. *Job\_title \= hepatologist, radiologist, transplant\_surgeon, transplant\_coordinator, super\_admin, billing\_admin* |
| 3 | **AuditLog** | Record of who viewed, created or changed which record, and when. |
| **Patient & Donor Registry** |  |  |
| 4 | **Patient** | Profile of every person who receives care: liver patients, transplant recipients and living donors. *Category \= liver\_patient, recipient, donor* |
| 5 | **DonorApplication** | A potential donor's application to donate to a named recipient, and its screening result. |
| 6 | **Consent** | Signed informed consent (donor surgery, CT contrast, data use, transplant). |
| **Appointments** |  |  |
| 7 | **DoctorSchedule** | Working days and time slots a doctor is available for booking. |
| 8 | **Appointment** | A booked visit of a patient or donor with a staff member. *Type \= consultation, ct\_scan, lab\_visit, donor\_evaluation, recipient\_evaluation, follow\_up* |
| **Electronic Medical Records** |  |  |
| 9 | **Encounter** | The clinical record of one visit, with the doctor's notes. |
| 10 | **MedicalHistory** | Past conditions, cause of liver disease, surgeries, allergies and family history. |
| 11 | **Diagnosis** | A diagnosis made during an encounter, coded with ICD-10. |
| 12 | **VitalSigns** | Vital signs taken during an encounter. |
| 13 | **Document** | An uploaded file: external reports, signed consents, report PDFs. |
| **Labs & Prescriptions** |  |  |
| 14 | **LabTest** | Catalog of lab tests with their units and normal range. |
| 15 | **LabOrder** | A request for one or more lab tests, sent to the external lab. |
| 16 | **LabResult** | One test in an order. Value stays empty (pending) until the lab sends the result. *Flag \= normal, low, high, critical* |
| 17 | **Prescription** | A medication prescribed by a doctor. |
| 18 | **TreatmentPlan** | A treatment plan with goals, steps and a review date. |
| **Radiology & AI Analysis** |  |  |
| 19 | **ImagingOrder** | A request for a CT scan (e.g., multiphase liver CT, donor volumetry CT). |
| 20 | **ImagingStudy** | A DICOM CT study stored in Orthanc. Only its metadata and IDs are kept in the database. |
| 21 | **RadiologyReport** | The radiologist's signed report for a study, with the LI-RADS category. |
| 22 | **AIAnalysis** | One AI run on a study, its status, the liver volume, and the radiologist's review. *Analysis\_type \= liver\_lesion or donor\_volumetry* |
| 23 | **Lesion** | One lesion found by the AI, with AI and confirmed measurements. |
| 24 | **VolumetryResult** | Donor liver volumes from CT: total, planned graft and remnant. |
| **Clinical Decision Support** |  |  |
| 25 | **CDSSAssessment** | One decision-support run: scores, criteria checks, the suggestion and the doctor's decision. *Decision \= accepted or overridden* |
| 26 | **ClinicalAlert** | An alert shown to the care team (abnormal lab, rising AFP, criteria not met, test missing). |
| 27 | **CDSSThreshold** | Rule thresholds the admin can change (minimum GRWR, minimum remnant %, donor age and BMI limits). |
| **Transplant & Follow-up** |  |  |
| 28 | **TransplantCase** | A transplant process for one recipient, from referral to follow-up. Links the recipient to donors. *Status \= referred, under\_evaluation, committee\_review, approved, rejected, surgery\_scheduled, transplanted, follow\_up* |
| 29 | **CaseDonor** | Links a candidate donor to a transplant case and tracks that donor's status. *Status \= candidate, under\_evaluation, approved, not\_suitable, withdrawn* |
| 30 | **ChecklistItem** | A required test, visit or document for the recipient or a donor in a case. |
| 31 | **CommitteeDecision** | The transplant team's decision on a case, recorded by the hepatologist. |
| 32 | **CommitteeMember** | Staff who took part in a committee decision (many-to-many link). |
| 33 | **Surgery** | The transplant operation: schedule, graft details and outcome. |
| 34 | **SurgeryTeamMember** | Staff on the surgical team and their role (many-to-many link). |
| 35 | **FollowUpPlan** | The follow-up schedule after surgery, one for the recipient and one for each donor. |
| 36 | **FollowUpVisit** | One follow-up visit and its recovery findings. |
| **Billing & Payments** |  |  |
| 37 | **Service** | Catalog of billable services and their prices. |
| 38 | **Invoice** | A bill issued to a patient or donor. |
| 39 | **InvoiceItem** | One billed service on an invoice. |
| 40 | **Payment** | A payment against an invoice, online or at the desk. |
| **Notifications & HL7** |  |  |
| 41 | **Notification** | An in-app or email message sent to a user (reminders, results ready, case updates). |
| 42 | **ExternalSystem** | An outside system that exchanges HL7 messages (external lab, clinic, hospital system). |
| 43 | **HL7Message** | Log of every HL7 message sent or received, with its acknowledgement. *Message\_type e.g. ADT^A04, SIU^S12, ORM^O01, ORU^R01* |

---


# 4. Entity dictionary

### Users & Access

## 4.2 User

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Users & Access | user_id | 7 | 6 |

The login account of every person who uses LiverLink: admins, clinical staff, patients and donors. It only holds what is needed to sign in and to decide what the person may do; personal details live in Staff or Patient.

**Attributes**

| **\#** | **Attribute** | **Data type** | **Key** | **Required** | **Description**                                                       | **Allowed values / constraints** |
|--------|---------------|---------------|---------|--------------|-----------------------------------------------------------------------|----------------------------------|
| 1      | **user_id**   | int           | **PK**  | Yes          | Unique ID of each User record (generated automatically).              |                                  |
| 2      | email         | varchar       | **UQ**  | Yes          | Login email address of the user.                                      | Unique, valid email              |
| 3      | password_hash | varchar       |         | Yes          | Hashed password (the real password is never stored).                  |                                  |
| 4      | role          | enum          |         | Yes          | Main role used for access control.                                    | admin, clinical_staff, patient   |
| 5      | is_active     | bool          |         | Yes          | Whether this record is active (inactive records are kept but hidden). |                                  |
| 6      | last_login    | datetime      |         | No           | Date and time of the last successful login.                           |                                  |
| 7      | created_at    | datetime      |         | Yes          | When the record was created.                                          |                                  |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                 | **Linked by (foreign key)**  |
|--------------------|-----------------|---------------------------------------------------------------------------------------------|------------------------------|
| **Staff**          | **1 : 0..1**    | One User has profile at most one Staff.                                                     | Staff.user_id → User         |
| **Patient**        | **1 : 0..1**    | One User has profile at most one Patient.                                                   | Patient.user_id → User       |
| **AuditLog**       | **1 : N**       | One User performs many AuditLog records; each AuditLog belongs to exactly one User.         | AuditLog.user_id → User      |
| **Notification**   | **1 : N**       | One User receives many Notification records; each Notification belongs to exactly one User. | Notification.user_id → User  |
| **Document**       | **1 : N**       | One User uploads many Document records; each Document belongs to exactly one User.          | Document.uploaded_by → User  |
| **Appointment**    | **1 : N**       | One User books many Appointment records; each Appointment belongs to exactly one User.      | Appointment.booked_by → User |

**Business rules**

- Each email can be used by one account only.

- A deactivated account cannot log in, but its records are kept.

- The role decides which pages and APIs the user can reach.

## 4.3 Staff

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Users & Access | staff_id | 7 | 25 |

The profile of a hospital employee. Clinical staff and admins share this table; the job title sets the sub-role (e.g., only a radiologist can sign a radiology report).

**Attributes**

| **\#** | **Attribute** | **Data type** | **Key**    | **Required** | **Description**                                                  | **Allowed values / constraints**                                                                  |
|--------|---------------|---------------|------------|--------------|------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| 1      | **staff_id**  | int           | **PK**     | Yes          | Unique ID of each Staff record (generated automatically).        |                                                                                                   |
| 2      | *user_id*     | int           | **FK, UQ** | Yes          | Login account of the staff member.                               | → User.user_id · Unique                                                                           |
| 3      | full_name     | varchar       |            | Yes          | Full name of the staff member.                                   |                                                                                                   |
| 4      | job_title     | enum          |            | Yes          | Sub-role of the staff member; decides which actions they can do. | hepatologist, radiologist, transplant_surgeon, transplant_coordinator, super_admin, billing_admin |
| 5      | license_no    | varchar       |            | No           | Medical license or syndicate number.                             |                                                                                                   |
| 6      | department    | varchar       |            | No           | Department or unit the staff member works in.                    |                                                                                                   |
| 7      | phone         | varchar       |            | No           | Contact phone number.                                            |                                                                                                   |

**Relationships**

| **Related entity**    | **Cardinality** | **Meaning**                                                                                              | **Linked by (foreign key)**            |
|-----------------------|-----------------|----------------------------------------------------------------------------------------------------------|----------------------------------------|
| **User**              | **0..1 : 1**    | One User has profile at most one Staff.                                                                  | Staff.user_id → User                   |
| **DonorApplication**  | **1 : N**       | One Staff screens many DonorApplication records; each DonorApplication may link to one Staff (optional). | DonorApplication.screened_by → Staff   |
| **Consent**           | **1 : N**       | One Staff witnesses many Consent records; each Consent may link to one Staff (optional).                 | Consent.witnessed_by → Staff           |
| **DoctorSchedule**    | **1 : N**       | One Staff defines many DoctorSchedule records; each DoctorSchedule belongs to exactly one Staff.         | DoctorSchedule.staff_id → Staff        |
| **Appointment**       | **1 : N**       | One Staff sees patient in many Appointment records; each Appointment belongs to exactly one Staff.       | Appointment.staff_id → Staff           |
| **Encounter**         | **1 : N**       | One Staff conducts many Encounter records; each Encounter belongs to exactly one Staff.                  | Encounter.staff_id → Staff             |
| **MedicalHistory**    | **1 : N**       | One Staff records many MedicalHistory records; each MedicalHistory may link to one Staff (optional).     | MedicalHistory.recorded_by → Staff     |
| **LabOrder**          | **1 : N**       | One Staff orders many LabOrder records; each LabOrder belongs to exactly one Staff.                      | LabOrder.ordered_by → Staff            |
| **Prescription**      | **1 : N**       | One Staff prescribes many Prescription records; each Prescription belongs to exactly one Staff.          | Prescription.prescribed_by → Staff     |
| **TreatmentPlan**     | **1 : N**       | One Staff creates many TreatmentPlan records; each TreatmentPlan belongs to exactly one Staff.           | TreatmentPlan.created_by → Staff       |
| **ImagingOrder**      | **1 : N**       | One Staff orders many ImagingOrder records; each ImagingOrder belongs to exactly one Staff.              | ImagingOrder.ordered_by → Staff        |
| **RadiologyReport**   | **1 : N**       | One Staff signs many RadiologyReport records; each RadiologyReport belongs to exactly one Staff.         | RadiologyReport.radiologist_id → Staff |
| **AIAnalysis**        | **1 : N**       | One Staff reviews many AIAnalysis records; each AIAnalysis may link to one Staff (optional).             | AIAnalysis.reviewed_by → Staff         |
| **VolumetryResult**   | **1 : N**       | One Staff confirms many VolumetryResult records; each VolumetryResult may link to one Staff (optional).  | VolumetryResult.confirmed_by → Staff   |
| **CDSSAssessment**    | **1 : N**       | One Staff decides many CDSSAssessment records; each CDSSAssessment may link to one Staff (optional).     | CDSSAssessment.decided_by → Staff      |
| **ClinicalAlert**     | **1 : N**       | One Staff acknowledges many ClinicalAlert records; each ClinicalAlert may link to one Staff (optional).  | ClinicalAlert.acknowledged_by → Staff  |
| **CDSSThreshold**     | **1 : N**       | One Staff updates many CDSSThreshold records; each CDSSThreshold belongs to exactly one Staff.           | CDSSThreshold.updated_by → Staff       |
| **TransplantCase**    | **1 : N**       | One Staff refers many TransplantCase records; each TransplantCase belongs to exactly one Staff.          | TransplantCase.referred_by → Staff     |
| **TransplantCase**    | **1 : N**       | One Staff coordinates many TransplantCase records; each TransplantCase may link to one Staff (optional). | TransplantCase.coordinator_id → Staff  |
| **CommitteeDecision** | **1 : N**       | One Staff records many CommitteeDecision records; each CommitteeDecision belongs to exactly one Staff.   | CommitteeDecision.recorded_by → Staff  |
| **CommitteeMember**   | **1 : N**       | One Staff takes part as many CommitteeMember records; each CommitteeMember belongs to exactly one Staff. | CommitteeMember.staff_id → Staff       |
| **Surgery**           | **1 : N**       | One Staff leads many Surgery records; each Surgery belongs to exactly one Staff.                         | Surgery.lead_surgeon_id → Staff        |
| **SurgeryTeamMember** | **1 : N**       | One Staff serves as many SurgeryTeamMember records; each SurgeryTeamMember belongs to exactly one Staff. | SurgeryTeamMember.staff_id → Staff     |
| **Invoice**           | **1 : N**       | One Staff issues many Invoice records; each Invoice may link to one Staff (optional).                    | Invoice.issued_by → Staff              |
| **Payment**           | **1 : N**       | One Staff receives many Payment records; each Payment may link to one Staff (optional).                  | Payment.received_by → Staff            |

**Business rules**

- Each staff member has exactly one User account.

- Only an admin can create staff accounts or change a job title.

## 4.4 AuditLog

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Users & Access | log_id | 8 | 2 |

A security log that records every important action on patient data. It answers "who saw or changed this record, and when?".

**Attributes**

| **\#** | **Attribute** | **Data type** | **Key** | **Required** | **Description**                                              | **Allowed values / constraints**                    |
|--------|---------------|---------------|---------|--------------|--------------------------------------------------------------|-----------------------------------------------------|
| 1      | **log_id**    | int           | **PK**  | Yes          | Unique ID of each AuditLog record (generated automatically). |                                                     |
| 2      | *user_id*     | int           | **FK**  | Yes          | User who did the action.                                     | → User.user_id                                      |
| 3      | *patient_id*  | int           | **FK**  | No           | Patient whose record was touched (if any).                   | → Patient.patient_id                                |
| 4      | action        | enum          |         | Yes          | What was done (view, create, update, delete, login, export). | view, create, update, delete, login, logout, export |
| 5      | entity_type   | varchar       |         | Yes          | Name of the table the action was on.                         |                                                     |
| 6      | entity_id     | int           |         | No           | ID of the row the action was on.                             |                                                     |
| 7      | ip_address    | varchar       |         | No           | IP address the request came from.                            |                                                     |
| 8      | timestamp     | datetime      |         | Yes          | When the action happened.                                    |                                                     |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                         | **Linked by (foreign key)**   |
|--------------------|-----------------|-----------------------------------------------------------------------------------------------------|-------------------------------|
| **User**           | **N : 1**       | One User performs many AuditLog records; each AuditLog belongs to exactly one User.                 | AuditLog.user_id → User       |
| **Patient**        | **N : 1**       | One Patient is accessed in many AuditLog records; each AuditLog may link to one Patient (optional). | AuditLog.patient_id → Patient |

**Business rules**

- Rows are only added, never edited or deleted.

- Every view, create, update and delete on clinical data writes a row.

### Patient & Donor Registry

## 4.5 Patient

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Patient & Donor Registry | patient_id | 16 | 23 |

The central profile of anyone who receives care: liver patients, transplant recipients and living donors. Almost every clinical table points to it.

**Attributes**

| **\#** | **Attribute**     | **Data type** | **Key**    | **Required** | **Description**                                                                 | **Allowed values / constraints** |
|--------|-------------------|---------------|------------|--------------|---------------------------------------------------------------------------------|----------------------------------|
| 1      | **patient_id**    | int           | **PK**     | Yes          | Unique ID of each Patient record (generated automatically).                     |                                  |
| 2      | *user_id*         | int           | **FK, UQ** | No           | Login account of the patient (empty if registered by staff without an account). | → User.user_id · Unique          |
| 3      | mrn               | varchar       | **UQ**     | Yes          | Medical Record Number generated by the system for this person.                  | Unique, e.g. LL-000482           |
| 4      | national_id       | varchar       | **UQ**     | No           | Egyptian national ID number.                                                    | Unique, 14 digits                |
| 5      | first_name        | varchar       |            | Yes          | First name.                                                                     |                                  |
| 6      | last_name         | varchar       |            | Yes          | Family name.                                                                    |                                  |
| 7      | date_of_birth     | date          |            | Yes          | Date of birth (used to calculate age).                                          |                                  |
| 8      | sex               | enum          |            | Yes          | Biological sex.                                                                 | male, female                     |
| 9      | phone             | varchar       |            | Yes          | Contact phone number.                                                           |                                  |
| 10     | address           | text          |            | No           | Home address.                                                                   |                                  |
| 11     | emergency_contact | varchar       |            | No           | Name and phone of an emergency contact.                                         |                                  |
| 12     | blood_group       | enum          |            | No           | ABO blood group and Rh factor.                                                  | A+, A-, B+, B-, AB+, AB-, O+, O- |
| 13     | height_cm         | decimal       |            | No           | Height in centimetres.                                                          | \> 0                             |
| 14     | weight_kg         | decimal       |            | No           | Body weight in kilograms (used for GRWR).                                       | \> 0                             |
| 15     | category          | enum          |            | Yes          | Current category of the person.                                                 | liver_patient, recipient, donor  |
| 16     | created_at        | datetime      |            | Yes          | When the record was created.                                                    |                                  |

**Relationships**

| **Related entity**   | **Cardinality** | **Meaning**                                                                                                            | **Linked by (foreign key)**             |
|----------------------|-----------------|------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| **User**             | **0..1 : 1**    | One User has profile at most one Patient.                                                                              | Patient.user_id → User                  |
| **AuditLog**         | **1 : N**       | One Patient is accessed in many AuditLog records; each AuditLog may link to one Patient (optional).                    | AuditLog.patient_id → Patient           |
| **DonorApplication** | **1 : N**       | One Patient applies as donor many DonorApplication records; each DonorApplication belongs to exactly one Patient.      | DonorApplication.donor_id → Patient     |
| **DonorApplication** | **1 : N**       | One Patient is named recipient in many DonorApplication records; each DonorApplication belongs to exactly one Patient. | DonorApplication.recipient_id → Patient |
| **Consent**          | **1 : N**       | One Patient signs many Consent records; each Consent belongs to exactly one Patient.                                   | Consent.patient_id → Patient            |
| **Appointment**      | **1 : N**       | One Patient has many Appointment records; each Appointment belongs to exactly one Patient.                             | Appointment.patient_id → Patient        |
| **Encounter**        | **1 : N**       | One Patient has many Encounter records; each Encounter belongs to exactly one Patient.                                 | Encounter.patient_id → Patient          |
| **MedicalHistory**   | **1 : N**       | One Patient has many MedicalHistory records; each MedicalHistory belongs to exactly one Patient.                       | MedicalHistory.patient_id → Patient     |
| **Diagnosis**        | **1 : N**       | One Patient has many Diagnosis records; each Diagnosis belongs to exactly one Patient.                                 | Diagnosis.patient_id → Patient          |
| **Document**         | **1 : N**       | One Patient owns many Document records; each Document may link to one Patient (optional).                              | Document.patient_id → Patient           |
| **LabOrder**         | **1 : N**       | One Patient has many LabOrder records; each LabOrder belongs to exactly one Patient.                                   | LabOrder.patient_id → Patient           |
| **Prescription**     | **1 : N**       | One Patient receives many Prescription records; each Prescription belongs to exactly one Patient.                      | Prescription.patient_id → Patient       |
| **TreatmentPlan**    | **1 : N**       | One Patient follows many TreatmentPlan records; each TreatmentPlan belongs to exactly one Patient.                     | TreatmentPlan.patient_id → Patient      |
| **ImagingOrder**     | **1 : N**       | One Patient has many ImagingOrder records; each ImagingOrder belongs to exactly one Patient.                           | ImagingOrder.patient_id → Patient       |
| **ImagingStudy**     | **1 : N**       | One Patient has many ImagingStudy records; each ImagingStudy belongs to exactly one Patient.                           | ImagingStudy.patient_id → Patient       |
| **CDSSAssessment**   | **1 : N**       | One Patient is assessed in many CDSSAssessment records; each CDSSAssessment belongs to exactly one Patient.            | CDSSAssessment.patient_id → Patient     |
| **ClinicalAlert**    | **1 : N**       | One Patient has many ClinicalAlert records; each ClinicalAlert belongs to exactly one Patient.                         | ClinicalAlert.patient_id → Patient      |
| **TransplantCase**   | **1 : N**       | One Patient is recipient in many TransplantCase records; each TransplantCase belongs to exactly one Patient.           | TransplantCase.recipient_id → Patient   |
| **CaseDonor**        | **1 : N**       | One Patient is donor in many CaseDonor records; each CaseDonor belongs to exactly one Patient.                         | CaseDonor.donor_id → Patient            |
| **ChecklistItem**    | **1 : N**       | One Patient must complete many ChecklistItem records; each ChecklistItem belongs to exactly one Patient.               | ChecklistItem.patient_id → Patient      |
| **FollowUpPlan**     | **1 : N**       | One Patient follows many FollowUpPlan records; each FollowUpPlan belongs to exactly one Patient.                       | FollowUpPlan.patient_id → Patient       |
| **Invoice**          | **1 : N**       | One Patient is billed in many Invoice records; each Invoice belongs to exactly one Patient.                            | Invoice.patient_id → Patient            |
| **HL7Message**       | **1 : N**       | One Patient is subject of many HL7Message records; each HL7Message may link to one Patient (optional).                 | HL7Message.patient_id → Patient         |

**Business rules**

- MRN and national ID are unique.

- Weight is required before a GRWR check can run.

- A person can move between categories (e.g., liver patient → recipient).

## 4.6 DonorApplication

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Patient & Donor Registry | application_id | 8 | 4 |

A request from a person who wants to donate part of their liver to a named recipient. The coordinator screens it before the donor joins a transplant case.

**Attributes**

| **\#** | **Attribute**      | **Data type** | **Key** | **Required** | **Description**                                                      | **Allowed values / constraints**                    |
|--------|--------------------|---------------|---------|--------------|----------------------------------------------------------------------|-----------------------------------------------------|
| 1      | **application_id** | int           | **PK**  | Yes          | Unique ID of each DonorApplication record (generated automatically). |                                                     |
| 2      | *donor_id*         | int           | **FK**  | Yes          | The person applying to donate.                                       | → Patient.patient_id                                |
| 3      | *recipient_id*     | int           | **FK**  | Yes          | The patient the donor wants to donate to.                            | → Patient.patient_id                                |
| 4      | relationship       | varchar       |         | Yes          | Relationship of the donor to the recipient (son, wife, brother...).  |                                                     |
| 5      | status             | enum          |         | Yes          | Current status of the record.                                        | submitted, screening, accepted, rejected, withdrawn |
| 6      | *screened_by*      | int           | **FK**  | No           | Coordinator who screened the application.                            | → Staff.staff_id                                    |
| 7      | screening_notes    | text          |         | No           | Coordinator notes from screening the application.                    |                                                     |
| 8      | submitted_at       | datetime      |         | Yes          | When the application was submitted.                                  |                                                     |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                            | **Linked by (foreign key)**                 |
|--------------------|-----------------|------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| **Patient**        | **N : 1**       | One Patient applies as donor many DonorApplication records; each DonorApplication belongs to exactly one Patient.      | DonorApplication.donor_id → Patient         |
| **Patient**        | **N : 1**       | One Patient is named recipient in many DonorApplication records; each DonorApplication belongs to exactly one Patient. | DonorApplication.recipient_id → Patient     |
| **Staff**          | **N : 1**       | One Staff screens many DonorApplication records; each DonorApplication may link to one Staff (optional).               | DonorApplication.screened_by → Staff        |
| **CaseDonor**      | **1 : 0..1**    | One DonorApplication becomes at most one CaseDonor.                                                                    | CaseDonor.application_id → DonorApplication |

**Business rules**

- Donor and recipient must be different people.

- Only an accepted application can be added to a transplant case.

## 4.7 Consent

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Patient & Donor Registry | consent_id | 7 | 3 |

A record that a patient or donor signed an informed consent form, with the scanned form attached.

**Attributes**

| **\#** | **Attribute**  | **Data type** | **Key** | **Required** | **Description**                                             | **Allowed values / constraints**                         |
|--------|----------------|---------------|---------|--------------|-------------------------------------------------------------|----------------------------------------------------------|
| 1      | **consent_id** | int           | **PK**  | Yes          | Unique ID of each Consent record (generated automatically). |                                                          |
| 2      | *patient_id*   | int           | **FK**  | Yes          | Person who signed.                                          | → Patient.patient_id                                     |
| 3      | *document_id*  | int           | **FK**  | No           | Scanned copy of the signed form.                            | → Document.document_id                                   |
| 4      | consent_type   | enum          |         | Yes          | What the consent covers.                                    | donor_surgery, transplant_surgery, ct_contrast, data_use |
| 5      | *witnessed_by* | int           | **FK**  | No           | Staff member who witnessed the signature.                   | → Staff.staff_id                                         |
| 6      | signed_at      | datetime      |         | No           | When it was signed.                                         |                                                          |
| 7      | status         | enum          |         | Yes          | Current status of the record.                               | signed, withdrawn                                        |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                              | **Linked by (foreign key)**    |
|--------------------|-----------------|------------------------------------------------------------------------------------------|--------------------------------|
| **Patient**        | **N : 1**       | One Patient signs many Consent records; each Consent belongs to exactly one Patient.     | Consent.patient_id → Patient   |
| **Staff**          | **N : 1**       | One Staff witnesses many Consent records; each Consent may link to one Staff (optional). | Consent.witnessed_by → Staff   |
| **Document**       | **0..1 : 1**    | One Document is the signed copy of at most one Consent.                                  | Consent.document_id → Document |

**Business rules**

- A donor cannot go to surgery without a signed donor_surgery consent.

- A withdrawn consent stops the related steps.

### Appointments

## 4.8 DoctorSchedule

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Appointments | schedule_id | 7 | 1 |

Defines when a doctor is available. The booking page uses it to show free slots.

**Attributes**

| **\#** | **Attribute**   | **Data type** | **Key** | **Required** | **Description**                                                       | **Allowed values / constraints**  |
|--------|-----------------|---------------|---------|--------------|-----------------------------------------------------------------------|-----------------------------------|
| 1      | **schedule_id** | int           | **PK**  | Yes          | Unique ID of each DoctorSchedule record (generated automatically).    |                                   |
| 2      | *staff_id*      | int           | **FK**  | Yes          | Doctor this schedule belongs to.                                      | → Staff.staff_id                  |
| 3      | day_of_week     | enum          |         | Yes          | Day of the week this schedule applies to.                             | sat, sun, mon, tue, wed, thu, fri |
| 4      | start_time      | time          |         | Yes          | Start time.                                                           |                                   |
| 5      | end_time        | time          |         | Yes          | End time.                                                             | After start_time                  |
| 6      | slot_minutes    | int           |         | Yes          | Length of each bookable slot in minutes.                              | \> 0, e.g. 15 or 30               |
| 7      | is_active       | bool          |         | Yes          | Whether this record is active (inactive records are kept but hidden). |                                   |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                      | **Linked by (foreign key)**     |
|--------------------|-----------------|--------------------------------------------------------------------------------------------------|---------------------------------|
| **Staff**          | **N : 1**       | One Staff defines many DoctorSchedule records; each DoctorSchedule belongs to exactly one Staff. | DoctorSchedule.staff_id → Staff |

**Business rules**

- end_time must be after start_time.

- Slots of the same doctor on the same day must not overlap.

## 4.9 Appointment

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Appointments | appointment_id | 10 | 7 |

A visit booked for a patient or donor with a doctor: consultations, scans, evaluations and follow-ups.

**Attributes**

| **\#** | **Attribute**      | **Data type** | **Key** | **Required** | **Description**                                                 | **Allowed values / constraints**                                                    |
|--------|--------------------|---------------|---------|--------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------|
| 1      | **appointment_id** | int           | **PK**  | Yes          | Unique ID of each Appointment record (generated automatically). |                                                                                     |
| 2      | *patient_id*       | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                      | → Patient.patient_id                                                                |
| 3      | *staff_id*         | int           | **FK**  | Yes          | Doctor or staff member the visit is with.                       | → Staff.staff_id                                                                    |
| 4      | *case_id*          | int           | **FK**  | No           | Transplant case, if this is an evaluation visit.                | → TransplantCase.case_id                                                            |
| 5      | *booked_by*        | int           | **FK**  | Yes          | User who made the booking (patient or staff).                   | → User.user_id                                                                      |
| 6      | appointment_type   | enum          |         | Yes          | Kind of visit.                                                  | consultation, ct_scan, lab_visit, donor_evaluation, recipient_evaluation, follow_up |
| 7      | start_time         | datetime      |         | Yes          | Start date and time.                                            |                                                                                     |
| 8      | end_time           | datetime      |         | Yes          | End date and time.                                              | After start_time                                                                    |
| 9      | status             | enum          |         | Yes          | Current status of the record.                                   | booked, checked_in, completed, no_show, cancelled                                   |
| 10     | reason             | text          |         | No           | Reason for the visit, as entered when booking.                  |                                                                                     |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                                        | **Linked by (foreign key)**                |
|--------------------|-----------------|------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| **User**           | **N : 1**       | One User books many Appointment records; each Appointment belongs to exactly one User.                                             | Appointment.booked_by → User               |
| **Patient**        | **N : 1**       | One Patient has many Appointment records; each Appointment belongs to exactly one Patient.                                         | Appointment.patient_id → Patient           |
| **Staff**          | **N : 1**       | One Staff sees patient in many Appointment records; each Appointment belongs to exactly one Staff.                                 | Appointment.staff_id → Staff               |
| **TransplantCase** | **N : 1**       | One TransplantCase includes evaluation visit many Appointment records; each Appointment may link to one TransplantCase (optional). | Appointment.case_id → TransplantCase       |
| **Encounter**      | **1 : 0..1**    | One Appointment results in at most one Encounter.                                                                                  | Encounter.appointment_id → Appointment     |
| **FollowUpVisit**  | **1 : 0..1**    | One Appointment is booked for at most one FollowUpVisit.                                                                           | FollowUpVisit.appointment_id → Appointment |
| **InvoiceItem**    | **1 : N**       | One Appointment is charged in many InvoiceItem records; each InvoiceItem may link to one Appointment (optional).                   | InvoiceItem.appointment_id → Appointment   |

**Business rules**

- Two booked appointments cannot use the same doctor slot.

- Cancelled and no-show appointments are kept for reports.

- Evaluation visits are linked to their transplant case.

### Electronic Medical Records

## 4.10 Encounter

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Electronic Medical Records | encounter_id | 8 | 9 |

The clinical record of one visit: what the doctor found and wrote. Diagnoses, vitals, orders and prescriptions hang off it.

**Attributes**

| **\#** | **Attribute**    | **Data type** | **Key**    | **Required** | **Description**                                               | **Allowed values / constraints**                                      |
|--------|------------------|---------------|------------|--------------|---------------------------------------------------------------|-----------------------------------------------------------------------|
| 1      | **encounter_id** | int           | **PK**     | Yes          | Unique ID of each Encounter record (generated automatically). |                                                                       |
| 2      | *patient_id*     | int           | **FK**     | Yes          | Patient (or donor) this record belongs to.                    | → Patient.patient_id                                                  |
| 3      | *appointment_id* | int           | **FK, UQ** | No           | Appointment this visit came from (empty for walk-ins).        | → Appointment.appointment_id · Unique (one encounter per appointment) |
| 4      | *staff_id*       | int           | **FK**     | Yes          | Doctor who saw the patient.                                   | → Staff.staff_id                                                      |
| 5      | encounter_date   | datetime      |            | Yes          | Date and time of the visit.                                   |                                                                       |
| 6      | chief_complaint  | text          |            | No           | Main complaint in the patient's words.                        |                                                                       |
| 7      | clinical_notes   | text          |            | No           | Doctor's notes for this visit.                                |                                                                       |
| 8      | status           | enum          |            | Yes          | Current status of the record.                                 | open, signed                                                          |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                    | **Linked by (foreign key)**                      |
|--------------------|-----------------|----------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| **Appointment**    | **0..1 : 1**    | One Appointment results in at most one Encounter.                                                              | Encounter.appointment_id → Appointment           |
| **Patient**        | **N : 1**       | One Patient has many Encounter records; each Encounter belongs to exactly one Patient.                         | Encounter.patient_id → Patient                   |
| **Staff**          | **N : 1**       | One Staff conducts many Encounter records; each Encounter belongs to exactly one Staff.                        | Encounter.staff_id → Staff                       |
| **Diagnosis**      | **1 : N**       | One Encounter records many Diagnosis records; each Diagnosis belongs to exactly one Encounter.                 | Diagnosis.encounter_id → Encounter               |
| **VitalSigns**     | **1 : N**       | One Encounter records many VitalSigns records; each VitalSigns belongs to exactly one Encounter.               | VitalSigns.encounter_id → Encounter              |
| **LabOrder**       | **1 : N**       | One Encounter creates many LabOrder records; each LabOrder may link to one Encounter (optional).               | LabOrder.encounter_id → Encounter                |
| **Prescription**   | **1 : N**       | One Encounter creates many Prescription records; each Prescription may link to one Encounter (optional).       | Prescription.encounter_id → Encounter            |
| **ImagingOrder**   | **1 : N**       | One Encounter creates many ImagingOrder records; each ImagingOrder may link to one Encounter (optional).       | ImagingOrder.encounter_id → Encounter            |
| **TransplantCase** | **1 : N (1:1)** | One Encounter refers to many TransplantCase records; each TransplantCase may link to one Encounter (optional). | TransplantCase.referral_encounter_id → Encounter |

**Business rules**

- At most one encounter per appointment.

- Once signed, an encounter can only be changed by an addendum.

## 4.11 MedicalHistory

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Electronic Medical Records | history_id | 6 | 2 |

Background information about the patient: past illnesses, cause of liver disease, surgeries, allergies and family history.

**Attributes**

| **\#** | **Attribute**  | **Data type** | **Key** | **Required** | **Description**                                                    | **Allowed values / constraints**                            |
|--------|----------------|---------------|---------|--------------|--------------------------------------------------------------------|-------------------------------------------------------------|
| 1      | **history_id** | int           | **PK**  | Yes          | Unique ID of each MedicalHistory record (generated automatically). |                                                             |
| 2      | *patient_id*   | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                         | → Patient.patient_id                                        |
| 3      | history_type   | enum          |         | Yes          | Kind of history item.                                              | condition, liver_etiology, surgery, allergy, family_history |
| 4      | description    | text          |         | Yes          | Free-text description.                                             |                                                             |
| 5      | onset_date     | date          |         | No           | When the condition started or the event happened.                  |                                                             |
| 6      | *recorded_by*  | int           | **FK**  | No           | Staff member who recorded it.                                      | → Staff.staff_id                                            |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                          | **Linked by (foreign key)**         |
|--------------------|-----------------|------------------------------------------------------------------------------------------------------|-------------------------------------|
| **Patient**        | **N : 1**       | One Patient has many MedicalHistory records; each MedicalHistory belongs to exactly one Patient.     | MedicalHistory.patient_id → Patient |
| **Staff**          | **N : 1**       | One Staff records many MedicalHistory records; each MedicalHistory may link to one Staff (optional). | MedicalHistory.recorded_by → Staff  |

**Business rules**

- Allergies are shown as a warning when prescribing.

## 4.12 Diagnosis

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Electronic Medical Records | diagnosis_id | 8 | 2 |

A diagnosis recorded in a visit, coded with ICD-10 so it can be reported and shared.

**Attributes**

| **\#** | **Attribute**    | **Data type** | **Key** | **Required** | **Description**                                               | **Allowed values / constraints** |
|--------|------------------|---------------|---------|--------------|---------------------------------------------------------------|----------------------------------|
| 1      | **diagnosis_id** | int           | **PK**  | Yes          | Unique ID of each Diagnosis record (generated automatically). |                                  |
| 2      | *encounter_id*   | int           | **FK**  | Yes          | Visit (encounter) in which this was recorded.                 | → Encounter.encounter_id         |
| 3      | *patient_id*     | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                    | → Patient.patient_id             |
| 4      | icd10_code       | varchar       |         | Yes          | ICD-10 diagnosis code (e.g., K74.6 cirrhosis, C22.0 HCC).     | Valid ICD-10 code                |
| 5      | description      | varchar       |         | Yes          | Diagnosis name.                                               |                                  |
| 6      | is_primary       | bool          |         | Yes          | Whether this is the main diagnosis of the visit.              |                                  |
| 7      | status           | enum          |         | Yes          | Current status of the record.                                 | active, resolved                 |
| 8      | diagnosed_at     | datetime      |         | Yes          | When the diagnosis was made.                                  |                                  |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                    | **Linked by (foreign key)**        |
|--------------------|-----------------|------------------------------------------------------------------------------------------------|------------------------------------|
| **Encounter**      | **N : 1**       | One Encounter records many Diagnosis records; each Diagnosis belongs to exactly one Encounter. | Diagnosis.encounter_id → Encounter |
| **Patient**        | **N : 1**       | One Patient has many Diagnosis records; each Diagnosis belongs to exactly one Patient.         | Diagnosis.patient_id → Patient     |

**Business rules**

- Each encounter has at most one primary diagnosis.

## 4.13 VitalSigns

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Electronic Medical Records | vitals_id | 10 | 1 |

Measurements taken in a visit: blood pressure, pulse, temperature, weight, height and BMI.

**Attributes**

| **\#** | **Attribute**  | **Data type** | **Key** | **Required** | **Description**                                                | **Allowed values / constraints** |
|--------|----------------|---------------|---------|--------------|----------------------------------------------------------------|----------------------------------|
| 1      | **vitals_id**  | int           | **PK**  | Yes          | Unique ID of each VitalSigns record (generated automatically). |                                  |
| 2      | *encounter_id* | int           | **FK**  | Yes          | Visit (encounter) in which this was recorded.                  | → Encounter.encounter_id         |
| 3      | bp_systolic    | int           |         | No           | Systolic blood pressure (mmHg).                                |                                  |
| 4      | bp_diastolic   | int           |         | No           | Diastolic blood pressure (mmHg).                               |                                  |
| 5      | pulse          | int           |         | No           | Heart rate (beats per minute).                                 |                                  |
| 6      | temperature    | decimal       |         | No           | Body temperature (°C).                                         |                                  |
| 7      | weight_kg      | decimal       |         | No           | Body weight in kilograms (used for GRWR).                      |                                  |
| 8      | height_cm      | decimal       |         | No           | Height in centimetres.                                         |                                  |
| 9      | bmi            | decimal       |         | No           | Body mass index, calculated from weight and height.            | weight_kg / (height_m)²          |
| 10     | recorded_at    | datetime      |         | Yes          | When the readings were taken.                                  |                                  |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                      | **Linked by (foreign key)**         |
|--------------------|-----------------|--------------------------------------------------------------------------------------------------|-------------------------------------|
| **Encounter**      | **N : 1**       | One Encounter records many VitalSigns records; each VitalSigns belongs to exactly one Encounter. | VitalSigns.encounter_id → Encounter |

**Business rules**

- BMI is calculated by the system from weight and height.

## 4.14 Document

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Electronic Medical Records | document_id | 8 | 3 |

An uploaded file such as an external report or a signed consent form.

**Attributes**

| **\#** | **Attribute**   | **Data type** | **Key** | **Required** | **Description**                                              | **Allowed values / constraints**                                   |
|--------|-----------------|---------------|---------|--------------|--------------------------------------------------------------|--------------------------------------------------------------------|
| 1      | **document_id** | int           | **PK**  | Yes          | Unique ID of each Document record (generated automatically). |                                                                    |
| 2      | *patient_id*    | int           | **FK**  | No           | Patient the document belongs to.                             | → Patient.patient_id                                               |
| 3      | *uploaded_by*   | int           | **FK**  | Yes          | User who uploaded the file.                                  | → User.user_id                                                     |
| 4      | document_type   | enum          |         | Yes          | Kind of document.                                            | external_report, consent_form, radiology_report, lab_report, other |
| 5      | title           | varchar       |         | Yes          | Short title shown in lists.                                  |                                                                    |
| 6      | file_path       | varchar       |         | Yes          | Storage path of the uploaded file.                           |                                                                    |
| 7      | is_released     | bool          |         | Yes          | Whether the patient can see it in the portal.                |                                                                    |
| 8      | uploaded_at     | datetime      |         | Yes          | When the file was uploaded.                                  |                                                                    |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                               | **Linked by (foreign key)**    |
|--------------------|-----------------|-------------------------------------------------------------------------------------------|--------------------------------|
| **User**           | **N : 1**       | One User uploads many Document records; each Document belongs to exactly one User.        | Document.uploaded_by → User    |
| **Consent**        | **1 : 0..1**    | One Document is the signed copy of at most one Consent.                                   | Consent.document_id → Document |
| **Patient**        | **N : 1**       | One Patient owns many Document records; each Document may link to one Patient (optional). | Document.patient_id → Patient  |

**Business rules**

- Patients can only see documents marked as released.

### Labs & Prescriptions

## 4.15 LabTest

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Labs & Prescriptions | lab_test_id | 6 | 1 |

The catalog of lab tests the center can order, with each test's unit and normal range.

**Attributes**

| **\#** | **Attribute**   | **Data type** | **Key** | **Required** | **Description**                                             | **Allowed values / constraints** |
|--------|-----------------|---------------|---------|--------------|-------------------------------------------------------------|----------------------------------|
| 1      | **lab_test_id** | int           | **PK**  | Yes          | Unique ID of each LabTest record (generated automatically). |                                  |
| 2      | code            | varchar       | **UQ**  | Yes          | Test code (e.g., LOINC).                                    | Unique                           |
| 3      | name            | varchar       |         | Yes          | Test name (e.g., Total bilirubin).                          |                                  |
| 4      | unit            | varchar       |         | No           | Unit of measurement.                                        |                                  |
| 5      | normal_min      | decimal       |         | No           | Lower limit of the normal range.                            |                                  |
| 6      | normal_max      | decimal       |         | No           | Upper limit of the normal range.                            |                                  |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                | **Linked by (foreign key)**     |
|--------------------|-----------------|--------------------------------------------------------------------------------------------|---------------------------------|
| **LabResult**      | **1 : N**       | One LabTest defines many LabResult records; each LabResult belongs to exactly one LabTest. | LabResult.lab_test_id → LabTest |

**Business rules**

- The normal range is used to set the flag on each result.

## 4.16 LabOrder

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Labs & Prescriptions | lab_order_id | 7 | 4 |

A doctor's request for lab tests, sent to the external lab through HL7 (ORM message).

**Attributes**

| **\#** | **Attribute**    | **Data type** | **Key** | **Required** | **Description**                                              | **Allowed values / constraints**                 |
|--------|------------------|---------------|---------|--------------|--------------------------------------------------------------|--------------------------------------------------|
| 1      | **lab_order_id** | int           | **PK**  | Yes          | Unique ID of each LabOrder record (generated automatically). |                                                  |
| 2      | *patient_id*     | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                   | → Patient.patient_id                             |
| 3      | *encounter_id*   | int           | **FK**  | No           | Visit the order was made in.                                 | → Encounter.encounter_id                         |
| 4      | *ordered_by*     | int           | **FK**  | Yes          | Doctor who ordered the tests.                                | → Staff.staff_id                                 |
| 5      | order_date       | datetime      |         | Yes          | When the order was placed.                                   |                                                  |
| 6      | priority         | enum          |         | Yes          | How urgent the order is.                                     | routine, urgent                                  |
| 7      | status           | enum          |         | Yes          | Current status of the record.                                | ordered, partially_resulted, resulted, cancelled |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                      | **Linked by (foreign key)**       |
|--------------------|-----------------|--------------------------------------------------------------------------------------------------|-----------------------------------|
| **Patient**        | **N : 1**       | One Patient has many LabOrder records; each LabOrder belongs to exactly one Patient.             | LabOrder.patient_id → Patient     |
| **Encounter**      | **N : 1**       | One Encounter creates many LabOrder records; each LabOrder may link to one Encounter (optional). | LabOrder.encounter_id → Encounter |
| **Staff**          | **N : 1**       | One Staff orders many LabOrder records; each LabOrder belongs to exactly one Staff.              | LabOrder.ordered_by → Staff       |
| **LabResult**      | **1 : N**       | One LabOrder contains many LabResult records; each LabResult belongs to exactly one LabOrder.    | LabResult.lab_order_id → LabOrder |

**Business rules**

- Status becomes resulted when all its tests have values.

## 4.17 LabResult

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Labs & Prescriptions | lab_result_id | 8 | 3 |

One test within a lab order. The row is created when the test is ordered and filled when the lab sends the result (ORU message).

**Attributes**

| **\#** | **Attribute**     | **Data type** | **Key** | **Required** | **Description**                                               | **Allowed values / constraints** |
|--------|-------------------|---------------|---------|--------------|---------------------------------------------------------------|----------------------------------|
| 1      | **lab_result_id** | int           | **PK**  | Yes          | Unique ID of each LabResult record (generated automatically). |                                  |
| 2      | *lab_order_id*    | int           | **FK**  | Yes          | Lab order this test belongs to.                               | → LabOrder.lab_order_id          |
| 3      | *lab_test_id*     | int           | **FK**  | Yes          | Which test this is, from the LabTest catalog.                 | → LabTest.lab_test_id            |
| 4      | *hl7_message_id*  | int           | **FK**  | No           | HL7 message that delivered the result.                        | → HL7Message.hl7_message_id      |
| 5      | value             | decimal       |         | No           | Result value (empty while pending).                           | Empty = pending                  |
| 6      | flag              | enum          |         | No           | Result compared with the normal range.                        | normal, low, high, critical      |
| 7      | result_time       | datetime      |         | No           | When the lab reported the result.                             |                                  |
| 8      | is_released       | bool          |         | Yes          | Whether the patient can see it in the portal.                 |                                  |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                           | **Linked by (foreign key)**           |
|--------------------|-----------------|-------------------------------------------------------------------------------------------------------|---------------------------------------|
| **LabOrder**       | **N : 1**       | One LabOrder contains many LabResult records; each LabResult belongs to exactly one LabOrder.         | LabResult.lab_order_id → LabOrder     |
| **LabTest**        | **N : 1**       | One LabTest defines many LabResult records; each LabResult belongs to exactly one LabTest.            | LabResult.lab_test_id → LabTest       |
| **HL7Message**     | **N : 1**       | One HL7Message delivers many LabResult records; each LabResult may link to one HL7Message (optional). | LabResult.hl7_message_id → HL7Message |

**Business rules**

- An empty value means the test is still pending.

- The flag is set automatically from the normal range.

- Patients see results only after the doctor releases them.

## 4.18 Prescription

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Labs & Prescriptions | prescription_id | 11 | 3 |

A medication prescribed to a patient or donor, shown in the active medication list and the patient portal.

**Attributes**

| **#** | **Attribute** | **Data type** | **Key** | **Required** | **Description** | **Allowed values / constraints** |
|---|---|---|---|---|---|---|
| 1 | **prescription_id** | int | **PK** | Yes | Unique ID of each Prescription record (generated automatically). |  |
| 2 | *patient_id* | int | **FK** | Yes | Patient (or donor) this record belongs to. | → Patient.patient_id |
| 3 | *encounter_id* | int | **FK** | No | Visit (encounter) in which this was recorded. | → Encounter.encounter_id |
| 4 | *prescribed_by* | int | **FK** | Yes | Doctor who prescribed. | → Staff.staff_id |
| 5 | drug_name | varchar **(enum)** |  | Yes | Medication name. **(national drug code)** |  |
| 6 | dose | varchar |  | Yes | Dose per intake (e.g., 3 mg). |  |
| 7 | route | enum |  | Yes | How the drug is taken. | oral, iv, im, sc, topical |
| 8 | frequency | varchar |  | Yes | How often (e.g., twice daily). |  |
| 9 | start_date | date |  | Yes | First day. |  |
| 10 | end_date | date |  | No | Last day (empty if ongoing). | After start_date |
| 11 | status | enum |  | Yes | Current status of the record. | active, stopped, completed |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                              | **Linked by (foreign key)**           |
|--------------------|-----------------|----------------------------------------------------------------------------------------------------------|---------------------------------------|
| **Patient**        | **N : 1**       | One Patient receives many Prescription records; each Prescription belongs to exactly one Patient.        | Prescription.patient_id → Patient     |
| **Encounter**      | **N : 1**       | One Encounter creates many Prescription records; each Prescription may link to one Encounter (optional). | Prescription.encounter_id → Encounter |
| **Staff**          | **N : 1**       | One Staff prescribes many Prescription records; each Prescription belongs to exactly one Staff.          | Prescription.prescribed_by → Staff    |

**Business rules**

- Only doctors can prescribe.

- end_date must be after start_date.

## 4.19 TreatmentPlan

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Labs & Prescriptions | plan_id | 9 | 2 |

The planned treatment for a patient, with goals, steps and a review date.

**Attributes**

| **\#** | **Attribute** | **Data type** | **Key** | **Required** | **Description**                                                   | **Allowed values / constraints**                                                    |
|--------|---------------|---------------|---------|--------------|-------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| 1      | **plan_id**   | int           | **PK**  | Yes          | Unique ID of each TreatmentPlan record (generated automatically). |                                                                                     |
| 2      | *patient_id*  | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                        | → Patient.patient_id                                                                |
| 3      | *created_by*  | int           | **FK**  | Yes          | Doctor who created the plan.                                      | → Staff.staff_id                                                                    |
| 4      | plan_type     | enum          |         | Yes          | Kind of treatment.                                                | surveillance, antiviral, ablation, tace, resection, transplant_referral, supportive |
| 5      | goals         | text          |         | Yes          | What the plan aims to achieve.                                    |                                                                                     |
| 6      | steps         | text          |         | No           | Planned steps.                                                    |                                                                                     |
| 7      | start_date    | date          |         | Yes          | First day.                                                        |                                                                                     |
| 8      | review_date   | date          |         | No           | When the plan should be reviewed.                                 |                                                                                     |
| 9      | status        | enum          |         | Yes          | Current status of the record.                                     | active, completed, cancelled                                                        |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                        | **Linked by (foreign key)**        |
|--------------------|-----------------|----------------------------------------------------------------------------------------------------|------------------------------------|
| **Patient**        | **N : 1**       | One Patient follows many TreatmentPlan records; each TreatmentPlan belongs to exactly one Patient. | TreatmentPlan.patient_id → Patient |
| **Staff**          | **N : 1**       | One Staff creates many TreatmentPlan records; each TreatmentPlan belongs to exactly one Staff.     | TreatmentPlan.created_by → Staff   |

**Business rules**

- A plan of type transplant_referral normally leads to a transplant case.

### Radiology & Ai Analysis

## 4.20 ImagingOrder

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Radiology & AI Analysis | imaging_order_id | 8 | 4 |

A doctor's request for a CT scan, such as a multiphase liver CT or a donor volumetry CT.

**Attributes**

| **\#** | **Attribute**        | **Data type** | **Key** | **Required** | **Description**                                                  | **Allowed values / constraints**                      |
|--------|----------------------|---------------|---------|--------------|------------------------------------------------------------------|-------------------------------------------------------|
| 1      | **imaging_order_id** | int           | **PK**  | Yes          | Unique ID of each ImagingOrder record (generated automatically). |                                                       |
| 2      | *patient_id*         | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                       | → Patient.patient_id                                  |
| 3      | *encounter_id*       | int           | **FK**  | No           | Visit (encounter) in which this was recorded.                    | → Encounter.encounter_id                              |
| 4      | *ordered_by*         | int           | **FK**  | Yes          | Doctor who ordered the scan.                                     | → Staff.staff_id                                      |
| 5      | protocol             | enum          |         | Yes          | CT protocol requested.                                           | multiphase_liver_ct, donor_volumetry_ct, follow_up_ct |
| 6      | indication           | text          |         | No           | Clinical reason for the scan.                                    |                                                       |
| 7      | status               | enum          |         | Yes          | Current status of the record.                                    | ordered, scheduled, acquired, cancelled               |
| 8      | order_date           | datetime      |         | Yes          | When the order was placed.                                       |                                                       |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                              | **Linked by (foreign key)**                  |
|--------------------|-----------------|----------------------------------------------------------------------------------------------------------|----------------------------------------------|
| **Patient**        | **N : 1**       | One Patient has many ImagingOrder records; each ImagingOrder belongs to exactly one Patient.             | ImagingOrder.patient_id → Patient            |
| **Encounter**      | **N : 1**       | One Encounter creates many ImagingOrder records; each ImagingOrder may link to one Encounter (optional). | ImagingOrder.encounter_id → Encounter        |
| **Staff**          | **N : 1**       | One Staff orders many ImagingOrder records; each ImagingOrder belongs to exactly one Staff.              | ImagingOrder.ordered_by → Staff              |
| **ImagingStudy**   | **1 : 0..1**    | One ImagingOrder is fulfilled by at most one ImagingStudy.                                               | ImagingStudy.imaging_order_id → ImagingOrder |

**Business rules**

- Status becomes acquired when the study arrives in Orthanc.

## 4.21 ImagingStudy

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Radiology & AI Analysis | study_id | 9 | 4 |

A CT study stored in Orthanc PACS. The database keeps only its IDs and metadata; the viewer and AI read the images through DICOMweb.

**Attributes**

| **\#** | **Attribute**      | **Data type** | **Key**    | **Required** | **Description**                                                  | **Allowed values / constraints**         |
|--------|--------------------|---------------|------------|--------------|------------------------------------------------------------------|------------------------------------------|
| 1      | **study_id**       | int           | **PK**     | Yes          | Unique ID of each ImagingStudy record (generated automatically). |                                          |
| 2      | *patient_id*       | int           | **FK**     | Yes          | Patient (or donor) this record belongs to.                       | → Patient.patient_id                     |
| 3      | *imaging_order_id* | int           | **FK, UQ** | No           | Order this study fulfils.                                        | → ImagingOrder.imaging_order_id · Unique |
| 4      | study_instance_uid | varchar       | **UQ**     | Yes          | DICOM Study Instance UID (unique worldwide).                     | Unique                                   |
| 5      | orthanc_id         | varchar       |            | No           | ID of the study inside Orthanc PACS.                             |                                          |
| 6      | modality           | varchar       |            | No           | Imaging modality (CT).                                           |                                          |
| 7      | study_date         | datetime      |            | Yes          | When the scan was taken.                                         |                                          |
| 8      | num_images         | int           |            | No           | Number of images in the study.                                   |                                          |
| 9      | status             | enum          |            | Yes          | Current status of the record.                                    | received, ai_pending, ai_done, reported  |

**Relationships**

| **Related entity**  | **Cardinality** | **Meaning**                                                                                                   | **Linked by (foreign key)**                  |
|---------------------|-----------------|---------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| **ImagingOrder**    | **0..1 : 1**    | One ImagingOrder is fulfilled by at most one ImagingStudy.                                                    | ImagingStudy.imaging_order_id → ImagingOrder |
| **Patient**         | **N : 1**       | One Patient has many ImagingStudy records; each ImagingStudy belongs to exactly one Patient.                  | ImagingStudy.patient_id → Patient            |
| **RadiologyReport** | **1 : 0..1**    | One ImagingStudy is reported in at most one RadiologyReport.                                                  | RadiologyReport.study_id → ImagingStudy      |
| **AIAnalysis**      | **1 : N**       | One ImagingStudy is analyzed by many AIAnalysis records; each AIAnalysis belongs to exactly one ImagingStudy. | AIAnalysis.study_id → ImagingStudy           |

**Business rules**

- study_instance_uid is unique.

- Uploading a study starts an AI analysis automatically for liver protocols.

## 4.22 RadiologyReport

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Radiology & AI Analysis | report_id | 8 | 2 |

The radiologist's written and signed report for a study, including the LI-RADS category.

**Attributes**

| **\#** | **Attribute**    | **Data type** | **Key**    | **Required** | **Description**                                                     | **Allowed values / constraints**                        |
|--------|------------------|---------------|------------|--------------|---------------------------------------------------------------------|---------------------------------------------------------|
| 1      | **report_id**    | int           | **PK**     | Yes          | Unique ID of each RadiologyReport record (generated automatically). |                                                         |
| 2      | *study_id*       | int           | **FK, UQ** | Yes          | Study being reported.                                               | → ImagingStudy.study_id · Unique (one report per study) |
| 3      | *radiologist_id* | int           | **FK**     | Yes          | Radiologist who wrote and signed the report.                        | → Staff.staff_id                                        |
| 4      | findings         | text          |            | No           | Radiologist's findings.                                             |                                                         |
| 5      | impression       | text          |            | No           | Radiologist's conclusion.                                           |                                                         |
| 6      | lirads_category  | enum          |            | No           | LI-RADS category chosen by the radiologist.                         | LR-1, LR-2, LR-3, LR-4, LR-5, LR-M, LR-TIV              |
| 7      | status           | enum          |            | Yes          | Current status of the record.                                       | draft, signed                                           |
| 8      | signed_at        | datetime      |            | No           | When it was signed.                                                 |                                                         |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                      | **Linked by (foreign key)**             |
|--------------------|-----------------|--------------------------------------------------------------------------------------------------|-----------------------------------------|
| **ImagingStudy**   | **0..1 : 1**    | One ImagingStudy is reported in at most one RadiologyReport.                                     | RadiologyReport.study_id → ImagingStudy |
| **Staff**          | **N : 1**       | One Staff signs many RadiologyReport records; each RadiologyReport belongs to exactly one Staff. | RadiologyReport.radiologist_id → Staff  |

**Business rules**

- One report per study.

- Only a radiologist can sign it, and a signed report cannot be edited.

## 4.23 AIAnalysis

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Radiology & AI Analysis | analysis_id | 12 | 5 |

One run of the AI model on a CT study. It keeps the AI's output and the radiologist's review separately.

**Attributes**

| **\#** | **Attribute**             | **Data type** | **Key** | **Required** | **Description**                                                | **Allowed values / constraints**    |
|--------|---------------------------|---------------|---------|--------------|----------------------------------------------------------------|-------------------------------------|
| 1      | **analysis_id**           | int           | **PK**  | Yes          | Unique ID of each AIAnalysis record (generated automatically). |                                     |
| 2      | *study_id*                | int           | **FK**  | Yes          | CT study that was analysed.                                    | → ImagingStudy.study_id             |
| 3      | analysis_type             | enum          |         | Yes          | Kind of AI analysis.                                           | liver_lesion, donor_volumetry       |
| 4      | model_version             | varchar       |         | Yes          | Name and version of the AI model used.                         |                                     |
| 5      | status                    | enum          |         | Yes          | Current status of the record.                                  | queued, running, completed, failed  |
| 6      | seg_series_uid            | varchar       |         | No           | UID of the DICOM SEG series the AI saved in Orthanc.           |                                     |
| 7      | ai_liver_volume_ml        | decimal       |         | No           | Liver volume measured by the AI (mL).                          |                                     |
| 8      | confirmed_liver_volume_ml | decimal       |         | No           | Liver volume after radiologist review (mL).                    |                                     |
| 9      | review_status             | enum          |         | Yes          | Result of the radiologist's review.                            | pending, accepted, edited, rejected |
| 10     | *reviewed_by*             | int           | **FK**  | No           | Radiologist who reviewed the AI result.                        | → Staff.staff_id                    |
| 11     | started_at                | datetime      |         | No           | When processing started.                                       |                                     |
| 12     | finished_at               | datetime      |         | No           | When processing finished.                                      |                                     |

**Relationships**

| **Related entity**  | **Cardinality** | **Meaning**                                                                                                   | **Linked by (foreign key)**              |
|---------------------|-----------------|---------------------------------------------------------------------------------------------------------------|------------------------------------------|
| **ImagingStudy**    | **N : 1**       | One ImagingStudy is analyzed by many AIAnalysis records; each AIAnalysis belongs to exactly one ImagingStudy. | AIAnalysis.study_id → ImagingStudy       |
| **Staff**           | **N : 1**       | One Staff reviews many AIAnalysis records; each AIAnalysis may link to one Staff (optional).                  | AIAnalysis.reviewed_by → Staff           |
| **Lesion**          | **1 : N**       | One AIAnalysis finds many Lesion records; each Lesion belongs to exactly one AIAnalysis.                      | Lesion.analysis_id → AIAnalysis          |
| **VolumetryResult** | **1 : 0..1**    | One AIAnalysis produces at most one VolumetryResult.                                                          | VolumetryResult.analysis_id → AIAnalysis |
| **CDSSAssessment**  | **1 : N**       | One AIAnalysis feeds many CDSSAssessment records; each CDSSAssessment may link to one AIAnalysis (optional).  | CDSSAssessment.analysis_id → AIAnalysis  |

**Business rules**

- Only results with review_status accepted or edited are used by the CDSS.

- The model version is stored so results can be traced.

## 4.24 Lesion

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Radiology & AI Analysis | lesion_id | 9 | 1 |

One liver lesion found by the AI, with its location and size before and after radiologist review.

**Attributes**

| **\#** | **Attribute**         | **Data type** | **Key** | **Required** | **Description**                                            | **Allowed values / constraints** |
|--------|-----------------------|---------------|---------|--------------|------------------------------------------------------------|----------------------------------|
| 1      | **lesion_id**         | int           | **PK**  | Yes          | Unique ID of each Lesion record (generated automatically). |                                  |
| 2      | *analysis_id*         | int           | **FK**  | Yes          | AI analysis that found the lesion.                         | → AIAnalysis.analysis_id         |
| 3      | lesion_no             | int           |         | Yes          | Lesion number within the analysis (1, 2, 3...).            |                                  |
| 4      | couinaud_segment      | enum          |         | No           | Liver segment (Couinaud I–VIII) where the lesion is.       | I, II, III, IV, V, VI, VII, VIII |
| 5      | ai_diameter_mm        | decimal       |         | Yes          | Longest diameter measured by the AI (mm).                  | \> 0                             |
| 6      | ai_volume_ml          | decimal       |         | No           | Lesion volume measured by the AI (mL).                     |                                  |
| 7      | confirmed_diameter_mm | decimal       |         | No           | Longest diameter after review (mm).                        |                                  |
| 8      | confirmed_volume_ml   | decimal       |         | No           | Lesion volume after review (mL).                           |                                  |
| 9      | review_status         | enum          |         | Yes          | Result of the radiologist's review.                        | accepted, edited, rejected       |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                              | **Linked by (foreign key)**     |
|--------------------|-----------------|------------------------------------------------------------------------------------------|---------------------------------|
| **AIAnalysis**     | **N : 1**       | One AIAnalysis finds many Lesion records; each Lesion belongs to exactly one AIAnalysis. | Lesion.analysis_id → AIAnalysis |

**Business rules**

- Rejected lesions are kept but not used in the Milan check.

## 4.25 VolumetryResult

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Radiology & AI Analysis | volumetry_id | 10 | 3 |

Donor liver volumes calculated from CT: total liver, planned graft and the remnant left in the donor.

**Attributes**

| **\#** | **Attribute**     | **Data type** | **Key**    | **Required** | **Description**                                                     | **Allowed values / constraints**            |
|--------|-------------------|---------------|------------|--------------|---------------------------------------------------------------------|---------------------------------------------|
| 1      | **volumetry_id**  | int           | **PK**     | Yes          | Unique ID of each VolumetryResult record (generated automatically). |                                             |
| 2      | *analysis_id*     | int           | **FK, UQ** | Yes          | AI analysis these volumes came from.                                | → AIAnalysis.analysis_id · Unique           |
| 3      | *case_donor_id*   | int           | **FK**     | Yes          | Donor (in a case) these volumes belong to.                          | → CaseDonor.case_donor_id                   |
| 4      | graft_type        | enum          |            | Yes          | Part of the liver used as the graft.                                | right_lobe, left_lobe, left_lateral_segment |
| 5      | total_volume_ml   | decimal       |            | Yes          | Total donor liver volume (mL).                                      |                                             |
| 6      | graft_volume_ml   | decimal       |            | Yes          | Planned graft volume (mL).                                          |                                             |
| 7      | remnant_volume_ml | decimal       |            | Yes          | Liver volume left in the donor (mL).                                |                                             |
| 8      | remnant_percent   | decimal       |            | No           | Remnant volume as % of total liver volume.                          | remnant_volume_ml / total_volume_ml × 100   |
| 9      | *confirmed_by*    | int           | **FK**     | No           | Radiologist or surgeon who confirmed the split.                     | → Staff.staff_id                            |
| 10     | confirmed_at      | datetime      |            | No           | When the values were confirmed.                                     |                                             |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                       | **Linked by (foreign key)**               |
|--------------------|-----------------|-------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| **AIAnalysis**     | **0..1 : 1**    | One AIAnalysis produces at most one VolumetryResult.                                                              | VolumetryResult.analysis_id → AIAnalysis  |
| **CaseDonor**      | **N : 1**       | One CaseDonor is measured in many VolumetryResult records; each VolumetryResult belongs to exactly one CaseDonor. | VolumetryResult.case_donor_id → CaseDonor |
| **Staff**          | **N : 1**       | One Staff confirms many VolumetryResult records; each VolumetryResult may link to one Staff (optional).           | VolumetryResult.confirmed_by → Staff      |

**Business rules**

- remnant_percent = remnant / total × 100.

- Values must be confirmed before the donor suitability check.

### Clinical Decision Support

## 4.26 CDSSAssessment

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Clinical Decision Support | assessment_id | 15 | 5 |

One run of the decision support rules: MELD, Milan criteria or donor suitability, the suggestion, and what the doctor decided.

**Attributes**

| **\#** | **Attribute**     | **Data type** | **Key** | **Required** | **Description**                                                    | **Allowed values / constraints**    |
|--------|-------------------|---------------|---------|--------------|--------------------------------------------------------------------|-------------------------------------|
| 1      | **assessment_id** | int           | **PK**  | Yes          | Unique ID of each CDSSAssessment record (generated automatically). |                                     |
| 2      | *patient_id*      | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                         | → Patient.patient_id                |
| 3      | *analysis_id*     | int           | **FK**  | No           | AI analysis used as input (if imaging-based).                      | → AIAnalysis.analysis_id            |
| 4      | *case_id*         | int           | **FK**  | No           | Transplant case (for donor suitability checks).                    | → TransplantCase.case_id            |
| 5      | assessment_type   | enum          |         | Yes          | Kind of CDSS assessment.                                           | liver_assessment, donor_suitability |
| 6      | meld_score        | int           |         | No           | MELD score from bilirubin, INR and creatinine.                     |                                     |
| 7      | meld_na_score     | int           |         | No           | MELD-Na score (adds sodium).                                       |                                     |
| 8      | milan_status      | enum          |         | No           | Milan criteria result from confirmed lesions.                      | within, outside, not_applicable     |
| 9      | grwr_percent      | decimal       |         | No           | Graft-to-recipient weight ratio (%).                               |                                     |
| 10     | remnant_percent   | decimal       |         | No           | Donor remnant % used in the check.                                 |                                     |
| 11     | recommendation    | text          |         | No           | Suggestion generated by the CDSS rules.                            |                                     |
| 12     | decision          | enum          |         | No           | Decision taken.                                                    | accepted, overridden                |
| 13     | decision_reason   | text          |         | No           | Reason given by the doctor, required when overriding.              | Required if overridden              |
| 14     | *decided_by*      | int           | **FK**  | No           | Doctor who accepted or overrode the suggestion.                    | → Staff.staff_id                    |
| 15     | created_at        | datetime      |         | Yes          | When the CDSS ran.                                                 |                                     |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                                  | **Linked by (foreign key)**                  |
|--------------------|-----------------|------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| **Patient**        | **N : 1**       | One Patient is assessed in many CDSSAssessment records; each CDSSAssessment belongs to exactly one Patient.                  | CDSSAssessment.patient_id → Patient          |
| **AIAnalysis**     | **N : 1**       | One AIAnalysis feeds many CDSSAssessment records; each CDSSAssessment may link to one AIAnalysis (optional).                 | CDSSAssessment.analysis_id → AIAnalysis      |
| **TransplantCase** | **N : 1**       | One TransplantCase is checked in many CDSSAssessment records; each CDSSAssessment may link to one TransplantCase (optional). | CDSSAssessment.case_id → TransplantCase      |
| **Staff**          | **N : 1**       | One Staff decides many CDSSAssessment records; each CDSSAssessment may link to one Staff (optional).                         | CDSSAssessment.decided_by → Staff            |
| **ClinicalAlert**  | **1 : N**       | One CDSSAssessment raises many ClinicalAlert records; each ClinicalAlert may link to one CDSSAssessment (optional).          | ClinicalAlert.assessment_id → CDSSAssessment |

**Business rules**

- Uses only confirmed imaging values.

- A reason is required when the doctor overrides the suggestion.

## 4.27 ClinicalAlert

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Clinical Decision Support | alert_id | 9 | 3 |

An alert raised for the care team, e.g., abnormal lab, rising AFP, criteria not met or a missing test.

**Attributes**

| **\#** | **Attribute**     | **Data type** | **Key** | **Required** | **Description**                                                   | **Allowed values / constraints**                         |
|--------|-------------------|---------------|---------|--------------|-------------------------------------------------------------------|----------------------------------------------------------|
| 1      | **alert_id**      | int           | **PK**  | Yes          | Unique ID of each ClinicalAlert record (generated automatically). |                                                          |
| 2      | *patient_id*      | int           | **FK**  | Yes          | Patient (or donor) this record belongs to.                        | → Patient.patient_id                                     |
| 3      | *assessment_id*   | int           | **FK**  | No           | Assessment that raised the alert (if any).                        | → CDSSAssessment.assessment_id                           |
| 4      | alert_type        | enum          |         | Yes          | Kind of alert.                                                    | abnormal_lab, rising_afp, criteria_not_met, missing_test |
| 5      | severity          | enum          |         | Yes          | How serious the alert is.                                         | info, warning, critical                                  |
| 6      | message           | text          |         | Yes          | Text shown to the user.                                           |                                                          |
| 7      | status            | enum          |         | Yes          | Current status of the record.                                     | open, acknowledged, resolved                             |
| 8      | *acknowledged_by* | int           | **FK**  | No           | Staff member who acknowledged it.                                 | → Staff.staff_id                                         |
| 9      | created_at        | datetime      |         | Yes          | When the record was created.                                      |                                                          |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                         | **Linked by (foreign key)**                  |
|--------------------|-----------------|---------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| **CDSSAssessment** | **N : 1**       | One CDSSAssessment raises many ClinicalAlert records; each ClinicalAlert may link to one CDSSAssessment (optional). | ClinicalAlert.assessment_id → CDSSAssessment |
| **Patient**        | **N : 1**       | One Patient has many ClinicalAlert records; each ClinicalAlert belongs to exactly one Patient.                      | ClinicalAlert.patient_id → Patient           |
| **Staff**          | **N : 1**       | One Staff acknowledges many ClinicalAlert records; each ClinicalAlert may link to one Staff (optional).             | ClinicalAlert.acknowledged_by → Staff        |

**Business rules**

- Critical alerts stay visible until acknowledged.

## 4.28 CDSSThreshold

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Clinical Decision Support | threshold_id | 6 | 1 |

Settings for the CDSS rules (minimum GRWR, minimum remnant %, donor age and BMI limits) that the admin can change without code changes.

**Attributes**

| **\#** | **Attribute**    | **Data type** | **Key** | **Required** | **Description**                                                   | **Allowed values / constraints**                                                          |
|--------|------------------|---------------|---------|--------------|-------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| 1      | **threshold_id** | int           | **PK**  | Yes          | Unique ID of each CDSSThreshold record (generated automatically). |                                                                                           |
| 2      | rule_name        | varchar       | **UQ**  | Yes          | Name of the rule the threshold belongs to.                        | Unique, e.g. min_grwr (0.8), min_remnant_pct (30), max_donor_age (55), max_donor_bmi (30) |
| 3      | value            | decimal       |         | Yes          | Threshold value used by the rule.                                 |                                                                                           |
| 4      | unit             | varchar       |         | No           | Unit of measurement.                                              |                                                                                           |
| 5      | *updated_by*     | int           | **FK**  | Yes          | Admin who last changed the value.                                 | → Staff.staff_id                                                                          |
| 6      | updated_at       | datetime      |         | Yes          | When the value was last changed.                                  |                                                                                           |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                    | **Linked by (foreign key)**      |
|--------------------|-----------------|------------------------------------------------------------------------------------------------|----------------------------------|
| **Staff**          | **N : 1**       | One Staff updates many CDSSThreshold records; each CDSSThreshold belongs to exactly one Staff. | CDSSThreshold.updated_by → Staff |

**Business rules**

- Each rule has exactly one current value.

- Only admins can change thresholds; each change is audited.

### Transplant & Follow-Up

## 4.29 TransplantCase

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | case_id | 8 | 11 |

The transplant process for one recipient, from referral through evaluation, committee, surgery and follow-up. It is the link between the recipient and their donor(s).

**Attributes**

| **\#** | **Attribute**           | **Data type** | **Key** | **Required** | **Description**                                                    | **Allowed values / constraints**                                                                                     |
|--------|-------------------------|---------------|---------|--------------|--------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| 1      | **case_id**             | int           | **PK**  | Yes          | Unique ID of each TransplantCase record (generated automatically). |                                                                                                                      |
| 2      | *recipient_id*          | int           | **FK**  | Yes          | Patient who needs the transplant.                                  | → Patient.patient_id                                                                                                 |
| 3      | *referral_encounter_id* | int           | **FK**  | No           | Visit in which the referral was made.                              | → Encounter.encounter_id                                                                                             |
| 4      | *referred_by*           | int           | **FK**  | Yes          | Hepatologist who referred the patient.                             | → Staff.staff_id                                                                                                     |
| 5      | *coordinator_id*        | int           | **FK**  | No           | Coordinator managing the case.                                     | → Staff.staff_id                                                                                                     |
| 6      | status                  | enum          |         | Yes          | Current status of the record.                                      | referred, under_evaluation, committee_review, approved, rejected, surgery_scheduled, transplanted, follow_up, closed |
| 7      | referral_date           | date          |         | Yes          | Date the patient was referred for transplant.                      |                                                                                                                      |
| 8      | closed_at               | datetime      |         | No           | When the case was closed.                                          |                                                                                                                      |

**Relationships**

| **Related entity**    | **Cardinality** | **Meaning**                                                                                                                        | **Linked by (foreign key)**                      |
|-----------------------|-----------------|------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| **Appointment**       | **1 : N**       | One TransplantCase includes evaluation visit many Appointment records; each Appointment may link to one TransplantCase (optional). | Appointment.case_id → TransplantCase             |
| **CDSSAssessment**    | **1 : N**       | One TransplantCase is checked in many CDSSAssessment records; each CDSSAssessment may link to one TransplantCase (optional).       | CDSSAssessment.case_id → TransplantCase          |
| **Patient**           | **N : 1**       | One Patient is recipient in many TransplantCase records; each TransplantCase belongs to exactly one Patient.                       | TransplantCase.recipient_id → Patient            |
| **Encounter**         | **N : 1**       | One Encounter refers to many TransplantCase records; each TransplantCase may link to one Encounter (optional).                     | TransplantCase.referral_encounter_id → Encounter |
| **Staff**             | **N : 1**       | One Staff refers many TransplantCase records; each TransplantCase belongs to exactly one Staff.                                    | TransplantCase.referred_by → Staff               |
| **Staff**             | **N : 1**       | One Staff coordinates many TransplantCase records; each TransplantCase may link to one Staff (optional).                           | TransplantCase.coordinator_id → Staff            |
| **CaseDonor**         | **1 : N**       | One TransplantCase has candidate many CaseDonor records; each CaseDonor belongs to exactly one TransplantCase.                     | CaseDonor.case_id → TransplantCase               |
| **ChecklistItem**     | **1 : N**       | One TransplantCase requires many ChecklistItem records; each ChecklistItem belongs to exactly one TransplantCase.                  | ChecklistItem.case_id → TransplantCase           |
| **CommitteeDecision** | **1 : N**       | One TransplantCase is decided in many CommitteeDecision records; each CommitteeDecision belongs to exactly one TransplantCase.     | CommitteeDecision.case_id → TransplantCase       |
| **Surgery**           | **1 : N**       | One TransplantCase leads to many Surgery records; each Surgery belongs to exactly one TransplantCase.                              | Surgery.case_id → TransplantCase                 |
| **FollowUpPlan**      | **1 : N**       | One TransplantCase has many FollowUpPlan records; each FollowUpPlan belongs to exactly one TransplantCase.                         | FollowUpPlan.case_id → TransplantCase            |

**Business rules**

- A recipient has at most one open case at a time.

- Status moves in order: referred → under_evaluation → committee_review → approved/rejected → surgery_scheduled → transplanted → follow_up.

## 4.30 CaseDonor

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | case_donor_id | 7 | 5 |

Links a candidate donor to a transplant case and tracks that donor's progress. A case can have several candidate donors.

**Attributes**

| **\#** | **Attribute**     | **Data type** | **Key**    | **Required** | **Description**                                                       | **Allowed values / constraints**                               |
|--------|-------------------|---------------|------------|--------------|-----------------------------------------------------------------------|----------------------------------------------------------------|
| 1      | **case_donor_id** | int           | **PK**     | Yes          | Unique ID of each CaseDonor record (generated automatically).         |                                                                |
| 2      | *case_id*         | int           | **FK**     | Yes          | Transplant case.                                                      | → TransplantCase.case_id                                       |
| 3      | *donor_id*        | int           | **FK**     | Yes          | Candidate donor.                                                      | → Patient.patient_id                                           |
| 4      | *application_id*  | int           | **FK, UQ** | No           | Donor application this came from.                                     | → DonorApplication.application_id · Unique                     |
| 5      | abo_compatible    | bool          |            | No           | Whether donor and recipient blood groups are compatible (calculated). |                                                                |
| 6      | status            | enum          |            | Yes          | Current status of the record.                                         | candidate, under_evaluation, approved, not_suitable, withdrawn |
| 7      | added_at          | datetime      |            | Yes          | When the donor was added to the case.                                 |                                                                |

**Relationships**

| **Related entity**   | **Cardinality** | **Meaning**                                                                                                       | **Linked by (foreign key)**                 |
|----------------------|-----------------|-------------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| **VolumetryResult**  | **1 : N**       | One CaseDonor is measured in many VolumetryResult records; each VolumetryResult belongs to exactly one CaseDonor. | VolumetryResult.case_donor_id → CaseDonor   |
| **TransplantCase**   | **N : 1**       | One TransplantCase has candidate many CaseDonor records; each CaseDonor belongs to exactly one TransplantCase.    | CaseDonor.case_id → TransplantCase          |
| **Patient**          | **N : 1**       | One Patient is donor in many CaseDonor records; each CaseDonor belongs to exactly one Patient.                    | CaseDonor.donor_id → Patient                |
| **DonorApplication** | **0..1 : 1**    | One DonorApplication becomes at most one CaseDonor.                                                               | CaseDonor.application_id → DonorApplication |
| **Surgery**          | **1 : 0..1**    | One CaseDonor donates in at most one Surgery.                                                                     | Surgery.case_donor_id → CaseDonor           |

**Business rules**

- abo_compatible is calculated from both blood groups.

- Only one donor per case can be approved for surgery.

## 4.31 ChecklistItem

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | item_id | 8 | 2 |

A test, visit or document that the recipient or a donor must complete before the case goes to committee.

**Attributes**

| **\#** | **Attribute** | **Data type** | **Key** | **Required** | **Description**                                                   | **Allowed values / constraints**          |
|--------|---------------|---------------|---------|--------------|-------------------------------------------------------------------|-------------------------------------------|
| 1      | **item_id**   | int           | **PK**  | Yes          | Unique ID of each ChecklistItem record (generated automatically). |                                           |
| 2      | *case_id*     | int           | **FK**  | Yes          | Transplant case.                                                  | → TransplantCase.case_id                  |
| 3      | *patient_id*  | int           | **FK**  | Yes          | Recipient or donor who must complete the item.                    | → Patient.patient_id                      |
| 4      | item_name     | varchar       |         | Yes          | Name of the required item (e.g., CT volumetry, viral serology).   |                                           |
| 5      | item_type     | enum          |         | Yes          | Kind of item.                                                     | lab_test, imaging, consultation, document |
| 6      | is_required   | bool          |         | Yes          | Whether the item must be done before committee review.            |                                           |
| 7      | status        | enum          |         | Yes          | Current status of the record.                                     | pending, done, waived                     |
| 8      | completed_at  | datetime      |         | No           | When the item was completed.                                      |                                           |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                       | **Linked by (foreign key)**            |
|--------------------|-----------------|-------------------------------------------------------------------------------------------------------------------|----------------------------------------|
| **TransplantCase** | **N : 1**       | One TransplantCase requires many ChecklistItem records; each ChecklistItem belongs to exactly one TransplantCase. | ChecklistItem.case_id → TransplantCase |
| **Patient**        | **N : 1**       | One Patient must complete many ChecklistItem records; each ChecklistItem belongs to exactly one Patient.          | ChecklistItem.patient_id → Patient     |

**Business rules**

- A case can move to committee_review only when all required items are done or waived.

## 4.32 CommitteeDecision

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | decision_id | 7 | 3 |

The transplant team's decision on a case, recorded by the hepatologist.

**Attributes**

| **\#** | **Attribute**   | **Data type** | **Key** | **Required** | **Description**                                                       | **Allowed values / constraints**      |
|--------|-----------------|---------------|---------|--------------|-----------------------------------------------------------------------|---------------------------------------|
| 1      | **decision_id** | int           | **PK**  | Yes          | Unique ID of each CommitteeDecision record (generated automatically). |                                       |
| 2      | *case_id*       | int           | **FK**  | Yes          | Case being decided.                                                   | → TransplantCase.case_id              |
| 3      | *recorded_by*   | int           | **FK**  | Yes          | Hepatologist who recorded the decision.                               | → Staff.staff_id                      |
| 4      | meeting_date    | date          |         | Yes          | Date of the committee meeting.                                        |                                       |
| 5      | decision        | enum          |         | No           | Decision taken.                                                       | approved, rejected, more_tests_needed |
| 6      | reasons         | text          |         | Yes          | Reasons for the decision.                                             |                                       |
| 7      | extra_tests     | text          |         | No           | Extra tests the committee asked for.                                  |                                       |

**Relationships**

| **Related entity**  | **Cardinality** | **Meaning**                                                                                                                    | **Linked by (foreign key)**                     |
|---------------------|-----------------|--------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|
| **TransplantCase**  | **N : 1**       | One TransplantCase is decided in many CommitteeDecision records; each CommitteeDecision belongs to exactly one TransplantCase. | CommitteeDecision.case_id → TransplantCase      |
| **Staff**           | **N : 1**       | One Staff records many CommitteeDecision records; each CommitteeDecision belongs to exactly one Staff.                         | CommitteeDecision.recorded_by → Staff           |
| **CommitteeMember** | **1 : N**       | One CommitteeDecision includes many CommitteeMember records; each CommitteeMember belongs to exactly one CommitteeDecision.    | CommitteeMember.decision_id → CommitteeDecision |

**Business rules**

- A decision of more_tests_needed sends the case back to evaluation.

## 4.33 CommitteeMember

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | decision_id + staff_id | 3 | 2 |

A link table listing which staff took part in a committee decision (many-to-many between CommitteeDecision and Staff).

**Attributes**

| **\#** | **Attribute**   | **Data type** | **Key**    | **Required** | **Description**             | **Allowed values / constraints** |
|--------|-----------------|---------------|------------|--------------|-----------------------------|----------------------------------|
| 1      | **decision_id** | int           | **PK, FK** | Yes          | Committee decision.         | → CommitteeDecision.decision_id  |
| 2      | **staff_id**    | int           | **PK, FK** | Yes          | Staff member who took part. | → Staff.staff_id                 |
| 3      | vote            | enum          |            | No           | This member's vote.         | approve, reject, abstain         |

**Relationships**

| **Related entity**    | **Cardinality** | **Meaning**                                                                                                                 | **Linked by (foreign key)**                     |
|-----------------------|-----------------|-----------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|
| **CommitteeDecision** | **N : 1**       | One CommitteeDecision includes many CommitteeMember records; each CommitteeMember belongs to exactly one CommitteeDecision. | CommitteeMember.decision_id → CommitteeDecision |
| **Staff**             | **N : 1**       | One Staff takes part as many CommitteeMember records; each CommitteeMember belongs to exactly one Staff.                    | CommitteeMember.staff_id → Staff                |

**Business rules**

- The pair (decision_id, staff_id) is unique.

## 4.34 Surgery

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | surgery_id | 12 | 4 |

The transplant operation: when and where it is scheduled, who leads it, the graft details and the outcome.

**Attributes**

| **\#** | **Attribute**     | **Data type** | **Key** | **Required** | **Description**                                             | **Allowed values / constraints**             |
|--------|-------------------|---------------|---------|--------------|-------------------------------------------------------------|----------------------------------------------|
| 1      | **surgery_id**    | int           | **PK**  | Yes          | Unique ID of each Surgery record (generated automatically). |                                              |
| 2      | *case_id*         | int           | **FK**  | Yes          | Transplant case.                                            | → TransplantCase.case_id                     |
| 3      | *case_donor_id*   | int           | **FK**  | Yes          | Donor who gave the graft.                                   | → CaseDonor.case_donor_id                    |
| 4      | *lead_surgeon_id* | int           | **FK**  | Yes          | Lead transplant surgeon.                                    | → Staff.staff_id                             |
| 5      | scheduled_at      | datetime      |         | Yes          | Planned date and time of surgery.                           |                                              |
| 6      | operating_room    | varchar       |         | No           | Operating room.                                             |                                              |
| 7      | status            | enum          |         | Yes          | Current status of the record.                               | scheduled, in_progress, completed, cancelled |
| 8      | graft_type        | enum          |         | No           | Part of the liver used as the graft.                        | right_lobe, left_lobe, left_lateral_segment  |
| 9      | graft_weight_g    | decimal       |         | No           | Actual graft weight in grams.                               |                                              |
| 10     | duration_min      | int           |         | No           | Length of the operation in minutes.                         |                                              |
| 11     | operative_notes   | text          |         | No           | Surgeon's operative notes.                                  |                                              |
| 12     | complications     | text          |         | No           | Complications, if any.                                      |                                              |

**Relationships**

| **Related entity**    | **Cardinality** | **Meaning**                                                                                            | **Linked by (foreign key)**            |
|-----------------------|-----------------|--------------------------------------------------------------------------------------------------------|----------------------------------------|
| **TransplantCase**    | **N : 1**       | One TransplantCase leads to many Surgery records; each Surgery belongs to exactly one TransplantCase.  | Surgery.case_id → TransplantCase       |
| **CaseDonor**         | **0..1 : 1**    | One CaseDonor donates in at most one Surgery.                                                          | Surgery.case_donor_id → CaseDonor      |
| **Staff**             | **N : 1**       | One Staff leads many Surgery records; each Surgery belongs to exactly one Staff.                       | Surgery.lead_surgeon_id → Staff        |
| **SurgeryTeamMember** | **1 : N**       | One Surgery has many SurgeryTeamMember records; each SurgeryTeamMember belongs to exactly one Surgery. | SurgeryTeamMember.surgery_id → Surgery |

**Business rules**

- The donor must be approved and consent signed before scheduling.

- Completing a surgery creates follow-up plans for the recipient and the donor.

## 4.35 SurgeryTeamMember

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | surgery_id + staff_id | 3 | 2 |

A link table listing the staff on a surgical team and their roles (many-to-many between Surgery and Staff).

**Attributes**

| **\#** | **Attribute**  | **Data type** | **Key**    | **Required** | **Description**                                                    | **Allowed values / constraints** |
|--------|----------------|---------------|------------|--------------|--------------------------------------------------------------------|----------------------------------|
| 1      | **surgery_id** | int           | **PK, FK** | Yes          | Surgery.                                                           | → Surgery.surgery_id             |
| 2      | **staff_id**   | int           | **PK, FK** | Yes          | Staff member on the team.                                          | → Staff.staff_id                 |
| 3      | team_role      | varchar       |            | Yes          | Role in the operation (e.g., assistant surgeon, anesthesiologist). |                                  |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                              | **Linked by (foreign key)**            |
|--------------------|-----------------|----------------------------------------------------------------------------------------------------------|----------------------------------------|
| **Surgery**        | **N : 1**       | One Surgery has many SurgeryTeamMember records; each SurgeryTeamMember belongs to exactly one Surgery.   | SurgeryTeamMember.surgery_id → Surgery |
| **Staff**          | **N : 1**       | One Staff serves as many SurgeryTeamMember records; each SurgeryTeamMember belongs to exactly one Staff. | SurgeryTeamMember.staff_id → Staff     |

**Business rules**

- The pair (surgery_id, staff_id) is unique.

## 4.36 FollowUpPlan

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | followup_plan_id | 6 | 3 |

The follow-up schedule after surgery. Each case gets one plan for the recipient and one for the donor.

**Attributes**

| **\#** | **Attribute**        | **Data type** | **Key** | **Required** | **Description**                                                  | **Allowed values / constraints** |
|--------|----------------------|---------------|---------|--------------|------------------------------------------------------------------|----------------------------------|
| 1      | **followup_plan_id** | int           | **PK**  | Yes          | Unique ID of each FollowUpPlan record (generated automatically). |                                  |
| 2      | *case_id*            | int           | **FK**  | Yes          | Transplant case.                                                 | → TransplantCase.case_id         |
| 3      | *patient_id*         | int           | **FK**  | Yes          | Recipient or donor being followed up.                            | → Patient.patient_id             |
| 4      | patient_role         | enum          |         | Yes          | Whether this plan is for the recipient or a donor.               | recipient, donor                 |
| 5      | start_date           | date          |         | Yes          | First day.                                                       |                                  |
| 6      | status               | enum          |         | Yes          | Current status of the record.                                    | active, completed                |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                    | **Linked by (foreign key)**                   |
|--------------------|-----------------|----------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| **TransplantCase** | **N : 1**       | One TransplantCase has many FollowUpPlan records; each FollowUpPlan belongs to exactly one TransplantCase.     | FollowUpPlan.case_id → TransplantCase         |
| **Patient**        | **N : 1**       | One Patient follows many FollowUpPlan records; each FollowUpPlan belongs to exactly one Patient.               | FollowUpPlan.patient_id → Patient             |
| **FollowUpVisit**  | **1 : N**       | One FollowUpPlan schedules many FollowUpVisit records; each FollowUpVisit belongs to exactly one FollowUpPlan. | FollowUpVisit.followup_plan_id → FollowUpPlan |

**Business rules**

- Created automatically when a surgery is completed.

## 4.37 FollowUpVisit

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Transplant & Follow-up | visit_id | 9 | 2 |

One follow-up visit and its recovery findings, such as immunosuppressant level for recipients or liver regrowth for donors.

**Attributes**

| **\#** | **Attribute**      | **Data type** | **Key**    | **Required** | **Description**                                                   | **Allowed values / constraints**      |
|--------|--------------------|---------------|------------|--------------|-------------------------------------------------------------------|---------------------------------------|
| 1      | **visit_id**       | int           | **PK**     | Yes          | Unique ID of each FollowUpVisit record (generated automatically). |                                       |
| 2      | *followup_plan_id* | int           | **FK**     | Yes          | Plan this visit belongs to.                                       | → FollowUpPlan.followup_plan_id       |
| 3      | *appointment_id*   | int           | **FK, UQ** | No           | Appointment booked for this visit.                                | → Appointment.appointment_id · Unique |
| 4      | due_date           | date          |            | Yes          | Date the visit or payment is due.                                 |                                       |
| 5      | immuno_level       | decimal       |            | No           | Immunosuppressant blood level (ng/mL), recipients only.           |                                       |
| 6      | rejection_episode  | bool          |            | No           | Whether signs of graft rejection were found.                      |                                       |
| 7      | complications      | text          |            | No           | Complications, if any.                                            |                                       |
| 8      | liver_regrowth_ml  | decimal       |            | No           | Liver volume on follow-up CT (mL), donors only.                   |                                       |
| 9      | notes              | text          |            | No           | Free-text notes.                                                  |                                       |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                    | **Linked by (foreign key)**                   |
|--------------------|-----------------|----------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| **FollowUpPlan**   | **N : 1**       | One FollowUpPlan schedules many FollowUpVisit records; each FollowUpVisit belongs to exactly one FollowUpPlan. | FollowUpVisit.followup_plan_id → FollowUpPlan |
| **Appointment**    | **0..1 : 1**    | One Appointment is booked for at most one FollowUpVisit.                                                       | FollowUpVisit.appointment_id → Appointment    |

**Business rules**

- Each visit is booked as an appointment.

### Billing & Payments

## 4.38 Service

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Billing & Payments | service_id | 6 | 1 |

The catalog of billable services and their prices.

**Attributes**

| **\#** | **Attribute**  | **Data type** | **Key** | **Required** | **Description**                                                       | **Allowed values / constraints**                                     |
|--------|----------------|---------------|---------|--------------|-----------------------------------------------------------------------|----------------------------------------------------------------------|
| 1      | **service_id** | int           | **PK**  | Yes          | Unique ID of each Service record (generated automatically).           |                                                                      |
| 2      | code           | varchar       | **UQ**  | Yes          | Service code.                                                         | Unique                                                               |
| 3      | name           | varchar       |         | Yes          | Display name.                                                         |                                                                      |
| 4      | category       | enum          |         | Yes          | Service group.                                                        | consultation, imaging, lab, ai_analysis, evaluation_package, surgery |
| 5      | price          | decimal       |         | Yes          | Price in EGP.                                                         | ≥ 0                                                                  |
| 6      | is_active      | bool          |         | Yes          | Whether this record is active (inactive records are kept but hidden). |                                                                      |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                         | **Linked by (foreign key)**      |
|--------------------|-----------------|-----------------------------------------------------------------------------------------------------|----------------------------------|
| **InvoiceItem**    | **1 : N**       | One Service is billed as many InvoiceItem records; each InvoiceItem belongs to exactly one Service. | InvoiceItem.service_id → Service |

**Business rules**

- Price changes do not affect invoices already issued.

## 4.39 Invoice

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Billing & Payments | invoice_id | 8 | 4 |

A bill issued to a patient or donor for services received.

**Attributes**

| **\#** | **Attribute**  | **Data type** | **Key** | **Required** | **Description**                                                | **Allowed values / constraints**        |
|--------|----------------|---------------|---------|--------------|----------------------------------------------------------------|-----------------------------------------|
| 1      | **invoice_id** | int           | **PK**  | Yes          | Unique ID of each Invoice record (generated automatically).    |                                         |
| 2      | invoice_no     | varchar       | **UQ**  | Yes          | Printed invoice number.                                        | Unique                                  |
| 3      | *patient_id*   | int           | **FK**  | Yes          | Person billed.                                                 | → Patient.patient_id                    |
| 4      | *issued_by*    | int           | **FK**  | No           | Staff member who issued it (empty if generated automatically). | → Staff.staff_id                        |
| 5      | issue_date     | date          |         | Yes          | Date the invoice was issued.                                   |                                         |
| 6      | due_date       | date          |         | Yes          | Date the visit or payment is due.                              |                                         |
| 7      | total_amount   | decimal       |         | Yes          | Invoice total in EGP.                                          | Sum of its line totals                  |
| 8      | status         | enum          |         | Yes          | Current status of the record.                                  | unpaid, partially_paid, paid, cancelled |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                     | **Linked by (foreign key)**      |
|--------------------|-----------------|-------------------------------------------------------------------------------------------------|----------------------------------|
| **Patient**        | **N : 1**       | One Patient is billed in many Invoice records; each Invoice belongs to exactly one Patient.     | Invoice.patient_id → Patient     |
| **Staff**          | **N : 1**       | One Staff issues many Invoice records; each Invoice may link to one Staff (optional).           | Invoice.issued_by → Staff        |
| **InvoiceItem**    | **1 : N**       | One Invoice contains many InvoiceItem records; each InvoiceItem belongs to exactly one Invoice. | InvoiceItem.invoice_id → Invoice |
| **Payment**        | **1 : N**       | One Invoice is paid by many Payment records; each Payment belongs to exactly one Invoice.       | Payment.invoice_id → Invoice     |

**Business rules**

- total_amount equals the sum of its items.

- Status becomes paid when payments cover the total.

## 4.40 InvoiceItem

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Billing & Payments | invoice_item_id | 7 | 3 |

One line on an invoice: which service, how many, and at what price.

**Attributes**

| **\#** | **Attribute**       | **Data type** | **Key** | **Required** | **Description**                                                 | **Allowed values / constraints** |
|--------|---------------------|---------------|---------|--------------|-----------------------------------------------------------------|----------------------------------|
| 1      | **invoice_item_id** | int           | **PK**  | Yes          | Unique ID of each InvoiceItem record (generated automatically). |                                  |
| 2      | *invoice_id*        | int           | **FK**  | Yes          | Invoice.                                                        | → Invoice.invoice_id             |
| 3      | *service_id*        | int           | **FK**  | Yes          | Service billed.                                                 | → Service.service_id             |
| 4      | *appointment_id*    | int           | **FK**  | No           | Visit the charge came from (if any).                            | → Appointment.appointment_id     |
| 5      | quantity            | int           |         | Yes          | Number of units.                                                | ≥ 1                              |
| 6      | unit_price          | decimal       |         | Yes          | Price per unit at billing time (EGP).                           |                                  |
| 7      | line_total          | decimal       |         | Yes          | quantity × unit_price.                                          | quantity × unit_price            |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                      | **Linked by (foreign key)**              |
|--------------------|-----------------|------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| **Invoice**        | **N : 1**       | One Invoice contains many InvoiceItem records; each InvoiceItem belongs to exactly one Invoice.                  | InvoiceItem.invoice_id → Invoice         |
| **Service**        | **N : 1**       | One Service is billed as many InvoiceItem records; each InvoiceItem belongs to exactly one Service.              | InvoiceItem.service_id → Service         |
| **Appointment**    | **N : 1**       | One Appointment is charged in many InvoiceItem records; each InvoiceItem may link to one Appointment (optional). | InvoiceItem.appointment_id → Appointment |

**Business rules**

- unit_price is copied from the service at billing time.

## 4.41 Payment

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Billing & Payments | payment_id | 9 | 2 |

A payment against an invoice, made online through the gateway or at the desk.

**Attributes**

| **\#** | **Attribute**  | **Data type** | **Key** | **Required** | **Description**                                             | **Allowed values / constraints**     |
|--------|----------------|---------------|---------|--------------|-------------------------------------------------------------|--------------------------------------|
| 1      | **payment_id** | int           | **PK**  | Yes          | Unique ID of each Payment record (generated automatically). |                                      |
| 2      | *invoice_id*   | int           | **FK**  | Yes          | Invoice being paid.                                         | → Invoice.invoice_id                 |
| 3      | *received_by*  | int           | **FK**  | No           | Billing staff who took a desk payment (empty for online).   | → Staff.staff_id                     |
| 4      | amount         | decimal       |         | Yes          | Amount paid (EGP).                                          | \> 0                                 |
| 5      | method         | enum          |         | Yes          | How it was paid.                                            | online, cash, card                   |
| 6      | gateway_txn_id | varchar       |         | No           | Transaction ID from the payment gateway (online payments).  |                                      |
| 7      | receipt_no     | varchar       | **UQ**  | Yes          | Receipt number.                                             | Unique                               |
| 8      | status         | enum          |         | Yes          | Current status of the record.                               | pending, succeeded, failed, refunded |
| 9      | paid_at        | datetime      |         | Yes          | When the payment was made.                                  |                                      |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                               | **Linked by (foreign key)**  |
|--------------------|-----------------|-------------------------------------------------------------------------------------------|------------------------------|
| **Invoice**        | **N : 1**       | One Invoice is paid by many Payment records; each Payment belongs to exactly one Invoice. | Payment.invoice_id → Invoice |
| **Staff**          | **N : 1**       | One Staff receives many Payment records; each Payment may link to one Staff (optional).   | Payment.received_by → Staff  |

**Business rules**

- The sum of successful payments cannot exceed the invoice total.

| **NOTIFICATIONS & HL7** |
|-------------------------|

## 4.42 Notification

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Notifications & HL7 | notification_id | 8 | 1 |

A message sent to a user in the app or by email (reminders, results ready, case updates).

**Attributes**

| **\#** | **Attribute**       | **Data type** | **Key** | **Required** | **Description**                                                  | **Allowed values / constraints**                                                  |
|--------|---------------------|---------------|---------|--------------|------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| 1      | **notification_id** | int           | **PK**  | Yes          | Unique ID of each Notification record (generated automatically). |                                                                                   |
| 2      | *user_id*           | int           | **FK**  | Yes          | User who receives the notification.                              | → User.user_id                                                                    |
| 3      | type                | enum          |         | Yes          | Kind of notification.                                            | appointment_reminder, result_ready, case_update, pending_task, follow_up_reminder |
| 4      | title               | varchar       |         | No           | Short title shown in lists.                                      |                                                                                   |
| 5      | message             | text          |         | Yes          | Text shown to the user.                                          |                                                                                   |
| 6      | channel             | enum          |         | Yes          | How it was delivered.                                            | in_app, email                                                                     |
| 7      | is_read             | bool          |         | Yes          | Whether the user has opened it.                                  |                                                                                   |
| 8      | sent_at             | datetime      |         | Yes          | When it was sent.                                                |                                                                                   |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                 | **Linked by (foreign key)** |
|--------------------|-----------------|---------------------------------------------------------------------------------------------|-----------------------------|
| **User**           | **N : 1**       | One User receives many Notification records; each Notification belongs to exactly one User. | Notification.user_id → User |

**Business rules**

- Appointment reminders are sent automatically before each visit.

## 4.43 ExternalSystem

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Notifications & HL7 | system_id | 6 | 1 |

An outside system that exchanges HL7 messages with LiverLink, such as the external lab client application.

**Attributes**

| **\#** | **Attribute** | **Data type** | **Key** | **Required** | **Description**                                                       | **Allowed values / constraints**   |
|--------|---------------|---------------|---------|--------------|-----------------------------------------------------------------------|------------------------------------|
| 1      | **system_id** | int           | **PK**  | Yes          | Unique ID of each ExternalSystem record (generated automatically).    |                                    |
| 2      | name          | varchar       |         | Yes          | Name of the external system.                                          |                                    |
| 3      | system_type   | enum          |         | Yes          | Kind of external system.                                              | external_lab, clinic, hospital_his |
| 4      | host          | varchar       |         | Yes          | Server address of the external system.                                |                                    |
| 5      | port          | int           |         | Yes          | Network port used for HL7 (MLLP).                                     |                                    |
| 6      | is_active     | bool          |         | Yes          | Whether this record is active (inactive records are kept but hidden). |                                    |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                  | **Linked by (foreign key)**           |
|--------------------|-----------------|--------------------------------------------------------------------------------------------------------------|---------------------------------------|
| **HL7Message**     | **1 : N**       | One ExternalSystem exchanges many HL7Message records; each HL7Message belongs to exactly one ExternalSystem. | HL7Message.system_id → ExternalSystem |

**Business rules**

- Messages from inactive systems are rejected.

## 4.44 HL7Message

| **Module** | **Primary Key** | **Attributes** | **Relationships** |
|---|---|---|---|
| Notifications & HL7 | hl7_message_id | 11 | 3 |

A log of every HL7 v2 message sent or received, with its acknowledgement and any error.

**Attributes**

| **\#** | **Attribute**      | **Data type** | **Key** | **Required** | **Description**                                                | **Allowed values / constraints**                              |
|--------|--------------------|---------------|---------|--------------|----------------------------------------------------------------|---------------------------------------------------------------|
| 1      | **hl7_message_id** | int           | **PK**  | Yes          | Unique ID of each HL7Message record (generated automatically). |                                                               |
| 2      | *system_id*        | int           | **FK**  | Yes          | External system on the other side.                             | → ExternalSystem.system_id                                    |
| 3      | *patient_id*       | int           | **FK**  | No           | Patient the message is about (if matched).                     | → Patient.patient_id                                          |
| 4      | direction          | enum          |         | Yes          | Whether the message was received or sent.                      | inbound, outbound                                             |
| 5      | message_type       | varchar       |         | Yes          | HL7 message type and trigger event.                            | ADT^A04, ADT^A08, SIU^S12, SIU^S13, SIU^S15, ORM^O01, ORU^R01 |
| 6      | control_id         | varchar       |         | Yes          | HL7 message control ID (MSH-10).                               |                                                               |
| 7      | raw_message        | text          |         | Yes          | Full HL7 message text.                                         |                                                               |
| 8      | ack_code           | enum          |         | No           | Acknowledgement code returned.                                 | AA (accepted), AE (error), AR (rejected)                      |
| 9      | status             | enum          |         | Yes          | Current status of the record.                                  | received, processed, sent, error                              |
| 10     | error_text         | text          |         | No           | Error details if processing failed.                            |                                                               |
| 11     | created_at         | datetime      |         | Yes          | When the message was sent or received.                         |                                                               |

**Relationships**

| **Related entity** | **Cardinality** | **Meaning**                                                                                                  | **Linked by (foreign key)**           |
|--------------------|-----------------|--------------------------------------------------------------------------------------------------------------|---------------------------------------|
| **LabResult**      | **1 : N**       | One HL7Message delivers many LabResult records; each LabResult may link to one HL7Message (optional).        | LabResult.hl7_message_id → HL7Message |
| **ExternalSystem** | **N : 1**       | One ExternalSystem exchanges many HL7Message records; each HL7Message belongs to exactly one ExternalSystem. | HL7Message.system_id → ExternalSystem |
| **Patient**        | **N : 1**       | One Patient is subject of many HL7Message records; each HL7Message may link to one Patient (optional).       | HL7Message.patient_id → Patient       |

**Business rules**

- Every inbound message gets an ACK (AA, AE or AR).

- Messages are kept for troubleshooting and audit.
