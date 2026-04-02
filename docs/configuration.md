# Configuration Reference

## Basic Configuration

Create a `config.yaml` file:

```yaml
host: "127.0.0.1"
port: 9030
user: "root"
database: "your_database"
repository: "your_repo_name"
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | Yes | StarRocks FE host address |
| `port` | integer | Yes | StarRocks MySQL protocol port (default: 9030) |
| `user` | string | Yes | Database user with backup/restore privileges |
| `database` | string | Yes | Database containing tables to backup |
| `repository` | string | Yes | Repository name (created via `CREATE REPOSITORY`) |
| `ops_database` | string | No | Custom name for ops database (default: "ops") |
| `table_inventory` | list | No | Table inventory groups definition (see below) |
| `minio` | object | No* | S3-compatible storage settings for the `prune` command (see below) |

\*Required fields inside `minio` are validated when the section is present. The **`prune` command requires a `minio` section** in the config file.

**Note:** The `database` field specifies which database contains your tables. The `ops` database is created automatically.

## Table Inventory Configuration

Define table inventory groups directly in your config file to avoid manual SQL inserts.

```yaml
host: "127.0.0.1"
port: 9030
user: "root"
database: "quickstart"
repository: "minio_repo"

table_inventory:
  - group: "full_backup"
    tables:
      - database: "production_db"
        table: "*"  # Wildcard for all tables

  - group: "fact_tables"
    tables:
      - database: "production_db"
        table: "fact_sales"
      - database: "production_db"
        table: "fact_orders"
```

### Table Inventory YAML Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `group` | string | Yes | Inventory group name |
| `tables` | list | Yes | List of table definitions |
| `tables[].database` | string | Yes | Database name |
| `tables[].table` | string | Yes | Table name or `"*"` for all tables |

When you run `starrocks-br init`, table inventory is automatically populated from your config. Manual SQL INSERT statements still work if you prefer that approach.

**Note:** If you modify the `table_inventory` section in your config file after the initial setup, you must rerun `starrocks-br init --config <config_file>` to update the database with your changes. The table inventory is persisted in the `ops.table_inventory` table and is not automatically updated when you change the config file.

## Password Management

Never store passwords in config files. Use environment variables:

### StarRocks database user

**Linux/macOS:**
```bash
export STARROCKS_PASSWORD="your_password"
```

**Windows (PowerShell):**
```powershell
$env:STARROCKS_PASSWORD="your_password"
```

**Windows (Command Prompt):**
```cmd
set STARROCKS_PASSWORD=your_password
```

### MinIO / S3 secret key (prune only)

The `prune` command deletes snapshot objects directly in object storage. Set the same secret you use as `aws.s3.secret_key` (or equivalent) in `CREATE REPOSITORY`:

**Linux/macOS:**
```bash
export MINIO_PASSWORD="your_s3_secret_key"
```

**Windows (PowerShell):**
```powershell
$env:MINIO_PASSWORD="your_s3_secret_key"
```

If `MINIO_PASSWORD` is unset, `prune` exits with an error.

## MinIO and S3-compatible storage for prune

The `prune` command does **not** use `DROP SNAPSHOT` (often unavailable). It removes objects under the path StarRocks uses for each snapshot:

```text
s3://<bucket>/<path>/__starrocks_repository_<repo_name>/__ss_<backup_label>/
```

Align `bucket`, `path`, `repo_name`, and `endpoint` with your repository definition. Example repository:

```sql
CREATE REPOSITORY `minio2`
WITH BROKER
ON LOCATION "s3://starrocks1/backup"
PROPERTIES(
    "aws.s3.access_key" = "minio",
    "aws.s3.secret_key" = "<use MINIO_PASSWORD>",
    "aws.s3.endpoint" = "http://minio.example:9000",
    "aws.s3.enable_path_style_access" = "true"
);
```

Matching `config.yaml` snippet:

```yaml
repository: "minio2"

minio:
  repo_name: "minio2"           # must match repository name; alias key: repoName
  endpoint: "http://minio.example:9000"
  bucket: "starrocks1"          # bucket from ON LOCATION
  path: "backup"                # path inside the bucket (empty string "" if none)
  access_key: "minio"
```

### MinIO YAML fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo_name` | string | Yes | Same as StarRocks repository name (you may use `repoName` instead) |
| `endpoint` | string | Yes | S3 API base URL, e.g. `http://host:9000` |
| `bucket` | string | Yes | Bucket name from the repository location |
| `path` | string | No | Prefix inside the bucket; omit or use `""` for bucket root |
| `access_key` | string | Yes | S3 access key id |

If `repository` and `minio.repo_name` differ, `prune` logs a warning; object paths always use `minio.repo_name`.

Other commands (`init`, `backup`, `restore`) do not require a `minio` section.

## TLS/SSL Configuration

Add a `tls` section to enable encrypted connections.

### Server Authentication

```yaml
host: "127.0.0.1"
port: 9030
user: "root"
database: "your_database"
repository: "your_repo_name"

tls:
  enabled: true
  ca_cert: "/path/to/ca.pem"
```

### Mutual TLS (mTLS)

```yaml
tls:
  enabled: true
  ca_cert: "/path/to/ca.pem"
  client_cert: "/path/to/client-cert.pem"
  client_key: "/path/to/client-key.pem"
```

### TLS Options

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | boolean | Yes | false | Enable TLS |
| `ca_cert` | string | Yes* | - | CA certificate path |
| `client_cert` | string | No | - | Client certificate (for mTLS) |
| `client_key` | string | No | - | Client private key (for mTLS) |
| `verify_server_cert` | boolean | No | true | Verify server certificate |
| `tls_versions` | list | No | ["TLSv1.2", "TLSv1.3"] | Allowed TLS versions |

*Required when `enabled: true`

## Repository Setup

Create a backup repository in StarRocks before using the tool.

### S3-Compatible Storage

```sql
CREATE REPOSITORY `s3_backup_repo`
WITH S3
ON LOCATION "s3://your-backup-bucket/backups/"
PROPERTIES (
    "aws.s3.access_key" = "your-access-key",
    "aws.s3.secret_key" = "your-secret-key",
    "aws.s3.endpoint" = "https://s3.amazonaws.com",
    "aws.s3.region" = "us-west-2"
);
```

### HDFS Storage

```sql
CREATE REPOSITORY `hdfs_backup_repo`
WITH BROKER
ON LOCATION "hdfs://namenode:9000/backups/"
PROPERTIES (
    "username" = "hdfs",
    "password" = ""
);
```

### Azure Blob Storage

```sql
CREATE REPOSITORY `azure_backup_repo`
WITH BROKER
ON LOCATION "wasb://container@account.blob.core.windows.net/backups/"
PROPERTIES (
    "azure.blob.storage_account" = "your-account",
    "azure.blob.shared_key" = "your-key"
);
```

### Verify Repository

```sql
SHOW REPOSITORIES;
```

Then reference it in your config:

```yaml
repository: "s3_backup_repo"
```

## Next Steps

- [Getting Started](getting-started.md)
- [Command Reference](commands.md)
