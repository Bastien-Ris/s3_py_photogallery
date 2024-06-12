import boto3
from botocore import exceptions


def s3_check_access(config, user, password):
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=config.get("host"),
            aws_access_key_id=user,
            aws_secret_access_key=password,
            verify == bool(config.get("verify")),
        )
        s3.list_objects_v2(Bucket=s3_config.get("bucket"))
        return True
    except exceptions.ClientError as e:
        return False


def s3_internal_access(config):
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=config.get("host"),
            aws_access_key_id=config.get("access_key"),
            aws_secret_access_key=s3_config.get("access_key_secret"),
            verify=bool(s3_config.get("verify")),
        )
    except exceptions.ClientError as e:
        print("Fatal error: Connection to s3 failed.")
        exit(1)
    return s3


def s3_list_objects(config):
    s3 = s3_internal_access(config)
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=config.get("bucket"))
    images_lst = []
    for obj in pages:
        content = obj["Contents"]

        for obj in content:
            key = obj.get("Key")
            metadata = s3.head_object(Bucket=config.get("bucket"), Key=key)
            if metadata.get("ContentType") == "image/jpeg":
                images_lst.append(key)
    return images_lst


def gen_temporary_url(config, obj):
    s3 = s3_internal_access(config)
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": config.get("bucket"), "Key": obj},
            ExpiresIn=config.get("url_expiration_time"),
        )
        return url
    except exceptions.ClientError as e:
        print(e)
        return
