"""Transplant module permissions (DRF permission classes)."""
from apps.accounts.permissions import HasCapability


# Convenience aliases used by transplant views.
CanViewTransplant = HasCapability('transplant.view')
CanManageTransplant = HasCapability('transplant.manage')
CanReferTransplant = HasCapability('transplant.refer')
CanCommitteeDecide = HasCapability('transplant.committee_decide')
CanRecordSurgery = HasCapability('transplant.record_surgery')
CanViewFollowUp = HasCapability('transplant.view_followup')
CanManageFollowUp = HasCapability('transplant.manage_followup')
