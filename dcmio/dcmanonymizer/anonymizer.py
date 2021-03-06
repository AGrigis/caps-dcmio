#! /usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################################
# NSAP - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# anonymizer dicom
import dicom
import os
import json


def anonymize_dicom(input_file, output_file, new_uid="anonymous",
                    remove_curves=True, remove_private_tags=False,
                    remove_overlays=True, generate_log=False):

    """ Function to anonymize DICOM

    .. note::

        Some fields (type 2 and 3) are removed, others are emptyed using their
        tag names.
        All private tags are removed too if necessary (parameters)

    Parameters
    ----------
    inputs :
        input_file: String (mandatory), a dicom filepath: the dicom file to
            process
        output_file: String (mandatory) the file to generate
        new_uid : string (optional): a value to set as participant name and
                  identifier. Default="anonymous"
        remove_curves: boolean (optional): anonymize or not the curves fields.
            Default=True
        remove_private_tags: boolean (optional): remove all provate tags. This
            may create conversion problems. Default=False
        remove_overlays: boolean (optional): remove all overlays if any.
            Default=True
        generate_log: boolean(optional): create a json file with all modified
            fields. Default=True

    Returns
    -------
    anonymized dicom path
    dictionary of modified fields path (if asked)

    <process>
        <return name="output_dicom" type="File" desc="anonymized dicom path" />
        <return name="json_log" type="File" desc="dictionary of modified
        fields path (if asked)" />
        <input name="input_file" type="File" desc="the dicom file to
            process" />
        <input name="output_file" type="File" desc="the file to generate" />
        <input name="new_uid" type="String" desc="a value to set as
            participant name and identifier (optional, default='anonymous')"
            optional="True" />
        <input name="remove_curves" type="Bool" desc="anonymize or not the
            curves fields (optional, default='True')" optional="True" />
        <input name="remove_private_tags" type="Bool" desc="move all private
            tags. This may create conversion problems (optional,
            default='False')"  optional="True" />
        <input name="remove_overlays" type="Bool" desc="remove all overlays
            if any (optional, default='True')" optional="True" />
        <input name="generate_log" type="Bool" desc="create a json file with
            all modified fields (optional, default='False')" optional="True" />
    </process>
    """

    # load the dataset
    dataset = dicom.read_file(input_file)

    # create dictionnaries of deleted/erased elements
    dictionary_removed_private = {}
    dictionary_removed_public = {}
    dictionary_blank_public = {}
    dictionary_patient_name = {}
    dictionary_diffusion = {}
    # Last dictionary : curve, overlay ... can be in public and private fields
    # walking the wholde dataset to erase them
    dictionary_other = {}

    # Define call-back functions for the dataset.walk() function
    def PN_callback(dataset, data_element):
        """Called from the dataset "walk" recursive function for all
        data elements."""
        if data_element.VR == "PN":
            dictionary_patient_name[repr(data_element.tag)] = repr(
                data_element.value)
            data_element.value = new_uid

    def curves_callback(dataset, data_element):
        """Called from the dataset "walk" recursive function for
        all data elements."""
        if data_element.tag.group == 0x5000:
            dictionary_other[repr(data_element.tag)] = repr(data_element.value)
            del dataset[data_element.tag]

    def private_callback(dataset, data_element):
        """Called from the dataset "walk" recursive function for
        all data elements."""
        if data_element.tag.is_private:
            dictionary_removed_private[repr(data_element.tag)] = repr(
                data_element.value)
            del dataset[data_element.tag]

    def overlay_callback(dataset, data_element):
        """Called from the dataset "walk" recursive function for
        all data elements."""
        if "verlay" in data_element.name:
            dictionary_other[repr(data_element.tag)] = repr(data_element.value)
            del dataset.data_element.tag

    def fields40_callback(dataset, data_element):
        """Called from the dataset "walk" recursive function for
        all data elements."""
        if data_element.tag.group == 0x0040:
            dictionary_removed_public[repr(data_element.tag)] = repr(
                data_element.value)
            dataset[data_element.tag].value = ""

    # Remove patient name and any other person names
    dataset.walk(PN_callback)

    # Remove 0040 fields group
    dataset.walk(fields40_callback)

    # Change ID
    dataset.PatientID = new_uid

    # Remove data elements in dicom_tag_to_remove
    for tag_name, tag in dicom_tag_to_remove.iteritems():
        if tag_name in dataset:
            dictionary_removed_public[repr(tag)] = repr(
                dataset.data_element(tag_name).value)
            delattr(dataset, tag_name)

    # Blank data elements in dicom_tag_to_blank
    for tag_name, tag in dicom_tag_to_blank.iteritems():
        if tag_name in dataset:
            dictionary_blank_public[repr(tag)] = repr(
                dataset.data_element(tag_name).value)
            dataset.data_element(tag_name).value = ""

    # Remove curves
    if remove_curves:
        dataset.walk(curves_callback)

    # Remove overlay
    if remove_overlays:
        dataset.walk(overlay_callback)

    # Remove private tags
    if remove_private_tags:
        dataset.walk(private_callback)

    dictionary = {'removed_private': dictionary_removed_private,
                  'removed_public': dictionary_removed_public,
                  'blank_public': dictionary_blank_public,
                  'diffusion': dictionary_diffusion,
                  'patient_name': dictionary_patient_name,
                  'misc': dictionary_other}

    dataset.save_as(output_file)

    if generate_log:
        json_path = os.path.join(
            os.path.dirname(output_file),
            "{0}.json".format(os.path.basename(output_file).split(".")[0]))

        with open(json_path, "w") as _file:
            json.dump(dictionary, _file)
    else:
        json_path = ""
    return output_file, json_path


##############################################################
#             De-identification dictionaries
##############################################################

# dicom type 3 element: optional
dicom_tag_to_remove = {
    "AcquisitionDate": (0x0008, 0x0022),
    "OperatorsName": (0x0008, 0x1070),
    "PerformingPhysicianName": (0x0008, 0x1050),
    "InstitutionalDepartmentName": (0x0008, 0x1040),
    "PhysiciansOfRecord": (0x0008, 0x1048),
    "PhysiciansOfRecordIdentificationSequence": (0x0008, 0x1049),
    "PerformingPhysicianIdentificationSequence": (0x0008, 0x1052),
    "OperatorIdentificationSequence": (0x0008, 0x1072),
    "ReferringPhysicianAddress": (0x0008, 0x0092),
    "ReferringPhysicianTelephoneNumbers": (0x0008, 0x0094),
    "ReferringPhysicianIdentificationSequence": (0x0008, 0x0096),
    "InstitutionName": (0x0008, 0x0080),
    "InstitutionAddress": (0x0008, 0x0081),
    "InstanceCreationDate": (0x0008, 0x0012),
    "OtherPatientIDs": (0x0010, 0x1000),
    "OtherPatientNames": (0x0010, 0x1001),
    "PatientComments": (0x0010, 0x4000),
    "DateOfSecondaryCapture": (0x0018, 0x1012),
    "RequestingService": (0x0032, 0x1033)}

# dicom type 2 element: mandatory but not really usefull
dicom_tag_to_blank = {
    "ClinicalTrialCoordinatingCenterName": (0x0012, 0x0060),
    "PatientIdentityRemoved": (0x0012, 0x0062),
    "ClinicalTrialSubjectReadingID": (0x0012, 0x0042),
    "ClinicalTrialSponsorName": (0x0012, 0x0010),
    "ClinicalTrialSubjectID": (0x0012, 0x0040),
    "ClinicalTrialSiteName": (0x0012, 0x0031),
    "ClinicalTrialSiteID": (0x0012, 0x0030),
    "AdditionalPatientHistory": (0x0010, 0x21B0),
    "PatientReligiousPreference": (0x0010, 0x21F0),
    "ResponsiblePerson": (0x0010, 0x2297),
    "ResponsiblePersonRole": (0x0010, 0x2298),
    "ResponsibleOrganization": (0x0010, 0x2299),
    "BranchOfService": (0x0010, 0x1081),
    "MedicalRecordLocator": (0x0010, 0x1090),
    "MedicalAlerts": (0x0010, 0x2000),
    "Allergies": (0x0010, 0x2110),
    "CountryOfResidence": (0x0010, 0x2150),
    "RegionOfResidence": (0x0010, 0x2152),
    "PatientTelephoneNumber": (0x0010, 0x2154),
    "MilitaryRank": (0x0010, 0x1080),
    "PatientMotherBirthName": (0x0010, 0x1060),
    "PatientAddress": (0x0010, 0x1040),
    "PatientBirthName": (0x0010, 0x1005),
    "IssuerOfPatientID": (0x0010, 0x0021),
    "ReferringPhysicianName": (0x0008, 0x0090),
    "ContentDate": (0x0008, 0x0023),
    "AcquisitionDatetime": (0x0008, 0x002A),
    "SeriesDate": (0x0008, 0x0021),
    "StudyDate": (0x0008, 0x0020),
    "PatientBirthDate": (0x0010, 0x0030),
    "StationName": (0x0008, 0x1010),
    "PatientID": (0x0010, 0x0020),
    "StudyDescription": (0x0010, 0x1030),
    "ManufacturerModelName": (0x0008, 0x1090),
    "DeviceSerialNumber": (0x0018, 0x1000)}
