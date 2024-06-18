import boto3
from botocore import exceptions

# botocore doesn't support class inheritance for Client.S3 object.
# This class is a dictionary holding the config,
# and supporting only methods required for this app.


class S3(dict):
    def __init__(self, config):
        super(S3client, self).__init__(
            **config
        )

    def __str__(self):
        return "S3Client: endpoint: {0}, access_key: {1}, secret_key: ***".format(
            self.get("endpoint_url"), self.get("aws_access_key_id"))

    def _build_client(self):
        try:
            s3 = boto3.client(
                "s3",
                **self
            )
            return s3
        except exceptions.ClientError as e:
            print("Fatal error: Connection to s3 failed.")
            print("config:")
            print(self.__str__())
            return

    def list_objects(self, bucket):
        client = self._build_client()
        try:
            paginator = client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket)
            images_lst = []
            for obj in pages:
                content = obj["Contents"]

                for obj in content:
                    key = obj.get("Key")
                    metadata = client.head_object(Bucket=bucket, Key=key)
                    if metadata.get("ContentType") == "image/jpeg":
                        images_lst.append(key)
            return images_lst
        except exceptions.PaginationError as e:
            print(e)
            return

    def gen_temporary_url(self, bucket, obj, expire):
        client = self._build_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": obj},
                ExpiresIn=expire,
            )
            return url
        except exceptions.ClientError as e:
            print(e)
            return
