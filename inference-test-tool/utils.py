import os
import tempfile
from functools import cmp_to_key
from pathlib import Path
import pydicom
from pydicom.errors import InvalidDicomError
import numpy as np
import SimpleITK as sitk
from PIL import Image


class DCM_Image:
    def __init__(self, instanceUID, position, orientation, path):
        self.instanceUID = instanceUID
        self.position = position
        self.orientation = orientation
        self.path = path

    def direction(self):
        if self.orientation is None:
            return None
        row0 = self.orientation[0:3]
        row1 = self.orientation[3:6]
        return np.cross(row0, row1)


def convert_image_to_dicom(image_file):
    """Read an image file, convert it to Dicom and return the file path"""

    # Load pixel array from image.
    img = Image.open(image_file)
    pix = np.array(img)

    # Write pixel array to Dicom file.
    stk = sitk.GetImageFromArray(pix)
    writer = sitk.ImageFileWriter()
    writer.KeepOriginalImageUIDOn()
    dicom_file = tempfile.NamedTemporaryFile().name + '.dcm'
    writer.SetFileName(dicom_file)
    writer.Execute(stk)

    return dicom_file


def load_image_data(folder):
    # Load all files in 'folder' as DICOM files
    images = []
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            file_path = str(file_path)

            try:
                dcm = pydicom.dcmread(file_path)
            except InvalidDicomError:
                # File is not a valid Dicom file. Assume it is an
                # image, convert it to Dicom, and retry loading it.
                print(file_path)
                file_path = convert_image_to_dicom(file_path)
                dcm = pydicom.dcmread(file_path)

            position = dcm.ImagePositionPatient if 'ImagePositionPatient' in dcm else None
            orientation = dcm.ImageOrientationPatient if 'ImageOrientationPatient' in dcm else None
            images.append(DCM_Image(dcm.SOPInstanceUID, position, orientation, file_path))
        elif os.path.isdir(file_path):
            images.extend(load_image_data(file_path))
    return images


def sort_images(images):
    pos = images[0].position
    direction = images[0].direction()

    if pos is None or direction is None:
        return images

    return sorted(images, key=cmp_to_key(
        lambda item1, item2: np.dot(np.subtract(np.array(item1.position), np.array(pos)), direction) -
                             np.dot(np.subtract(np.array(item2.position), np.array(pos)), direction)))


def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
