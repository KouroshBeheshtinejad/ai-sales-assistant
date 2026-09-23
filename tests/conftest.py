import os


# Keep the test client host separate from production trusted-host settings.
os.environ.setdefault("APP_ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")