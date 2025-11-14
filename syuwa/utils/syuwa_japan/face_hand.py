#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pprint
import csv
import copy
import itertools
from collections import Counter
import cv2 as cv
import numpy as np
import mediapipe as mp
import datetime

from utils import CvFpsCalc
from utils import draw
from utils import hand
from model import KeyPointClassifier


def main():
    # 処理用の変数 #
    mode = 0
    out_no = 87
    v = hand.Variables(out_no)

    # モデルロード #
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.5,)
    keypoint_classifier = KeyPointClassifier("model/keypoint_classifier/hand_keypoint_classifier.tflite")

    # 動画撮影時の顔隠し用にfaceを使用 #
    img_ama = cv.imread("ama.png", cv.IMREAD_UNCHANGED)
    mp_face = mp.solutions.face_mesh
    face = mp_face.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    # ラベル読み込み #
    with open('model/keypoint_classifier/hand_keypoint_classifier_label.csv', encoding='utf-8-sig') as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [row[0] for row in keypoint_classifier_labels]

    # カメラ準備 #
    cap = cv.VideoCapture(0)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 540)

    # FPS計測モジュール #
    cvFpsCalc = CvFpsCalc(buffer_len=10)

    # 処理開始# 
    while True:
        fps = cvFpsCalc.get()

        # キー処理(ESC：終了) #
        key = cv.waitKey(5)
        if key == 27: break #ESC
        number, mode = select_mode(key, mode)

        # カメラキャプチャ #
        ret, image = cap.read()
        if not ret: break
        image = cv.flip(image, 1)  # ミラー表示
        debug_image = copy.deepcopy(image)

        # 検出実施 #
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = hands.process(image)
        face_results = face.process(image)
        image.flags.writeable = True

        # 顔を隠す処理 #
        if face_results.multi_face_landmarks:
            for face_landmarks in face_results.multi_face_landmarks:
                face_brect = calc_bounding_rect(image, face_landmarks)
                debug_image = draw.overlay_Image(debug_image, img_ama, face_brect)

        # 手の処理 #
        if results.multi_hand_landmarks is not None and mode != 9:
            left_fg, right_fg = 0,0
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                # 外接矩形の計算、ランドマークの計算、相対座標・正規化座標への変換、学習データ保存 #
                brect = calc_bounding_rect(debug_image, hand_landmarks)
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)
                pre_processed_landmark_list = pre_process_landmark(landmark_list)
                logging_csv(number, mode, pre_processed_landmark_list)

                # 手型分類、左手は入力文字を1文字削除するフラグとして使用 #
                if handedness.classification[0].label[0:] == "Left":
                    left_fg = 1
                    v.hand_sign_id = out_no

                # 手型分類、右手のみ、ひらがな入力 #
                else:
                    right_fg = 1
                    #手型分類、分類後のパターンマッチのために上下左右のランドマークポイント取得 #
                    v.hand_sign_id = keypoint_classifier(pre_processed_landmark_list)
                    landmark_tips = get_landmark_tips(image,hand_landmarks)
                    
                    #手型判定 #
                    v.get_hand_sign_id(landmark_tips,hand_landmarks)

                    #濁音、半濁音等のために手の動きを判定 #
                    landmarks_ave = calc_landmarks_ave(hand_landmarks)
                    v.get_move_id(hand_landmarks, landmarks_ave)

                    #手型＋動きで判定 #
                    v.fix_hand_sign_id()

                    #入力判定 #
                    if left_fg == 0: v.get_input_letters(keypoint_classifier_labels)

                # 手型の判定結果描画 #
                brect_center = calc_brect_center(brect)
                v.input_letters_position_x = round(brect_center[0])
                debug_image = draw.draw_landmarks(debug_image, landmark_list)
                debug_image = draw.draw_jp_brect(debug_image, brect, keypoint_classifier_labels[v.hand_sign_id])

            # 両手を検出しているときは入力文字を1文字ずつ削除 # 
            if left_fg == 1 and right_fg == 1:
                v.hand_sign_id = out_no -1
                if get_tm_int() - v.del_lock_tm > 100 and 2 <= len(v.input_letters):
                    v.input_letters = v.input_letters[:-2] + v.input_letters[-1]
                    v.del_lock_tm = get_tm_int() 
        # 手を認識していないときは入力文字を全削除 #
        else:
            if get_tm_int() - v.del_lock_tm > 300:
                v.input_letters = "" 
                v.del_lock_tm = get_tm_int()

        # fps、入力モード、入力時の番号、手型入力結果の描画
        debug_image = draw.draw_info(debug_image, fps, mode, number)
        debug_image = draw.draw_jp_input_letters(debug_image, v.input_letters)
        
        # 画面反映 #############################################################
        cv.imshow('Hand Gesture Recognition', debug_image)

    # 終了処理 #
    cap.release()
    face.close()
    hands.close()
    cv.destroyAllWindows()


def get_tm_int():
    return int(datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:16])

def get_landmark_tips(image, landmarks):
    up_num, down_num, left_num, right_num = 0,0,0,0
    up_base, down_base, left_base, right_base = image.shape[0], 0 ,image.shape[1], 0
    for i,landmark in enumerate(landmarks.landmark):
        if up_base >= landmark.y:
            up_num, up_base = i, landmark.y
        if down_base <= landmark.y:
            down_num, down_base = i, landmark.y
        if left_base >= landmark.x:
            left_num, left_base = i, landmark.x
        if right_base <= landmark.x:
            right_num, right_base = i, landmark.x
    return [up_num, down_num, left_num, right_num]

def select_mode(key, mode):
    number = -1
    if 48 <= key <= 57:  # 0 ~ 9
        number = key - 48
    if key == 110:  # n
        mode = 0
    if key == 107:  # k
        mode = 1
    if key == ord("s"):
        mode = 9
    return number, mode

def calc_bounding_rect(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_array = np.empty((0, 2), int)
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_point = [np.array((landmark_x, landmark_y))]
        landmark_array = np.append(landmark_array, landmark_point, axis=0)
    x, y, w, h = cv.boundingRect(landmark_array)
    return [x, y, x + w, y + h]

def calc_brect_center(brect):
    center_x = (brect[0] + brect[2]) /2
    center_y = (brect[1] + brect[3]) /2
    return [center_x , center_y]
    
def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_point = []
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_z = landmark.z
        landmark_point.append([landmark_x, landmark_y, landmark_z])
    return landmark_point

def calc_landmarks_ave(landmarks):
    sum_x, sum_y, sum_z = 0,0,0
    for _, landmark in enumerate(landmarks.landmark):
        sum_x = sum_x + landmark.x
        sum_y = sum_y + landmark.y
        sum_z = sum_z + landmark.z
    ave_x, ave_y, ave_z = sum_x/21, sum_y/21, sum_z/21
    return [ave_x, ave_y, ave_z]

def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)
    # 相対座標に変換
    base_x, base_y, base_z = 0, 0, 0
    for index, landmark_point in enumerate(temp_landmark_list):
        if index == 0:
            base_x, base_y, base_z = landmark_point[0], landmark_point[1], landmark_point[2]
        temp_landmark_list[index][0] = temp_landmark_list[index][0] - base_x
        temp_landmark_list[index][1] = temp_landmark_list[index][1] - base_y
        temp_landmark_list[index][2] = (temp_landmark_list[index][2] - base_z)*200
    # 1次元リストに変換
    temp_landmark_list = list(
        itertools.chain.from_iterable(temp_landmark_list))
    # 正規化
    max_value = max(list(map(abs, temp_landmark_list)))
    def normalize_(n): return n / max_value
    temp_landmark_list = list(map(normalize_, temp_landmark_list))
    return temp_landmark_list

def logging_csv(number, mode, landmark_list):
    if mode == 0: pass
    if mode == 1 and (0 <= number <= 9):
        csv_path = 'model/keypoint_classifier/keypoint.csv'
        with open(csv_path, 'a', newline="") as f:
            writer = csv.writer(f)
            writer.writerow([number, *landmark_list])


if __name__ == '__main__':
    main()
