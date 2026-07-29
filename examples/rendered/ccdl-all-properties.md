# Machbarkeitsanfrage: Example-CCDL

**Quelle:** `ccdl-all-properties.json`  
**Erstellt:** 2026-07-29  
**CCDL-Version:** https://medizininformatik-initiative.de/fdpg/ClinicalCohortDefinitionLanguage/v1/schema

## Kohortendefinition

Eine Person gehört zur Kohorte, wenn **alle Einschlussbedingungen (E1–E4)** erfüllt sind **und** **keine der Ausschlussbedingungen (A1–A3)** zutrifft.

### Einschlusskriterien

**Alle 4 Bedingungen E1–E4 müssen erfüllt sein** (mit UND verknüpft).

*Formale Struktur:* `E1 UND E2 UND (E3a ODER E3b) UND (E4 UND (E4r1a ODER E4r1b))`  
<sub>Alle 7 Kriterien dieses Abschnitts sind in der formalen Struktur genau einmal referenziert.</sub>

> **E1** [Patient] Geschlecht (LL2191-6, LOINC)
> ↳ Wert: Weiblich (F, LOINC) ODER Männlich (M, LOINC)

**UND**

> **E2** [Patient] Alter (30525-0, LOINC)
> ↳ Wert: > 18 Jahr(e)

**UND**

> **E3** · Mindestens eines der folgenden 2 Kriterien (E3a–E3b):
> 
> > **E3a** [Diagnose] F00 (ICD-10-GM)
> > 
> > **ODER**
> > 
> > **E3b** [Diagnose] F09 (ICD-10-GM)
> > ↳ Zeitraum (Überschneidung): von 09.09.2021 bis 09.10.2021

**UND**

> **E4** [Bioprobe] Exzision und Destruktion von erkranktem Gewebe der Schädelknochen: Schädelbasis, Tumorgewebe (5-016.0, OPS 2023)
> 
> > **E4r1** · Referenzbedingung über „specimen diagnosis“ — es muss mindestens eines der folgenden Kriterien dazu vorliegen:
> > 
> > > **E4r1a** [Diagnose] Some cid-o-3 Cancer (C50.0, ICD-O-3)
> > > ↳ status: active (fhir)
> > > 
> > > **ODER**
> > > 
> > > **E4r1b** [Diagnose] Some cid-o-3 Cancer (C50.1, ICD-O-3)


### Ausschlusskriterien

**Trifft mindestens eine der 3 Bedingungen A1–A3 zu, wird die Person ausgeschlossen** (mit ODER verknüpft).

*Formale Struktur:* `A1 ODER A2 ODER (A3a UND A3b)`  
<sub>Alle 4 Kriterien dieses Abschnitts sind in der formalen Struktur genau einmal referenziert.</sub>

> **A1** [Patient] Geschlecht (LL2191-6, LOINC) → Ausschluss
> ↳ Wert: male (ohne System)

**ODER**

> **A2** [Patient] Alter (30525-0, LOINC) → Ausschluss
> ↳ Wert: > 65 year
> ↳ ⚠ Einheit im Export widersprüchlich: UCUM-Code „year“, Bezeichnung „Jahr“ — dargestellt wird der Code.

**ODER**

> **A3** · Alle folgenden 2 Kriterien (A3a–A3b) gemeinsam → Ausschluss:
> 
> > **A3a** [Diagnose] F00.9 (ICD-10-GM)
> > 
> > **UND**
> > 
> > **A3b** [Patient] Körpertemperatur (8310-5, LOINC)
> > ↳ Wert: 35 bis 39 °C
> > ↳ method: Axillary (LA9370-3, LOINC)
> > ↳ Zeitraum (Überschneidung): von 09.09.2021 bis 09.10.2021


## Kodiersysteme

| Kurzform | System-URI | Version(en) |
|---|---|---|
| FDPG | `fdpg.mii.cds` | 1.0.0 |
| ICD-10-GM | `http://fhir.de/CodeSystem/dimdi/icd-10-gm` | — |
| ICD-O-3 | `icd-o-3` | — |
| LOINC ⚠ | `http://loinc.org` | — |
| LOINC ⚠ | `https://fhir.loinc.org/CodeSystem/$lookup?system=http://loinc.org&code=LL2191-6` | — |
| OPS | `http://fhir.de/CodeSystem/bfarm/ops` | 2023 |
| abide | `abide` | — |
| fhir | `http://hl7.org/fhir/` | — |
| mii.abide | `mii.abide` | — |
| ohne System | `(ohne System)` | — |

> ⚠ Diese Kurzform steht im Dokument für mehr als eine System-URI. Die Kriterien nennen nur die Kurzform; maßgeblich ist die URI aus dem Export.

## Lesehilfe

| Notation | Bedeutung |
|---|---|
| `E1, E2 …` | Einschlussbedingung; alle müssen erfüllt sein |
| `A1, A2 …` | Ausschlussbedingung; eine genügt für den Ausschluss |
| `E2a, E2b …` | Kriterien innerhalb der Bedingung E2 |
| `E4r1a …` | Kriterium einer Referenzbedingung von E4 |
| `Name (Code, System Version)` | Bezeichnung, Code und Kodiersystem des Konzepts; die vollständige System-URI steht unter „Kodiersysteme“ |
| `x bis y` | Wertebereich; die CCDL legt nicht fest, ob die Grenzen eingeschlossen sind — hier unverändert wiedergegeben |
| `Einheiten` | dargestellt wird der UCUM-Code aus dem Export, nicht die freie Bezeichnung; Abweichungen zwischen beiden werden am Kriterium vermerkt |
| `Bezeichnungen` | aus der FDPG-Terminologie aufgelöst und können daher von den im Export enthaltenen Bezeichnungen abweichen; Codes und Systeme stammen unverändert aus dem Export |
| `→ Ausschluss` | Zutreffen dieser Bedingung schließt die Person aus |

---
*Für folgende Codes lag keine geprüfte deutsche Bezeichnung vor; angezeigt wird die im Export enthaltene Bezeichnung: `diagnose` (mii.abide), `C50.0` (ICD-O-3), `status` (mii.abide), `active` (fhir), `C50.1` (ICD-O-3), `male` (ohne System), `method` (abide)*
