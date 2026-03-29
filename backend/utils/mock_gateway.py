"""
mock_gateway.py
===============
Simulates a real UPI payment gateway for LOCAL TESTING ONLY.

Used to test full transaction flow without connecting to actual banks.
Mimics behavior of real gateways like Razorpay, PayU, or Cashfree.

Features:
- Accept transaction requests
- Process mock payments
- Simulate success/failure scenarios
- Track transaction status
- Generate transaction receipts
"""

import uuid
import datetime
import json
from typing import Dict, Any, Tuple
from enum import Enum


class PaymentStatus(Enum):
    """Payment transaction statuses"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    FRAUD_BLOCKED = "FRAUD_BLOCKED"


class MockGateway:
    """
    Mock Payment Gateway - Simulates real payment processing.
    
    Usage:
        gateway = MockGateway()
        result = gateway.process_payment({
            "payer_upi": "user@bank",
            "payee_upi": "merchant@bank",
            "amount": 5000,
            "fraud_check": "LEGITIMATE"
        })
    """
    
    # Storage for transactions (in-memory for testing)
    transactions = {}
    
    def __init__(self):
        self.gateway_name = "MockGateway v1.0"
        self.merchant_id = "MOCK_MERCHANT_001"
        
    def process_payment(
        self,
        payer_upi: str,
        payee_upi: str,
        amount: float,
        fraud_label: str = "Legitimate",
        transaction_id: str = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Process a mock payment transaction.
        
        Parameters:
        -----------
        payer_upi : str
            Sender's UPI ID (e.g., "priya@bank")
        payee_upi : str
            Receiver's UPI ID (e.g., "merchant@bank")
        amount : float
            Transaction amount in INR
        fraud_label : str
            Fraud detection result: "Legitimate", "Fraud", or "Anomaly"
        transaction_id : str
            Unique transaction ID (auto-generated if not provided)
        metadata : dict
            Additional transaction data
            
        Returns:
        --------
        dict with keys:
            - gateway_txn_id: Unique transaction ID from gateway
            - status: PENDING/PROCESSING/SUCCESS/FAILED/FRAUD_BLOCKED
            - amount: Transaction amount
            - payer_upi: Sender UPI
            - payee_upi: Receiver UPI
            - timestamp: Processing timestamp
            - receipt_url: URL to receipt (mock)
            - message: Status message
            - fraud_blocked: Boolean indicating if fraud detected
        """
        
        # Generate transaction ID if not provided
        gateway_txn_id = transaction_id or f"MOCK_{uuid.uuid4().hex[:12].upper()}"
        
        # Create transaction record
        txn_record = {
            "gateway_txn_id": gateway_txn_id,
            "payer_upi": payer_upi,
            "payee_upi": payee_upi,
            "amount": amount,
            "fraud_label": fraud_label,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "status": None,
            "message": None
        }
        
        # ─── Step 1: Check if transaction is blocked due to fraud ─────────────
        if fraud_label in ("Fraud", "Anomaly"):
            txn_record["status"] = PaymentStatus.FRAUD_BLOCKED.value
            txn_record["message"] = f"Transaction blocked: {fraud_label} detected by fraud detection system"
            txn_record["fraud_blocked"] = True
            
            MockGateway.transactions[gateway_txn_id] = txn_record
            
            return {
                "gateway_txn_id": gateway_txn_id,
                "status": PaymentStatus.FRAUD_BLOCKED.value,
                "amount": amount,
                "payer_upi": payer_upi,
                "payee_upi": payee_upi,
                "timestamp": txn_record["created_at"],
                "message": txn_record["message"],
                "fraud_blocked": True,
                "receipt_url": f"https://mock-gateway.local/receipt/{gateway_txn_id}"
            }
        
        # ─── Step 2: Validate transaction ──────────────────────────────────
        validation_error = self._validate_transaction(payer_upi, payee_upi, amount)
        if validation_error:
            txn_record["status"] = PaymentStatus.FAILED.value
            txn_record["message"] = validation_error
            MockGateway.transactions[gateway_txn_id] = txn_record
            
            return {
                "gateway_txn_id": gateway_txn_id,
                "status": PaymentStatus.FAILED.value,
                "amount": amount,
                "payer_upi": payer_upi,
                "payee_upi": payee_upi,
                "timestamp": txn_record["created_at"],
                "message": validation_error,
                "fraud_blocked": False,
                "receipt_url": None
            }
        
        # ─── Step 3: Process payment (simulate delay) ──────────────────────
        txn_record["status"] = PaymentStatus.PROCESSING.value
        txn_record["message"] = "Processing payment..."
        
        # Simulate payment processing
        import time
        time.sleep(0.5)  # Mock processing delay
        
        # ─── Step 4: Simulate success/failure ──────────────────────────────
        # For demo: Most transactions succeed (90% success rate)
        import random
        if random.random() < 0.9:  # 90% success rate
            txn_record["status"] = PaymentStatus.SUCCESS.value
            txn_record["message"] = "Payment successful"
            status = PaymentStatus.SUCCESS.value
        else:
            txn_record["status"] = PaymentStatus.FAILED.value
            txn_record["message"] = "Payment failed: Bank declined"
            status = PaymentStatus.FAILED.value
        
        # Store transaction record
        MockGateway.transactions[gateway_txn_id] = txn_record
        
        # Return response
        return {
            "gateway_txn_id": gateway_txn_id,
            "status": status,
            "amount": amount,
            "payer_upi": payer_upi,
            "payee_upi": payee_upi,
            "timestamp": txn_record["created_at"],
            "message": txn_record["message"],
            "fraud_blocked": False,
            "receipt_url": f"https://mock-gateway.local/receipt/{gateway_txn_id}",
            "success": status == PaymentStatus.SUCCESS.value
        }
    
    def _validate_transaction(self, payer: str, payee: str, amount: float) -> str:
        """Validate transaction details. Returns error message or empty string if valid."""
        
        if not payer or "@" not in payer:
            return "Invalid payer UPI ID"
        
        if not payee or "@" not in payee:
            return "Invalid payee UPI ID"
        
        if payer == payee:
            return "Payer and payee cannot be the same"
        
        if amount <= 0:
            return "Amount must be greater than 0"
        
        if amount > 100000:
            return "Amount exceeds maximum limit (₹100,000)"
        
        return ""
    
    def get_transaction_status(self, gateway_txn_id: str) -> Dict[str, Any]:
        """Get status of a transaction"""
        
        if gateway_txn_id not in MockGateway.transactions:
            return {
                "status": "NOT_FOUND",
                "message": f"Transaction {gateway_txn_id} not found",
                "gateway_txn_id": gateway_txn_id
            }
        
        txn = MockGateway.transactions[gateway_txn_id]
        return {
            "gateway_txn_id": gateway_txn_id,
            "status": txn["status"],
            "amount": txn["amount"],
            "payer_upi": txn["payer_upi"],
            "payee_upi": txn["payee_upi"],
            "timestamp": txn["created_at"],
            "message": txn["message"],
            "fraud_label": txn["fraud_label"]
        }
    
    def get_all_transactions(self, limit: int = 10) -> list:
        """Get all transactions (for testing/debugging)"""
        
        txns = list(MockGateway.transactions.values())
        # Sort by creation time (newest first)
        txns.sort(
            key=lambda x: x["created_at"],
            reverse=True
        )
        return txns[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        
        all_txns = MockGateway.transactions.values()
        
        total = len(all_txns)
        successful = sum(1 for t in all_txns if t["status"] == PaymentStatus.SUCCESS.value)
        failed = sum(1 for t in all_txns if t["status"] == PaymentStatus.FAILED.value)
        fraud_blocked = sum(1 for t in all_txns if t["status"] == PaymentStatus.FRAUD_BLOCKED.value)
        total_amount = sum(t["amount"] for t in all_txns)
        
        return {
            "total_transactions": total,
            "successful": successful,
            "failed": failed,
            "fraud_blocked": fraud_blocked,
            "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%",
            "total_amount": total_amount,
            "gateway_name": self.gateway_name
        }


# Singleton instance
_gateway = None

def get_gateway() -> MockGateway:
    """Get or create gateway singleton"""
    global _gateway
    if _gateway is None:
        _gateway = MockGateway()
    return _gateway
