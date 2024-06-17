import boto3
from botocore import exceptions


def internal_access(config):
    try:
        s3 = boto3.client(
            "s3",
            **config
        )
    except exceptions.ClientError as e:
        print("Fatal error: Connection to s3 failed.")
        exit(1)
    return s3


def list_objects(config, bucket):
    s3 = internal_access(config)
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket)
    images_lst = []
    for obj in pages:
        content = obj["Contents"]

        for obj in content:
            key = obj.get("Key")
            metadata = s3.head_object(Bucket=bucket, Key=key)
            if metadata.get("ContentType") == "image/jpeg":
                images_lst.append(key)
    return images_lst


def gen_temporary_url(config, bucket, obj, expire):
    s3 = internal_access(config)
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": obj},
            ExpiresIn=expire,
        )
        return url
    except exceptions.ClientError as e:
        print(e)
        return


def check_access(config, bucket, user, password):
    config["aws_access_key_id"] = user
    config["aws_secret_access_key"] = password
    try:
        s3 = boto3.client("s3", **config)
        s3.list_objects_v2(Bucket=bucket)
        return True
    except exceptions.ClientError as e:
        print(e)
        return False
