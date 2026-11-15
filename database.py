"""
SQLite Database Storage for AgriNext.
Provides persistent storage for farm boundaries, acreage declarations,
NASA POWER cache records, and environmental evidence objects.
"""

import sqlite3
import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env.local")
DB_PATH = Path(os.getenv("AGRINEXT_DB_PATH", str(Path(__file__).resolve().parent / "agrinext.db"))).expanduser()

def get_connection() -> sqlite3.Connection:
    """Open the configured SQLite database, creating its parent directory if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # SQLite disables FK enforcement by default; enable it for every connection.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes SQLite schema for farm profiles, NASA cache, and evidence."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Authentication tables. Passwords are stored only as PBKDF2 hashes.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'farmer',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")

        # 1. Farm Profiles Table (with Village & LGD Hierarchy)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT,
                farm_name TEXT NOT NULL,
                state_id TEXT NOT NULL,
                district_id TEXT NOT NULL,
                mandal_id TEXT NOT NULL,
                village_id TEXT,
                village_name TEXT,
                village_lgd INTEGER,
                district_lgd INTEGER,
                mandal_lgd INTEGER,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                polygon_acreage REAL NOT NULL,
                manual_acreage REAL,
                effective_acreage REAL NOT NULL,
                acreage_discrepancy_warning TEXT,
                boundary_geojson TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Database Schema Migration for existing databases
        cursor.execute("PRAGMA table_info(farms)")
        existing_cols = {col[1] for col in cursor.fetchall()}
        for col_name, col_type in [
            ("owner_user_id", "TEXT"),
            ("village_id", "TEXT"),
            ("village_name", "TEXT"),
            ("village_lgd", "INTEGER"),
            ("district_lgd", "INTEGER"),
            ("mandal_lgd", "INTEGER")
        ]:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE farms ADD COLUMN {col_name} {col_type}")

        # 2. NASA POWER Query Cache Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nasa_power_cache (
                cache_key TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                parameters TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 3. NASA SMAP Soil Moisture Cache Table (SPL3SMP_E V006)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nasa_smap_cache (
                cache_key TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                product_version TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 4. NASA GPM IMERG Precipitation Cache Table (V07 Final Run)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nasa_gpm_cache (
                cache_key TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                product_version TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 5. Environmental Evidence Objects Table (linked to farm)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farm_environmental_evidence (
                id TEXT PRIMARY KEY,
                farm_id TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                dataset_name TEXT NOT NULL,
                parameter_name TEXT NOT NULL,
                unit TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 6. Farmer Profiles Table (Ground-Truth Soil, Crop History, & Irrigation)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmer_profiles (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT,
                farm_id TEXT,
                soil_type TEXT NOT NULL,
                soil_source_type TEXT NOT NULL,
                soil_source_reference TEXT,
                soil_ph REAL,
                nitrogen_value REAL,
                nitrogen_rating TEXT,
                phosphorus_value REAL,
                phosphorus_rating TEXT,
                potassium_value REAL,
                potassium_rating TEXT,
                organic_carbon_pct REAL,
                organic_carbon_rating TEXT,
                current_crop TEXT,
                previous_crops_json TEXT,
                available_crops_json TEXT,
                irrigation_source TEXT NOT NULL,
                farming_season TEXT NOT NULL,
                preferred_crops_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("PRAGMA table_info(farmer_profiles)")
        profile_cols = {col[1] for col in cursor.fetchall()}
        if "owner_user_id" not in profile_cols:
            cursor.execute("ALTER TABLE farmer_profiles ADD COLUMN owner_user_id TEXT")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_farms_owner_user_id ON farms(owner_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_owner_user_id ON farmer_profiles(owner_user_id)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS soil_reports (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT NOT NULL,
                farm_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                extraction_status TEXT NOT NULL,
                extracted_metrics_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_soil_reports_owner_farm ON soil_reports(owner_user_id, farm_id)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farm_alerts (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT NOT NULL,
                farm_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                observed_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                unit TEXT NOT NULL,
                source TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                acknowledged_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(owner_user_id) REFERENCES users(id),
                FOREIGN KEY(farm_id) REFERENCES farms(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_farm_alerts_owner_created ON farm_alerts(owner_user_id, created_at DESC)")
        cursor.execute("""CREATE TABLE IF NOT EXISTS crop_rotation_records (
            id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, farm_id TEXT NOT NULL,
            crop_name TEXT NOT NULL, season TEXT NOT NULL, crop_year INTEGER NOT NULL,
            planting_date TEXT, harvest_date TEXT, yield_value REAL, yield_unit TEXT,
            notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users(id), FOREIGN KEY(farm_id) REFERENCES farms(id)
        )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rotation_owner_farm ON crop_rotation_records(owner_user_id, farm_id, crop_year DESC)")
        cursor.execute("""CREATE TABLE IF NOT EXISTS farm_activity_log (
            id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, farm_id TEXT NOT NULL,
            activity_type TEXT NOT NULL, description TEXT NOT NULL, metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL, FOREIGN KEY(owner_user_id) REFERENCES users(id),
            FOREIGN KEY(farm_id) REFERENCES farms(id)
        )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_owner_farm ON farm_activity_log(owner_user_id, farm_id, created_at DESC)")
        # Persistent lifecycle records for long-running NASA retrievals.
        cursor.execute("""CREATE TABLE IF NOT EXISTS nasa_jobs (
            id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            request_json TEXT NOT NULL,
            result_json TEXT,
            error_message TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nasa_jobs_owner_created ON nasa_jobs(owner_user_id, created_at DESC)")
        conn.commit()


# --- Persistent NASA Job Operations ---

def create_nasa_job(job_id: str, owner_user_id: str, job_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO nasa_jobs (id, owner_user_id, job_type, status, request_json, created_at, updated_at) VALUES (?, ?, ?, 'queued', ?, ?, ?)",
            (job_id, owner_user_id, job_type, json.dumps(request_data), now, now)
        )
        conn.commit()
    return get_nasa_job(job_id, owner_user_id)  # type: ignore

def update_nasa_job(job_id: str, status: str, *, result: Optional[Dict[str, Any]] = None,
                    error_message: Optional[str] = None, increment_attempts: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute("""UPDATE nasa_jobs SET status = ?, result_json = COALESCE(?, result_json),
            error_message = ?, attempts = attempts + ?,
            started_at = CASE WHEN ? = 'running' AND started_at IS NULL THEN ? ELSE started_at END,
            completed_at = CASE WHEN ? IN ('succeeded','failed','cancelled') THEN ? ELSE completed_at END,
            updated_at = ? WHERE id = ?""",
            (status, json.dumps(result) if result is not None else None, error_message,
             1 if increment_attempts else 0, status, now, status, now, now, job_id))
        conn.commit()

def get_nasa_job(job_id: str, owner_user_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM nasa_jobs WHERE id = ? AND owner_user_id = ?", (job_id, owner_user_id)).fetchone()
    if not row:
        return None
    item = dict(row)
    item['request'] = json.loads(item.pop('request_json'))
    item['result'] = json.loads(item.pop('result_json')) if item.get('result_json') else None
    item.pop('result_json', None)
    return item

def count_active_nasa_jobs(owner_user_id: Optional[str] = None) -> int:
    init_db()
    with get_connection() as conn:
        if owner_user_id:
            row = conn.execute("SELECT COUNT(*) AS total FROM nasa_jobs WHERE owner_user_id=? AND status IN ('queued','running')", (owner_user_id,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS total FROM nasa_jobs WHERE status IN ('queued','running')").fetchone()
        return int(row['total']) if row else 0

def claim_queued_nasa_job(job_id: str, owner_user_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute("UPDATE nasa_jobs SET status='running', started_at=COALESCE(started_at, ?), attempts=attempts+1, updated_at=? WHERE id=? AND owner_user_id=? AND status='queued'",
                           (now, now, job_id, owner_user_id))
        conn.commit()
        return cur.rowcount == 1

def cancel_queued_nasa_job(job_id: str, owner_user_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute("UPDATE nasa_jobs SET status='cancelled', completed_at=?, updated_at=? WHERE id=? AND owner_user_id=? AND status='queued'",
                           (now, now, job_id, owner_user_id))
        conn.commit()
        return cur.rowcount == 1

def cleanup_old_nasa_jobs(retention_days: int = 30) -> int:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))).isoformat()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM nasa_jobs WHERE status IN ('succeeded','failed','cancelled') AND completed_at < ?", (cutoff,))
        conn.commit()
        return cur.rowcount

def recover_interrupted_nasa_jobs() -> int:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute("UPDATE nasa_jobs SET status='failed', error_message='Job interrupted by server restart; please submit it again.', completed_at=?, updated_at=? WHERE status IN ('queued','running')", (now, now))
        conn.commit()
        return cur.rowcount


# --- Authentication Operations ---

def create_user(user_id: str, full_name: str, email: str, password_hash: str) -> Dict[str, Any]:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (id, full_name, email, password_hash, role, is_active, created_at) VALUES (?, ?, ?, ?, 'farmer', 1, ?)",
            (user_id, full_name.strip(), email.strip().lower(), password_hash, now)
        )
        conn.commit()
    return get_user_by_id(user_id)  # type: ignore

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)).fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT id, full_name, email, role, is_active, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

def create_session(session_id: str, user_id: str, token_hash: str, expires_at: str) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute("INSERT INTO user_sessions (id, user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?, ?)", (session_id, user_id, token_hash, expires_at, now))
        conn.commit()

def get_user_by_session_hash(token_hash: str) -> Optional[Dict[str, Any]]:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT u.id, u.full_name, u.email, u.role, u.is_active, u.created_at FROM users u JOIN user_sessions s ON s.user_id = u.id WHERE s.token_hash = ? AND s.expires_at > ? AND u.is_active = 1",
            (token_hash, now)
        ).fetchone()
        return dict(row) if row else None

def revoke_session(token_hash: str) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM user_sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()

# --- Farm Operations ---

def save_farm(farm_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update a farm profile in SQLite."""
    init_db()
    farm_id = farm_data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    created_at = farm_data.get("created_at") or now
    updated_at = now

    boundary_json = json.dumps(farm_data.get("boundary_geojson", {}))

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO farms (
                id, owner_user_id, farm_name, state_id, district_id, mandal_id,
                village_id, village_name, village_lgd, district_lgd, mandal_lgd,
                latitude, longitude, polygon_acreage, manual_acreage,
                effective_acreage, acreage_discrepancy_warning,
                boundary_geojson, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            farm_id,
            farm_data.get("owner_user_id"),
            farm_data.get("farm_name", "My Farm Plot"),
            farm_data.get("state_id", "andhra_pradesh"),
            farm_data.get("district_id", ""),
            farm_data.get("mandal_id", ""),
            farm_data.get("village_id"),
            farm_data.get("village_name"),
            int(farm_data["village_lgd"]) if farm_data.get("village_lgd") is not None else None,
            int(farm_data["district_lgd"]) if farm_data.get("district_lgd") is not None else None,
            int(farm_data["mandal_lgd"]) if farm_data.get("mandal_lgd") is not None else None,
            float(farm_data.get("latitude", 0.0)),
            float(farm_data.get("longitude", 0.0)),
            float(farm_data.get("polygon_acreage", 0.0)),
            float(farm_data.get("manual_acreage")) if farm_data.get("manual_acreage") is not None else None,
            float(farm_data.get("effective_acreage", farm_data.get("polygon_acreage", 0.0))),
            farm_data.get("acreage_discrepancy_warning"),
            boundary_json,
            created_at,
            updated_at
        ))
        conn.commit()

    return get_farm_by_id(farm_id) # type: ignore

def get_farms(owner_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve farms; API callers must supply an authenticated owner ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if owner_user_id is None:
            cursor.execute("SELECT * FROM farms ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM farms WHERE owner_user_id = ? ORDER BY created_at DESC", (owner_user_id,))
        rows = cursor.fetchall()
        farms = []
        for row in rows:
            f = dict(row)
            f["boundary_geojson"] = json.loads(f["boundary_geojson"])
            farms.append(f)
        return farms

def get_farm_by_id(farm_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single farm profile by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
        row = cursor.fetchone()
        if not row:
            return None
        f = dict(row)
        f["boundary_geojson"] = json.loads(f["boundary_geojson"])
        return f

def delete_farm(farm_id: str) -> bool:
    """Delete a farm and all farm-owned records atomically."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM farms WHERE id = ?", (farm_id,))
        if cursor.fetchone() is None:
            return False
        # Delete children explicitly so this also works with legacy schemas that
        # were created before foreign-key constraints/cascades were introduced.
        for table in (
            "crop_rotation_records",
            "farm_alerts",
            "farmer_profiles",
            "soil_reports",
            "farm_environmental_evidence",
            "farm_activity_log",
        ):
            cursor.execute(f"DELETE FROM {table} WHERE farm_id = ?", (farm_id,))
        cursor.execute("DELETE FROM farms WHERE id = ?", (farm_id,))
        return cursor.rowcount > 0

# --- NASA POWER Cache Operations ---

def get_cached_power_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached NASA POWER API response if available."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT response_json, created_at FROM nasa_power_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        if not row:
            return None
        payload = json.loads(row["response_json"])
        payload["_cache_hit"] = True
        payload["_cached_at"] = row["created_at"]
        return payload

def save_cached_power_data(
    cache_key: str,
    lat: float,
    lng: float,
    start_date: str,
    end_date: str,
    parameters: str,
    response_data: Dict[str, Any]
):
    """Store NASA POWER API response into persistent cache."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO nasa_power_cache (
                cache_key, latitude, longitude, start_date, end_date,
                parameters, response_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            lat,
            lng,
            start_date,
            end_date,
            parameters,
            json.dumps(response_data),
            now
        ))
        conn.commit()

# --- NASA SMAP Cache Operations ---

def get_cached_smap_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached NASA SMAP response if available."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT response_json, created_at FROM nasa_smap_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        if not row:
            return None
        payload = json.loads(row["response_json"])
        payload["_cache_hit"] = True
        payload["_cached_at"] = row["created_at"]
        return payload

def save_cached_smap_data(
    cache_key: str,
    lat: float,
    lng: float,
    start_date: str,
    end_date: str,
    product_version: str,
    response_data: Dict[str, Any]
):
    """Store NASA SMAP response into persistent cache."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO nasa_smap_cache (
                cache_key, latitude, longitude, start_date, end_date,
                product_version, response_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            lat,
            lng,
            start_date,
            end_date,
            product_version,
            json.dumps(response_data),
            now
        ))
        conn.commit()

# --- NASA GPM Cache Operations ---

def get_cached_gpm_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached NASA GPM IMERG response if available."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT response_json, created_at FROM nasa_gpm_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        if not row:
            return None
        payload = json.loads(row["response_json"])
        payload["_cache_hit"] = True
        payload["_cached_at"] = row["created_at"]
        return payload

def save_cached_gpm_data(
    cache_key: str,
    lat: float,
    lng: float,
    start_date: str,
    end_date: str,
    product_version: str,
    response_data: Dict[str, Any]
):
    """Store NASA GPM IMERG response into persistent cache."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO nasa_gpm_cache (
                cache_key, latitude, longitude, start_date, end_date,
                product_version, response_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            lat,
            lng,
            start_date,
            end_date,
            product_version,
            json.dumps(response_data),
            now
        ))
        conn.commit()

# --- Environmental Evidence Operations ---

def save_farm_evidence(
    farm_id: Optional[str],
    lat: float,
    lng: float,
    evidence_list: List[Dict[str, Any]]
):
    """Persist environmental evidence objects for decision support provenance."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        for ev in evidence_list:
            ev_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO farm_environmental_evidence (
                    id, farm_id, latitude, longitude, dataset_name,
                    parameter_name, unit, evidence_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ev_id,
                farm_id,
                lat,
                lng,
                ev.get("dataset_name", "NASA POWER"),
                ev.get("parameter_name", ""),
                ev.get("unit", ""),
                json.dumps(ev),
                now
            ))
        conn.commit()


# --- Farmer Profile Operations ---

def save_farmer_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update a farmer profile in SQLite."""
    init_db()
    profile_id = profile_data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    created_at = profile_data.get("created_at") or now
    updated_at = now

    prev_crops_json = json.dumps(profile_data.get("previous_crops", []))
    avail_crops_json = json.dumps(profile_data.get("available_crops", []))
    pref_crops_json = json.dumps(profile_data.get("preferred_crops", []))

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO farmer_profiles (
                id, owner_user_id, farm_id, soil_type, soil_source_type, soil_source_reference,
                soil_ph, nitrogen_value, nitrogen_rating, phosphorus_value, phosphorus_rating,
                potassium_value, potassium_rating, organic_carbon_pct, organic_carbon_rating,
                current_crop, previous_crops_json, available_crops_json,
                irrigation_source, farming_season, preferred_crops_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            profile_data.get("owner_user_id"),
            profile_data.get("farm_id"),
            profile_data.get("soil_type", "Red Sandy Loam"),
            profile_data.get("soil_source_type", "farmer_measured"),
            profile_data.get("soil_source_reference"),
            float(profile_data.get("soil_ph")) if profile_data.get("soil_ph") is not None else None,
            float(profile_data.get("nitrogen_value")) if profile_data.get("nitrogen_value") is not None else None,
            profile_data.get("nitrogen_rating"),
            float(profile_data.get("phosphorus_value")) if profile_data.get("phosphorus_value") is not None else None,
            profile_data.get("phosphorus_rating"),
            float(profile_data.get("potassium_value")) if profile_data.get("potassium_value") is not None else None,
            profile_data.get("potassium_rating"),
            float(profile_data.get("organic_carbon_pct")) if profile_data.get("organic_carbon_pct") is not None else None,
            profile_data.get("organic_carbon_rating"),
            profile_data.get("current_crop"),
            prev_crops_json,
            avail_crops_json,
            profile_data.get("irrigation_source", "Rainfed"),
            profile_data.get("farming_season", "Kharif"),
            pref_crops_json,
            created_at,
            updated_at
        ))
        conn.commit()

    return get_farmer_profile_by_id(profile_id) # type: ignore

def get_farmer_profile_by_id(profile_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a farmer profile by profile ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM farmer_profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        if not row:
            return None
        p = dict(row)
        p["previous_crops"] = json.loads(p.get("previous_crops_json") or "[]")
        p["available_crops"] = json.loads(p.get("available_crops_json") or "[]")
        p["preferred_crops"] = json.loads(p.get("preferred_crops_json") or "[]")
        return p

def get_farmer_profile_by_farm_id(farm_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve farmer profile associated with a farm ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM farmer_profiles WHERE farm_id = ? ORDER BY updated_at DESC LIMIT 1", (farm_id,))
        row = cursor.fetchone()
        if not row:
            return None
        p = dict(row)
        p["previous_crops"] = json.loads(p.get("previous_crops_json") or "[]")
        p["available_crops"] = json.loads(p.get("available_crops_json") or "[]")
        p["preferred_crops"] = json.loads(p.get("preferred_crops_json") or "[]")
        return p


# --- Soil Health Report Documents ---
def save_soil_report(report: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    with get_connection() as conn:
        conn.execute("""INSERT INTO soil_reports (id, owner_user_id, farm_id, original_filename, stored_filename, content_type, file_size, extraction_status, extracted_metrics_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            report["id"], report["owner_user_id"], report["farm_id"], report["original_filename"], report["stored_filename"], report["content_type"], report["file_size"], report["extraction_status"], json.dumps(report.get("extracted_metrics", {})), report["created_at"]
        ))
        conn.commit()
    return report

def list_soil_reports(owner_user_id: str, farm_id: str) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM soil_reports WHERE owner_user_id = ? AND farm_id = ? ORDER BY created_at DESC", (owner_user_id, farm_id)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["extracted_metrics"] = json.loads(item.pop("extracted_metrics_json") or "{}")
        item.pop("stored_filename", None)
        result.append(item)
    return result


def create_farm_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    with get_connection() as conn:
        conn.execute("""INSERT INTO farm_alerts (
            id, owner_user_id, farm_id, alert_type, severity, title, message,
            observed_value, threshold_value, unit, source, observed_at, acknowledged_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)""", (
            alert["id"], alert["owner_user_id"], alert["farm_id"], alert["alert_type"],
            alert["severity"], alert["title"], alert["message"], alert["observed_value"],
            alert["threshold_value"], alert["unit"], alert["source"], alert["observed_at"], alert["created_at"]
        ))
        conn.commit()
    return get_farm_alert(alert["id"], alert["owner_user_id"])  # type: ignore


def get_farm_alert(alert_id: str, owner_user_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM farm_alerts WHERE id = ? AND owner_user_id = ?", (alert_id, owner_user_id)).fetchone()
        return dict(row) if row else None


def list_farm_alerts(owner_user_id: str, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        if farm_id:
            rows = conn.execute("SELECT * FROM farm_alerts WHERE owner_user_id = ? AND farm_id = ? ORDER BY created_at DESC", (owner_user_id, farm_id)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM farm_alerts WHERE owner_user_id = ? ORDER BY created_at DESC", (owner_user_id,)).fetchall()
        return [dict(row) for row in rows]


def acknowledge_farm_alert(alert_id: str, owner_user_id: str) -> bool:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute("UPDATE farm_alerts SET acknowledged_at = ? WHERE id = ? AND owner_user_id = ? AND acknowledged_at IS NULL", (now, alert_id, owner_user_id))
        conn.commit()
        return cursor.rowcount > 0


def create_rotation_record(record: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    with get_connection() as conn:
        conn.execute("""INSERT INTO crop_rotation_records
        (id, owner_user_id, farm_id, crop_name, season, crop_year, planting_date, harvest_date, yield_value, yield_unit, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", tuple(record.get(k) for k in ["id","owner_user_id","farm_id","crop_name","season","crop_year","planting_date","harvest_date","yield_value","yield_unit","notes","created_at","updated_at"]))
        conn.commit()
    log_farm_activity(record["owner_user_id"], record["farm_id"], "crop_planted", f"Recorded {record['crop_name']} for {record['season']} {record['crop_year']}.", {"rotation_record_id": record["id"], "crop_name": record["crop_name"], "season": record["season"]})
    return get_rotation_record(record["id"], record["owner_user_id"])  # type: ignore


def get_rotation_record(record_id: str, owner_user_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM crop_rotation_records WHERE id=? AND owner_user_id=?", (record_id, owner_user_id)).fetchone()
        return dict(row) if row else None


def list_rotation_records(owner_user_id: str, farm_id: str) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM crop_rotation_records WHERE owner_user_id=? AND farm_id=? ORDER BY crop_year DESC, CASE season WHEN 'Kharif' THEN 1 WHEN 'Rabi' THEN 2 ELSE 3 END", (owner_user_id, farm_id)).fetchall()
        return [dict(row) for row in rows]


def delete_rotation_record(record_id: str, owner_user_id: str) -> bool:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT farm_id, crop_name FROM crop_rotation_records WHERE id=? AND owner_user_id=?", (record_id, owner_user_id)).fetchone()
        if not row: return False
        conn.execute("DELETE FROM crop_rotation_records WHERE id=? AND owner_user_id=?", (record_id, owner_user_id)); conn.commit()
    log_farm_activity(owner_user_id, row["farm_id"], "crop_record_deleted", f"Removed crop record: {row['crop_name']}.", {"rotation_record_id": record_id})
    return True


def log_farm_activity(owner_user_id: str, farm_id: str, activity_type: str, description: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    init_db(); item = {"id": str(uuid.uuid4()), "owner_user_id": owner_user_id, "farm_id": farm_id, "activity_type": activity_type, "description": description, "metadata_json": json.dumps(metadata or {}), "created_at": datetime.now(timezone.utc).isoformat()}
    with get_connection() as conn:
        conn.execute("INSERT INTO farm_activity_log (id, owner_user_id, farm_id, activity_type, description, metadata_json, created_at) VALUES (:id,:owner_user_id,:farm_id,:activity_type,:description,:metadata_json,:created_at)", item); conn.commit()
    item["metadata"] = json.loads(item.pop("metadata_json")); return item


def list_farm_activity(owner_user_id: str, farm_id: str) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM farm_activity_log WHERE owner_user_id=? AND farm_id=? ORDER BY created_at DESC LIMIT 200", (owner_user_id, farm_id)).fetchall()
    result=[]
    for row in rows:
        item=dict(row); item["metadata"] = json.loads(item.pop("metadata_json") or "{}"); result.append(item)
    return result
