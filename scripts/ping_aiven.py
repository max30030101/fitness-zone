import os

import mysql.connector


def main():
    required = ("MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_SSL_CA")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing required Aiven ping settings: " + ", ".join(missing))

    ca_file = os.environ["MYSQL_SSL_CA"]
    if not os.path.isfile(ca_file):
        raise RuntimeError(f"MYSQL_SSL_CA does not point to a readable CA certificate file: {ca_file}")

    connection = mysql.connector.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ.get("MYSQL_PORT") or "3306"),
        database=os.environ["MYSQL_DATABASE"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        ssl_ca=ca_file,
        ssl_verify_cert=True,
        ssl_verify_identity=True,
        connection_timeout=15,
    )
    try:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        connection.close()

    if result != (1,):
        raise RuntimeError(f"Unexpected result from Aiven MySQL ping: {result!r}")

    print("Aiven MySQL ping succeeded.")


if __name__ == "__main__":
    main()
