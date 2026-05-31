# Transversal Skill Impact Report

## Scope

This report compares the gap-generation pipeline before and after preserving transversal skills such as communication, teamwork, reporting, cloud tools, data platform tools, and analytical collaboration skills.

## Definition used in this report

- **Skills retained**: market signals preserved as useful curriculum intelligence, including `covered`, `partial`, `missing`, and `emerging`.
- **Skills discarded**: signals classified as `irrelevant`.
- **Gaps generated**: signals surfaced for curriculum action, including `partial`, `missing`, and `emerging`.
- **Recommendations generated**: actionable recommendations emitted by the recommendation engine from the current gap set.

## Before vs after

| Metric | Current pipeline before preserving transversal skills | Pipeline after preserving transversal skills |
|---|---:|---:|
| Market skills reviewed | 49 | 49 |
| Skills retained | 18 | 45 |
| Skills discarded | 31 | 4 |
| Gaps generated | 4 | 31 |
| Recommendations generated | 2 | 12 |

## Interpretation

The earlier pipeline treated most transversal and platform-adjacent skills as `irrelevant`, which suppressed curriculum signals that are clearly useful for academic decision-making.

After the change:

- transversal capabilities such as communication, teamwork, reporting, Agile, and executive reporting are no longer discarded;
- platform skills such as Azure, AWS, PostgreSQL, APIs, SQL, and cloud/data tooling remain visible as actionable curriculum signals;
- the observatory now surfaces a much broader and more realistic gap set;
- the recommendation layer has enough evidence to produce a richer executive action list.

## Skills retained

### Before

- Covered: 14
- Partial: 4
- Missing: 0
- Emerging: 0
- Total retained: 18

### After

- Covered: 14
- Partial: 31
- Missing: 0
- Emerging: 0
- Total retained: 45

## Skills discarded

### Before

- Irrelevant: 31

### After

- Irrelevant: 4

## Top new curriculum gaps after preserving transversal skills

1. comunicacion
2. Azure
3. AWS
4. reporting
5. trabajo en equipo
6. APIs
7. resolucion de problemas
8. Oracle
9. Agile
10. liderazgo
11. ingles
12. PostgreSQL

## Top new recommendations after preserving transversal skills

1. Student recommendation for Visual Analytics y Big Data: APIs, Software/Data Platform
2. Student recommendation for Visual Analytics y Big Data: Azure, Cloud Analytics
3. Student recommendation for Visual Analytics y Big Data: AWS, Cloud Analytics
4. Student recommendation for Visual Analytics y Big Data: reporting, Reporting & KPI
5. Student recommendation for Visual Analytics y Big Data: comunicacion, Enterprise Analytics
6. Student recommendation for Visual Analytics y Big Data: trabajo en equipo, Enterprise Analytics
7. Curriculum recommendation for Especializacion en Visual Analytics y Big Data: comunicacion
8. Curriculum recommendation for Especializacion en Visual Analytics y Big Data: Azure
9. Curriculum recommendation for Especializacion en Visual Analytics y Big Data: AWS
10. Curriculum recommendation for Especializacion en Visual Analytics y Big Data: reporting
11. Curriculum recommendation for Especializacion en Visual Analytics y Big Data: trabajo en equipo
12. Curriculum recommendation for Especializacion en Visual Analytics y Big Data: APIs

## Business effect

The impact is not just a larger number of gaps. The practical effect is that the observatory now keeps the kinds of skills that academic committees actually need to evaluate:

- collaboration and communication
- executive reporting
- cloud and data platform capabilities
- integration and platform tooling
- applied analytics tooling

This makes the curriculum intelligence layer more believable, more complete, and more useful for executive decision-making.

## Notes

- The `program_intelligence` layer may still narrow some signals downstream through its own program-matching logic.
- This report measures the effect of preserving transversal skills in the market-to-curriculum signal layer, which is the main bottleneck the audit identified.
