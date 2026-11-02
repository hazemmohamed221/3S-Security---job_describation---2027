"""Explicit account roles; JD editing does not grant system administration."""
JD_EDIT_ROLES = frozenset({'admin', 'hr', 'editor'})
USER_ROLES = JD_EDIT_ROLES | {'manager', 'employee'}
ROLE_LABELS = {'employee': 'موظف', 'manager': 'مدير إدارة', 'hr': 'موارد بشرية',
               'editor': 'محرر بطاقات الموارد البشرية', 'admin': 'مسؤول النظام'}
