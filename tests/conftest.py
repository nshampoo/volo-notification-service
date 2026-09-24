import os

# The poller creates boto3 clients at import time, which needs a region.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
