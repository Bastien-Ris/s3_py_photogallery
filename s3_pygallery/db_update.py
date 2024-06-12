import os
from datetime import datetime

from exif import Image as exif
from geopy.geocoders import Nominatim
from PIL import Image as pil
from s3_pygallery.s3 import internal_access, list_objects
from s3_pygallery.core import Image

geolocator = Nominatim(user_agent="BZ12hl303")


def compare(db, config, bucket):
    database_keys = db.session.execute(db.select(Image.key)).scalars()
    storage_keys = list_objects(config, bucket)
    _to_delete = [key for key in database_keys if key not in storage_keys]
    _to_add = [key for key in storage_keys if key not in database_keys]
    return _to_delete, _to_add


def dms_do_dd(gps_coords, gps_coords_ref):
    try:
        d, m, s = gps_coords
    except TypeError as e:
        return
    dd = d + m / 60 + s / 3600
    if gps_coords_ref.upper() in ("S", "W"):
        return -dd
    elif gps_coords_ref.upper() in ("N", "E"):
        return dd
    else:
        raise RuntimeError(
            "Incorrect gps_coords_ref {}".format(gps_coords_ref))


def get_metadata(image, key):
    print("Image: {0} ...".format(key))
    album, filename = os.path.split(key)
    album = album.replace("/", "_")
    _meta = {"key": key, "album": album}
    with open(image, "rb") as tmp_file:
        exif_info = exif(tmp_file)
        pil_info = pil.open(image)
        _meta["width"], _meta["height"] = pil_info.size

        if exif.has_exif:
            try:
                _meta["orientation"] = str(exif_info.get("orientation")).replace(
                    "Orientation.", ""
                )
            except (ValueError, KeyError, ConnectionError) as e:
                print(e)

            try:
                if exif_info.get("datetime_original"):
                    exif_date = datetime.strptime(
                        exif_info.get("datetime_original"), "%Y:%m:%d %H:%M:%S"
                    )
                    _meta["date"] = exif_date.strftime("%Y-%m-%d")
                    _meta["time"] = exif_date.strftime("%H:%M:%S")
            except (ValueError, KeyError, ConnectionError) as e:
                print(e)

            try:
                exif_long = dms_do_dd(
                    exif_info.get("gps_longitude"), exif_info.get(
                        "gps_longitude_ref")
                )
                exif_lat = dms_do_dd(
                    exif_info.get("gps_latitude"), exif_info.get(
                        "gps_latitude_ref")
                )
                image_location = geolocator.reverse(f"{exif_lat}, {exif_long}").raw.get(
                    "address"
                )

                for key in image_location.keys():
                    if key in dir(Image):
                        _meta[key] = image_location[key]
            except (ValueError, KeyError, ConnectionError, Exception) as e:
                print(e)
    return _meta


def harvest_metadata(config, bucket, keylist):
    s3 = internal_access(config)
    image_lst = []
    for key in keylist:
        dirname, filename = os.path.split(key)
        temp_file = os.path.normpath("/tmp/" + filename)
        s3.download_file(bucket, key, temp_file)
        image_lst.append(Image(**get_metadata(temp_file, key)))
        os.remove(temp_file)
    return image_lst


def main(config, bucket, db):

    _to_delete, _to_add = compare(config=config, bucket=bucket, db=db)
    s3 = internal_access(config)

    for key in _to_delete:
        db.session.delete(Image).where(Image.key == key)
    db.session.commit()

    _meta = harvest_metadata(config, bucket, _to_add)
    for image in _meta:
        db.session.add(image)
    db.session.commit()
