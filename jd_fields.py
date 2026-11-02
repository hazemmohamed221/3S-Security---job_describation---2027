"""Additive JD detail fields and the public full-editor field allowlist."""
DETAIL_FIELDS = {
    'subordinates': 'الوظائف التابعة / المرؤوسون',
    'job_grade': 'المستوى / الدرجة الوظيفية',
    'working_conditions': 'ظروف وبيئة العمل',
    'education': 'المؤهل العلمي',
    'experience': 'سنوات ونوع الخبرة',
    'certifications': 'الشهادات المهنية والدورات',
    'languages': 'اللغات المطلوبة',
    'skills': 'المهارات المطلوبة',
}
EDIT_GROUPS = (
    ('البيانات العامة والهيكل التنظيمي', (
        ('title', 'المسمى الوظيفي'), ('job_code', 'كود الوظيفة'),
        ('department', 'الإدارة'), ('sector', 'القطاع'), ('reports_to', 'الرئيس المباشر'),
        ('subordinates', DETAIL_FIELDS['subordinates']), ('job_grade', DETAIL_FIELDS['job_grade']),
        ('dimensions', 'أبعاد الوظيفة والنطاق الإشرافي'),
        ('approvals', 'بيانات الاعتماد في المصدر (لا تمنح اعتماداً إلكترونياً)'),
    )),
    ('الهدف وشروط التأهيل والخبرة', (
        ('purpose', 'الهدف العام من الوظيفة'), ('working_conditions', DETAIL_FIELDS['working_conditions']),
        ('education', DETAIL_FIELDS['education']), ('experience', DETAIL_FIELDS['experience']),
        ('certifications', DETAIL_FIELDS['certifications']), ('languages', DETAIL_FIELDS['languages']),
        ('qualifications', 'المؤهلات والخبرات المجمعة في المصدر'),
        ('hazards', 'مخاطر الوظيفة'), ('safe_practices', 'ممارسات السلامة والصحة المهنية'),
    )),
    ('المهام والمسؤوليات', (('frameworks', 'إطار العمل وحدود اتخاذ القرارات'),)),
    ('الجدارات والكفاءات', (
        ('skills', DETAIL_FIELDS['skills']), ('competencies', 'الجدارات الفنية والسلوكية ومعاييرها'),
        ('internal_relations', 'العلاقات الداخلية'), ('external_relations', 'العلاقات الخارجية'),
    )),
)
EDIT_FIELDS = {name: label for _, fields in EDIT_GROUPS for name, label in fields}
FIELD_ALIASES = {'job_title': 'title', 'direct_manager': 'reports_to', 'job_purpose': 'purpose'}
