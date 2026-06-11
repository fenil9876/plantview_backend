"""Application roles used for RBAC."""
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"        # builds templates, manages users
    OPERATOR = "operator"  # feeds operational data
    VIEWER = "viewer"      # read-only / dashboards


ALL_ROLES = [r.value for r in Role]
