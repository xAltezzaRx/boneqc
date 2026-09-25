from dataclasses import dataclass
from io import BytesIO

import pydicom
from pydicom.datadict import tag_for_keyword
from pydicom.dataset import Dataset
from pydicom.multival import MultiValue
from pydicom.uid import PYDICOM_IMPLEMENTATION_UID, generate_uid


DEIDENTIFICATION_METHOD = "BoneQC privacy baseline 0.1"


# Attributes whose values may identify a patient, personnel,
# organization, order, encounter or source device.
SENSITIVE_KEYWORDS = {
    # Patient identity / demographics
    "PatientName",
    "PatientID",
    "IssuerOfPatientID",
    "TypeOfPatientID",
    "IssuerOfPatientIDQualifiersSequence",
    "PatientBirthDate",
    "PatientBirthTime",
    "PatientSex",
    "PatientAge",
    "PatientSize",
    "PatientWeight",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "OtherPatientIDs",
    "OtherPatientIDsSequence",
    "OtherPatientNames",
    "PatientMotherBirthName",
    "EthnicGroup",
    "Occupation",
    "AdditionalPatientHistory",
    "PatientComments",
    "CountryOfResidence",
    "RegionOfResidence",
    "PatientReligiousPreference",
    "MedicalRecordLocator",
    "ResponsiblePerson",
    "ResponsiblePersonRole",
    "ResponsibleOrganization",

    # Personnel
    "ReferringPhysicianName",
    "ConsultingPhysicianName",
    "PhysiciansOfRecord",
    "NameOfPhysiciansReadingStudy",
    "PerformingPhysicianName",
    "OperatorsName",
    "RequestingPhysician",
    "RequestingService",

    # Organization / location / device identity
    "InstitutionName",
    "InstitutionAddress",
    "InstitutionalDepartmentName",
    "InstitutionalDepartmentTypeCodeSequence",
    "StationName",
    "DeviceSerialNumber",

    # Orders / workflow identifiers
    "AccessionNumber",
    "IssuerOfAccessionNumberSequence",
    "StudyID",
    "RequestedProcedureID",
    "ScheduledProcedureStepID",
    "PlacerOrderNumberImagingServiceRequest",
    "FillerOrderNumberImagingServiceRequest",

    # Free-text descriptors that may contain names or identifiers
    "StudyDescription",
    "SeriesDescription",
    "ProtocolName",
    "ImageComments",
    "AcquisitionComments",
    "ReasonForTheRequestedProcedure",
    "RequestedProcedureDescription",
    "ScheduledProcedureStepDescription",
}


# UIDs that may provide a link back to the source study/instance.
# Class UIDs and Transfer Syntax UIDs are intentionally NOT changed.
UID_KEYWORDS_TO_REMAP = {
    "SOPInstanceUID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "FrameOfReferenceUID",
    "SynchronizationFrameOfReferenceUID",
    "RelatedFrameOfReferenceUID",
    "ReferencedSOPInstanceUID",
    "ConcatenationUID",
    "DimensionOrganizationUID",
    "TrackingUID",
    "AcquisitionUID",
    "IrradiationEventUID",
}


FILE_META_REMOVE_KEYWORDS = {
    "SourceApplicationEntityTitle",
    "SendingApplicationEntityTitle",
    "ReceivingApplicationEntityTitle",
    "PrivateInformationCreatorUID",
    "PrivateInformation",
}


@dataclass(slots=True)
class DicomDeidentificationResult:
    data: bytes
    uid_count: int
    cleared_attribute_count: int
    removed_private_tag_count: int


class DicomDeidentifier:
    def __init__(self) -> None:
        self._uid_map: dict[str, str] = {}
        self._cleared_attribute_count = 0
        self._removed_private_tag_count = 0

    def deidentify(
        self,
        dataset: pydicom.Dataset,
    ) -> DicomDeidentificationResult:
        self._uid_map = {}
        self._cleared_attribute_count = 0
        self._removed_private_tag_count = 0

        self._sanitize_dataset(dataset)

        dataset.PatientIdentityRemoved = "YES"
        dataset.DeidentificationMethod = DEIDENTIFICATION_METHOD

        self._clean_file_meta(dataset)

        output = BytesIO()

        dataset.save_as(
            output,
            enforce_file_format=True,
        )

        return DicomDeidentificationResult(
            data=output.getvalue(),
            uid_count=len(self._uid_map),
            cleared_attribute_count=self._cleared_attribute_count,
            removed_private_tag_count=self._removed_private_tag_count,
        )

    def _sanitize_dataset(
        self,
        dataset: Dataset,
    ) -> None:
        for element in list(dataset):
            if element.tag.is_private:
                del dataset[element.tag]
                self._removed_private_tag_count += 1
                continue

            keyword = element.keyword or ""

            if keyword in SENSITIVE_KEYWORDS:
                if element.VR == "SQ":
                    element.value = []
                else:
                    element.value = ""

                self._cleared_attribute_count += 1
                continue

            # Person Name can appear in many sequences and attributes.
            if element.VR == "PN":
                element.value = ""
                self._cleared_attribute_count += 1
                continue

            # Remove longitudinal dates/times from the de-identified copy.
            if element.VR in {"DA", "DT", "TM"}:
                element.value = ""
                self._cleared_attribute_count += 1
                continue

            if keyword in UID_KEYWORDS_TO_REMAP:
                element.value = self._remap_uid_value(
                    element.value
                )
                continue

            if element.VR == "SQ":
                for item in element.value:
                    self._sanitize_dataset(item)

        # Belt-and-suspenders cleanup using pydicom's supported API.
        dataset.remove_private_tags()

    def _remap_uid_value(self, value):
        if value is None:
            return value

        if isinstance(value, MultiValue):
            return [
                self._map_uid(str(item))
                for item in value
            ]

        if isinstance(value, (list, tuple)):
            return [
                self._map_uid(str(item))
                for item in value
            ]

        text = str(value)

        if not text:
            return value

        return self._map_uid(text)

    def _map_uid(self, original: str) -> str:
        if original not in self._uid_map:
            self._uid_map[original] = generate_uid(
                prefix=None
            )

        return self._uid_map[original]

    def _clean_file_meta(
        self,
        dataset: Dataset,
    ) -> None:
        file_meta = getattr(
            dataset,
            "file_meta",
            None,
        )

        if file_meta is None:
            return

        for keyword in FILE_META_REMOVE_KEYWORDS:
            tag = tag_for_keyword(keyword)

            if (
                tag is not None
                and tag in file_meta
            ):
                del file_meta[tag]

        # Do not retain implementation identifiers from the source system.
        file_meta.ImplementationClassUID = (
            PYDICOM_IMPLEMENTATION_UID
        )
        file_meta.ImplementationVersionName = (
            "BONEQC_0_1"
        )

        sop_class_uid = getattr(
            dataset,
            "SOPClassUID",
            None,
        )

        if sop_class_uid is not None:
            file_meta.MediaStorageSOPClassUID = (
                sop_class_uid
            )

        sop_instance_uid = getattr(
            dataset,
            "SOPInstanceUID",
            None,
        )

        if sop_instance_uid is None:
            original = getattr(
                file_meta,
                "MediaStorageSOPInstanceUID",
                None,
            )

            if original:
                sop_instance_uid = self._map_uid(
                    str(original)
                )
            else:
                sop_instance_uid = generate_uid(
                    prefix=None
                )

            dataset.SOPInstanceUID = sop_instance_uid

        file_meta.MediaStorageSOPInstanceUID = (
            dataset.SOPInstanceUID
        )
