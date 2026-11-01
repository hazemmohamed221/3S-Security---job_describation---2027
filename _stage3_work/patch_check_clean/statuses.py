"""Workflow domains: canonical Arabic values with explicit legacy compatibility."""
from enum import StrEnum


class WorkflowStatus(StrEnum):
    @classmethod
    def parse(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise ValueError('حالة سير العمل غير صالحة.')
        canonical = ALIASES[cls].get(value, value)
        try:
            return cls(canonical)
        except ValueError as exc:
            raise ValueError('حالة سير العمل غير صالحة.') from exc


class CardStatus(WorkflowStatus):
    DRAFT = 'مسودة'
    PENDING_REVIEW = 'قيد المراجعة'
    APPROVED = 'معتمد'
    REJECTED = 'مرفوض'


class ReviewStatus(WorkflowStatus):
    PENDING = 'قيد الانتظار'
    ACCEPTED = 'مقبول'
    REJECTED = 'مرفوض'


class InterviewStatus(WorkflowStatus):
    PENDING_REVIEW = 'قيد المراجعة'
    COMPLETED = 'مكتملة'
    POSTPONED = 'مؤجلة'
    NOT_STARTED = 'لم تبدأ'


ALIASES = {
    CardStatus: dict(zip(('Draft', 'Under Review', 'Pending Review', 'Approved', 'Rejected'),
                        (CardStatus.DRAFT, CardStatus.PENDING_REVIEW, CardStatus.PENDING_REVIEW,
                         CardStatus.APPROVED, CardStatus.REJECTED))),
    ReviewStatus: {'Pending': ReviewStatus.PENDING, 'Accept': ReviewStatus.ACCEPTED,
                   'Accepted': ReviewStatus.ACCEPTED, 'Reject': ReviewStatus.REJECTED,
                   'Rejected': ReviewStatus.REJECTED},
    InterviewStatus: {'Under Review': InterviewStatus.PENDING_REVIEW,
                      'Pending Review': InterviewStatus.PENDING_REVIEW,
                      'Completed': InterviewStatus.COMPLETED, 'Postponed': InterviewStatus.POSTPONED,
                      'Not Started': InterviewStatus.NOT_STARTED},
}
for domain, values in ALIASES.items():
    values.update({member.value: member for member in domain})


def display_status(domain, value):
    """Known legacy values display consistently; unknown history is retained."""
    try:
        return domain.parse(value).value
    except ValueError:
        return value


def install_constraints(conn):
    """Guard future writes without rewriting immutable/historical legacy rows."""
    for table, domain in (('job_descriptions', CardStatus), ('modification_requests', ReviewStatus),
                          ('interview_schedule', InterviewStatus)):
        allowed = ','.join("'" + v.replace("'", "''") + "'" for v in ALIASES[domain])
        for action in ('INSERT', 'UPDATE OF status'):
            suffix = 'insert' if action == 'INSERT' else 'update'
            changed = '' if suffix == 'insert' else 'NEW.status IS NOT OLD.status AND '
            conn.execute(f"""CREATE TRIGGER IF NOT EXISTS stage3_{table}_status_{suffix}
                BEFORE {action} ON {table}
                WHEN {changed}(NEW.status IS NULL OR NEW.status NOT IN ({allowed}))
                BEGIN SELECT RAISE(ABORT,'Invalid workflow status'); END""")
