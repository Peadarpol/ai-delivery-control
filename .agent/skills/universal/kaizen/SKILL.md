---
name: kaizen
deprecated: true
superseded-by: python-backend-guidelines
deprecation-note: |
  All content has been reviewed and migrated. Poka-Yoke and YAGNI sections
  moved to python-backend-guidelines §Development Philosophy (2026-05-09).
  Standardised Work / DomainException pattern migrated to
  python-backend-guidelines §Standardised Work — Exception Patterns.
  Note: the Payment.amount:float example in this file violates BR-POS-01
  (money must be stored as integer cents) — it was NOT migrated.
description: Guide for continuous improvement, error proofing (Poka-Yoke), and standardization. Use this skill when the user wants to improve code quality, refactor, or discuss process improvements.
skill_type: universal
version: 1.0.0
---

# Kaizen: Continuous Improvement (Python Edition)

## Overview

Small improvements, continuously. Error-proof by design. Follow what works. Build only what's needed.

**Core principle:** Many small improvements beat one big change. Prevent errors at design time (using types and validation), not just with fixes.

## When to Use

**Always applied for:**
- Python code implementation and refactoring
- Architecture and design decisions
- Process and workflow improvements
- Error handling and Pydantic validation

**Philosophy:** Quality through incremental progress and prevention, not perfection through massive effort.

## The Four Pillars

### 1. Continuous Improvement (Kaizen)

Small, frequent improvements compound into major gains.

#### Principles

**Incremental over revolutionary:**
- Make smallest viable change that improves quality.
- One improvement at a time.
- Verify each change before next (run `pytest`).

**Always leave code better:**
- Fix small issues as you encounter them.
- Refactor while you work (within scope).
- Update docstrings and type hints.

**Iterative refinement:**
- **First version**: make it work.
- **Second pass**: make it clear (Pythonic idioms).
- **Third pass**: make it efficient and robust.

<Good>
```python
# Iteration 1: Make it work
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total

# Iteration 2: Make it clear (Refactor - Pythonic)
def calculate_total(items: list[dict]) -> float:
    return sum(item['price'] * item['quantity'] for item in items)

# Iteration 3: Make it robust (Add validation & Type Safety)
from pydantic import BaseModel, PositiveInt, PositiveFloat

class Item(BaseModel):
    price: PositiveFloat
    quantity: PositiveInt

def calculate_total(items: list[Item]) -> float:
    if not items:
        return 0.0
    return sum(item.price * item.quantity for item in items)
```
Each step is complete, tested, and working.
</Good>

---

### 2. Poka-Yoke (Error Proofing)

Design systems that prevent errors at development time, not runtime.

#### Principles

**Make errors impossible:**
- Type hints catch mistakes.
- Pydantic enforces contracts.
- Invalid states unrepresentable (using Enums and Discriminated Unions).

**Design for safety:**
- Fail fast and loudly (Early validation).
- Provide helpful error messages.
- Use Pythonic `with` blocks (Context Managers) for resource management.

#### Type System & Pydantic Error Proofing

<Good>
```python
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Union

# Bad: string status can be any value
class OrderBad(BaseModel):
    status: str  # Can be "pending", "PENDING", "pnding", anything!
    total: float

# Good: Only valid states possible using Enum or Literal
class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

# Better: States with associated data (Discriminated Union)
class PendingOrder(BaseModel):
    status: Literal[OrderStatus.PENDING] = OrderStatus.PENDING
    created_at: datetime

class ShippedOrder(BaseModel):
    status: Literal[OrderStatus.SHIPPED] = OrderStatus.SHIPPED
    tracking_number: str
    shipped_at: datetime

Order = Union[PendingOrder, ShippedOrder] # Add others...

# Now impossible to have a ShippedOrder without a tracking_number
```
Type system prevents entire classes of errors.
</Good>

#### Validation Error Proofing

<Good>
```python
from pydantic import BaseModel, field_validator

# Good: Validate immediately at the boundary (Pydantic Model)
class Payment(BaseModel):
    amount: float

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Payment amount must be positive')
        if v > 10000:
            raise ValueError('Payment exceeds maximum allowed (10,000)')
        return v

def process_payment(payment: Payment):
    # payment.amount is GUARANTEED valid here
    fee = payment.amount * 0.03
    return fee
```
Validate once at the boundary, safe everywhere else.
</Good>

---

### 3. Standardized Work

Follow established patterns. Document what works. Make good practices easy to follow.

#### Principles

**Consistency over cleverness:**
- Follow existing codebase patterns (Clean Architecture).
- Don't reinvent solved problems (Use `fastapi.Depends`).
- New pattern only if significantly better + team agreement.

**Standardized Error Handling:**

<Good>
```python
# Project standard: Use custom exceptions for business logic
from src.domain.exceptions import DomainException

class InsufficientFundsError(DomainException):
    def __init__(self, required: float, available: float):
        self.message = f"Insufficient funds. Required {required}, but only {available} available."
        super().__init__(self.message)

# Service layer follows the pattern
def withdraw(account_id: str, amount: float):
    account = repository.get(account_id)
    if account.balance < amount:
        raise InsufficientFundsError(amount, account.balance)
    account.balance -= amount
    repository.save(account)
```
Standard pattern across the codebase.
</Good>

---

### 4. Just-In-Time (JIT)

Build what's needed now. No more, no less. Avoid premature optimization and over-engineering.

#### Principles

**YAGNI (You Aren't Gonna Need It):**
- Implement only current requirements.
- No "just in case" features.
- No "we might need this later" code.

**Simplest thing that works:**
- Start with straightforward solution.
- Refactor when requirements change.
- Don't anticipate future needs until they emerge.

<Good>
```python
# Current requirement: Log errors to console
import logging

def log_error(error: Exception):
    logging.error(f"Error occurred: {str(error)}")
```
Simple, meets current need.
</Good>

<Bad>
```python
# Over-engineered for "future needs"
class ILogTransport(ABC):
    @abstractmethod
    def write(self, message: str): pass

class ConsoleTransport(ILogTransport): ...
class RemoteTransport(ILogTransport): ...

class Logger:
    def __init__(self, transports: list[ILogTransport]):
        self.transports = transports

    def log(self, message: str):
        for t in self.transports: t.write(message)

# 200 lines of code for "maybe we'll need it"
```
Building for imaginary future requirements.
</Bad>

---

## 🚩 Red Flags

- **Violating Kaizen**: "I'll refactor it later." (Technical debt accumulates).
- **Violating Poka-Yoke**: Trusting client-side input or skipping type hints.
- **Violating JIT**: Building complex generic frameworks before having 3 actual use cases.

## Remember

**Kaizen is about:**
- Small improvements continuously.
- Preventing errors by design (Pydantic + Type Hints).
- Following proven patterns (Clean Architecture).
- Building only what's needed.

**Mindset:** Good enough today, better tomorrow. Repeat.
