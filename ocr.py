from tesserocr import PyTessBaseAPI
import pytesseract
from weighted_levenshtein import lev
import numpy as np
import pandas as pd
import timeit
from PIL import Image, ImageGrab, ImageOps
import skimage
from skimage import filters, morphology
from sklearn.base import BaseEstimator
from sklearn import model_selection

def native_image_to_string(api, image):
    api.SetImage(image)
    return api.GetUTF8Text()


delete_costs = np.ones(128, dtype=np.float64) * 0.1
def cost(result, gt):
    # lev() appears to require ASCII encoding.
    return lev(result.encode("ascii", errors="ignore"), gt, delete_costs=delete_costs)


def binarize_channel(data, threshold_function, correction_block_size):
    threshold = threshold_function(data)
    data = data > threshold
    ubyte_data = skimage.img_as_ubyte(data)
    ubyte_data[ubyte_data == 255] = 1
    histograms = filters.rank.windowed_histogram(ubyte_data,
                                                 morphology.square(correction_block_size),
                                                 n_bins=2)
    assert histograms.shape[2] == 2
    white_background = histograms[:, :, 1] > 0.5
    data = data == white_background
    return data


def preprocess(image, threshold_function, correction_block_size, margin, resize_factor):
    image = ImageOps.expand(image, margin, "white")
    new_size = (image.size[0] * resize_factor, image.size[1] * resize_factor)
    image = image.resize(new_size, Image.NEAREST)
    
    data = np.array(image)
    channels = [binarize_channel(data[:, :, i], threshold_function, correction_block_size)
                for i in range(3)]
    data = np.stack(channels, axis=-1)
    data = np.all(data, axis=-1)
    image = Image.fromarray(data)

    image.load()
    return image


class OcrEstimator(BaseEstimator):
    def __init__(self,
                 threshold_type=None,
                 threshold_block_size=None,
                 correction_block_size=None,
                 margin=None,
                 resize_factor=None):
        self.threshold_type = threshold_type
        self.threshold_block_size = threshold_block_size
        self.correction_block_size = correction_block_size
        self.margin = margin
        self.resize_factor = resize_factor

    def fit(self, X=None, y=None):
        if self.threshold_type == "otsu":
            self.threshold_function_ = lambda data: filters.threshold_otsu(data)
        elif self.threshold_type == "local":
            self.threshold_function_ = lambda data: filters.threshold_local(data, self.threshold_block_size)
        elif self.threshold_type == "niblack":
            self.threshold_function_ = lambda data: filters.threshold_niblack(data, self.threshold_block_size)
        elif self.threshold_type == "sauvola":
            self.threshold_function_ = lambda data: filters.threshold_sauvola(data, self.threshold_block_size)
        else:
            raise ValueError("Unknown threshold type: {}".format(self.threshold_type))

    def score(self, X, y):
        error = 0
        for image, gt_text in zip(X, y):
            image = preprocess(image,
                               threshold_function=self.threshold_function_,
                               correction_block_size=self.correction_block_size,
                               margin=self.margin,
                               resize_factor=self.resize_factor)
            # Assume "api" is set globally. This is easier than making it a
            # param because it does not support deepcopy.
            result = native_image_to_string(api, image)
            error += cost(result, gt_text)
        return -error
            

# Load image and crop.
# bounding_box = (0, 0, 200, 200)
image_path = r"C:\Users\james\Documents\OCR\pillow_docs_cropped.png"
image = Image.open(image_path).convert("RGB")  # .crop(bounding_box)
# image = ImageGrab.grab(bounding_box)

# # Preprocess the image.
# block_size = 51
# threshold_function = lambda data: filters.threshold_local(data, block_size)
# margin = 10
# resize_factor = 4
# preprocessing_time = timeit.timeit("global preprocessed_image; preprocessed_image = preprocess(image, threshold_function, block_size, margin, resize_factor)", globals=globals(), number=1)
# preprocessed_image.save(r"C:\Users\james\Documents\OCR\debug.png")

# Load ground truth.
gt_path = r"C:\Users\james\Documents\OCR\pillow_docs_cropped_gt.txt"
with open(gt_path, "r") as gt_file:
    gt_string = gt_file.read()

# Run OCR.
data_path = r"C:\Program Files\Tesseract-OCR\tessdata"
# data_path = r"C:\Users\james\tessdata_fast"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata_dir_config = r'--tessdata-dir "{}"'.format(data_path)
with PyTessBaseAPI(path=data_path) as api:
    # native_string = None
    # native_time = timeit.timeit("global native_string; native_string = native_image_to_string(api, preprocessed_image)", globals=globals(), number=1)
    # native_cost = cost(native_string, gt_string)
    # binary_string = None
    # binary_time = timeit.timeit("global binary_string; binary_string = pytesseract.image_to_string(preprocessed_image, config=tessdata_dir_config)", globals=globals(), number=1)
    # binary_cost = cost(binary_string, gt_string)
    # print(native_string)
    # print("------------------")
    # print(binary_string)
    # print("preprocessing time: {:f}".format(preprocessing_time))
    # print("native\ttime: {:.2f}\tcost: {:.2f}".format(native_time, native_cost))
    # print("binary\ttime: {:.2f}\tcost: {:.2f}".format(binary_time, binary_cost))

    X = [image]
    y = [gt_string]
    grid_search = model_selection.GridSearchCV(
        OcrEstimator(),
        {
            "threshold_type": ["local", "niblack", "sauvola"],
            "threshold_block_size": [41, 51, 61],
            "correction_block_size": [41, 51, 61],
            "margin": [10],
            "resize_factor": [4],
        },
        cv=model_selection.PredefinedSplit([0] * len(y))
    )
    grid_search.fit(X, y)
    results = pd.DataFrame(grid_search.cv_results_)
    results.set_index("params", inplace=True)
    print(results["mean_test_score"].sort_values(ascending=False))
    print(grid_search.best_params_)
