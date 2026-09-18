# AssetFlow — Inventory & Billing System

AssetFlow is a Flask and SQLite web application built for a University of Michigan-Flint software engineering project. It gives small teams a straightforward way to manage inventory, process sales, monitor low-stock items, and review system activity.

## Features

- Role-based authentication for Admin, Manager, and Regular User accounts
- Admin user management
- Inventory creation, stock adjustments, and low-stock indicators
- Billing transactions with automatic inventory deductions
- Sales totals, stock history, and access logs
- Searchable inventory table
- Password hashing and environment-based session configuration

## Tech stack

- Python and Flask
- SQLite
- HTML, CSS, and Jinja templates
- Werkzeug password hashing

## Run locally

1. Clone the repository and enter the project folder.
2. Create and activate a virtual environment.
3. Install the dependency:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:

   ```bash
   python app.py
   ```

5. Open `http://127.0.0.1:5000/login`.

The application creates `inventory.db` automatically on first launch and loads sample inventory.

## Demo accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| Manager | `manager` | `manager123` |
| Regular User | `regUser` | `user123` |

These credentials are for local demonstration only. Change them before deploying the application anywhere public.

## Role access

| Feature | Admin | Manager | Regular User |
| --- | :---: | :---: | :---: |
| Inventory | ✓ | ✓ | ✓ |
| Billing | ✓ | ✓ | ✓ |
| Reports | ✓ | ✓ | — |
| User management | ✓ | — | — |

## Project structure

```text
inventory-billing-system/
├── app.py
├── schema.sql
├── requirements.txt
├── templates/
└── README.md
```

## Security notes

- Local passwords are stored as salted hashes rather than plain text.
- Set a persistent `SECRET_KEY` environment variable for deployment.
- The generated SQLite database is ignored by Git so local accounts and activity logs are not published.
- This is an educational project and should receive additional production hardening before an Internet-facing deployment.

## Team

- Jackson Garrett
- Jacob Schlautman
- Mahroush Chowdhury
