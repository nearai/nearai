from hub.api.v1.models import OrgMember, RegistryEntry


def check_org_access(org_name: str, user_id: str) -> bool:
    # Direct access to the org
    if OrgMember.exists(org_name, user_id):
        return True

    # Indirect access through the author
    entry = RegistryEntry.find_by_org_and_author(org_name, user_id)
    return entry is not None
