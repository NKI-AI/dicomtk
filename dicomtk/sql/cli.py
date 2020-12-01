# coding=utf-8
# Copyright (c) Jonas Teuwen
import argparse
import sys
import pathlib
import pydicom
import re

from tqdm import tqdm
from pydicom.misc import is_dicom
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


def recursive_find_dicom_files(folder, strict_checking=True):
    folder = pathlib.Path(folder)
    all_files = folder.glob("**/*")
    output = []
    failed_dicoms = []
    total_size = 0
    for idx, fn in tqdm(enumerate(all_files)):

        if not fn.is_file():
            continue

        if strict_checking:
            try:
                if not is_dicom(fn):
                    failed_dicoms.append(fn)
                    continue

            except OSError:
                failed_dicoms.append(fn)
                continue
        total_size += fn.stat().st_size
        output.append(fn)

    return output, failed_dicoms, total_size


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


def parse_dicom(path_to_dicom, database_fn):
    engine = create_engine(f"sqlite:///{database_fn.absolute()}")
    if not database_fn.exists():
        # Create all tables in the engine.
        Base.metadata.create_all(engine)

    Base.metadata.bind = engine
    DBSession = sessionmaker()
    DBSession.bind = engine
    session = DBSession()

    tqdm.write(f"Looking for dicom files in {path_to_dicom} recursively...")
    dicoms, failed_dicoms, total_size = recursive_find_dicom_files(path_to_dicom)
    tqdm.write(
        f"Found {len(dicoms)} dicom files (total={sizeof_fmt(total_size)}) "
        f"with {len(failed_dicoms)} skipped files."
    )

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
    for idx, dcm_fn in tqdm(enumerate(dicoms), total=len(dicoms)):
        already_imported = session.query(Image).filter_by(filename=str(dcm_fn)).first()
        if already_imported:
            num_already_imported += 1
            continue

        dcm_obj = pydicom.read_file(dcm_fn, stop_before_pixels=True)

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

    num_imported += 1
    tqdm.write(
        f"Imported {num_imported} dicom files (skipped {num_already_imported} already in database)."
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
