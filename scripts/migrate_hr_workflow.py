"""Install HR workflow guards without changing any business rows.

SQLite: uses the existing verified-backup integrity migrator.
PostgreSQL: applies transactional DDL to the operator-selected DATABASE_URL.
Run with: python -B -m scripts.migrate_hr_workflow --postgres
"""
import argparse
from contextlib import closing

import governance
from jd_fields import DETAIL_FIELDS


def install_postgres_guards(conn):
    """Supports the schema shipped by migrate_to_supabase; caller owns the transaction."""
    old = 'CASE OLD.status ' + ' '.join(
        f"WHEN '{alias}' THEN '{status}'" for alias, status in governance.STATUS_ALIASES.items()) + ' END'
    new = old.replace('OLD.', 'NEW.')
    dirty = ' OR '.join(f'NEW.{field} IS DISTINCT FROM OLD.{field}' for field in governance.CONTENT_FIELDS)
    with conn.cursor() as cur:
        for name in (*DETAIL_FIELDS, 'edit_batch_token'):
            cur.execute(f'ALTER TABLE public.job_descriptions ADD COLUMN IF NOT EXISTS {name} TEXT')
        cur.execute(f'''
            CREATE SCHEMA IF NOT EXISTS jd_governance;
            REVOKE ALL ON SCHEMA jd_governance FROM PUBLIC;
            ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;
            ALTER TABLE public.users ADD CONSTRAINT users_role_check
                CHECK (role IN ('admin','hr','editor','manager','employee'));

            CREATE OR REPLACE FUNCTION jd_governance.guard_card_revision()
            RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $body$
            BEGIN
                IF NEW.version < OLD.version THEN
                    RAISE EXCEPTION 'Revision cannot decrease' USING ERRCODE = '23514';
                END IF;
                IF NEW.edit_batch_token IS NULL AND ({dirty}) THEN
                    IF NOT (OLD.status IN ('Draft','مسودة') AND NEW.status='مسودة'
                            AND NEW.version=OLD.version+1) THEN
                        NEW.status := 'قيد المراجعة';
                    END IF;
                    NEW.version := OLD.version+1;
                    NEW.review_version := NULL;
                    NEW.review_hash := NULL;
                    NEW.updated_at := CURRENT_TIMESTAMP;
                END IF;
                IF ({new}) IS NULL OR NOT (
                    ({old})=({new}) OR
                    (({old}) IN ('مسودة','مرفوض') AND ({new})='قيد المراجعة') OR
                    (({old})='قيد المراجعة' AND ({new}) IN ('معتمد','مرفوض')) OR
                    (({old})='معتمد' AND ({new})='قيد المراجعة' AND NEW.version>OLD.version) OR
                    (({old})='معتمد' AND ({new})='مسودة' AND NEW.version=OLD.version+1
                        AND NEW.review_version IS NULL AND NEW.review_hash IS NULL)
                ) THEN
                    RAISE EXCEPTION 'Invalid document state transition' USING ERRCODE = '23514';
                END IF;
                RETURN NEW;
            END $body$;
            REVOKE ALL ON FUNCTION jd_governance.guard_card_revision() FROM PUBLIC;
            DROP TRIGGER IF EXISTS hr_card_revision ON public.job_descriptions;
            CREATE TRIGGER hr_card_revision BEFORE UPDATE ON public.job_descriptions
                FOR EACH ROW EXECUTE FUNCTION jd_governance.guard_card_revision();

            CREATE OR REPLACE FUNCTION jd_governance.guard_audit_evidence()
            RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $body$
            BEGIN
                RAISE EXCEPTION 'Audit evidence is immutable' USING ERRCODE = '23514';
            END $body$;
            REVOKE ALL ON FUNCTION jd_governance.guard_audit_evidence() FROM PUBLIC;
            DROP TRIGGER IF EXISTS hr_audit_immutable ON public.jd_audit_trail;
            CREATE TRIGGER hr_audit_immutable BEFORE UPDATE OR DELETE ON public.jd_audit_trail
                FOR EACH ROW EXECUTE FUNCTION jd_governance.guard_audit_evidence();

            CREATE OR REPLACE FUNCTION jd_governance.advance_parent_revision()
            RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $body$
            DECLARE parent_id integer;
            BEGIN
                IF TG_OP='UPDATE' AND NEW.jd_id IS DISTINCT FROM OLD.jd_id THEN
                    RAISE EXCEPTION 'Responsibility parent is immutable' USING ERRCODE = '23514';
                END IF;
                IF TG_OP='DELETE' THEN parent_id := OLD.jd_id; ELSE parent_id := NEW.jd_id; END IF;
                IF TG_OP<>'UPDATE' OR ROW(NEW.description,NEW.kpi,NEW.item_order,NEW.is_active)
                        IS DISTINCT FROM ROW(OLD.description,OLD.kpi,OLD.item_order,OLD.is_active) THEN
                    UPDATE public.job_descriptions SET version=version+1,status='قيد المراجعة',
                        review_version=NULL,review_hash=NULL,updated_at=CURRENT_TIMESTAMP
                        WHERE id=parent_id AND edit_batch_token IS NULL;
                END IF;
                RETURN NULL;
            END $body$;
            REVOKE ALL ON FUNCTION jd_governance.advance_parent_revision() FROM PUBLIC;
            DROP TRIGGER IF EXISTS hr_child_revision ON public.accountabilities;
            CREATE TRIGGER hr_child_revision AFTER INSERT OR UPDATE OR DELETE ON public.accountabilities
                FOR EACH ROW EXECUTE FUNCTION jd_governance.advance_parent_revision();
        ''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--postgres', action='store_true', help='Use DATABASE_URL; no SQLite fallback.')
    args = parser.parse_args()
    if args.postgres:
        import database
        if not database.HAS_PSYCOPG2 or not database.get_database_url():
            parser.error('PostgreSQL driver and DATABASE_URL are required.')
        with closing(database.psycopg2.connect(database.get_database_url(), connect_timeout=15)) as conn, conn:
            install_postgres_guards(conn)
        print('PostgreSQL HR workflow guards installed; business rows unchanged.')
    else:
        from scripts.migrate_integrity import migrate_integrity
        counts, backup = migrate_integrity()
        print(f'SQLite HR workflow guards installed. Verified backup: {backup}')


if __name__ == '__main__':
    main()
