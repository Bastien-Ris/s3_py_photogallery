FLASK_SECRET_KEY = "a long and complicated hash"

# Set this url according to SQLAlchemy url
# Note: you must create the user and database first.
DB_URL = "postgres+psycopg://myuser:mypassword@localhost:5432/mydatabase"

# Set this dictionary according to boto client params.
S3_BACKEND = {
    "host": "http://myminio.com:9000",
    "region": "myregion",
    "bucket": "myphotobucket",
    "aws_key": "myminiouser",
    "aws_secret_key": "myminiouserpassword"
}
