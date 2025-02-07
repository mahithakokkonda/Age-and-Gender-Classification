import cv2
import os
from time import sleep
import numpy as np
import argparse
from wide_resnet import WideResNet  # Custom-defined class for wide residual network
from keras.utils.data_utils import get_file

class FaceCV(object):  # This is called from the main function to detect age and gender for selected image or face
  
    CASE_PATH = ".\\models\\haarcascade_frontalface_alt.xml"  # Voila-Jones algorithm (Haar Cascade classifier)
    WRN_WEIGHTS_PATH = ".\\models\\weights.18-4.06.hdf5"  # Wide Residual Network

    def __new__(cls, weight_file=None, depth=16, width=8, face_size=64):
        if not hasattr(cls, 'instance'):
            cls.instance = super(FaceCV, cls).__new__(cls)
        return cls.instance

    def __init__(self, depth=16, width=8, face_size=64):
        self.face_size = face_size
        self.model = WideResNet(face_size, depth=depth, k=width)()
        model_dir = os.path.join(os.getcwd(), "models").replace("//", "\\")
        fpath = get_file('weights.18-4.06.hdf5',
                         self.WRN_WEIGHTS_PATH,
                         cache_subdir=model_dir)
        self.model.load_weights(fpath)

    @classmethod
    def draw_label(cls, image, point, label, font=cv2.FONT_HERSHEY_SIMPLEX,
                   font_scale=1, thickness=2):
        size = cv2.getTextSize(label, font, font_scale, thickness)[0]
        x, y = point
        cv2.rectangle(image, (x, y - size[1]), (x + size[0], y), (0, 255, 0), cv2.FILLED)
        cv2.putText(image, label, point, font, font_scale, (0, 0, 0), thickness)

    def crop_face(self, imgarray, section, margin=40, size=64):
        img_h, img_w, _ = imgarray.shape
        if section is None:
            section = [0, 0, img_w, img_h]
        (x, y, w, h) = section
        margin = int(min(w, h) * margin / 100)
        x_a = x - margin
        y_a = y - margin
        x_b = x + w + margin
        y_b = y + h + margin
        if x_a < 0:
            x_b = min(x_b - x_a, img_w-1)
            x_a = 0
        if y_a < 0:
            y_b = min(y_b - y_a, img_h-1)
            y_a = 0
        if x_b > img_w:
            x_a = max(x_a - (x_b - img_w), 0)
            x_b = img_w
        if y_b > img_h:
            y_a = max(y_a - (y_b - img_h), 0)
            y_b = img_h
        cropped = imgarray[y_a: y_b, x_a: x_b]
        resized_img = cv2.resize(cropped, (size, size), interpolation=cv2.INTER_AREA)
        resized_img = np.array(resized_img)
        return resized_img, (x_a, y_a, x_b - x_a, y_b - y_a)

    def detect_face(self):
        face_cascade = cv2.CascadeClassifier(self.CASE_PATH)

        # 0 means the default video capture device in OS
        video_capture = cv2.VideoCapture(0)

        # Initialize lists to store predictions for stabilization
        age_predictions = []
        gender_predictions = []
        max_store = 5  # Number of frames to average

        while True:
            if not video_capture.isOpened():
                sleep(5)
            
            ret, frame = video_capture.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=10,
                minSize=(self.face_size, self.face_size)
            )

            # Placeholder for cropped faces
            face_imgs = np.empty((len(faces), self.face_size, self.face_size, 3))
            for i, face in enumerate(faces):
                face_img, cropped = self.crop_face(frame, face, margin=40, size=self.face_size)
                (x, y, w, h) = cropped
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                face_imgs[i, :, :, :] = face_img

            if len(face_imgs) > 0:
                results = self.model.predict(face_imgs)
                predicted_genders = results[0]
                ages = np.arange(0, 101).reshape(101, 1)
                predicted_ages = results[1].dot(ages).flatten()

                # Store predictions and keep only the last 'max_store' results
                age_predictions.append(predicted_ages)
                gender_predictions.append(predicted_genders)
                if len(age_predictions) > max_store:
                    age_predictions.pop(0)
                    gender_predictions.pop(0)

                # Average predictions
                avg_ages = np.mean(age_predictions, axis=0)
                avg_genders = np.mean(gender_predictions, axis=0)

            for i, face in enumerate(faces):
                label = "{}, {}".format(int(avg_ages[i]),
                                        "F" if avg_genders[i][0] > 0.5 else "M")
                self.draw_label(frame, (face[0], face[1]), label)

            cv2.imshow('Predicted Faces', frame)
            
            # Add a delay to control frame rate
            sleep(0.05)  # Adjust the value as needed
            
            if cv2.waitKey(5) == 27:  # ESC key press
                break
        
        # When everything is done, release the capture
        video_capture.release()
        cv2.destroyAllWindows()

def get_args():
    parser = argparse.ArgumentParser(description="Estimates age and gender for the detected faces.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--depth", type=int, default=16,
                        help="Depth of network")
    parser.add_argument("--width", type=int, default=8,
                        help="Width of network")
    args = parser.parse_args()
    return args

def main():
    args = get_args()
    depth = args.depth
    width = args.width

    face = FaceCV(depth=depth, width=width)

    face.detect_face()

if __name__ == "__main__":
    main()
