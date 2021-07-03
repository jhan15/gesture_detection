"""
Control volume by hand gestures.

Usage:
    $ python3 vol_controller.py --control continuous
"""

import argparse
import cv2
import numpy as np
import time
from osascript import osascript

from gesture import GestureDetector
from utils.utils import two_landmark_distance, draw_vol_bar, draw_landmarks
from utils.utils import update_trajectory, check_trajectory


CAM_W = 640                                 # camera width
CAM_H = 480                                 # camera height
TEXT_COLOR = (102,51,0)                     # text color
LINE_COLOR_HIGH = (0,0,255)                 # landmark color high
LINE_COLOR_LOW = (0,255,0)                  # landmark color low
VOL_RANGE = [0, 100]                        # system volume range
BAR_X_RANGE = [350, 550]                    # bar x position range
LEN_RANGE = [20, 150]                       # range of thumb and index fingertips
STEP_THRESHOLD = [30, 130]                  # threshold of step control


def vol_control(control='continuous', step=10, traj_size=10):
    cap = cv2.VideoCapture(0)
    cap.set(3, CAM_W)
    cap.set(4, CAM_H)
    ges_detector = GestureDetector(max_num_hands=1)

    vol = (VOL_RANGE[0] + VOL_RANGE[1]) // 2
    vol_bar = (BAR_X_RANGE[0] + BAR_X_RANGE[1]) // 2
    osascript("set volume output volume {}".format(vol))

    ptime = 0
    ctime = 0
    window_name = 'Volume controller'
    trajectory = list()
    joint1, joint2 = 4, 8
    activated = False

    while True:
        _, img = cap.read()
        img = cv2.flip(img, 1)
        detected_gesture = ges_detector.detect_gesture(img, 'single')

        if detected_gesture == 'C shape' or detected_gesture == 'Pinch':
            ges_detector.draw_gesture_box(img)

        if detected_gesture == 'Pinch':
            activated = True
        if activated and detected_gesture == 'C shape':
            activated = False
        
        if activated:
            hands = ges_detector.hand_detector.decoded_hands
            if hands:
                # control
                hand = hands[-1]
                landmarks = hand['landmarks']
                pt1 = landmarks[joint1][:2]
                pt2 = landmarks[joint2][:2]
                length = two_landmark_distance(pt1, pt2)
                
                # continuous control mode
                if control == 'continuous':
                    draw_landmarks(img, pt1, pt2)
                    finger_states = ges_detector.check_finger_states(hand)
                    if finger_states[4] > 2:
                        vol = np.interp(length, LEN_RANGE, VOL_RANGE)
                        vol_bar = np.interp(length, LEN_RANGE, BAR_X_RANGE)
                        osascript("set volume output volume {}".format(vol))

                # step control mode
                if control == 'step':
                    if length > STEP_THRESHOLD[1]:
                        draw_landmarks(img, pt1, pt2, LINE_COLOR_HIGH)
                    elif length < STEP_THRESHOLD[0]:
                        draw_landmarks(img, pt1, pt2, LINE_COLOR_LOW)
                    else:
                        draw_landmarks(img, pt1, pt2)

                    trajectory = update_trajectory(length, trajectory, traj_size)
                    up = False
                    down = False

                    if len(trajectory) == traj_size and length > STEP_THRESHOLD[1]:
                        up = check_trajectory(trajectory, direction=1)
                        if up:
                            vol = min(vol + step, VOL_RANGE[1])
                            osascript("set volume output volume {}".format(vol))
                    if len(trajectory) == traj_size and length < STEP_THRESHOLD[0]:
                        down = check_trajectory(trajectory, direction=-1)
                        if down:
                            vol = max(vol - step, VOL_RANGE[0])
                            osascript("set volume output volume {}".format(vol))
                    if up or down:
                        vol_bar = np.interp(vol, VOL_RANGE, BAR_X_RANGE)
                        trajectory = []           
             
        ctime = time.time()
        fps = 1 / (ctime - ptime)
        ptime = ctime
        
        draw_vol_bar(img, vol_bar, vol, BAR_X_RANGE)
        cv2.putText(img, f'FPS: {int(fps)}', (30,40), 0, 0.8,
                    TEXT_COLOR, 2, lineType=cv2.LINE_AA)
        if activated:
            cv2.putText(img, f'Volume controller activated!', (100,80), 0, 0.8,
                        (0,255,0), 2, lineType=cv2.LINE_AA)
        else:
            cv2.putText(img, f'Volume controller de-activated!', (100,80), 0, 0.8,
                        (0,0,255), 2, lineType=cv2.LINE_AA)
        cv2.imshow(window_name, img)
        key = cv2.waitKey(1)
        if key == ord('q'):
            cv2.destroyAllWindows()
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--control', type=str, default='continuous')
    parser.add_argument('--step', type=int, default=10)
    parser.add_argument('--traj_size', type=int, default=10)
    opt = parser.parse_args()

    vol_control(**vars(opt))
    