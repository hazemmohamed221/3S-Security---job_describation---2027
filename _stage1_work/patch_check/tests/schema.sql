CREATE TABLE accountabilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER NOT NULL,
        item_order INTEGER NOT NULL,
        description TEXT NOT NULL,
        kpi TEXT,
        version INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (jd_id) REFERENCES job_descriptions (id) ON DELETE CASCADE
    );

CREATE TABLE interview_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seq_num INTEGER,
        department TEXT NOT NULL,
        manager_name TEXT NOT NULL,
        day_date TEXT,
        meeting_time TEXT,
        discussion_topics TEXT,
        status TEXT DEFAULT 'قيد المراجعة',
        notes TEXT
    );

CREATE TABLE jd_audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER NOT NULL,
        mod_request_id INTEGER,
        section_name TEXT,
        action TEXT NOT NULL, -- 'Initial Import', 'Modification Accepted', 'Approved As Is', 'Direct Update'
        old_text TEXT,
        new_text TEXT,
        changed_by TEXT NOT NULL,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (jd_id) REFERENCES job_descriptions (id) ON DELETE CASCADE
    );

CREATE TABLE job_descriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_code TEXT,
        title TEXT NOT NULL,
        department TEXT,
        sector TEXT,
        reports_to TEXT,
        purpose TEXT,
        dimensions TEXT,
        frameworks TEXT,
        qualifications TEXT,
        competencies TEXT,
        hazards TEXT,
        safe_practices TEXT,
        internal_relations TEXT,
        external_relations TEXT,
        approvals TEXT,
        source_file TEXT,
        status TEXT DEFAULT 'Under Review', -- 'Draft', 'Under Review', 'Approved'
        version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE TABLE modification_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER NOT NULL,
        section_name TEXT NOT NULL,
        clause_id TEXT, -- e.g. accountability ID or field name
        original_text TEXT,
        proposed_text TEXT NOT NULL,
        justification TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Pending', -- 'Pending', 'Accepted', 'Rejected'
        reviewer_comments TEXT,
        reviewed_by TEXT,
        reviewed_at TIMESTAMP,
        FOREIGN KEY (jd_id) REFERENCES job_descriptions (id) ON DELETE CASCADE
    );

CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL, -- 'admin', 'manager', 'employee'
        department TEXT,
        assigned_jd_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
