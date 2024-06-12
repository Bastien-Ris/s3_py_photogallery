SECRET_KEY = "f5fd66f0eeea0094a2dd29cc38e17ec0f2a9540f6b537686ab1e131a74e312b9"

# Set this url according to SQLAlchemy url
# Note: you must create the user and database first.
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://pygallery:labatie1962@10.184.174.64:5432/gallery"
# Set this dictionary according to boto client params.

S3_BACKEND = {
    "endpoint_url": "http://10.184.174.193:9000",
    "aws_access_key_id": "bastien",
    "aws_secret_access_key": "labatie1962"
}

BUCKET = "bastien-test"
APP_TITLE = "Forestnest photo gallery"
