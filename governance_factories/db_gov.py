"""
Database Governance Factory - Audit Trail and Database Operations
SQLite-based audit database with hash-chain integrity verification
"""

import sqlite3
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import os

class DBGovernanceFactory:
    """
    Database operations and audit trail management with hash-chain integrity
    """
    
    def __init__(self, db_path: str = "db/audit.db"):
        self.db_path = db_path
        self.secret_key = "poc_hmac_key_change_in_production"  # POC only
        self._ensure_db_directory()
        self._initialize_db()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def _initialize_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_entries (
                    id TEXT PRIMARY KEY,
                    request_id TEXT,
                    timestamp TEXT,
                    event_type TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    actor TEXT,
                    details TEXT,
                    previous_hash TEXT,
                    current_hash TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_request_id ON audit_entries(request_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_entries(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_entries(resource_type, resource_id)
            """)
    
    def _calculate_hash(self, entry: Dict[str, Any], previous_hash: str = "") -> str:
        """Calculate HMAC-SHA256 hash for entry"""
        # Create deterministic string representation
        hash_input = f"{entry['request_id']}|{entry['timestamp']}|{entry['event_type']}|{entry['resource_type']}|{entry['resource_id']}|{entry['actor']}|{json.dumps(entry['details'], sort_keys=True)}|{previous_hash}"
        
        return hmac.new(
            self.secret_key.encode(),
            hash_input.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def insert_entry(self, entry: Dict[str, Any]) -> str:
        """
        Insert audit entry with hash-chain integrity
        """
        try:
            entry_id = str(uuid.uuid4())
            
            # Get previous hash for chain integrity
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT current_hash FROM audit_entries ORDER BY created_at DESC LIMIT 1"
                )
                result = cursor.fetchone()
                previous_hash = result[0] if result else ""
            
            # Calculate current hash
            current_hash = self._calculate_hash(entry, previous_hash)
            
            # Insert entry
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO audit_entries 
                    (id, request_id, timestamp, event_type, resource_type, resource_id, 
                     actor, details, previous_hash, current_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry_id,
                    entry.get("request_id", ""),
                    entry.get("timestamp", datetime.utcnow().isoformat()),
                    entry.get("event_type", ""),
                    entry.get("resource_type", ""),
                    entry.get("resource_id", ""),
                    entry.get("actor", ""),
                    json.dumps(entry.get("details", {})),
                    previous_hash,
                    current_hash
                ))
            
            return entry_id
            
        except Exception as e:
            raise Exception(f"Failed to insert audit entry: {e}")
    
    async def get_entries_by_request(self, request_id: str) -> List[Dict[str, Any]]:
        """Get all audit entries for a specific request"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM audit_entries WHERE request_id = ? ORDER BY created_at",
                (request_id,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    async def get_entries_by_resource(self, resource_type: str, resource_id: str) -> List[Dict[str, Any]]:
        """Get all audit entries for a specific resource"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM audit_entries WHERE resource_type = ? AND resource_id = ? ORDER BY created_at",
                (resource_type, resource_id)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    async def get_all_entries(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all audit entries (limited for performance)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM audit_entries ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    async def verify_hash_chain(self) -> Dict[str, Any]:
        """
        Verify integrity of the hash chain
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM audit_entries ORDER BY created_at"
                )
                
                entries = [dict(row) for row in cursor.fetchall()]
            
            if not entries:
                return {"status": "OK", "message": "No entries to verify"}
            
            verification_errors = []
            previous_hash = ""
            
            for entry in entries:
                # Reconstruct entry for hash calculation
                entry_for_hash = {
                    "request_id": entry["request_id"],
                    "timestamp": entry["timestamp"],
                    "event_type": entry["event_type"],
                    "resource_type": entry["resource_type"],
                    "resource_id": entry["resource_id"],
                    "actor": entry["actor"],
                    "details": json.loads(entry["details"])
                }
                
                # Calculate expected hash
                expected_hash = self._calculate_hash(entry_for_hash, previous_hash)
                
                # Check hash integrity
                if expected_hash != entry["current_hash"]:
                    verification_errors.append({
                        "entry_id": entry["id"],
                        "expected_hash": expected_hash,
                        "actual_hash": entry["current_hash"],
                        "timestamp": entry["timestamp"]
                    })
                
                # Check previous hash linkage
                if entry["previous_hash"] != previous_hash:
                    verification_errors.append({
                        "entry_id": entry["id"],
                        "error": "previous_hash_mismatch",
                        "expected_previous": previous_hash,
                        "actual_previous": entry["previous_hash"]
                    })
                
                previous_hash = entry["current_hash"]
            
            if verification_errors:
                return {
                    "status": "MISMATCH",
                    "errors": verification_errors,
                    "total_entries": len(entries),
                    "error_count": len(verification_errors)
                }
            else:
                return {
                    "status": "OK",
                    "message": "Hash chain integrity verified",
                    "total_entries": len(entries)
                }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Verification failed: {e}"
            }
    
    async def export_audit_package(self, request_id: str = None, tenant_id: str = None) -> Dict[str, Any]:
        """
        Export audit package for specific request or tenant
        """
        try:
            if request_id:
                entries = await self.get_entries_by_request(request_id)
            elif tenant_id:
                # Get entries where details contains tenant_id
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM audit_entries WHERE details LIKE ? ORDER BY created_at",
                        (f'%"tenant_id": "{tenant_id}"%',)
                    )
                    entries = [dict(row) for row in cursor.fetchall()]
            else:
                entries = await self.get_all_entries(limit=10000)
            
            # Verify hash chain for exported entries
            verification_result = await self.verify_hash_chain()
            
            package = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "tenant_id": tenant_id,
                "entry_count": len(entries),
                "entries": entries,
                "verification": verification_result,
                "package_id": str(uuid.uuid4())
            }
            
            return package
            
        except Exception as e:
            raise Exception(f"Failed to export audit package: {e}")
    
    def get_db_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as total_entries FROM audit_entries")
            total_entries = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT event_type, COUNT(*) as count 
                FROM audit_entries 
                GROUP BY event_type 
                ORDER BY count DESC
            """)
            event_type_counts = dict(cursor.fetchall())
            
            cursor = conn.execute("""
                SELECT MIN(created_at) as first_entry, MAX(created_at) as last_entry
                FROM audit_entries
            """)
            date_range = cursor.fetchone()
            
            return {
                "total_entries": total_entries,
                "event_type_counts": event_type_counts,
                "first_entry": date_range[0],
                "last_entry": date_range[1],
                "db_file_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            }
