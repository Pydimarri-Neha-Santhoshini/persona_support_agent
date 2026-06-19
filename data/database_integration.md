# Database Integration and Migrations

Follow these steps to integrate your local application with our PostgreSQL database cluster.

## 1. Connection String Format
Configure your environment variables with the following connection URI pattern:
`postgresql://<username>:<password>@<db-host>:<port>/<database_name>`

## 2. Schema Migrations
All schema updates must go through migration files managed by Alembic:
1. Generate migration: `alembic revision --autogenerate -m "description"`
2. Run database migration: `alembic upgrade head`
3. Roll back migration: `alembic downgrade -1`