# Coordinated Vulnerability Disclosure Memo

**Date**: {{ date }}
**From**: {{ researcher_name }}
**To**: {{ recipient_name }}
**Subject**: Security Vulnerability Report — {{ finding_id }}

---

## Classification

| Field | Value |
|-------|-------|
| **Finding ID** | {{ finding_id }} |
| **Severity** | {{ severity }} |
| **Device Type** | {{ device_type }} |
| **Manufacturer** | {{ manufacturer }} |
| **Affected System** | {{ affected_system }} |
| **Location** | {{ location_description }} |
| **Discovery Date** | {{ discovery_date }} |
| **Disclosure Deadline** | {{ disclosure_deadline }} (90 days from discovery) |

---

## Executive Summary

{{ summary }}

---

## Vulnerability Details

**Description**: {{ description }}

**Impact**: {{ impact }}

**CVSS Score** (if applicable): {{ cvss_score }}

**CVE Reference** (if known): {{ cve_reference }}

---

## Evidence

{{ evidence }}

*Note: All evidence has been collected through authorized testing or passive observation. No data was exfiltrated, and testing ceased immediately upon confirming the vulnerability.*

---

## Reproduction Steps

{{ reproduction_steps }}

---

## Recommended Remediation

{{ remediation }}

**Urgency**: {{ urgency }}

**Estimated Remediation Effort**: {{ remediation_effort }}

---

## Disclosure Timeline

| Date | Action |
|------|--------|
| {{ discovery_date }} | Vulnerability discovered |
| {{ report_date }} | This report sent to {{ recipient_name }} |
| {{ followup_date_30 }} | 30-day follow-up if no response |
| {{ followup_date_60 }} | 60-day follow-up if no remediation |
| {{ disclosure_deadline }} | 90-day public disclosure deadline |

If no response is received within 30 days, this report will be escalated to:
1. {{ escalation_contact_1 }}
2. CISA (Cybersecurity and Infrastructure Security Agency)
3. EFF (Electronic Frontier Foundation)

---

## Researcher Information

**Name**: {{ researcher_name }}
**Contact**: {{ researcher_contact }}
**Affiliation**: Independent security researcher
**Authorization**: {{ authorization_basis }}

This report follows the Coordinated Vulnerability Disclosure (CVD) process as outlined by CERT/CC and the DOJ Good-Faith Security Research Policy. The researcher acted in good faith with the sole purpose of improving the security posture of public safety infrastructure.

---

*This document is confidential and intended solely for the recipient. It contains information about a security vulnerability that, if exploited, could compromise public safety systems. Please handle accordingly.*
