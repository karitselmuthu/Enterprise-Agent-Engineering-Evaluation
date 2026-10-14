# Data volume and schema audit

Verified against committed project data on 2026-10-14. These are suggested
initial volumes from the project brief, not current completion criteria.

| Dataset | Suggested volume | Current committed data | Field check | Target met? |
| --- | ---: | ---: | --- | --- |
| Infrastructure inventory | 50 servers | 0 standalone records; 20 distinct server IDs embedded in scenarios | No inventory records with explicit environment, application, and region | No |
| Infrastructure metrics | 10,000 records | 80 replay samples | CPU, memory, disk, network, and UTC timestamp present | No |
| Application logs | 20,000 records | 82 replay entries | Timestamp, severity, and message present; service inherited from scenario | No |
| Incident records | 500 incidents | 20 simulated alerts, plus 1 separate unit-test fixture | Simulated alerts have ID, service, and severity; status comes from timeline | No |
| Knowledge-base documents | 50 documents | 5 Markdown runbooks with 10 sections total | Runbook text is present | No |

The 20 simulated alerts are separate scenario cases. Nineteen cases have four
events and the payment case has eight; events do not create distinct incidents.
The embedded server IDs do not constitute a standalone inventory. The `INC-001` fixture remains separate from
the simulation corpus and is not added to its alert count.

Re-run the audit from the repository root:

```sh
python3 -m scripts.audit_data
```

The audit counts committed files and nested replay observations. It does not
measure data realism or model quality. Increasing volume should preserve links
among server, service, incident, and time; the missing standalone inventory
should be added before using these corpora as a
bulk enterprise data benchmark.
