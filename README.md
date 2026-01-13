
# MarketLink Backend (Django + DRF)

MarketLink is a multi-vendor marketplace backend that connects vehicle owners with local repair shops.
This project is built as part of a backend engineering assessment, focusing on concurrency safety,
secure payment handling, and real-world API design.

---

## 🚀 Key Features

- Custom User model with role-based access (`customer`, `vendor`, `admin`)
- Vendor-managed services with variant-based pricing
- Concurrency-safe order booking with stock control
- Payment integration using SSLCommerz
- Secure, idempotent webhook-based payment confirmation
- JWT-based authentication
- Swagger API documentation

---

## 🏗️ Tech Stack

- Python 3.12
- Django & Django REST Framework
- JWT Authentication
- Redis (distributed locking)
- SSLCommerz (payment gateway)
- SQLite (dev) / PostgreSQL
- Swagger (drf-yasg)

---

## 🔐 Authentication

- Custom User model built with `AbstractBaseUser` and `PermissionsMixin`
- Stateless authentication using **JWT**
- Role-based access control at API level

---

## 🧱 Core Models

- **User** – Custom user with roles
- **VendorProfile** – One-to-one with User
- **Service** – Repair service created by vendor
- **ServiceVariant** – Variant with price, estimated time, and stock
- **RepairOrder** – Customer order with UUID, status, and total amount

Order lifecycle:
```

pending → paid → processing → completed / failed / cancelled

```

---

## 🔒 Concurrency Handling

**Problem:** Prevent double booking when variant stock is limited  
**Solution:**  
- Redis-based distributed lock (`variant_lock_<id>`)
- Atomic stock decrement inside `transaction.atomic()`

This guarantees race-condition-safe order creation.

---

## 💳 Payment Flow

1. Customer creates order
2. API returns `payment_url`
3. Customer completes payment on SSLCommerz
4. Payment gateway calls webhook
5. Order status is updated to `paid`

Order status is **never trusted from client redirects**.

---

## 🔁 Webhook Handling

Endpoint:
```

POST /api/v1/webhooks/sslcommerz/

```

Responsibilities:
- Signature validation using `WEBHOOK_SECRET`
- Idempotent processing (duplicate events ignored)
- Payment amount verification
- Secure order status update

---

## 🔐 Security Practices

- No hardcoded secrets
- Environment-based configuration
- Server-side price calculation
- Webhook signature validation
- Role-based permissions

---

## 📚 API Docs

Swagger UI:
```
/swagger/
http://127.0.0.1:8000/swagger/
````

---

## ▶️ Run Locally

```bash
git clone <repo-url>
cd marketlink
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py runserver
````

## ▶️ Create Admin user:

```bash
python3 manage.py createsuperuser
- email
- password

```
then login admin pannel and show of all
