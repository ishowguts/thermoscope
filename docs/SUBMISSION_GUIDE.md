# SIH26162 submission package

Prepared from the official 2026 sources and the team's current artifacts. This is a revision brief and draft narrative, not an already revised or submitted PPT. The original PPT and Canva design have not been changed.

## Immediate priority

The [2026 guidelines](https://sih.gov.in/letters/2026/SIH%202026%20Guidelines.pdf) give 30 September 2026 as the submission deadline and cap ideas per PS at 500. The [public table](https://www.sih.gov.in/sih2026PS) showed 93/500 for SIH26162 at approximately 23:31 IST on 25 September. Recheck at submission; being below the cap now does not reserve a place.

Use the [official presentation template](https://sih.gov.in/letters/2026/SIH2026-IDEA-Presentation-Format.pptx): retain the six content positions and their headings, remove its final instruction page, and submit a PDF. The instruction page limits the presentation to six slides including the title. Signed-in portal limits, optional links and editing after submission are still unverified.

Team leader access is available according to the user. Team ID 144613, registered name Git_Push_Pray, leader Bittu Mandal and college INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE are confirmed in `SUBMISSION_DETAILS.md`. Verify nomination status and portal limits before final packaging. Do not put credentials in this repository.

## Six-slide narrative

The copy below describes the **proposed fresh system**. Change wording to implemented only after the specific capability has saved evidence. Any screenshot must identify its release and whether it shows genuine observations, historical replay or synthetic fixtures.

### 1. Title page

Use SMART INDIA HACKATHON 2026 and the current official artwork. Enter the exact PS title and ID SIH26162, NTRO, Software and Disaster Management. Idea name: **ThermoScope — Industrial Thermal Intelligence**. Use Team ID **144613** and exact registered name **Git_Push_Pray**. The old deck’s “Git push pray” wording must be corrected.

Suggested one-line pitch: **Distinguish recurring industrial heat from unusual thermal activity, with a map, history and evidence for every assessment.**

### 2. Idea / proposed solution

Suggested compact points under the supplied headings:

- **Problem addressed:** a thermal hotspot can be a routine industrial source, field/forest burning, or an unusual event requiring review.
- **Solution:** combine FIRMS observations, mapped infrastructure, dated satellite context and prior site history in one analyst workbench.
- **Output:** likely source, behaviour relative to history, and an explained review priority; abstain when evidence is insufficient.
- **Proposed distinction:** evidence-led review for Indian industrial sites, tested against proximity and persistence baselines.

Visual: three small cases using the same layout—recurring industrial source, unusual candidate and nearby non-industrial burning. Until real cases are verified, use a clearly labeled conceptual diagram. Do not invent a “live” screenshot.

### 3. Technical approach

Visual: **FIRMS + cached OSM + dated land cover/imagery → normalized observations → events/sites + prior history → baseline/model + uncertainty → PostGIS/API → analyst map and evidence.**

Keep a short technology line: FastAPI, PostGIS, React/MapLibre, XGBoost; AlphaEarth context experiment; optional Prithvi multispectral experiment. Model names should support the method, not occupy most of the slide.

Show how the same facility can have a recurring source and a new abnormal episode. Include a small “validation” box: held-out sites/region, independent reviewed labels, simpler-baseline comparison and missing-data tests. Use one genuine case-panel image if available by the submission date; otherwise show an explicitly proposed wireframe.

Remove the old simulated-event/facility/endpoint counts and custom-AI-engine claims unless the exact demonstrated release proves them. Remove the unlabeled synthetic fire footprint.

### 4. Feasibility and viability

Use a simple risk/response layout:

| Constraint | Planned response |
|---|---|
| Cloud, overpass and publication gaps | Display data age; retain history; abstain when evidence is insufficient |
| Unmapped or nearby facilities | Multiple possible associations and uncertainty support region |
| Scarce incident labels | Independently reviewed cases; separate source classification from incident validation |
| Limited time | Regional workflow first, evaluated baseline next, imagery experiments after comparison |
| Demonstration connectivity | Clearly marked historical replay with permitted offline assets |

Only insert a result chart if a frozen evaluation exists. Otherwise label this a validation plan. A deadline-driven proposal can be credible without pretending the complete research system is already built.

### 5. Impact and benefits

Show the operator journey: select a hotspot → compare history → inspect evidence → review/annotate → export a case.

Suggested outcomes to **measure**: unnecessary reviews at a defined incident-recall level, source-classification errors by class/region, review time in a small operator study, and successful operation during source outages. These are evaluation goals, not achieved impact.

Avoid unverified claims of prevented explosions, lives saved, exact losses avoided, ignition-time warning or continuous monitoring. State satellite-driven near-real-time availability. Recurring heat can be operationally normal, but the application cannot certify safety.

### 6. Research and references

Use 4-6 readable references: NASA FIRMS/product fields, persistent-source research, spatial-leakage research, AlphaEarth documentation and the selected model card. Link the real repository/demo/video only when viewers can open them without requesting access. A private development repository is not a public judge-facing evidence link.

Use a short limitation sentence: **Source mapping, satellite coverage and label quality constrain confidence; uncertain cases remain reviewable.** Keep the PDF understandable without following any links.

## Draft idea description

ThermoScope proposes an AI-enabled GIS workbench for distinguishing industrial thermal sources from vegetation and agricultural burning. It combines NASA FIRMS observations with mapped industrial infrastructure, dated land-cover and satellite context, and each site's earlier thermal activity. The system separates likely source, behaviour relative to its observed baseline, and analyst review priority, avoiding the assumption that every industrial hotspot is an accident. Each assessment exposes its timestamps, supporting evidence, uncertainty and data gaps. A structured baseline will be compared with satellite-embedding features using independently reviewed labels and held-out sites. The workbench will support map overlays, history, analyst review and reproducible case exports. Initial validation will focus on a bounded Indian pilot and include routine industrial sources, independently corroborated abnormal cases where satellite observations exist, nearby non-industrial burning and missing-data failures.

Adapt to the actual portal's character limit. This paragraph is a proposed-system description, not a report of completed validation.

## Video: recommended supporting evidence

The inspected guideline fields establish a PDF requirement; they do not establish a mandatory student demo video. Confirm the portal's link fields before recording/uploading. A short video can make the workflow easier to judge, but no defensible selection uplift is known.

Suggested length: approximately 2 minutes 45 seconds, unless the portal imposes another limit.

| Time | Screen / narration goal |
|---|---|
| 0:00-0:20 | A routine industrial hotspot and an unusual event can look similar in a basic hotspot feed. Explain the decision problem. |
| 0:20-0:55 | Open a genuine recurring-source case; show its dates, mapped context and historical pattern. |
| 0:55-1:35 | Open a corroborated abnormal candidate or an uncertainty case; explain the evidence and what remains unknown. |
| 1:35-2:05 | Show real baseline/evaluation evidence if available; otherwise state the planned validation and current build boundary. |
| 2:05-2:30 | Review/export workflow that actually exists. If unbuilt, omit the demonstration and label the proposed flow. |
| 2:30-2:45 | Deployment/replay status, limitation and next milestone; end with the project/team identity. |

Use team narration, captions and legible screen capture. Record at a fixed release, avoid credentials/notifications, and label replay throughout. Test the viewing link in a signed-out browser. Keep a local copy and transcript. Do not replace genuine application footage with generated UI/video presented as working software.

## Package checks before the final click

- Registered details and selected PS match the portal; required team/authorization information is complete.
- Six-slide PDF, required headings, correct year and no instruction slide; every page visually checked at normal viewing size.
- Every numeric/capability claim maps to the actual release and evidence; proposed items use future/conditional wording.
- Submission links work for a judge without your account. No private credentials, confidential data or unlicensed imagery.
- Team checks clarity and can explain the data limitations, one hard failure case and the baseline comparison.
- User reviews the exact final PDF and portal entries before submission. Save the receipt/reference number, timestamp and submitted PDF afterwards.

The strongest controllable improvements are exact PS fit, clear reasoning, truthful evidence and a working review flow. Neither an expensive model nor a polished video guarantees selection.
