# coding=utf-8
# Copyright (c) Jonas Teuwen
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Patient(Base):
    __tablename__ = "Patients"
    id = Column(Integer, primary_key=True)

    PatientID = Column(String)
    PatientBirthDate = Column(String)
    PatientAge = Column(Integer)
    PatientSex = Column(String)

    def __repr__(self):
        return f"<Patient(PatientID={self.PatientID})>"


class Study(Base):
    __tablename__ = "Studies"
    id = Column(Integer, primary_key=True)

    StudyInstanceUID = Column(String)
    StudyDate = Column(String)
    StudyID = Column(String)
    StudyDescription = Column(String)
    AccessionNumber = Column(String)
    ModalitiesInStudy = Column(String)

    patient_id = Column(Integer, ForeignKey("Patients.id"))
    patient = relationship(Patient)

    def __repr__(self):
        return f"<Study(StudyInstanceUID={self.StudyInstanceUID})>"


class Series(Base):
    __tablename__ = "Series"
    id = Column(Integer, primary_key=True)

    SeriesInstanceUID = Column(String)
    SeriesNumber = Column(String)
    SeriesDate = Column(String)
    SeriesDescription = Column(String)
    Modality = Column(String)
    PatientPosition = Column(String)
    ContrastBolusAgent = Column(String)
    Manufacturer = Column(String)
    ManufacturerModelName = Column(String)
    BodyPartExamined = Column(String)
    ProtocolName = Column(String)
    InstitutionName = Column(String)
    FrameOfReferenceUID = Column(String)
    StudyInstanceUID = Column(String)

    study_id = Column(Integer, ForeignKey("Studies.id"))
    study = relationship(Study)

    def __repr__(self):
        return f"<Series(SeriesInstanceUID={self.SeriesInstanceUID})>"


class Image(Base):
    __tablename__ = "Images"
    id = Column(Integer, primary_key=True)

    SOPInstanceUID = Column(String)
    SOPClassUID = Column(String)
    ImageID = Column(String)
    InstanceNumber = Column(String)
    ContentDate = Column(String)
    ContentTime = Column(String)
    NumberOfFrames = Column(String)
    AcquisitionNumber = Column(String)
    AcquisitionDate = Column(String)
    AcquisitionTime = Column(String)
    ReceiveCoilName = Column(String)
    SliceLocation = Column(String)
    Rows = Column(String)
    Columns = Column(String)
    SamplesPerPixel = Column(String)
    PhotometricInterpretation = Column(String)
    BitsStored = Column(String)
    ImageType = Column(String)
    SeriesInstanceUID = Column(String)
    filename = Column(String)

    series_id = Column(Integer, ForeignKey("Series.id"))
    series = relationship(Series)

    def __repr__(self):
        return f"<Image(filename={self.filename})>"


#  C.8.3.1 MR Image Module
class MRIImage(Base):
    __tablename__ = "MRIImages"
    id = Column(Integer, primary_key=True)

    SOPInstanceUID = Column(String)
    ScanningSequence = Column(String)
    SequenceVariant = Column(String)
    AcquisitionType = Column(String)
    EchoTime = Column(String)
    EchoTrainLength = Column(String)
    EchoNumbers = Column(String)
    InversionTime = Column(String)
    TriggerTime = Column(String)
    RepetitionTime = Column(String)
    SequenceName = Column(String)
    SeriesTime = Column(String)
    MRAcquisitionType = Column(String)
    MagneticFieldStrength = Column(String)
    FlipAngle = Column(String)
    NumberOfTemporalPositions = Column(String)
    TemporalPositionIdentifier = Column(String)
    TemporalResolution = Column(String)

    image_id = Column(Integer, ForeignKey("Images.id"))
    image = relationship(Image)

    def __repr__(self):
        return f"<MRIImage(filename={self.image.filename})>"
