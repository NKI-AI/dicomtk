# coding=utf-8
# Copyright (c) Jonas Teuwen
import argparse
import sys
import pathlib
import pydicom
import re

from tqdm import tqdm
from pydicom.errors import InvalidDicomError
from dicomtk.sql.models import Base, Patient, Image, Series, Study, MRIImage

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def sizeof_fmt(num, suffix="B"):
    # From: https://stackoverflow.com/a/1094933/576363
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def populate_object_from_dicom(object, dcm_obj, tags, extra_fields=None, **kwargs):
    # TODO: Get proper datatype, now everything is a string
    if extra_fields is None:
        extra_fields = {}

    from_dicom = {}
    # This parsing must be more elaborate, checking datatype
    for k in tags[object.__name__]:
        dcm_val = getattr(dcm_obj, k, "NULL")
        if isinstance(dcm_val, pydicom.multival.MultiValue):
            dcm_val = "/".join(dcm_val)
        from_dicom[k] = dcm_val

    return object(**{**from_dicom, **extra_fields}, **kwargs)


def add_or_update(session, model, instance, **kwargs):
    exists = session.query(model).filter_by(**kwargs).first()
    if not exists:
        session.add(instance)
        session.commit()
        return instance

    else:  # TODO: Update only the fields which are new, DICOM does not require each slice to have all the data.
        pass

    return exists


def import_into_db(session, tags, dcm_fn):
    try:
        dcm_obj = pydicom.read_file(dcm_fn, stop_before_pixels=True)
    except InvalidDicomError:
        return False
    # Create Patient
    # TODO: Create a partial always populating tags
    patient = populate_object_from_dicom(Patient, dcm_obj, tags)
    patient = add_or_update(session, Patient, patient, PatientID=patient.PatientID)

    study = populate_object_from_dicom(Study, dcm_obj, tags, patient=patient)
    study = add_or_update(
        session, Study, study, StudyInstanceUID=study.StudyInstanceUID
    )

    series = populate_object_from_dicom(Series, dcm_obj, tags, study=study)
    series = add_or_update(
        session, Series, series, SeriesInstanceUID=series.SeriesInstanceUID
    )

    image = populate_object_from_dicom(
        Image, dcm_obj, tags, extra_fields={"filename": str(dcm_fn)}, series=series
    )
    # Already imported images are skipped.
    session.add(image)
    session.commit()

    # Check SOPClassUID if this is a MRI.
    if dcm_obj.SOPClassUID == "1.2.840.10008.5.1.4.1.1.4":  # MR Image Storage
        mri_image = populate_object_from_dicom(MRIImage, dcm_obj, tags, image=image)
        session.add(mri_image)
        session.commit()
    return True


def parse_dicom(path_to_dicom, database_fn):
    engine = create_engine(f"sqlite:///{database_fn.absolute()}")
    if not database_fn.exists():
        # Create all tables in the engine.
        Base.metadata.create_all(engine)

    Base.metadata.bind = engine
    DBSession = sessionmaker()
    DBSession.bind = engine
    session = DBSession()

    tqdm.write(f"Looking for dicom files in {path_to_dicom} and adding to {database_fn}...")

    path_to_dicom = pathlib.Path(path_to_dicom)
    all_files = path_to_dicom.glob("**/*")

    # The table names correspond to the names in the DICOM standard,
    # we build the tags names here (excluding id and filenames)
    objects_to_fill = [Patient, Study, Series, Image, MRIImage]
    ignore_regex = "^.*(id|filename)$"

    tags = {
        k.__name__: [
            kk for kk in k.__table__.columns.keys() if not re.match(ignore_regex, kk)
        ]
        for k in objects_to_fill
    }

    num_already_imported = 0
    num_imported = 0
    total_size = 0
    with tqdm(unit=" files") as pbar:
        for idx, dcm_fn in enumerate(all_files):
            if not dcm_fn.is_file():
                continue

            already_imported = session.query(Image).filter_by(filename=str(dcm_fn)).first()
            if already_imported:
                num_already_imported += 1
                continue

            if not import_into_db(session, tags, dcm_fn):
                with open("errors.log", "a") as f:
                    f.write(str(dcm_fn) + "\n")

            total_size += dcm_fn.stat().st_size
            num_imported += 1
            pbar.update(1)
            pbar.set_postfix({"total amount of data processed":f"{sizeof_fmt(total_size)}"})

    tqdm.write(
        f"Imported {num_imported} dicom files (total={sizeof_fmt(total_size)}), "
        f"and skipped {num_already_imported} already in database."
    )


def main():
    """Console script for dicomtosql."""
    parser = argparse.ArgumentParser(
        usage="""dicomtosql parses folders recursively for dicom files,
        and saves relevant data to an SQLite database."""
    )
    parser.add_argument(
        "PATH_TO_DICOM", type=pathlib.Path, help="Path to the dicom files."
    )
    parser.add_argument(
        "--sql-database",
        type=pathlib.Path,
        default="dicomtosql.db",
        help="Path to SQLite database.",
    )

    args = parser.parse_args()
    parse_dicom(args.PATH_TO_DICOM, args.sql_database)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
