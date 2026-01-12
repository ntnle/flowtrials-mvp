"""
Normalization functions for ClinicalTrials.gov API v2 responses
Maps raw CT.gov JSON to our internal StudyCreate schema
"""
import json
from typing import Dict, Any, List, Optional
from main import StudyCreate, Intervention, Location, Contact


def safe_get(data: Dict, *keys, default=None):
    """Safely navigate nested dict"""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, {})
        else:
            return default
    return data if data != {} else default


def normalize_ctgov_study(raw_study: Dict[str, Any]) -> StudyCreate:
    """
    Normalize a single CT.gov study to our StudyCreate model

    Args:
        raw_study: Raw study object from CT.gov API

    Returns:
        StudyCreate instance
    """
    protocol = raw_study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    description_mod = protocol.get("descriptionModule", {})
    eligibility_mod = protocol.get("eligibilityModule", {})
    status_mod = protocol.get("statusModule", {})
    design_mod = protocol.get("designModule", {})
    conditions_mod = protocol.get("conditionsModule", {})
    arms_interventions_mod = protocol.get("armsInterventionsModule", {})
    contacts_locations_mod = protocol.get("contactsLocationsModule", {})

    # NCT ID
    nct_id = identification.get("nctId", "")

    # Title
    title = identification.get("officialTitle") or identification.get("briefTitle", "Untitled Study")

    # Descriptions
    brief_summary = safe_get(description_mod, "briefSummary", default="")
    detailed_description = safe_get(description_mod, "detailedDescription", default="")

    # Eligibility
    eligibility_criteria = safe_get(eligibility_mod, "eligibilityCriteria", default="")

    # Status
    recruiting_status = safe_get(status_mod, "overallStatus", default="Unknown")

    # Study type
    study_type = safe_get(design_mod, "studyType", default="")

    # Conditions
    conditions = conditions_mod.get("conditions", [])
    conditions_normalized = [c.lower().replace(" ", "-") for c in conditions]

    # Interventions
    interventions_raw = arms_interventions_mod.get("interventions", [])
    interventions = []
    for intv in interventions_raw:
        interventions.append(Intervention(
            intervention_type=intv.get("type"),
            intervention_name=intv.get("name", "Unknown"),
            description=intv.get("description")
        ))

    # Locations
    locations_raw = contacts_locations_mod.get("locations", [])
    locations = []
    for loc in locations_raw:
        facility = loc.get("facility", "")
        city = loc.get("city", "")
        state = loc.get("state", "")
        country = loc.get("country", "")
        geo = loc.get("geoPoint", {})

        locations.append(Location(
            facility_name=facility,
            city=city,
            state=state,
            country=country,
            lat=geo.get("lat") if geo else None,
            lon=geo.get("lon") if geo else None
        ))

    # Contacts
    central_contacts_raw = contacts_locations_mod.get("centralContacts", [])
    contacts = []
    for contact in central_contacts_raw:
        contacts.append(Contact(
            name=contact.get("name", "Unknown"),
            role=contact.get("role"),
            phone=contact.get("phone"),
            email=contact.get("email")
        ))

    # Site zips (we don't have this in CT.gov, so empty for now)
    site_zips = []

    # Raw JSON
    raw_json = json.dumps(raw_study)

    return StudyCreate(
        source="ctgov",
        source_id=nct_id,
        title=title,
        brief_summary=brief_summary,
        detailed_description=detailed_description,
        eligibility_criteria=eligibility_criteria,
        recruiting_status=recruiting_status,
        study_type=study_type,
        interventions=interventions,
        conditions=conditions_normalized,
        locations=locations,
        contacts=contacts,
        site_zips=site_zips,
        raw_json=raw_json
    )
