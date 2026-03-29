"""
audit.py
--------
Audit trail and compliance logging for all critical operations.
Logs user actions, fraud detections, blocklists, and system events.
"""

import json
from typing import Dict, Any, Optional
from database.db import execute
from utils.logger import logger


def log_audit(
    user_id: Optional[int],
    action: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> int:
    """
    Log an audit trail entry for compliance and forensics.
    
    Args:
        user_id: ID of user performing action (None for system actions)
        action: Action name (e.g., "TRANSACTION_CHECKED", "ALERT_RESOLVED")
        details: Optional dict with action details (auto-converted to JSON)
        ip_address: Optional client IP address
    
    Returns:
        Inserted audit log ID
        
    Raises:
        Exception: If database insert fails
    """
    # Convert details dict to JSON string
    details_json = json.dumps(details) if details else None
    
    audit_id = execute(
        """INSERT INTO audit_logs (user_id, action, details, ip_address)
           VALUES (?, ?, ?, ?)""",
        (user_id, action, details_json, ip_address)
    )
    
    logger.debug(f"[AUDIT] {action}: user_id={user_id}, audit_id={audit_id}")
    return audit_id


def log_transaction_checked(
    user_id: int,
    txn_id: str,
    amount: float,
    city: str,
    final_label: str,
    fraud_score: float,
    is_blocked: bool,
    ip_address: Optional[str] = None
) -> int:
    """Log a transaction fraud check audit entry."""
    return log_audit(
        user_id=user_id,
        action="TRANSACTION_CHECKED",
        details={
            "txn_id": txn_id,
            "amount": amount,
            "city": city,
            "final_label": final_label,
            "fraud_score": fraud_score,
            "is_blocked": int(is_blocked)
        },
        ip_address=ip_address
    )


def log_transaction_blocked(
    user_id: int,
    txn_id: str,
    reason: str,
    ip_address: Optional[str] = None
) -> int:
    """Log manual transaction block audit entry."""
    return log_audit(
        user_id=user_id,
        action="TRANSACTION_BLOCKED",
        details={
            "txn_id": txn_id,
            "reason": reason
        },
        ip_address=ip_address
    )


def log_alert_resolved(
    user_id: int,
    alert_id: int,
    txn_id: str,
    resolution: str,
    notes: Optional[str] = None,
    ip_address: Optional[str] = None
) -> int:
    """Log alert resolution audit entry."""
    return log_audit(
        user_id=user_id,
        action="ALERT_RESOLVED",
        details={
            "alert_id": alert_id,
            "txn_id": txn_id,
            "resolution": resolution,
            "notes": notes or ""
        },
        ip_address=ip_address
    )


def log_user_login(
    user_id: int,
    username: str,
    ip_address: Optional[str] = None
) -> int:
    """Log user login audit entry."""
    return log_audit(
        user_id=user_id,
        action="USER_LOGIN",
        details={"username": username},
        ip_address=ip_address
    )


def log_user_signup(
    user_id: int,
    username: str,
    email: str,
    ip_address: Optional[str] = None
) -> int:
    """Log user registration audit entry."""
    return log_audit(
        user_id=user_id,
        action="USER_SIGNUP",
        details={"username": username, "email": email},
        ip_address=ip_address
    )


def log_model_retrain(
    user_id: int,
    model_name: str,
    status: str,
    metrics: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> int:
    """Log model retraining audit entry."""
    return log_audit(
        user_id=user_id,
        action="MODEL_RETRAINED",
        details={
            "model": model_name,
            "status": status,
            "metrics": metrics or {}
        },
        ip_address=ip_address
    )


def get_audit_trail(
    action_filter: Optional[str] = None,
    user_id_filter: Optional[int] = None,
    limit: int = 100
) -> list:
    """
    Retrieve audit trail entries with optional filtering.
    
    Args:
        action_filter: Filter by action name exact match
        user_id_filter: Filter by user_id
        limit: Max results to return
    
    Returns:
        List of audit log entries
    """
    from database.db import query
    
    where_clauses = []
    params = []
    
    if action_filter:
        where_clauses.append("action = ?")
        params.append(action_filter)
    
    if user_id_filter:
        where_clauses.append("user_id = ?")
        params.append(user_id_filter)
    
    where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    sql = f"""
        SELECT id, user_id, action, details, ip_address, created_at
        FROM audit_logs
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(limit)
    
    return query(sql, tuple(params))
