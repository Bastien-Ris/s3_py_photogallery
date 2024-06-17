import os
import io
from datetime import datetime

from urllib.request import urlopen
from geopy.geocoders import Nominatim
from PIL import Image as pil, ExifTags
from s3_pygallery.s3 import internal_access, list_objects, gen_temporary_url
from s3_pygallery.core import Image
from sqlalchemy.exc import IntegrityError


geolocator = Nominatim(user_agent="BZ12hl303", timeout=5)


def compare(db, config, bucket):
    database_keys = list(db.session.execute(db.select(Image.key)).scalars())
    storage_keys = list_objects(config, bucket)
    _to_delete = [key for key in database_keys if key not in storage_keys]
    _to_add = [key for key in storage_keys if key not in database_keys]
    return _to_delete, _to_add


def harvest_metadata(config, bucket, keylist):
    image_lst = []
    for key in keylist:
        fd = urlopen(gen_temporary_url(config, bucket, key, expire=60))
        im = io.BytesIO(fd.read())
        image_lst.append(Image(**get_metadata(im, key)))
    return image_lst


def main(config, bucket, db):

    _to_delete, _to_add = compare(config=config, bucket=bucket, db=db)

    for key in _to_delete:
        db.session.delete(Image).where(Image.key == key)
    db.session.commit()

    while len(_to_add) > 0:
        if len(_to_add) > 20:
            _meta = harvest_metadata(config, bucket, _to_add[0:20])
            for image in _meta:
                try:
                    db.session.add(image)
                except IntegrityError as e:
                    print(e)
                    break
            db.session.commit()
            del _to_add[0:20]
        else:
            _meta = harvest_metadata(config, bucket, _to_add)
            for image in _meta:
                try:
                    db.session.add(image)
                except IntegrityError as e:
                    print(e)
                    break
            db.session.commit()
            return
    return
