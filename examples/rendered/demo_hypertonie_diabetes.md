# Machbarkeitsanfrage: Erwachsene mit Hypertonie und Diabetes mellitus Typ 2 (Demo)

**Quelle:** `demo_hypertonie_diabetes.json`  
**Erstellt:** 2026-07-29  
**CRTDL-Version:** http://json-schema.org/to-be-done/schema#  
**CCDL-Version:** https://medizininformatik-initiative.de/fdpg/ClinicalCohortDefinitionLanguage/v1/schema

## Kohortendefinition

Eine Person gehört zur Kohorte, wenn **alle Einschlussbedingungen (E1–E6)** erfüllt sind **und** **keine der Ausschlussbedingungen (A1–A2)** zutrifft.

### Einschlusskriterien

**Alle 6 Bedingungen E1–E6 müssen erfüllt sein** (mit UND verknüpft).

*Formale Struktur:* `E1 UND (E2a ODER E2b) UND E3 UND E4 UND E5 UND E6`  
<sub>Alle 7 Kriterien dieses Abschnitts sind in der formalen Struktur genau einmal referenziert.</sub>

> **E1** [Person] Alter (424144002, SNOMED CT)
> ↳ Wert: ≥ 18 Jahr(e)

**UND**

> **E2** · Mindestens eines der folgenden 2 Kriterien (E2a–E2b):
> 
> > **E2a** [Diagnose] Essentielle (primäre) Hypertonie (I10, ICD-10-GM 2024)
> > ↳ Zeitraum (Überschneidung): von 01.01.2020 bis 31.12.2024
> > 
> > **ODER**
> > 
> > **E2b** [Diagnose] Hypertensive Herzkrankheit ohne (kongestive) Herzinsuffizienz (I11.9, ICD-10-GM 2024)

**UND**

> **E3** [Diagnose] Diabetes mellitus, Typ 2: Ohne Komplikationen (E11.9, ICD-10-GM 2024)
> ↳ Diagnosesicherheit: Gesicherte Diagnose (G, KBV_CS_SFHIR_ICD_DIAGNOSESICHERHEIT)

**UND**

> **E4** [Laboruntersuchung] Hämoglobin A1c/Hämoglobin.gesamt in Blut (4548-4, LOINC)
> ↳ Wert: > 7 %
> ↳ Zeitraum (Überschneidung): ab 01.01.2022

**UND**

> **E5** [Medikation] Metformin (A10BA02, ATC 2024)

**UND**

> **E6** [Einwilligung] MDAT wissenschaftlich nutzen EU DSGVO NIVEAU (2.16.840.1.113883.3.1937.777.24.5.3.8, MII-Consent 1.0.7)
> ↳ (Einwilligung)


### Ausschlusskriterien

**Trifft mindestens eine der 2 Bedingungen A1–A2 zu, wird die Person ausgeschlossen** (mit ODER verknüpft).

*Formale Struktur:* `A1 ODER (A2a UND A2b)`  
<sub>Alle 3 Kriterien dieses Abschnitts sind in der formalen Struktur genau einmal referenziert.</sub>

> **A1** [Diagnose] Diabetes mellitus, während der Schwangerschaft auftretend (O24.4, ICD-10-GM 2024) → Ausschluss

**ODER**

> **A2** · Alle folgenden 2 Kriterien (A2a–A2b) gemeinsam → Ausschluss:
> 
> > **A2a** [Prozedur] Hämodialyse (8-854, OPS 2024)
> > 
> > **UND**
> > 
> > **A2b** [Laboruntersuchung] Creatinin [Masse/Volumen] in Serum oder Plasma (2160-0, LOINC)
> > ↳ Wert: 3 bis 15 mg/dL


## Datenextraktion

| Modul / Profil | Filter | Attribute |
|---|---|---|
| Person — Patient | — | Patient.gender<br>Patient.birthDate **(Pflicht)** |
| HbA1c-Laborwerte | code: Hämoglobin A1c/Hämoglobin.gesamt in Blut (4548-4, LOINC) ODER Hämoglobin A1c/Hämoglobin.gesamt in Blut mittels Hochleistungsflüssigkeitschromatografie (HPLC) (17856-6, LOINC)<br>date: 01.01.2022 bis 31.12.2024 | Observation.code<br>Observation.value **(Pflicht)**<br>Observation.encounter → Fall — KontaktGesundheitseinrichtung |
| Fall — KontaktGesundheitseinrichtung (nur als Referenz) | — | Encounter.period<br>Encounter.diagnosis |

> **(Pflicht): Fehlt das Attribut bei einer Person, wird diese vollständig von der Extraktion ausgeschlossen (mustHave-Regel).**

## Kodiersysteme

| Kurzform | System-URI | Version(en) |
|---|---|---|
| ATC | `http://fhir.de/CodeSystem/bfarm/atc` | 2024 |
| FDPG | `fdpg.mii.cds` | 1.0.0 |
| ICD-10-GM | `http://fhir.de/CodeSystem/bfarm/icd-10-gm` | 2024 |
| KBV_CS_SFHIR_ICD_DIAGNOSESICHERHEIT | `https://fhir.kbv.de/CodeSystem/KBV_CS_SFHIR_ICD_DIAGNOSESICHERHEIT` | — |
| LOINC | `http://loinc.org` | — |
| MII-Consent | `urn:oid:2.16.840.1.113883.3.1937.777.24.5.3` | 1.0.7 |
| OPS | `http://fhir.de/CodeSystem/bfarm/ops` | 2024 |
| SNOMED CT | `http://snomed.info/sct` | — |
| mii.abide | `mii.abide` | — |

## Lesehilfe

| Notation | Bedeutung |
|---|---|
| `E1, E2 …` | Einschlussbedingung; alle müssen erfüllt sein |
| `A1, A2 …` | Ausschlussbedingung; eine genügt für den Ausschluss |
| `E2a, E2b …` | Kriterien innerhalb der Bedingung E2 |
| `Name (Code, System Version)` | Bezeichnung, Code und Kodiersystem des Konzepts; die vollständige System-URI steht unter „Kodiersysteme“ |
| `x bis y` | Wertebereich; die CCDL legt nicht fest, ob die Grenzen eingeschlossen sind — hier unverändert wiedergegeben |
| `Einheiten` | dargestellt wird der UCUM-Code aus dem Export, nicht die freie Bezeichnung; Abweichungen zwischen beiden werden am Kriterium vermerkt |
| `Bezeichnungen` | aus der FDPG-Terminologie aufgelöst und können daher von den im Export enthaltenen Bezeichnungen abweichen; Codes und Systeme stammen unverändert aus dem Export |
| `→ Ausschluss` | Zutreffen dieser Bedingung schließt die Person aus |

---
*Für folgende Codes lag keine geprüfte deutsche Bezeichnung vor; angezeigt wird die im Export enthaltene Bezeichnung: `diagnosesicherheit` (mii.abide)*
