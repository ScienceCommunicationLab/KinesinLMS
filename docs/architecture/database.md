# Database

Although Django supports multiple databases, KinesinLMS is designed to work with the [PostgreSQL](https://www.postgresql.org/) database.
KinesinLMS uses some features of PostgreSQL that may not be available on other databases.

- [JSON Field](https://docs.djangoproject.com/en/5.0/ref/models/fields/#jsonfield)
- [Full-text Search](https://docs.djangoproject.com/en/5.0/ref/contrib/postgres/search/)

Although you could set up and manage your own PostgreSQL instance yourself, it sure is nice when a vendor platform handles that for you,
including things like replication, failover, metrics, monitoring and daily snapshots. So consider that before you decide.
