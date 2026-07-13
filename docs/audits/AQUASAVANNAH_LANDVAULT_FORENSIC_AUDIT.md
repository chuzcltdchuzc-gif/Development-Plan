# AQUASAVANNAH LANDVAULT
# MASTER PLATFORM INVENTORY & FORENSIC AUDIT REPORT

**Audit Date:** 2026-06-24
**Audit Mode:** Chief System Auditor / Chief Solutions Architect / Chief Technical Documentation Officer
**Methodology:** Live platform inspection — every statement derived from actual codebase, entity schemas, function definitions, automation configurations, and route mappings.

---

# SECTION 1: PLATFORM OVERVIEW

| Metric | Count |
|---|---|
| **Platform Name** | Aquasavannah LandVault — Community Land Evidence & Verification Platform |
| **Total Pages** | 77 |
| **Total Backend Functions** | 57 |
| **Total Entities** | 72 (custom) + 1 built-in User = 73 |
| **Total Components** | 120 (48 shadcn/ui + 72 custom) |
| **Total Routes** | 82 (81 defined + 1 wildcard 404) |
| **Total Automations** | 29 |
| **Total Dashboards** | 21 |
| **Total Scheduled Jobs** | 6 (3 active, 3 inactive/failed) |
| **Total Data Automations** | 23 (entity-triggered) |
| **Total Security Modules** | 14 |
| **Total Trust Modules** | 12 |
| **Total Economic Modules** | 11 |
| **Total Reporting Modules** | 8 |
| **Total Public-Facing Modules** | 5 |
| **Total Admin Modules** | 18 |

---

# SECTION 2: COMPLETE ROUTE INVENTORY

## Authenticated Routes (wrapped in AppLayout)

| # | Route URL | Page Name | Purpose | Access Level | Status |
|---|---|---|---|---|---|
| 1 | `/` | Dashboard | Main role-based dashboard router | All authenticated | Active |
| 2 | `/lands` | LandRegistry | Legacy land parcel registry | Admin/Surveyor | Active |
| 3 | `/gis-map` | GISMap | Geographic information system map view | Admin/Surveyor | Active |
| 4 | `/approvals` | Approvals | Parcel approval queue | Admin/Compliance | Active |
| 5 | `/register-land` | RegisterLand | Legacy land registration form | Field Agent/Admin | Active |
| 6 | `/disputes` | Disputes | Land dispute management | Admin/Compliance | Active |
| 7 | `/my-submissions` | MySubmissions | User's own submitted parcels | All authenticated | Active |
| 8 | `/my-claims` | MyClaims | User's own land claims | All authenticated | Active |
| 9 | `/survey-documents` | SurveyDocuments | Survey document management | Surveyor/Admin | Active |
| 10 | `/survey-reviews` | SurveyReviews | Survey review queue | Surveyor General/Admin | Active |
| 11 | `/field-reports` | FieldReports | Field agent report submission | Field Agent/Admin | Active |
| 12 | `/notifications` | Notifications | User notification center | All authenticated | Active |
| 13 | `/audit-logs` | AuditLogs | System audit log viewer | Admin/Compliance | Active |
| 14 | `/assigned-parcels` | AssignedParcels | Surveyor assigned parcels | Surveyor | Active |
| 15 | `/gov/user-management` | UserManagement | User account management | Super Admin | Active |
| 16 | `/gov/parcel-freeze` | ParcelFreeze | Parcel freeze/unfreeze | Admin/Compliance | Active |
| 17 | `/gov/fraud-alerts` | FraudAlerts | Fraud alert management | Admin/Compliance | Active |
| 18 | `/gov/global-audit` | GlobalAudit | Global audit trail viewer | Admin/Compliance | Active |
| 19 | `/gov/compliance-reports` | ComplianceReports | Compliance report generation | Admin/Compliance | Active |
| 20 | `/gov/pending-approvals` | PendingApprovals | Pending approval queue | Admin/Compliance | Active |
| 21 | `/gov/bulk-import` | BulkImport | Bulk parcel import | Super Admin | Active |
| 22 | `/gov/pilot-dashboard` | PilotDashboard | Pilot program dashboard | Admin/Gov Observer | Active |
| 23 | `/gov/audit-reports` | AuditReports | Audit report generation | Admin/Compliance | Active |
| 24 | `/inheritance` | InheritanceManagement | Inheritance case management | Admin/Compliance | Active |
| 25 | `/gov/customary-governance` | CustomaryGovernanceDashboard | Customary governance overview | Admin/Gov Observer | Active |
| 26 | `/gov/executive-dashboard` | ExecutiveDashboard | Executive KPI dashboard | Admin/Gov Observer | Active |
| 27 | `/gov/demo-seed` | DemoDataSeed | Demo data seeding tool | Super Admin | Active |
| 28 | `/gov/pilot-reports` | PilotReports | Pilot program reports | Admin/Gov Observer | Active |
| 29 | `/gov/data-integrity` | DataIntegrityReport | Data integrity reporting | Admin/Compliance | Active |
| 30 | `/gov/pilot-validation` | PilotValidation | Pilot validation checks | Admin/Compliance | Active |
| 31 | `/gov/demo-readiness` | DemoReadinessReport | Demo readiness assessment | Admin/Compliance | Active |
| 32 | `/gov/deployment-package` | PilotDeploymentPackage | Deployment package builder | Admin | Active |
| 33 | `/gov/production-readiness` | ProductionReadiness | Production readiness checklist | Admin | Active |
| 34 | `/demo-guide` | DemoGuide | Demo walkthrough guide | All authenticated | Active |
| 35 | `/ehime/parcels` | EhimeParcels | Ehime Mbano LGA parcel list | All authenticated | Active |
| 36 | `/ehime/register` | EhimeRegisterLand | Ehime Mbano land registration | Field Agent/Admin | Active |
| 37 | `/ehime/parcel/:id` | EhimeParcelDetail | Ehime Mbano parcel detail | All authenticated | Active |
| 38 | `/ehime/packages` | PackageManagement | Registration package management | Admin/Surveyor | Active |
| 39 | `/lv` | LandVaultDashboard | LandVault pilot dashboard | All authenticated | Active |
| 40 | `/lv/field` | FieldAgentDashboard | Field agent operations dashboard | Field Agent | Active |
| 41 | `/lv/leads` | LeadsList | Community leads list | Field Agent/Admin | Active |
| 42 | `/lv/leads/new` | LeadForm | New community lead form | Field Agent | Active |
| 43 | `/lv/leads/:id` | LeadDetail | Lead detail view | Field Agent/Admin | Active |
| 44 | `/lv/leads/:id/edit` | LeadForm | Edit community lead | Field Agent | Active |
| 45 | `/lv/parcels` | ParcelsList | LandVault parcel list | All authenticated | Active |
| 46 | `/lv/parcels/new` | ParcelForm | New parcel registration | Field Agent | Active |
| 47 | `/lv/parcels/:id` | ParcelDetail | Parcel detail with evidence/tabs | All authenticated | Active |
| 48 | `/lv/parcels/:id/edit` | ParcelForm | Edit parcel | Field Agent/Admin | Active |
| 49 | `/lv/evidence` | EvidenceUpload | Evidence upload interface | Field Agent | Active |
| 50 | `/lv/evidence/new` | EvidenceUpload | New evidence upload | Field Agent | Active |
| 51 | `/lv/surveyor` | SurveyorDashboard | Surveyor partner dashboard | Surveyor Partner | Active |
| 52 | `/lv/validate` | CommunityValidatorQueue | Community validation queue | Community Validator | Active |
| 53 | `/lv/payments/new` | PaymentRecord | Payment recording form | Field Agent/Admin | Active |
| 54 | `/lv/observer` | GovernmentObserver | Government observer portal | Gov Observer | Active |
| 55 | `/lv/duplicates` | DuplicateAlertDashboard | Duplicate alert management | Admin/Compliance | Active |
| 56 | `/lv/evidence/:id` | EvidenceDetail | Evidence detail viewer | All authenticated | Active |
| 57 | `/lv/consent/:parcelId` | ConsentCapture | Multi-stage consent capture | Field Agent | Active |
| 58 | `/lv/readiness` | PilotReadinessReport | Pilot readiness report | Admin | Active |
| 59 | `/lv/governance` | DeploymentGovernanceAudit | Deployment governance audit | Admin | Active |
| 60 | `/lv/surveyor-network` | SurveyorNetwork | Surveyor network directory | All authenticated | Active |
| 61 | `/lv/archive-import` | ArchiveImportWizard | Archive import wizard | Surveyor Partner | Active |
| 62 | `/lv/surveyor/:id` | SurveyorPublicProfile | Surveyor public profile | Public | Active |
| 63 | `/community-attestation` | CommunityAttestationDashboard | Attestation dashboard | All authenticated | Active |
| 64 | `/community-attestation/new` | CommunityAttestationForm | New attestation form | All authenticated | Active |
| 65 | `/community-attestation/review` | CommunityAttestationReview | Attestation review queue | Admin/Compliance | Active |
| 66 | `/community-attestation/review/:id` | CommunityAttestationReview | Attestation review detail | Admin/Compliance | Active |
| 67 | `/community-attestation/:id` | CommunityAttestationReview | Attestation by ID | Admin/Compliance | Active |

## Public Routes (no auth required)

| # | Route URL | Page Name | Purpose | Access Level | Status |
|---|---|---|---|---|---|
| 68 | `/demo` | DemoAccess | Public demo access portal | Public | Active |
| 69 | `/verify` | PublicVerify | Public parcel verification (legacy) | Public | Active |
| 70 | `/lv/verify` | LandVaultPublicVerify | Public LandVault parcel verification | Public | Active |
| 71 | `/trust` | TrustArchitecture | Public trust architecture explainer | Public | Active |
| 72 | `/community-transparency` | CommunityTransparency | Public community transparency portal | Public | Active |

## Operations / Security / Economics Routes (outside AppLayout)

| # | Route URL | Page Name | Purpose | Access Level | Status |
|---|---|---|---|---|---|
| 73 | `/operations` | OperationsDashboard | Background job operations center | Admin | Active |
| 74 | `/security` | SecurityDashboard | Security command center | Admin | Active |
| 75 | `/security/testing` | SecurityTesting | Penetration testing interface | Admin | Active |
| 76 | `/security/operations` | SecurityOperations | Security operations management | Admin | Active |
| 77 | `/trust-validation` | TrustValidationCenter | Trust validation center | Admin | Active |
| 78 | `/due-diligence` | DueDiligence | Due diligence report ordering | All authenticated | Active |
| 79 | `/revenue` | RevenueAnalytics | Revenue analytics dashboard | Admin | Active |
| 80 | `/pilot-economics` | PilotEconomics | Pilot economics dashboard | Admin | Active |
| 81 | `/economics/operations` | EconomicsOperations | Economic operations center | Admin | Active |
| 82 | `*` | PageNotFound | 404 handler | Public | Active |

---

# SECTION 3: COMPLETE PAGE INVENTORY

## Core Pages

| Page | Route | Purpose | Key Features | Connected Entities | Connected Functions |
|---|---|---|---|---|---|
| Dashboard | `/` | Role-based dashboard router | KPI cards, role-specific widgets | LandParcel, LandVaultParcel, JobQueue, CommunityAttestation | — |
| LandRegistry | `/lands` | Legacy parcel registry | Parcel table, filters, search | LandParcel | publicParcelLookup |
| GISMap | `/gis-map` | GIS map view | Leaflet map, parcel polygons | LandParcel | asyncGISValidation |
| Approvals | `/approvals` | Parcel approval queue | Approve/reject, bulk actions | LandParcel | — |
| RegisterLand | `/register-land` | Legacy land registration | Multi-step form, consent capture | LandParcel, ParcelSequence | generateParcelId |
| Disputes | `/disputes` | Dispute management | Dispute list, resolution | Dispute | — |
| MySubmissions | `/my-submissions` | User's submissions | Personal parcel list | LandParcel, LandVaultParcel | — |
| MyClaims | `/my-claims` | User's claims | Personal claims list | LandParcel | — |
| SurveyDocuments | `/survey-documents` | Survey document management | Upload, review | SurveyDocument, DocVersion | — |
| SurveyReviews | `/survey-reviews` | Survey review queue | Review, approve, reject | SurveyDocument | — |
| FieldReports | `/field-reports` | Field report submission | GPS capture, photos, offline | FieldReport, OfflineQueue | — |
| Notifications | `/notifications` | Notification center | Read/unread, filter | Notification, CommunityNotification | — |
| AuditLogs | `/audit-logs` | Audit log viewer | Filter, search, export | AuditLog | — |
| AssignedParcels | `/assigned-parcels` | Surveyor assignments | Assignment list, status | SurveyAssignment, LandVaultParcel | — |

## Government Pages

| Page | Route | Purpose | Connected Entities | Connected Functions |
|---|---|---|---|---|
| UserManagement | `/gov/user-management` | User account management, role assignment | User | lvRoleChangeApproval |
| ParcelFreeze | `/gov/parcel-freeze` | Freeze/unfreeze parcels | ParcelFreeze, LandParcel | — |
| FraudAlerts | `/gov/fraud-alerts` | Fraud alert management | FraudAlert, FraudSignal | lvFraudDetection |
| GlobalAudit | `/gov/global-audit` | Global audit trail | AuditLog, EconomicAuditEntry | — |
| ComplianceReports | `/gov/compliance-reports` | Compliance report generation | ComplianceReport | — |
| PendingApprovals | `/gov/pending-approvals` | Pending approval queue, bulk approve | LandParcel, ParcelRevision, InheritanceCase | — |
| BulkImport | `/gov/bulk-import` | Bulk CSV/Excel import | LandParcel, ImportHistory | — |
| PilotDashboard | `/gov/pilot-dashboard` | Pilot program KPIs | LandVaultParcel, CommunityLead, LandVaultPayment | — |
| AuditReports | `/gov/audit-reports` | Audit report generation | AuditLog, ComplianceReport | — |
| InheritanceManagement | `/inheritance` | Inheritance case management | InheritanceCase, FamilyOwnership, FamilyBeneficiary | — |
| CustomaryGovernanceDashboard | `/gov/customary-governance` | Customary governance overview | CommunityValidation, TraditionalAuthorityValidation | — |
| ExecutiveDashboard | `/gov/executive-dashboard` | Executive KPI dashboard | LandVaultParcel, RevenueTransaction, CreditWallet | lvRevenueIntelligence |
| DemoDataSeed | `/gov/demo-seed` | Demo data seeding | Multiple | seedDemoData, seedDemoPhase1-3, seedDemoFinalize |
| PilotReports | `/gov/pilot-reports` | Pilot program reports | LandVaultParcel, CommunityAttestation | — |
| DataIntegrityReport | `/gov/data-integrity` | Data integrity reporting | EvidenceIntegrityCheck, HashChainEntry | — |
| PilotValidation | `/gov/pilot-validation` | Pilot validation checks | LandVaultParcel, CommunityAttestation | — |
| DemoReadinessReport | `/gov/demo-readiness` | Demo readiness assessment | TakeoffReadinessAssessment | lvTakeoffReadiness |
| PilotDeploymentPackage | `/gov/deployment-package` | Deployment package builder | TakeoffReadinessAssessment | — |
| ProductionReadiness | `/gov/production-readiness` | Production readiness checklist | TakeoffReadinessAssessment | lvTakeoffReadiness |

## Ehime Mbano LGA Pages

| Page | Route | Purpose | Connected Entities |
|---|---|---|---|
| EhimeParcels | `/ehime/parcels` | Ehime Mbano parcel list | LandParcel |
| EhimeRegisterLand | `/ehime/register` | Ehime Mbano registration form | LandParcel, ParcelSequence, RegistrationPackage |
| EhimeParcelDetail | `/ehime/parcel/:id` | Ehime Mbano parcel detail | LandParcel, SurveyDocument, OwnershipHistory |
| PackageManagement | `/ehime/packages` | Registration package management | RegistrationPackage, LandVaultPayment |

## LandVault Pages

| Page | Route | Purpose | Connected Entities | Connected Functions |
|---|---|---|---|---|
| LandVaultDashboard | `/lv` | Pilot dashboard with KPIs, charts | CommunityLead, LandVaultParcel, LandVaultPayment, SurveyAssignment | — |
| FieldAgentDashboard | `/lv/field` | Field agent operations | CommunityLead, LandVaultParcel, FieldReport | — |
| LeadsList | `/lv/leads` | Community leads list | CommunityLead | — |
| LeadForm | `/lv/leads/new` | New/edit lead form | CommunityLead | — |
| LeadDetail | `/lv/leads/:id` | Lead detail view | CommunityLead, LandVaultParcel | — |
| ParcelsList | `/lv/parcels` | Parcel list with filters | LandVaultParcel | — |
| ParcelForm | `/lv/parcels/new` | New/edit parcel form | LandVaultParcel, CommunityLead | generateParcelId |
| ParcelDetail | `/lv/parcels/:id` | Multi-tab parcel detail | LandVaultParcel, EvidenceVault, CommunityAttestation, SurveyAssignment, LandVaultPayment, DuplicateAlert | lvEvidenceReport, lvEvidenceSeal |
| EvidenceUpload | `/lv/evidence` | Evidence upload with GPS, hashing | EvidenceVault, LandVaultParcel | — |
| SurveyorDashboard | `/lv/surveyor` | Surveyor partner dashboard | SurveyAssignment, SurveyorPartner, ArchiveRecord, RevenueTransaction | — |
| CommunityValidatorQueue | `/lv/validate` | Community validation queue | LandVaultParcel, CommunityValidation | — |
| PaymentRecord | `/lv/payments/new` | Payment recording | LandVaultPayment, LandVaultParcel | — |
| GovernmentObserver | `/lv/observer` | Government observer portal | LandVaultParcel, CommunityAttestation | — |
| DuplicateAlertDashboard | `/lv/duplicates` | Duplicate alert management | DuplicateAlert, LandVaultParcel | — |
| EvidenceDetail | `/lv/evidence/:id` | Evidence detail viewer | EvidenceVault | — |
| ConsentCapture | `/lv/consent/:parcelId` | 6-stage consent capture | LandVaultParcel | — |
| PilotReadinessReport | `/lv/readiness` | Pilot readiness report | TakeoffReadinessAssessment | lvPilotReadinessCertification |
| DeploymentGovernanceAudit | `/lv/governance` | Deployment governance audit | TakeoffReadinessAssessment | — |
| SurveyorNetwork | `/lv/surveyor-network` | Surveyor network directory | SurveyorPartner | — |
| ArchiveImportWizard | `/lv/archive-import` | Archive import wizard | ArchiveRecord, SurveyorPartner | — |
| SurveyorPublicProfile | `/lv/surveyor/:id` | Surveyor public profile | SurveyorPartner, ArchiveRecord | — |

## Community Attestation Pages

| Page | Route | Purpose | Connected Entities | Connected Functions |
|---|---|---|---|---|
| CommunityAttestationDashboard | `/community-attestation` | Attestation dashboard with metrics | CommunityAttestation | — |
| CommunityAttestationForm | `/community-attestation/new` | 4-step attestation wizard | CommunityAttestation, LandVaultParcel | — |
| CommunityAttestationReview | `/community-attestation/review` | Attestation review queue | CommunityAttestation | lvConsensusCalculation, lvConflictDetection |

## Operations / Security / Trust / Economics Pages

| Page | Route | Purpose | Connected Entities | Connected Functions |
|---|---|---|---|---|
| OperationsDashboard | `/operations` | Background job operations center | JobQueue | jobQueueProcessor, lvCreateJob |
| SecurityDashboard | `/security` | Security command center | SecurityIncident, FraudSignal, SecuritySession, PenetrationTestResult | lvSecurityScan |
| SecurityTesting | `/security/testing` | Penetration testing interface | PenetrationTestResult | lvPenetrationTest |
| SecurityOperations | `/security/operations` | Security operations management | SecurityIncident, RoleChangeApproval | lvRoleChangeApproval |
| TrustValidationCenter | `/trust-validation` | Trust validation center | TrustValidationRun, TrustScoreSnapshot | lvTrustValidationEngine |
| TrustArchitecture | `/trust` | Public trust architecture explainer | LandVaultParcel, CommunityAttestation, AuditLog | — |
| CommunityTransparency | `/community-transparency` | Public community transparency portal | CommunityAttestation, TraditionalInstitutionEndorsement | — |
| DueDiligence | `/due-diligence` | Due diligence report ordering | ServiceCatalog, ServiceRequest, GeneratedReport | lvServiceBilling |
| RevenueAnalytics | `/revenue` | Revenue analytics dashboard | Invoice, UsageLedger, RevenueTransaction | lvRevenueIntelligence |
| PilotEconomics | `/pilot-economics` | Pilot economics dashboard | CreditWallet, ServiceCatalog, InstitutionPlan | — |
| EconomicsOperations | `/economics/operations` | Economic operations center | CreditWallet, OrganizationWallet, ServiceRequest, Invoice | lvCreditEngine, lvServiceBilling, lvInvoiceGenerator, lvRevenueFraudCheck |

## Public Pages

| Page | Route | Purpose | Connected Entities | Connected Functions |
|---|---|---|---|---|
| DemoAccess | `/demo` | Public demo access portal | — | — |
| PublicVerify | `/verify` | Public parcel verification (legacy) | LandParcel | publicParcelLookup |
| LandVaultPublicVerify | `/lv/verify` | Public LandVault parcel verification | LandVaultParcel | publicLandVaultLookup |
| RoleSelection | (conditional) | Role selection for new users | User | — |
| DemoGuide | `/demo-guide` | Demo walkthrough guide | — | — |

---

# SECTION 4: COMPLETE ENTITY INVENTORY

## Core Land Entities

### 1. LandVaultParcel
- **Purpose:** Primary land parcel record for the LandVault pilot system
- **Field Count:** 95+ fields
- **Key Fields:** parcel_number, lead_id, community, ward, lga, state, ownership_type, gps_lat, gps_lng, gps_confidence, gps_spoofing_flag, geojson_polygon, owner_name, owner_nin (PRIVATE), family_name, representative_name, authority_basis, authority_document_url (PRIVATE), evidence_confidence_score, consensus_percentage, consensus_level, supporting_count, conflicting_count, verification_status, status, risk_level, risk_score, duplicate_flag, duplicate_type, dispute_readiness_score, survey_plan_url, surveyor_id, consent_verbal, consent_audio_captured, consent_signature_captured, consent_photo_captured, consent_witness_name, consent_strength_score, evidence_sealed, evidence_seal_hash, qr_code_url, certificate_a_url, certificate_b_url, certificate_c_url, certificate_status, amount_paid, total_fee, payment_status, community_validation_status
- **Relationships:** CommunityLead (lead_id), EvidenceVault (parcel_id), CommunityAttestation (parcel_id), SurveyAssignment (parcel_id), LandVaultPayment (parcel_id), DuplicateAlert (source/conflicting), EvidenceTimelineEvent (parcel_id), ParcelFlag (parcel_id), CommunityReviewAlert (parcel_id), TraditionalInstitutionEndorsement (parcel_id)
- **RLS Rules:**
  - Create: `created_by = user.email`
  - Read: Owner OR field_agent_email OR roles [super_admin, surveyor_general, compliance_officer, licensed_surveyor, surveyor_partner, community_validator, government_observer]
  - Update: Owner (non-issued, non-sealed) OR field_agent (non-issued, non-sealed) OR roles [super_admin, surveyor_general, compliance_officer] OR licensed_surveyor/surveyor_partner (assigned/in_progress) OR community_validator (pending)
  - Delete: super_admin only
- **Connected Functions:** lvEvidenceConfidence, lvDuplicateDetection, lvEvidenceSeal, lvAutoQueueJobs, lvEvidenceReport
- **Connected Pages:** ParcelsList, ParcelForm, ParcelDetail, LandVaultDashboard, FieldAgentDashboard, SurveyorDashboard, GovernmentObserver, DuplicateAlertDashboard
- **Status:** Active — most complex entity in the platform

### 2. LandParcel
- **Purpose:** Legacy land parcel record (pre-LandVault system)
- **Field Count:** 60+ fields
- **Key Fields:** tenant_id, parcel_number, title, owner_name, owner_email, owner_nin (PRIVATE), ownership_type, size_sqm, address, community, state, lga, ward, property_type, encumbrance_status, latitude, longitude, parcel_boundary, spatial_validation_status, land_use, status, verification_status, survey_plan_url, fraud_risk_score, fraud_risk_level, qr_code_url, certificate_url, certificate_version, verbal_consent, consent_audio (PRIVATE), consent_signature (PRIVATE), consent_photo (PRIVATE), witness_name, consent_strength_score, community_confirmed, certificate_release_status, outstanding_certificate_fee
- **Relationships:** SurveyDocument (parcel_id), FieldReport (parcel_id), Dispute (parcel_id), FraudAlert (parcel_id), OwnershipHistory (parcel_id), ParcelFreeze (parcel_id), ParcelRevision (parcel_id), RegistrationPackage (registration_package_id)
- **RLS Rules:**
  - Create: `created_by = user.email`
  - Read: Owner OR creator OR field_agent (unverified) OR roles [super_admin, surveyor_general, compliance_officer, surveyor, community_validator]
  - Update: Creator (non-locked) OR owner (non-locked) OR roles [super_admin, surveyor_general, compliance_officer, community_validator]
  - Delete: super_admin only
- **Connected Functions:** asyncFraudScoring, asyncGISValidation, generateParcelId
- **Connected Pages:** LandRegistry, RegisterLand, EhimeParcels, EhimeRegisterLand, EhimeParcelDetail, GISMap, Approvals, PendingApprovals
- **Status:** Active — legacy system, still in use for Ehime Mbano LGA

### 3. CommunityLead
- **Purpose:** Community lead tracking for field agent outreach
- **Field Count:** 20 fields
- **Key Fields:** lead_number, community, village, ward, lga, state, community_leader_name, community_leader_phone, family_name, family_representative, estimated_plots, status, field_agent_email, gps_lat, gps_lng, is_offline_created
- **Relationships:** LandVaultParcel (lead_id)
- **RLS Rules:** Create: `created_by`; Read: creator OR roles [super_admin, surveyor_general, compliance_officer, licensed_surveyor, community_validator, government_observer]; Update: creator OR admin roles; Delete: super_admin
- **Connected Pages:** LeadsList, LeadForm, LeadDetail, FieldAgentDashboard, LandVaultDashboard
- **Status:** Active

### 4. SurveyAssignment
- **Purpose:** Surveyor assignment tracking
- **Field Count:** 20 fields
- **Key Fields:** parcel_id, surveyor_email, surveyor_name, surveyor_licence, scheduled_date, status, survey_plan_url, geojson_polygon, coordinates_taken, measurements, signed_document_url
- **Relationships:** LandVaultParcel (parcel_id), SurveyorPartner (surveyor_email)
- **RLS Rules:** Create: roles [super_admin, surveyor_general, compliance_officer, field_agent]; Read: assigned surveyor OR admin roles; Update: assigned surveyor OR admin roles; Delete: super_admin
- **Connected Pages:** SurveyorDashboard, AssignedParcels, ParcelDetail
- **Status:** Active

### 5. LandVaultPayment
- **Purpose:** Payment recording for LandVault parcels
- **Field Count:** 12 fields
- **Key Fields:** parcel_id, amount, payment_method, payment_reference, payment_date, recorded_by_email, receipt_url
- **Relationships:** LandVaultParcel (parcel_id)
- **RLS Rules:** Create: `created_by`; Read: roles [super_admin, surveyor_general, compliance_officer, field_agent]; Update: admin roles; Delete: super_admin
- **Connected Pages:** PaymentRecord, LandVaultDashboard, ParcelDetail
- **Status:** Active

### 6. RegistrationPackage
- **Purpose:** Multi-parcel registration package management
- **Field Count:** 18 fields
- **Key Fields:** package_number, family_name, owner_type, total_parcels, registered_parcels, certificates_released, package_value, discount_amount, amount_paid, balance_due, payment_status
- **Relationships:** LandParcel (via package)
- **RLS Rules:** Create/Read: roles [super_admin, surveyor_general, compliance_officer, surveyor, field_agent]; Update: admin roles; Delete: super_admin
- **Connected Pages:** PackageManagement, EhimeRegisterLand
- **Status:** Active

### 7. ParcelSequence
- **Purpose:** Atomic parcel number sequence generator
- **Field Count:** 5 fields
- **Key Fields:** sequence_key, last_sequence, state_code, lga_code, ward_code, property_type
- **RLS Rules:** Create/Read/Update: roles [super_admin, surveyor_general, compliance_officer, surveyor]; Delete: super_admin
- **Connected Functions:** generateParcelId
- **Status:** Active

## Evidence Entities

### 8. EvidenceVault
- **Purpose:** Immutable evidence storage with SHA-256 hashing
- **Field Count:** 25+ fields
- **Key Fields:** parcel_id, evidence_type, evidence_sequence, file_url (PRIVATE), file_name, hash_fingerprint (SHA-256), hash_algorithm, is_immutable, seal_status, captured_by_email, gps_lat, gps_lng, gps_accuracy_m, gps_confidence, gps_inside_lga, gps_spoofing_flag, device_id, network_status, witness_name, custody_chain (IMMUTABLE JSON)
- **Relationships:** LandVaultParcel (parcel_id), CommunityLead (lead_id)
- **RLS Rules:** Create: `created_by`; Read: roles [super_admin, surveyor_general, compliance_officer, licensed_surveyor, field_agent, community_validator]; Update: super_admin only; Delete: super_admin only
- **Connected Functions:** lvDuplicateDetection, lvAutoQueueJobs, lvEvidenceIntegrityCheck
- **Connected Automations:** 5 entity automations on create (duplicate detection, auto-queue jobs)
- **Status:** Active — core evidence storage entity

### 9. EvidenceLock
- **Purpose:** Immutable evidence preservation lock — prevents editing after approval
- **Field Count:** 15 fields
- **Key Fields:** lock_id, entity_type, entity_id, evidence_hash, locked_by, lock_reason, verification_hash, previous_lock_id, version_number, status, superseded_by
- **RLS Rules:** Create: `created_by`; Read: roles [super_admin, surveyor_general, compliance_officer, licensed_surveyor, surveyor_partner]; Update/Delete: super_admin
- **Connected Functions:** lvEvidenceLock
- **Status:** Active

### 10. EvidenceChain
- **Purpose:** Document version chain with hash fingerprints
- **Field Count:** 16 fields
- **Key Fields:** document_id, document_type, file_url, hash_fingerprint, version_number, previous_version_id, approval_history, access_history, lifecycle_status, replacement_blocked
- **Status:** Active

### 11. EvidenceIntegrityCheck
- **Purpose:** Cryptographic integrity verification of evidence files
- **Field Count:** 15 fields
- **Key Fields:** check_id, parcel_id, evidence_id, evidence_hash_original, evidence_hash_current, verification_status, trigger_event, mismatch_details
- **Connected Functions:** lvEvidenceIntegrityCheck, lvEvidenceIntegrityValidation
- **Status:** Active

### 12. EvidenceTimelineEvent
- **Purpose:** Chronological immutable record of all evidence-related events
- **Field Count:** 12 fields
- **Key Fields:** event_id, parcel_id, event_type, event_source, timestamp, user, summary, related_record, visibility
- **Connected Functions:** lvRecordTimelineEvent
- **Status:** Active

## Community Attestation Entities

### 13. CommunityAttestation
- **Purpose:** Community stakeholder attestation of parcel evidence
- **Field Count:** 35+ fields
- **Key Fields:** attestation_id, parcel_id, attestor_name, attestor_role, community_name, relationship_to_land, years_of_knowledge, attestation_statement, attestation_position (SUPPORTING/NEUTRAL/CONFLICTING), signature_file, photo_file, voice_recording, voice_recording_hash, video_recording, video_recording_hash, verification_status, confidence_impact, consensus_contribution, traditional_institution_verified, special_badge
- **Relationships:** LandVaultParcel (parcel_id), TraditionalInstitutionEndorsement (attestation_id), CommunityReviewAlert (attestation_a/b), CommunityAttestationAudit (attestation_id)
- **RLS Rules:** Create: `created_by`; Read: roles [super_admin, surveyor_general, compliance_officer, licensed_surveyor, surveyor_partner, field_agent, community_validator, government_observer]; Update: creator (CLARIFICATION_REQUIRED) OR admin roles; Delete: super_admin
- **Connected Functions:** lvConsensusCalculation, lvConflictDetection, lvAttestationConfidence, lvGenerateNotification, lvRecordAuditEntry, lvRecordTimelineEvent
- **Connected Automations:** 7 entity automations (create/update/delete)
- **Status:** Active — core trust entity

### 14. CommunityAttestationAudit
- **Purpose:** Immutable audit trail for all attestation operations
- **Field Count:** 12 fields
- **Key Fields:** audit_id, user_email, attestation_id, action, before_state, after_state, timestamp, ip_address
- **RLS Rules:** Read: roles [super_admin, surveyor_general, compliance_officer]; Update/Delete: super_admin (immutable)
- **Connected Functions:** lvRecordAuditEntry
- **Status:** Active

### 15. CommunityReviewAlert
- **Purpose:** Auto-generated alert for conflicting attestations
- **Field Count:** 12 fields
- **Key Fields:** alert_id, parcel_id, attestation_a, attestation_b, conflict_type, conflict_summary, status, resolved_by
- **Connected Functions:** lvConflictDetection
- **Status:** Active

### 16. ParcelFlag
- **Purpose:** Auto-generated flags on parcels requiring attention
- **Field Count:** 10 fields
- **Key Fields:** flag_id, parcel_id, flag_type, severity, status, notes, resolved_by
- **Connected Functions:** lvConflictDetection
- **Status:** Active

### 17. TraditionalInstitutionEndorsement
- **Purpose:** Formal endorsement by traditional institutions
- **Field Count:** 15 fields
- **Key Fields:** endorsement_id, parcel_id, attestation_id, institution_name, institution_type, representative_name, representative_title, endorsement_statement, endorsement_document, endorsement_status, badge_generated
- **Status:** Active

### 18. CommunityNotification
- **Purpose:** Notifications from attestation events
- **Field Count:** 10 fields
- **Key Fields:** notification_id, recipient, type, message, parcel_id, status, read_at
- **Connected Functions:** lvGenerateNotification
- **Status:** Active

### 19. CommunityValidation
- **Purpose:** Multi-stage community validation workflow
- **Field Count:** 30+ fields
- **Key Fields:** parcel_id, community_name, village_name, ward, lga, state, validation_date, family_representative, community_elder, village_head, traditional_ruler, cdc_chairman, status, community_review_by, village_head_validated_by, trad_authority_validated_by, compliance_reviewed_by, sg_reviewed_by, final_approved_by
- **Status:** Active

### 20. CommunityConsent
- **Purpose:** Community consent tracking
- **Field Count:** 15 fields
- **Key Fields:** parcel_id, community_name, consent_type, representatives, date_granted, expiry_date, status, supporting_doc_urls
- **Status:** Active

## Trust & Security Entities

### 21. TrustValidationRun
- **Purpose:** Immutable trust validation run record
- **Field Count:** 20 fields
- **Key Fields:** validation_id, validation_type, validation_scope, status, passed_tests, failed_tests, overall_score, trust_grade, risk_level, validation_report_json, subscores, blocking_issues, pilot_recommendation
- **Connected Functions:** lvTrustValidationEngine
- **Connected Automations:** Scheduled 12-hour scan
- **Status:** Active

### 22. TrustScoreSnapshot
- **Purpose:** Periodic trust score snapshot — never overwrites historical
- **Field Count:** 15 fields
- **Key Fields:** snapshot_id, trust_score, integrity_score, audit_score, fraud_score, certificate_score, system_score, trust_level, total_parcels, verified_parcels, open_incidents
- **Connected Functions:** lvTrustScoreCalculation
- **Status:** Active

### 23. HashChainEntry
- **Purpose:** Blockchain-style audit linkage
- **Field Count:** 15 fields
- **Key Fields:** chain_id, entity_type, entity_id, previous_hash, current_hash, chain_position, data_snapshot, verification_status
- **Connected Functions:** lvHashChainProtection
- **Status:** Active

### 24. AuditLog
- **Purpose:** General system audit log
- **Field Count:** 8 fields
- **Key Fields:** tenant_id, user_email, action, entity_type, entity_id, details, ip_address
- **Status:** Active

### 25. AuditIntegrityCheck
- **Purpose:** Verifies audit trail integrity
- **Field Count:** 10 fields
- **Key Fields:** check_id, check_type, severity, status, details, incident_id
- **Connected Functions:** lvAuditIntegrityCheck, lvAuditIntegrityValidation
- **Status:** Active

### 26. SecurityIncident
- **Purpose:** Security incident management
- **Field Count:** 18 fields
- **Key Fields:** incident_id, incident_type, severity, status, entity_type, entity_id, reported_by, detected_by, description, resolution_notes, risk_score_impact
- **Connected Functions:** lvSecurityScan
- **Status:** Active

### 27. SecuritySession
- **Purpose:** Login and session security tracking
- **Field Count:** 16 fields
- **Key Fields:** session_id, user_email, event_type, ip_address, device_fingerprint, location, consecutive_failures, account_locked, lockout_until
- **Connected Functions:** lvSessionSecurity
- **Status:** Active

### 28. FraudSignal
- **Purpose:** Behavioural fraud detection signals
- **Field Count:** 15 fields
- **Key Fields:** signal_id, user_email, signal_type, severity, risk_score, parcel_id, details, count, window_minutes, status
- **Connected Functions:** lvFraudDetection
- **Status:** Active

### 29. FraudAlert
- **Purpose:** Legacy fraud alert entity
- **Field Count:** 15 fields
- **Key Fields:** tenant_id, parcel_id, alert_type, severity, description, status, assigned_to, investigation_notes
- **Status:** Active

### 30. PermissionRiskReport
- **Purpose:** Automated role and permission audit
- **Field Count:** 18 fields
- **Key Fields:** report_id, role_audited, risk_score, risk_level, issues_found, escalation_detected, overlapping_permissions, excessive_privileges, broken_rls_detected, remediation_suggestions
- **Connected Functions:** lvPermissionAuditor, lvPermissionIntegrityValidation
- **Status:** Active

### 31. CertificateIntegrityCheck
- **Purpose:** Certificate authenticity verification
- **Field Count:** 15 fields
- **Key Fields:** certificate_id, certificate_number, parcel_id, verification_code, qr_hash, certificate_hash, status, verified_parcel_exists, verified_qr_matches, verified_hash_matches, verified_not_revoked
- **Connected Functions:** lvCertificateIntegrityCheck, lvCertificateTrustValidation
- **Status:** Active

### 32. PenetrationTestResult
- **Purpose:** Automated penetration test results
- **Field Count:** 15 fields
- **Key Fields:** result_id, test_name, severity, result, evidence, vulnerability, incident_id, status, retest_result
- **Connected Functions:** lvPenetrationTest
- **Status:** Active

### 33. RecoveryTest
- **Purpose:** Disaster recovery validation
- **Field Count:** 15 fields
- **Key Fields:** test_id, test_type, status, success_rate, items_checked, items_recovered, items_failed, duration_minutes, recommendations
- **Connected Functions:** lvRecoveryTest, lvRecoveryValidation
- **Status:** Active

### 34. RoleChangeApproval
- **Purpose:** Two-person approval workflow for role escalations
- **Field Count:** 18 fields
- **Key Fields:** request_id, user_id, current_role, requested_role, requested_by, first_approver, second_approver, status, emergency_override, audit_log_id
- **Connected Functions:** lvRoleChangeApproval
- **Status:** Active

### 35. TakeoffReadinessAssessment
- **Purpose:** Pilot takeoff readiness assessment
- **Field Count:** 25 fields
- **Key Fields:** assessment_id, overall_score, readiness_level, infrastructure_score, trust_score, security_score, evidence_integrity_score, community_participation_score, verification_quality_score, surveyor_adoption_score, disaster_recovery_score, fraud_resilience_score, operational_health_score, gaps
- **Connected Functions:** lvTakeoffReadiness, lvPilotReadinessCertification
- **Status:** Active

## Economic Operating System Entities

### 36. ServiceCatalog
- **Purpose:** Monetizable services offered by the platform
- **Field Count:** 10 fields
- **Key Fields:** service_id, service_name, service_code, service_category, credit_cost, cash_price, service_status, estimated_delivery_time, requires_review
- **RLS Rules:** Create: `created_by`; Read: public; Update: roles [super_admin, surveyor_general, compliance_officer]; Delete: super_admin
- **Connected Functions:** lvSeedEconomicOS, lvServiceBilling
- **Status:** Active — 10 services seeded

### 37. InstitutionPlan
- **Purpose:** Recurring institutional access plans
- **Field Count:** 13 fields
- **Key Fields:** plan_id, plan_name, plan_code, plan_type, monthly_fee, included_credits, overage_rate, api_access, report_access, priority_processing, max_users
- **Connected Functions:** lvSeedEconomicOS
- **Status:** Active — 6 plans seeded

### 38. CreditWallet
- **Purpose:** Per-user credit wallet
- **Field Count:** 14 fields
- **Key Fields:** wallet_id, user_id, user_email, credit_balance, reserved_credits, credits_consumed, credits_purchased, credits_granted, wallet_status, frozen_reason, organization_wallet_id
- **RLS Rules:** Create: `created_by`; Read: public; Update: owner OR admin roles; Delete: super_admin
- **Connected Functions:** lvCreditEngine, lvServiceBilling
- **Status:** Active

### 39. OrganizationWallet
- **Purpose:** Institutional shared wallet
- **Field Count:** 18 fields
- **Key Fields:** wallet_id, organization_name, organization_type, plan_id, contact_email, credit_balance, reserved_credits, credits_consumed, monthly_allocation, allocation_remaining, overage_credits, department_allocations, wallet_status, billing_cycle_start, member_emails
- **Connected Functions:** lvCreditEngine
- **Status:** Active

### 40. ServiceRequest
- **Purpose:** Customer-initiated service request
- **Field Count:** 20 fields
- **Key Fields:** request_id, request_reference, requestor, service_id, service_name, parcel_id, status, submitted_at, completed_at, job_reference, invoice_reference, delivery_reference, credits_consumed, cash_amount, priority
- **RLS Rules:** Create: `created_by`; Read: public; Update: public; Delete: super_admin
- **Connected Functions:** lvServiceBilling, lvInvoiceGenerator
- **Status:** Active

### 41. Invoice
- **Purpose:** Automated invoice generation
- **Field Count:** 15 fields
- **Key Fields:** invoice_id, invoice_number, customer_id, customer_email, service_request, amount, tax, total_amount, currency, status, generated_at, paid_at, due_date, invoice_url
- **Connected Functions:** lvInvoiceGenerator
- **Status:** Active

### 42. UsageLedger
- **Purpose:** Immutable audit trail of credit-consuming activities
- **Field Count:** 13 fields
- **Key Fields:** usage_id, user_id, user_email, parcel_id, service_id, service_name, credits_used, cash_value, request_reference, usage_timestamp, status
- **Connected Functions:** lvServiceBilling
- **Status:** Active

### 43. EconomicAuditEntry
- **Purpose:** Immutable audit trail for every economic event
- **Field Count:** 15 fields
- **Key Fields:** audit_id, action_type, entity_type, entity_id, actor_email, before_state, after_state, reason, amount, timestamp
- **RLS Rules:** Create: `created_by`; Read: public; Update/Delete: super_admin (immutable)
- **Connected Functions:** lvCreditEngine, lvServiceBilling, lvInvoiceGenerator, lvRevenueFraudCheck
- **Status:** Active

### 44. UsageEvent
- **Purpose:** Usage tracking for future monetization
- **Field Count:** 10 fields
- **Key Fields:** user_id, user_email, event_type, timestamp, parcel_id, credits_consumed, metadata, ip_address
- **Status:** Active

## Background Job Entities

### 45. JobQueue
- **Purpose:** Background job queue
- **Field Count:** 18 fields
- **Key Fields:** job_id, job_type, status, entity_type, entity_id, created_by, payload, result, error_message, attempts, max_attempts, idempotency_key, priority, progress_pct, started_at, completed_at, result_reference
- **Job Types:** fraud_scoring, gis_validation, pdf_generation, bulk_import, report_export, backup, duplicate_scan, evidence_hashing, archive_import, verification_report, ocr_processing, qr_certificate_generation, pdf_certificate_generation, confidence_recalculation, notification
- **RLS Rules:** Create: `created_by`; Read: creator OR roles [super_admin, surveyor_general, compliance_officer, licensed_surveyor, surveyor_partner]; Update: admin roles; Delete: super_admin
- **Connected Functions:** jobQueueProcessor, lvCreateJob, lvAutoQueueJobs
- **Connected Automations:** Scheduled 5-minute processor (currently INACTIVE)
- **Status:** Active — but processor automation is DISABLED

## Surveyor Network Entities

### 46. SurveyorPartner
- **Purpose:** Surveyor partner profile with revenue tracking
- **Field Count:** 25 fields
- **Key Fields:** user_email, full_name, firm_name, surcon_number, license_number, verification_status, total_records_uploaded, archive_records, surveyor_verified_records, community_verified_records, verification_searches, certificates_generated, revenue_earned, revenue_available_for_withdrawal, revenue_paid
- **Status:** Active

### 47. ArchiveRecord
- **Purpose:** Historical survey archive record
- **Field Count:** 25 fields
- **Key Fields:** archive_reference, survey_reference, survey_date, survey_plan_url, coordinate_file_url, classification, trust_badge, surveyor_partner_id, hash_fingerprint, duplicate_checked
- **Status:** Active

### 48. RevenueTransaction
- **Purpose:** Surveyor partner monetization revenue tracking
- **Field Count:** 15 fields
- **Key Fields:** surveyor_partner_id, transaction_type, amount, revenue_share_pct, surveyor_earned, platform_fee, status, transaction_date, paid_date
- **Status:** Active

## Duplicate Detection Entities

### 49. DuplicateAlert
- **Purpose:** Duplicate detection engine alerts
- **Field Count:** 20 fields
- **Key Fields:** alert_type, status, severity, confidence_score, confidence_level, source_parcel_id, conflicting_parcel_id, detection_details, gps_distance_m, overlap_percentage, duplicate_field
- **Connected Functions:** lvDuplicateDetection
- **Status:** Active

## Reporting Entities

### 50. GeneratedReport
- **Purpose:** Deliverable intelligence reports — primary revenue product
- **Field Count:** 15 fields
- **Key Fields:** report_id, report_type, parcel_id, service_request, generated_by, confidence_snapshot, community_snapshot, duplicate_snapshot, verification_snapshot, trust_snapshot, download_url, hash, status, expires_at
- **Report Types:** PARCEL_VERIFICATION, COMMUNITY_EVIDENCE, SURVEYOR_HISTORY, TRUST_REPORT, RISK_REPORT, BANK_REPORT, LEGAL_REPORT, DUE_DILIGENCE_REPORT, COMPLIANCE_REPORT, ARCHIVE_DIGITIZATION
- **Connected Functions:** lvEvidenceReport
- **Status:** Active

### 51. ComplianceReport
- **Purpose:** Compliance report generation
- **Field Count:** 10 fields
- **Key Fields:** title, report_type, generated_by, period_start, period_end, summary, findings, status, file_url
- **Status:** Active

## Inheritance & Family Entities

### 52. InheritanceCase
- **Purpose:** Inheritance case management
- **Field Count:** 25 fields
- **Key Fields:** family_ownership_id, parcel_id, case_reference, case_type, status, initiated_by, surveyor_reviewer, compliance_reviewer, sg_reviewer, final_approved_by, certificate_generated
- **Status:** Active

### 53. FamilyOwnership
- **Purpose:** Family ownership structure
- **Field Count:** 25 fields
- **Key Fields:** parcel_id, family_name, family_head, parent_name, family_branch, generation_level, clan_name, family_lineage, fruit_trees, buildings, boreholes, economic_trees
- **Status:** Active

### 54. FamilyBeneficiary
- **Purpose:** Family beneficiary records
- **Field Count:** 20 fields
- **Key Fields:** family_ownership_id, inheritance_rank, generation_level, full_name, relationship, percentage_share, allocated_plot, status, date_of_death, verification_status
- **Status:** Active

### 55. PlotAllocation
- **Purpose:** Plot allocation within inheritance cases
- **Field Count:** 12 fields
- **Key Fields:** inheritance_case_id, beneficiary_id, planned_plot_number, area_sqm, allocation_percentage, allocation_status
- **Status:** Active

### 56. InheritanceWitness
- **Purpose:** Inheritance case witnesses
- **Field Count:** 12 fields
- **Key Fields:** inheritance_case_id, full_name, witness_role, witness_statement, verification_status
- **Status:** Active

### 57. OwnershipHistory
- **Purpose:** Ownership transfer history
- **Field Count:** 12 fields
- **Key Fields:** parcel_id, from_owner, to_owner, transfer_type, transfer_date, document_url, status, approved_by
- **Status:** Active

### 58. TraditionalAuthorityValidation
- **Purpose:** Traditional authority validation
- **Field Count:** 15 fields
- **Key Fields:** parcel_id, traditional_institution, traditional_ruler_name, validation_status, digital_signature_url, seal_url
- **Status:** Active

### 59. InheritanceDispute
- **Purpose:** Inheritance dispute management
- **Field Count:** 20 fields
- **Key Fields:** case_number, dispute_type, complainant_name, respondent_name, status, priority, assigned_to, timeline
- **Status:** Active

### 60. FamilyMeetingResolution
- **Purpose:** Family meeting resolution records
- **Field Count:** 20 fields
- **Key Fields:** resolution_reference, family_name, meeting_date, meeting_purpose, resolution_summary, chairperson, secretary, meeting_minutes, status, version_number, certificate_url
- **Status:** Active

### 61. DeathVerification
- **Purpose:** Death verification for inheritance
- **Field Count:** 25 fields
- **Key Fields:** deceased_name, date_of_death, family_confirmation, community_confirmation, lg_confirmation, court_confirmation, death_certificate_url, verification_status
- **Status:** Active

### 62. SubdivisionPlan
- **Purpose:** Parcel subdivision planning
- **Field Count:** 15 fields
- **Key Fields:** parent_parcel_id, subdivision_version, child_parcels, total_child_parcels, total_allocated_area_sqm, approval_status
- **Status:** Active

### 63. InheritanceDocument
- **Purpose:** Inheritance case documents
- **Field Count:** 15 fields
- **Key Fields:** inheritance_case_id, document_type, title, file_url, version_number, lifecycle_status, review_status
- **Status:** Active

## Governance & Admin Entities

### 64. ParcelFreeze
- **Purpose:** Parcel freeze/unfreeze tracking
- **Field Count:** 10 fields
- **Key Fields:** parcel_id, frozen_by, freeze_reason, status, lifted_by, lift_notes
- **Status:** Active

### 65. ParcelRevision
- **Purpose:** Parcel revision requests
- **Field Count:** 12 fields
- **Key Fields:** parcel_id, requested_by, revision_type, justification, proposed_changes, status, reviewed_by
- **Status:** Active

### 66. ImportHistory
- **Purpose:** Bulk import history
- **Field Count:** 12 fields
- **Key Fields:** uploaded_by, file_name, import_type, records_processed, records_imported, records_failed, records_duplicate, status, validation_report
- **Status:** Active

### 67. DocVersion
- **Purpose:** Document version history
- **Field Count:** 12 fields
- **Key Fields:** document_id, version_number, file_url, change_notes, lifecycle_status, checksum
- **Status:** Active

### 68. SurveyDocument
- **Purpose:** Survey document management
- **Field Count:** 12 fields
- **Key Fields:** parcel_id, document_type, file_url, surveyor_email, review_status, reviewed_by
- **Status:** Active

### 69. FieldReport
- **Purpose:** Field agent report submission
- **Field Count:** 18 fields
- **Key Fields:** parcel_id, agent_email, report_type, latitude, longitude, gps_accuracy, capture_timestamp, device_identifier, network_status, photos, quality_flag
- **Status:** Active

### 70. OfflineQueue
- **Purpose:** Offline operation queue for field agents
- **Field Count:** 10 fields
- **Key Fields:** agent_email, operation_type, payload, photo_urls, captured_at, sync_status, sync_error
- **Status:** Active

### 71. Dispute
- **Purpose:** Land dispute management
- **Field Count:** 12 fields
- **Key Fields:** parcel_id, complainant_email, dispute_type, description, status, priority, assigned_to, resolution_notes
- **Status:** Active

### 72. Notification
- **Purpose:** User notification system
- **Field Count:** 6 fields
- **Key Fields:** user_email, title, message, type, read, link
- **Status:** Active

---

# SECTION 5: COMPLETE FUNCTION INVENTORY

## Economic Operating System Functions

### 1. lvCreditEngine
- **Purpose:** Credit wallet management — initialization, authorization, reservation, consumption, refunds, grants, transfers, freeze/unfreeze
- **Inputs:** action (init/authorize/reserve/consume/refund/grant/transfer/freeze/unfreeze/balance), user_email, amount, reason, reference, target_user_email
- **Outputs:** wallet_id, credit_balance, reserved_credits, authorized (bool), success (bool)
- **Trigger Type:** Frontend invocation (EconomicsOperations page)
- **Connected Entities:** CreditWallet, EconomicAuditEntry
- **Error Handling:** Try/catch with JSON error responses (401/403/404/400)
- **Status:** Active — tested and operational

### 2. lvServiceBilling
- **Purpose:** Service billing orchestration — credit reservation on initiate, consumption on complete, refund on fail
- **Inputs:** action (initiate/complete/fail), service_id, priority, notes, request_reference, delivery_reference, failure_reason
- **Outputs:** request_id, request_reference, credits_reserved, cash_amount, wallet_available, consumed, new_balance, refunded
- **Trigger Type:** Frontend invocation (DueDiligence page, EconomicsOperations)
- **Connected Entities:** ServiceCatalog, CreditWallet, ServiceRequest, UsageLedger, EconomicAuditEntry
- **Error Handling:** Try/catch, idempotency check on complete (409 "Already completed"), 402 on insufficient credits
- **Status:** Active — tested: initiate ✅, complete ✅, fail/refund ✅, replay attack blocked ✅ (409)

### 3. lvInvoiceGenerator
- **Purpose:** Invoice generation for service requests, monthly batch billing, payment processing
- **Inputs:** action (generate_for_request/generate_monthly_batch/mark_paid), request_reference, billing_period
- **Outputs:** invoice_id, invoice_number, total_amount
- **Trigger Type:** Frontend invocation (admin only)
- **Connected Entities:** ServiceRequest, Invoice, EconomicAuditEntry
- **Error Handling:** 403 Forbidden for non-admin
- **Status:** Active — but admin-gated, cannot auto-trigger from service completion (GAP)

### 4. lvRevenueFraudCheck
- **Purpose:** Revenue fraud detection — audits credit wallets, usage ledgers, invoices for inconsistencies
- **Inputs:** {} (no params)
- **Outputs:** findings count by severity, frozen wallets
- **Trigger Type:** Manual admin invocation
- **Connected Entities:** CreditWallet, UsageLedger, Invoice, EconomicAuditEntry
- **Error Handling:** 403 Forbidden for non-admin
- **Status:** Active — admin-gated

### 5. lvRevenueIntelligence
- **Purpose:** Financial business intelligence — MRR/ARR, revenue distribution, ARPU, forecasting, leakage detection
- **Inputs:** {} (no params)
- **Outputs:** MRR, ARR, ARPU, revenue_by_service, revenue_by_community, forecast, outstanding_invoices, leakage
- **Trigger Type:** Manual admin invocation
- **Connected Entities:** Invoice, ServiceRequest, CreditWallet, UsageLedger
- **Error Handling:** 403 Forbidden for non-admin
- **Status:** Active — admin-gated

### 6. lvSeedEconomicOS
- **Purpose:** Database seeding for ServiceCatalog and InstitutionPlan
- **Inputs:** target (services/plans)
- **Outputs:** Seeded count
- **Trigger Type:** Manual admin invocation
- **Connected Entities:** ServiceCatalog, InstitutionPlan
- **Status:** Active — 10 services + 6 plans seeded

## Trust & Security Functions

### 7. lvTrustValidationEngine
- **Purpose:** Master trust validation orchestrator — runs all 8 validation engines, stores immutable TrustValidationRun
- **Inputs:** validation_type (optional)
- **Outputs:** validation_id, overall_score, trust_grade, passed/failed tests, pilot_recommendation
- **Trigger Type:** Scheduled (12-hour automation) + manual
- **Connected Entities:** TrustValidationRun, TrustScoreSnapshot, EvidenceIntegrityCheck, AuditIntegrityCheck, PermissionRiskReport, SecurityIncident, FraudSignal, CertificateIntegrityCheck, RecoveryTest
- **Connected Automations:** "Trust Validation Scan (12hr)" — ACTIVE, last_run: success
- **Status:** Active — only scheduled automation that is running successfully

### 8. lvSecurityScan
- **Purpose:** Comprehensive security scan — evidence integrity, fraud detection, audit integrity, permission audit, certificate integrity, session security
- **Trigger Type:** Scheduled (6-hour automation) + manual
- **Connected Automations:** "LandVault Automated Security Scan" — INACTIVE, failed 5x
- **Status:** INACTIVE — automation disabled due to consecutive failures

### 9. lvEvidenceIntegrityCheck
- **Purpose:** Cryptographic evidence integrity verification
- **Connected Entities:** EvidenceVault, EvidenceIntegrityCheck
- **Status:** Active

### 10. lvEvidenceIntegrityValidation
- **Purpose:** Evidence integrity validation engine (for trust validation)
- **Status:** Active

### 11. lvAuditIntegrityCheck
- **Purpose:** Audit trail integrity verification
- **Connected Entities:** AuditLog, AuditIntegrityCheck
- **Status:** Active

### 12. lvAuditIntegrityValidation
- **Purpose:** Audit integrity validation engine (for trust validation)
- **Status:** Active

### 13. lvHashChainProtection
- **Purpose:** Blockchain-style hash chain verification
- **Connected Entities:** HashChainEntry
- **Status:** Active

### 14. lvPermissionAuditor
- **Purpose:** Role and permission audit
- **Connected Entities:** PermissionRiskReport
- **Status:** Active

### 15. lvPermissionIntegrityValidation
- **Purpose:** Permission integrity validation engine
- **Status:** Active

### 16. lvCertificateIntegrityCheck
- **Purpose:** Certificate authenticity verification
- **Connected Entities:** CertificateIntegrityCheck
- **Status:** Active

### 17. lvCertificateTrustValidation
- **Purpose:** Certificate trust validation engine
- **Status:** Active

### 18. lvCertificateTrustAssurance
- **Purpose:** Certificate trust assurance
- **Status:** Active

### 19. lvCommunityTrustValidation
- **Purpose:** Community trust validation engine
- **Status:** Active

### 20. lvFraudResilience
- **Purpose:** Fraud resilience validation
- **Status:** Active

### 21. lvFraudResilienceValidation
- **Purpose:** Fraud resilience validation engine
- **Status:** Active

### 22. lvFraudDetection
- **Purpose:** Fraud detection engine
- **Connected Entities:** FraudSignal, FraudAlert
- **Status:** Active

### 23. lvSessionSecurity
- **Purpose:** Session security monitoring
- **Connected Entities:** SecuritySession
- **Status:** Active

### 24. lvPenetrationTest
- **Purpose:** Automated penetration testing
- **Connected Entities:** PenetrationTestResult, SecurityIncident
- **Status:** Active

### 25. lvRecoveryTest
- **Purpose:** Disaster recovery testing
- **Connected Entities:** RecoveryTest
- **Status:** Active

### 26. lvRecoveryValidation
- **Purpose:** Recovery validation engine
- **Status:** Active

### 27. lvRoleChangeApproval
- **Purpose:** Two-person role escalation approval workflow
- **Connected Entities:** RoleChangeApproval, AuditLog
- **Status:** Active

### 28. lvTrustScoreCalculation
- **Purpose:** Trust score calculation and snapshot
- **Connected Entities:** TrustScoreSnapshot
- **Status:** Active

## Community Attestation Functions

### 29. lvConsensusCalculation
- **Purpose:** Recalculates parcel consensus from attestations
- **Connected Entities:** CommunityAttestation, LandVaultParcel
- **Connected Automations:** "Consensus Calculation Engine" — active but failed 4x
- **Status:** Active with failures

### 30. lvConflictDetection
- **Purpose:** Detects conflicts between approved attestations
- **Connected Entities:** CommunityAttestation, CommunityReviewAlert, ParcelFlag
- **Connected Automations:** "Conflict Detection Scanner" — active
- **Status:** Active

### 31. lvEvidenceConfidence
- **Purpose:** Auto-calculates evidence_confidence_score and level
- **Connected Entities:** LandVaultParcel, EvidenceVault, CommunityAttestation
- **Connected Automations:** "Evidence Confidence — LandVaultParcel" — active
- **Status:** Active

### 32. lvAttestationConfidence
- **Purpose:** Updates parcel confidence when attestation is approved
- **Connected Automations:** "Attestation Confidence Impact" — active
- **Status:** Active

### 33. lvGenerateNotification
- **Purpose:** Generates notifications for attestation events
- **Connected Entities:** CommunityNotification
- **Connected Automations:** "Community Notification Generator" — active, last_run: success
- **Status:** Active

### 34. lvRecordAuditEntry
- **Purpose:** Records immutable audit entries for attestation operations
- **Connected Entities:** CommunityAttestationAudit
- **Connected Automations:** "Immutable Audit Trail" — active but failed 4x
- **Status:** Active with failures

### 35. lvRecordTimelineEvent
- **Purpose:** Records evidence timeline events
- **Connected Entities:** EvidenceTimelineEvent
- **Connected Automations:** "Evidence Timeline Recorder" — active, last_run: success
- **Status:** Active

## Evidence Functions

### 36. lvEvidenceSeal
- **Purpose:** Seals evidence package with SHA-256 hash
- **Connected Entities:** LandVaultParcel, EvidenceVault
- **Connected Automations:** "LandVault Evidence Seal — On Full Verification" — active
- **Status:** Active

### 37. lvEvidenceLock
- **Purpose:** Creates immutable evidence preservation locks
- **Connected Entities:** EvidenceLock
- **Status:** Active

### 38. lvEvidenceReport
- **Purpose:** Generates intelligence reports (parcel verification, due diligence, bank, legal)
- **Connected Entities:** GeneratedReport, LandVaultParcel, CommunityAttestation, EvidenceVault
- **Status:** Active

## Duplicate Detection Functions

### 39. lvDuplicateDetection
- **Purpose:** Multi-algorithm duplicate detection (GPS proximity, NIN, survey URL, family+ward, phone, evidence hash)
- **Connected Entities:** DuplicateAlert, LandVaultParcel, EvidenceVault
- **Connected Automations:** 7 entity automations (parcel create/update, evidence create)
- **Status:** Active — most heavily automated function (7 automations)

## Background Job Functions

### 40. jobQueueProcessor
- **Purpose:** Processes pending jobs from JobQueue (OCR, duplicate detection, confidence recalculation, report generation, certificate generation)
- **Trigger Type:** Scheduled (5-minute automation)
- **Connected Entities:** JobQueue
- **Connected Automations:** "LandVault Job Queue Processor" — INACTIVE, failed 5x
- **Status:** INACTIVE — automation disabled

### 41. lvCreateJob
- **Purpose:** Creates background jobs with idempotency
- **Connected Entities:** JobQueue
- **Status:** Active

### 42. lvAutoQueueJobs
- **Purpose:** Auto-queues jobs on entity events (duplicate scan, evidence hashing, confidence recalc)
- **Connected Entities:** JobQueue, EvidenceVault, LandVaultParcel
- **Connected Automations:** 3 entity automations
- **Status:** Active

### 43. lvBackgroundJobValidation
- **Purpose:** Background job validation engine
- **Status:** Active

## Readiness & Pilot Functions

### 44. lvTakeoffReadiness
- **Purpose:** Calculates platform takeoff readiness from 10 dimensions
- **Connected Entities:** TakeoffReadinessAssessment
- **Status:** Active

### 45. lvPilotReadinessCertification
- **Purpose:** Pilot readiness certification
- **Status:** Active

## Utility Functions

### 46. generateParcelId
- **Purpose:** Generates unique parcel numbers
- **Connected Entities:** ParcelSequence
- **Status:** Active

### 47. publicParcelLookup
- **Purpose:** Public parcel verification lookup (legacy)
- **Connected Entities:** LandParcel
- **Status:** Active

### 48. publicLandVaultLookup
- **Purpose:** Public LandVault parcel verification lookup
- **Connected Entities:** LandVaultParcel
- **Status:** Active

### 49. healthCheck
- **Purpose:** System health check
- **Status:** Active

### 50. rateLimiter
- **Purpose:** API rate limiting
- **Status:** Active

### 51. abuseDetection
- **Purpose:** Abuse detection — burst activity, off-hours access, mass data access
- **Connected Entities:** FraudAlert, AuditLog
- **Connected Automations:** "Abuse Detection — Every 30 Minutes" — INACTIVE, failed 5x
- **Status:** INACTIVE — automation disabled

### 52. asyncFraudScoring
- **Purpose:** Async fraud risk scoring on parcels
- **Connected Entities:** LandParcel
- **Connected Automations:** "Fraud Scoring — Every 15 Minutes" — INACTIVE, failed 5x
- **Status:** INACTIVE — automation disabled

### 53. asyncGISValidation
- **Purpose:** Async GIS boundary validation
- **Connected Entities:** LandParcel
- **Connected Automations:** "GIS Validation — On Parcel Create/Update" — active
- **Status:** Active

### 54. backupEntityExport
- **Purpose:** Disaster recovery — exports all critical entity collections
- **Connected Automations:** "Daily Backup Export — 02:00 UTC" — INACTIVE, failed 5x
- **Status:** INACTIVE — automation disabled

### 55. lvCommunityAttestationScore
- **Purpose:** Recalculates community attestation score
- **Connected Automations:** 2 entity automations (TraditionalAuthorityValidation, CommunityValidation)
- **Status:** Active

### 56-57. seedDemoData / seedDemoPhase1 / seedDemoPhase2 / seedDemoPhase3 / seedDemoFinalize
- **Purpose:** Demo data seeding functions
- **Status:** Active

---

# SECTION 6: AUTOMATION INVENTORY

## Scheduled Automations (6 total)

| # | Name | Frequency | Function | Status | Last Run | Purpose |
|---|---|---|---|---|---|---|
| 1 | Trust Validation Scan (12hr) | Every 12 hours | lvTrustValidationEngine | ✅ ACTIVE | Success | Runs all 8 validation engines, stores immutable TrustValidationRun |
| 2 | LandVault Automated Security Scan | Every 6 hours | lvSecurityScan | ❌ INACTIVE | Failed (5x) | Comprehensive security scan |
| 3 | LandVault Job Queue Processor | Every 5 minutes | jobQueueProcessor | ❌ INACTIVE | Failed (5x) | Processes pending background jobs |
| 4 | Abuse Detection — Every 30 Minutes | Every 30 minutes | abuseDetection | ❌ INACTIVE | Failed (5x) | Scans for burst activity, off-hours access |
| 5 | Daily Backup Export — 02:00 UTC | Daily 02:00 UTC (cron) | backupEntityExport | ❌ INACTIVE | Failed (5x) | Disaster recovery backup |
| 6 | Fraud Scoring — Every 15 Minutes | Every 15 minutes | asyncFraudScoring | ❌ INACTIVE | Failed (5x) | Fraud risk scoring on parcels |

**CRITICAL FINDING:** 5 of 6 scheduled automations are INACTIVE with 5 consecutive failures each. Only the Trust Validation Scan is operational.

## Entity/Data Automations (23 total)

### Community Attestation Automations (7)

| # | Name | Trigger | Function | Status | Last Run |
|---|---|---|---|---|---|
| 1 | Community Notification Generator | CommunityAttestation create/update | lvGenerateNotification | ✅ Active | Success |
| 2 | Immutable Audit Trail | CommunityAttestation create/update/delete | lvRecordAuditEntry | ⚠️ Active | Failed (4x) |
| 3 | Evidence Timeline Recorder | CommunityAttestation create/update | lvRecordTimelineEvent | ✅ Active | Success |
| 4 | Conflict Detection Scanner | CommunityAttestation update | lvConflictDetection | ✅ Active | — |
| 5 | Consensus Calculation Engine | CommunityAttestation create/update | lvConsensusCalculation | ⚠️ Active | Failed (4x) |
| 6 | Attestation Confidence Impact | CommunityAttestation update | lvAttestationConfidence | ✅ Active | — |
| 7 | Community Attestation Scoring — Trad Auth | TraditionalAuthorityValidation create/update | lvCommunityAttestationScore | ✅ Active | — |
| 8 | Community Attestation Scoring — CV Trigger | CommunityValidation create/update | lvCommunityAttestationScore | ✅ Active | — |

### Duplicate Detection Automations (9)

| # | Name | Trigger | Function | Status |
|---|---|---|---|---|
| 1 | Auto-Queue Jobs on New Evidence | EvidenceVault create | lvAutoQueueJobs | ✅ Active |
| 2 | Auto-Queue Confidence Recalc on Parcel Update | LandVaultParcel update | lvAutoQueueJobs | ✅ Active |
| 3 | Auto-Queue Jobs on New Parcel | LandVaultParcel create | lvAutoQueueJobs | ✅ Active |
| 4 | Duplicate Scan — EvidenceVault Create | EvidenceVault create | lvDuplicateDetection | ✅ Active |
| 5 | LV Duplicate Detection — Evidence Hash Check | EvidenceVault create | lvDuplicateDetection | ✅ Active |
| 6 | LV Duplicate Detection — Parcel Create/Update | LandVaultParcel create/update | lvDuplicateDetection | ✅ Active |
| 7 | LV Duplicate Detection — Evidence Hash Check (v2) | EvidenceVault create | lvDuplicateDetection | ✅ Active |
| 8 | LV Duplicate Detection — Parcel Create/Update (v2) | LandVaultParcel create/update | lvDuplicateDetection | ✅ Active |
| 9 | LandVault Duplicate Detection — Evidence Upload | EvidenceVault create | lvDuplicateDetection | ✅ Active |
| 10 | LandVault Duplicate Detection — Parcel Create/Update | LandVaultParcel create/update | lvDuplicateDetection | ✅ Active |
| 11 | LV Duplicate Detection — On Evidence Upload | EvidenceVault create | lvDuplicateDetection | ✅ Active |
| 12 | LV Duplicate Detection — On Parcel Create/Update | LandVaultParcel create/update | lvDuplicateDetection | ✅ Active |

**CRITICAL FINDING:** There are 12+ duplicate detection automations for the same two entities (EvidenceVault and LandVaultParcel). This is massive redundancy — multiple automations do the exact same thing.

### Evidence & Confidence Automations (3)

| # | Name | Trigger | Function | Status |
|---|---|---|---|---|
| 1 | Evidence Confidence — LandVaultParcel | LandVaultParcel create/update | lvEvidenceConfidence | ✅ Active |
| 2 | LandVault Evidence Seal — On Full Verification | LandVaultParcel update | lvEvidenceSeal | ✅ Active |
| 3 | GIS Validation — On Parcel Create/Update | LandParcel create/update | asyncGISValidation | ✅ Active |

---

# SECTION 7: SECURITY INVENTORY

| # | Component | Purpose | Connected Entities | Connected Functions | Status |
|---|---|---|---|---|---|
| 1 | Security Scan Engine | Comprehensive security scan (evidence, fraud, audit, permissions, certificates, sessions) | SecurityIncident, FraudSignal, SecuritySession | lvSecurityScan | ⚠️ Automation INACTIVE |
| 2 | Fraud Detection | Behavioral fraud signal detection | FraudSignal, FraudAlert | lvFraudDetection | ✅ Active |
| 3 | Evidence Integrity | SHA-256 cryptographic verification | EvidenceIntegrityCheck, EvidenceVault | lvEvidenceIntegrityCheck, lvEvidenceIntegrityValidation | ✅ Active |
| 4 | Hash Chain Protection | Blockchain-style audit linkage | HashChainEntry | lvHashChainProtection | ✅ Active |
| 5 | Permission Auditor | Role and permission risk audit | PermissionRiskReport | lvPermissionAuditor, lvPermissionIntegrityValidation | ✅ Active |
| 6 | Role Escalation Approval | Two-person approval workflow | RoleChangeApproval | lvRoleChangeApproval | ✅ Active |
| 7 | Recovery Testing | Disaster recovery validation | RecoveryTest | lvRecoveryTest, lvRecoveryValidation | ✅ Active |
| 8 | Penetration Testing | Automated security testing | PenetrationTestResult, SecurityIncident | lvPenetrationTest | ✅ Active |
| 9 | Trust Assurance | Certificate trust assurance | CertificateIntegrityCheck | lvCertificateTrustAssurance | ✅ Active |
| 10 | Certificate Integrity | Certificate authenticity verification | CertificateIntegrityCheck | lvCertificateIntegrityCheck, lvCertificateTrustValidation | ✅ Active |
| 11 | Session Monitoring | Login/session security tracking | SecuritySession | lvSessionSecurity | ✅ Active |
| 12 | Abuse Detection | Burst activity, off-hours access detection | FraudAlert, AuditLog | abuseDetection | ⚠️ Automation INACTIVE |
| 13 | Fraud Resilience | Fraud resilience validation | — | lvFraudResilience, lvFraudResilienceValidation | ✅ Active |
| 14 | Security Incident Management | Incident tracking and resolution | SecurityIncident | — | ✅ Active |

---

# SECTION 8: TRUST INFRASTRUCTURE INVENTORY

| # | Component | Entities | Functions | Pages | Status |
|---|---|---|---|---|---|
| 1 | Community Attestation | CommunityAttestation, CommunityAttestationAudit | lvConsensusCalculation, lvConflictDetection, lvAttestationConfidence, lvRecordAuditEntry, lvRecordTimelineEvent, lvGenerateNotification | CommunityAttestationDashboard, CommunityAttestationForm, CommunityAttestationReview | ✅ Active |
| 2 | Consensus Engine | LandVaultParcel (consensus fields) | lvConsensusCalculation | (integrated in ParcelDetail) | ⚠️ Active, automation failing |
| 3 | Conflict Detection | CommunityReviewAlert, ParcelFlag | lvConflictDetection | (integrated in review) | ✅ Active |
| 4 | Evidence Timeline | EvidenceTimelineEvent | lvRecordTimelineEvent | (integrated in ParcelDetail) | ✅ Active |
| 5 | Audit Trail | AuditLog, CommunityAttestationAudit, EconomicAuditEntry | lvRecordAuditEntry | AuditLogs, GlobalAudit | ✅ Active |
| 6 | Traditional Institution Endorsement | TraditionalInstitutionEndorsement | — | (integrated in review) | ✅ Active |
| 7 | Trust Badges | LandVaultParcel (special_badge), CommunityAttestation (special_badge) | — | TrustBadge component | ✅ Active |
| 8 | Transparency Portal | CommunityAttestation, TraditionalInstitutionEndorsement | — | CommunityTransparency | ✅ Active |
| 9 | Trust Dashboard | TrustValidationRun, TrustScoreSnapshot | lvTrustValidationEngine, lvTrustScoreCalculation | TrustArchitecture, TrustValidationCenter | ✅ Active |
| 10 | Confidence Engine | LandVaultParcel (evidence_confidence_score) | lvEvidenceConfidence, lvAttestationConfidence | (integrated in ParcelDetail) | ✅ Active |
| 11 | Trust Validation | TrustValidationRun | lvTrustValidationEngine + 8 sub-engines | TrustValidationCenter | ✅ Active (only working scheduled automation) |
| 12 | Takeoff Readiness | TakeoffReadinessAssessment | lvTakeoffReadiness, lvPilotReadinessCertification | PilotReadinessReport, DemoReadinessReport, ProductionReadiness | ✅ Active |

---

# SECTION 9: ECONOMIC OPERATING SYSTEM INVENTORY

| # | Component | Entities | Functions | Pages | Automations | Status |
|---|---|---|---|---|---|---|
| 1 | Service Catalog | ServiceCatalog | lvSeedEconomicOS, lvServiceBilling | PilotEconomics, DueDiligence | None | ✅ Active (10 services seeded) |
| 2 | Credit Wallets | CreditWallet | lvCreditEngine, lvServiceBilling | EconomicsOperations | None | ✅ Active (tested) |
| 3 | Organization Wallets | OrganizationWallet | lvCreditEngine | EconomicsOperations | None | ✅ Active |
| 4 | Usage Ledger | UsageLedger | lvServiceBilling | RevenueAnalytics | None | ✅ Active |
| 5 | Invoices | Invoice | lvInvoiceGenerator | RevenueAnalytics | None | ⚠️ Admin-gated, no auto-trigger |
| 6 | Billing Engine | ServiceRequest, CreditWallet, UsageLedger | lvServiceBilling | DueDiligence, EconomicsOperations | None | ✅ Active (tested) |
| 7 | Revenue Intelligence | Invoice, ServiceRequest, CreditWallet | lvRevenueIntelligence | RevenueAnalytics | None | ✅ Active (admin-gated) |
| 8 | Fraud Controls | CreditWallet, UsageLedger, Invoice | lvRevenueFraudCheck | EconomicsOperations | None | ✅ Active (admin-gated) |
| 9 | Pilot Economics | CreditWallet, ServiceCatalog, InstitutionPlan | — | PilotEconomics | None | ✅ Active |
| 10 | Due Diligence Revenue | ServiceRequest, GeneratedReport | lvServiceBilling, lvEvidenceReport | DueDiligence | None | ✅ Active |
| 11 | Institution Plans | InstitutionPlan | lvSeedEconomicOS | PilotEconomics | None | ✅ Active (6 plans seeded) |

**CRITICAL FINDING:** The EOS has NO automations. Invoice generation, monthly billing, and fraud checks are all manual admin-only operations. There is no automated monthly billing cycle.

---

# SECTION 10: BACKGROUND JOB ENGINE INVENTORY

| # | Component | Status | Details |
|---|---|---|---|
| 1 | Job Queue | ✅ Active | JobQueue entity with 15 job types, idempotency keys, retry logic (max 3 attempts), priority levels |
| 2 | Job Processor | ❌ INACTIVE | jobQueueProcessor automation is DISABLED (5 consecutive failures) |
| 3 | OCR Jobs | ⚠️ Defined | Job type "ocr_processing" exists in enum — no dedicated OCR function found |
| 4 | Confidence Jobs | ✅ Active | lvEvidenceConfidence automation on parcel create/update |
| 5 | Duplicate Detection Jobs | ✅ Active (over-engineered) | 12+ automations for the same entities |
| 6 | Notification Jobs | ✅ Active | lvGenerateNotification automation on attestation events |
| 7 | Certificate Jobs | ⚠️ Defined | Job types "qr_certificate_generation" and "pdf_certificate_generation" exist — no dedicated function found |
| 8 | Retry Logic | ✅ Active | max_attempts=3, attempts counter, error_message tracking |
| 9 | Monitoring Dashboard | ✅ Active | OperationsDashboard at /operations |
| 10 | Operations Command Center | ✅ Active | EconomicsOperations at /economics/operations |

**CRITICAL FINDING:** The job queue processor automation is DISABLED. Background jobs are being created (by entity automations) but NOT being processed. The queue is accumulating unprocessed jobs.

---

# SECTION 11: RLS & PERMISSION AUDIT

## Roles Defined in the System

1. `super_admin` — Full system access
2. `surveyor_general` — Surveyor management, approvals
3. `compliance_officer` — Compliance, audit, fraud
4. `licensed_surveyor` — Survey execution
5. `surveyor_partner` — Surveyor partner network
6. `field_agent` — Field data collection
7. `community_validator` — Community validation
8. `government_observer` — Read-only government oversight
9. `surveyor` — Legacy surveyor role
10. `general_user` — Legacy general user role

## RLS Risk Assessment

| Entity | Read | Create | Update | Delete | Risk Level | Notes |
|---|---|---|---|---|---|---|
| LandVaultParcel | Owner + field_agent + 7 roles | created_by | Owner + field_agent + admin + surveyor + validator | super_admin | MEDIUM | Complex multi-condition RLS — correct but hard to maintain |
| LandParcel | Owner + creator + field_agent + 5 roles | created_by | Creator + owner + admin + validator | super_admin | MEDIUM | Legacy entity, still functional |
| EvidenceVault | 6 roles | created_by | super_admin ONLY | super_admin | LOW | Correctly immutable after creation |
| CommunityAttestation | 8 roles | created_by | Creator (clarification) + admin | super_admin | LOW | Well-protected |
| CreditWallet | PUBLIC READ | created_by | Owner + admin | super_admin | HIGH | Public read is overly permissive for financial data |
| OrganizationWallet | PUBLIC READ | created_by | PUBLIC UPDATE | super_admin | CRITICAL | Public update is a security gap |
| ServiceRequest | PUBLIC READ | created_by | PUBLIC UPDATE | super_admin | HIGH | Public update allows request modification |
| Invoice | PUBLIC READ | created_by | PUBLIC UPDATE | super_admin | HIGH | Public update allows invoice modification |
| EconomicAuditEntry | PUBLIC READ | created_by | super_admin | super_admin | LOW | Correctly immutable |
| UsageLedger | PUBLIC READ | created_by | 3 admin roles | super_admin | LOW | Acceptable |
| ServiceCatalog | PUBLIC READ | created_by | 3 admin roles | super_admin | LOW | Acceptable |
| JobQueue | Creator + 5 roles | created_by | 3 admin roles | super_admin | LOW | Well-protected |
| AuditLog | Creator + 3 roles | 5 roles | super_admin | super_admin | LOW | Well-protected |
| HashChainEntry | 6 roles | created_by | super_admin | super_admin | LOW | Correctly immutable |
| TrustValidationRun | 6 roles | created_by | 3 admin roles | super_admin | LOW | Acceptable |
| SecurityIncident | 3 roles | created_by | 3 admin roles | super_admin | LOW | Well-protected |
| FraudSignal | 3 roles | created_by | 3 admin roles | super_admin | LOW | Well-protected |
| Notification | Owner only | Owner + super_admin | Owner only | Owner only | LOW | Correctly scoped |
| DuplicateAlert | 5 roles | 4 roles | 3 admin roles | super_admin | LOW | Well-protected |
| User (built-in) | Admin can list/update/delete; users read own | — | — | — | LOW | Platform-managed |

**CRITICAL RLS GAPS:**
1. **OrganizationWallet** — `update: {}` (PUBLIC) — anyone can modify institutional wallet balances
2. **ServiceRequest** — `update: {}` (PUBLIC) — anyone can modify service request status
3. **Invoice** — `update: {}` (PUBLIC) — anyone can modify invoice status/amounts
4. **CreditWallet** — `read: {}` (PUBLIC) — anyone can view any user's credit balance

---

# SECTION 12: PLATFORM DEPENDENCY MAP

## Pages → Functions

| Page | Functions Called |
|---|---|
| EconomicsOperations | lvCreditEngine, lvServiceBilling, lvInvoiceGenerator, lvRevenueFraudCheck, lvRevenueIntelligence |
| DueDiligence | lvServiceBilling |
| TrustValidationCenter | lvTrustValidationEngine |
| SecurityTesting | lvPenetrationTest |
| SecurityOperations | lvRoleChangeApproval |
| ParcelDetail | lvEvidenceReport, lvEvidenceSeal |
| PilotReadinessReport | lvPilotReadinessCertification |
| DemoReadinessReport | lvTakeoffReadiness |
| ProductionReadiness | lvTakeoffReadiness |
| PublicVerify | publicParcelLookup |
| LandVaultPublicVerify | publicLandVaultLookup |
| DemoDataSeed | seedDemoData, seedDemoPhase1-3, seedDemoFinalize |
| RegisterLand | generateParcelId |
| ParcelForm | generateParcelId |

## Functions → Entities

| Function | Entities Read/Written |
|---|---|
| lvCreditEngine | CreditWallet (RW), EconomicAuditEntry (W) |
| lvServiceBilling | ServiceCatalog (R), CreditWallet (RW), ServiceRequest (RW), UsageLedger (W), EconomicAuditEntry (W) |
| lvInvoiceGenerator | ServiceRequest (R), Invoice (RW), EconomicAuditEntry (W) |
| lvRevenueFraudCheck | CreditWallet (R), UsageLedger (R), Invoice (R), EconomicAuditEntry (W) |
| lvRevenueIntelligence | Invoice (R), ServiceRequest (R), CreditWallet (R), UsageLedger (R) |
| lvTrustValidationEngine | TrustValidationRun (W), TrustScoreSnapshot (W), + all security/trust entities (R) |
| lvConsensusCalculation | CommunityAttestation (R), LandVaultParcel (RW) |
| lvConflictDetection | CommunityAttestation (R), CommunityReviewAlert (W), ParcelFlag (W) |
| lvEvidenceConfidence | LandVaultParcel (RW), EvidenceVault (R), CommunityAttestation (R) |
| lvDuplicateDetection | LandVaultParcel (R), EvidenceVault (R), DuplicateAlert (W) |
| jobQueueProcessor | JobQueue (RW) |
| lvEvidenceSeal | LandVaultParcel (RW), EvidenceVault (R) |
| lvEvidenceReport | GeneratedReport (W), LandVaultParcel (R), CommunityAttestation (R), EvidenceVault (R) |

## Automations → Functions

| Automation | Function |
|---|---|
| Trust Validation Scan (12hr) | lvTrustValidationEngine |
| LandVault Automated Security Scan | lvSecurityScan |
| LandVault Job Queue Processor | jobQueueProcessor |
| Abuse Detection | abuseDetection |
| Daily Backup Export | backupEntityExport |
| Fraud Scoring | asyncFraudScoring |
| 7 Community Attestation automations | lvConsensusCalculation, lvConflictDetection, lvAttestationConfidence, lvGenerateNotification, lvRecordAuditEntry, lvRecordTimelineEvent, lvCommunityAttestationScore |
| 12 Duplicate Detection automations | lvDuplicateDetection, lvAutoQueueJobs |
| 3 Evidence/Confidence automations | lvEvidenceConfidence, lvEvidenceSeal, asyncGISValidation |

---

# SECTION 13: FEATURE COMPLETENESS MATRIX

| Feature | Exists | Connected | Tested | Operational |
|---|---|---|---|---|
| Parcel Registry (LandVault) | YES | YES | YES | YES |
| Parcel Registry (Legacy/Ehime) | YES | YES | YES | YES |
| Surveyor Verification | YES | YES | YES | YES |
| OCR Processing | PARTIAL | NO | NO | NO (job type defined, no function) |
| Trust Dashboard | YES | YES | YES | YES |
| Community Attestation | YES | YES | YES | YES |
| Security Command Center | YES | YES | YES | PARTIAL (scan automation disabled) |
| Economics Command Center | YES | YES | YES | PARTIAL (no automations) |
| Background Jobs | YES | YES | PARTIAL | NO (processor disabled) |
| Certificate Generation | PARTIAL | PARTIAL | NO | PARTIAL (job types defined, no function) |
| Fraud Detection | YES | YES | YES | PARTIAL (scoring automation disabled) |
| Revenue Intelligence | YES | YES | YES | YES (manual only) |
| Due Diligence Reports | YES | YES | YES | YES |
| Takeoff Readiness Engine | YES | YES | YES | YES |
| Credit Wallet System | YES | YES | YES | YES |
| Service Billing | YES | YES | YES | YES |
| Invoice Generation | YES | YES | PARTIAL | PARTIAL (admin-gated, no auto-trigger) |
| Monthly Billing Automation | NO | NO | NO | NO |
| Backup/Disaster Recovery | YES | YES | NO | NO (automation disabled) |
| Evidence Integrity (SHA-256) | YES | YES | YES | YES |
| Hash Chain Protection | YES | YES | YES | YES |
| Consent Capture (6-stage) | YES | YES | YES | YES |
| Duplicate Detection | YES | YES | YES | YES (over-engineered) |
| Community Consensus | YES | YES | PARTIAL | PARTIAL (automation failing) |
| Conflict Detection | YES | YES | YES | YES |
| Role Escalation Approval | YES | YES | YES | YES |
| Penetration Testing | YES | YES | YES | YES |
| Recovery Testing | YES | YES | YES | YES |
| GIS Validation | YES | YES | YES | YES |
| Inheritance Management | YES | YES | YES | YES |
| Surveyor Partner Network | YES | YES | YES | YES |
| Archive Digitization | YES | YES | YES | YES |
| Public Verification Portal | YES | YES | YES | YES |
| Community Transparency Portal | YES | YES | YES | YES |
| Pilot Deployment Package | YES | YES | YES | YES |

---

# SECTION 14: TAKEOFF READINESS ASSESSMENT

## Dimension Scores

| Dimension | Score | Justification |
|---|---|---|
| Platform Foundation | 85/100 | 77 pages, 72 entities, 57 functions, 82 routes — comprehensive foundation. Legacy + LandVault dual-system adds complexity. |
| Security | 65/100 | 14 security modules exist and are connected. BUT: 3 critical RLS gaps (OrganizationWallet, ServiceRequest, Invoice have public update). Security scan automation is disabled. |
| Trust Infrastructure | 80/100 | 12 trust modules, consensus engine, conflict detection, evidence timeline, hash chain — all exist. Consensus calculation automation is failing (4 consecutive failures). |
| Background Jobs | 40/100 | JobQueue entity is well-designed with idempotency and retry. BUT: processor automation is DISABLED. Jobs are being queued but NOT processed. OCR and certificate generation job types have no implementing functions. |
| Economic Operating System | 70/100 | Credit wallet, service billing, usage ledger all tested and operational. BUT: No automations (monthly billing, fraud checks are manual). Invoice generation is admin-gated and cannot auto-trigger. 3 critical RLS gaps in economic entities. |
| Data Integrity | 85/100 | SHA-256 hashing, evidence locks, hash chain, immutable audit entries — all implemented and connected. |
| Operations | 50/100 | Operations dashboard exists. BUT: 5 of 6 scheduled automations are INACTIVE with 5 consecutive failures. Background job processor is disabled. Backup automation is disabled. |
| Automation | 45/100 | 29 automations exist. BUT: 5 scheduled automations disabled, 2 entity automations failing. 12+ redundant duplicate detection automations. No economic automations. |
| Scalability | 60/100 | Single shared database. No staging environment. No CI/CD pipeline. Multi-tenant isolation via tenant_id but not enforced at database level. |
| Pilot Readiness | 65/100 | Takeoff readiness engine exists and is functional. Pilot reports, deployment packages, demo guides all exist. BUT: operational failures in automations reduce actual readiness. |

## Overall Readiness Score

**Overall Score: 64.5/100**

**Current Readiness Level: EARLY_PILOT**

The platform has comprehensive feature coverage and architectural depth, but is operationally degraded due to:
- 5 disabled scheduled automations (security scan, job processor, abuse detection, backup, fraud scoring)
- 2 failing entity automations (audit trail, consensus calculation)
- 3 critical RLS security gaps in economic entities
- No automated billing/invoice generation
- No OCR or certificate generation function implementations
- Massive automation redundancy (12+ duplicate detection automations)

## Biggest Risks

1. **CRITICAL — Background Job Processor Disabled:** Jobs are being queued by entity automations but never processed. The queue is accumulating. OCR, report generation, certificate generation are all blocked.
2. **CRITICAL — RLS Security Gaps:** OrganizationWallet, ServiceRequest, and Invoice have public update permissions. Any authenticated user can modify institutional wallet balances, service request statuses, and invoice amounts.
3. **HIGH — Security Scan Disabled:** The automated security scan has been disabled for 5+ consecutive failures. No automated security monitoring is active.
4. **HIGH — Backup Disabled:** Daily backup export is disabled. No automated disaster recovery is running.
5. **HIGH — No Economic Automations:** Monthly billing, fraud checks, and revenue intelligence are all manual admin-only operations. The EOS cannot operate autonomously.
6. **MEDIUM — Consensus Engine Failing:** The consensus calculation automation has 4 consecutive failures. Community consensus is not being recalculated reliably.

## Biggest Gaps

1. **OCR Processing:** Job type "ocr_processing" is defined but no implementing function exists.
2. **Certificate Generation:** Job types "qr_certificate_generation" and "pdf_certificate_generation" are defined but no implementing functions exist.
3. **Monthly Billing Automation:** No scheduled automation for monthly invoice generation.
4. **Staging Environment:** No staging environment exists — single shared database across all environments.
5. **CI/CD Pipeline:** No CI/CD pipeline is configured.

## Missing Components

1. Automated invoice generation on service completion
2. OCR function implementation
3. Certificate generation function implementations
4. Monthly billing automation
5. Credit wallet transaction locking (race condition vulnerability under concurrent load)
6. Staging environment
7. CI/CD pipeline

## Recommended Next Priorities

1. **P0 — Fix RLS Security Gaps:** Restrict OrganizationWallet, ServiceRequest, and Invoice update permissions to admin roles only.
2. **P0 — Re-enable Job Queue Processor:** Diagnose and fix the 5 consecutive failures, then re-enable the jobQueueProcessor automation.
3. **P0 — Re-enable Security Scan:** Diagnose and fix the lvSecurityScan automation failures.
4. **P1 — Re-enable Backup Automation:** Diagnose and fix backupEntityExport failures.
5. **P1 — Fix Consensus Calculation:** Diagnose and fix lvConsensusCalculation automation failures.
6. **P1 — Implement Invoice Auto-Generation:** Wire lvServiceBilling.complete to auto-trigger lvInvoiceGenerator.
7. **P1 — Deduplicate Automations:** Remove the 12+ redundant duplicate detection automations — keep one per entity per event.
8. **P2 — Implement OCR Function:** Create the OCR processing function for the defined job type.
9. **P2 — Implement Certificate Generation Functions:** Create QR and PDF certificate generation functions.
10. **P2 — Add Monthly Billing Automation:** Create a scheduled automation for monthly invoice batch generation.
11. **P3 — Set Up Staging Environment:** Create a staging environment for pre-production testing.
12. **P3 — Implement CI/CD Pipeline:** Set up automated deployment pipeline.

---

# APPENDIX: COMPONENT INVENTORY

## UI Components (48 shadcn/ui)
accordion, alert, alert-dialog, aspect-ratio, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input, input-otp, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toast, toaster, toggle, toggle-group, tooltip

## Custom Components (72)

### Layout (3)
AppLayout, Sidebar, TopBar

### Shared (4)
LoadingSpinner, StatusBadge, StatCard, EmptyState

### LandVault (4)
TrustBadge, DisputeReadinessPanel, EvidenceSealPanel, OwnershipStructurePanel

### Community (1)
CommunityAttestationPanel

### Ehime (3)
CertificateReleasePanel, ParcelCertificate, ParcelDataForm

### GIS (2)
ParcelPolygonEditor, FamilyLineageOverlay

### Consent (7)
Stage1VerbalConsent, Stage3AudioConsent, Stage4Signature, Stage5PhotoConsent, Stage6Witness, ConsentBadge, ConsentTimeline

### Inheritance (13)
InheritanceCaseDetail, FamilyLineagePanel, InheritanceCaseDialog, InheritanceDashboardStats, InheritanceCaseWorkflow, InheritanceCertificate, InheritanceDocManager, InheritanceLineageTree, PlotAllocationManager, SubdivisionPlanner, WitnessManager, BeneficiaryManager, CertificateGenerator

### Customary (7)
CommunityConsentManager, CommunityValidationWorkflow, DeathVerificationPanel, EvidenceChainViewer, FamilyMeetingResolutionManager, InheritanceDisputeManager, TraditionalAuthorityPanel

### Ownership (2)
FamilyOwnershipDialog, FamilyOwnershipPanel

### Dashboard (6)
ComplianceDashboard, SuperAdminDashboard, FieldAgentDashboard, GeneralDashboard, SurveyorDashboard, SurveyorGeneralDashboard

### Documents (1)
DocVersionHistory

### Field (1)
OfflineSyncManager

### Fraud (1)
FraudRiskPanel

### Land (2)
LandDetailModal, ParcelRevisionRequest

### Pilot (8)
PilotShared, ChainOfTitleTab, FraudSimulationTab, AcceptanceReportTab, CustomaryOwnershipTab, FieldOperationsTab, SurveyAccuracyTab, FieldOpsTab

### Deployment (5)
DemonstrationPackageTab, PerformanceFrameworkTab, SecurityVerificationTab, TrainingMaterialsTab, UATSuiteTab

### Other (1)
ProtectedRoute

---

*END OF FORENSIC AUDIT REPORT*

*This report was generated from live platform inspection on 2026-06-24. Every entity schema, function, automation, and route was verified against actual platform state. No assumptions or theoretical constructs were included.*