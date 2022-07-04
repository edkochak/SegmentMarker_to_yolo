from pprint import pprint
import shutil
import xml.etree.ElementTree as ET
import os
import re
import json
import imagesize
import yaml
import argparse


def parse_data(path):
    opencv_storage = ET.parse(path).getroot()
    classes_info = opencv_storage.find('ClassInfoArray')
    frame_data = opencv_storage.find('FrameDataArray')

    classes = []
    for clas in classes_info.findall('_'):
        classes.append({})
        classes[-1]['class_name'] = clas.find('className').text.strip()
        classes[-1]['type'] = clas.find('type').text.strip()
        classes[-1]['subType'] = (clas.findall('subType') or clas.findall('flags'))[
            0].text.strip()
        classes[-1]['color'] = clas.find('color').text.strip()

    data = {}
    for frame in frame_data.findall('_'):

        frame_id = frame.find('FrameNumber').text.strip()

        for obj in frame.find('FrameObjects'):
            if frame_id not in data:
                data[frame_id] = []
            data[frame_id].append({})

            data[frame_id][-1]['type'] = obj.find('type').text.strip()
            data[frame_id][-1]['rect'] = obj.find('rect').text.strip()
            if obj.findall('subType')== [] and obj.findall('flags') == []:
                data[frame_id].pop()
                continue
            elif obj.findall('subType') == []:
                data[frame_id][-1]['subtype'] = obj.findall('flags')[
                    0].text.strip()
            else:
                data[frame_id][-1]['subtype'] = obj.findall('subType')[
                    0].text.strip()

            data[frame_id][-1]['vertices'] = obj.find('vertices').text.strip()

    return classes, data


def create_yaml(result, classes_data, path_to_train_images, path_to_val_images):

    data = {
        'names': classes_data,
        'nc': len(classes_data),
        'path': '..',
        'train': path_to_train_images,
        'val': path_to_val_images,
    }

    with open(os.path.join(result, 'dataset.yaml'), 'w') as f:
        yaml.dump(data, f, default_flow_style=False)


def transfer(source, result, count_test, one_class=None):
    re_seasons = '\w+.\d{3}'
    re_episode_frames = '\w+.\d{3}.\d{3}.\w+'

    path_to_train_labels = os.path.join(result, 'train', 'labels')
    path_to_train_images = os.path.join(result, 'train', 'images')
    os.makedirs(path_to_train_labels)
    os.makedirs(path_to_train_images)
    path_to_val_labels = os.path.join(result, 'val', 'labels')
    path_to_val_images = os.path.join(result, 'val', 'images')
    os.makedirs(path_to_val_labels)
    os.makedirs(path_to_val_images)

    with open(os.path.join(source, '#classes.json'), 'r') as f:
        classes_data = json.loads(f.read())

    # Парсим классы
    if one_class is None:
        classes_data = [(item.get("subType")or item.get("subtype")) or str(item.get("flags")) 
                        for item in classes_data[0]['classes']]
        
    else:
        classes_data = [one_class]
    # создаем yaml файл
    print(classes_data)
    create_yaml(result, classes_data, path_to_train_images, path_to_val_images)

    count = 1
    for season in filter(lambda x: re.fullmatch(re_seasons, x), os.listdir(source)):
        i_season = season.split('.')[1]
        season_name = season.split('.')[0]

        path_to_season = os.path.join(source, season)
        files_in_season = os.listdir(path_to_season)

        for episode in filter(lambda x: re.fullmatch(re_episode_frames, x), files_in_season):
            path_to_episode_frames = os.path.join(path_to_season, episode)
            mark = episode.split('.')[3]
            i_episode = episode.split('.')[2]

            re_episode_data = f'{episode}.\w+.dat'
            # находим нужную папку с xml файлом
            check = list(filter(lambda file: re.fullmatch(
                re_episode_data, file), files_in_season))
            if check:
                # находим нужный xml файл
                path_to_episode_data = os.path.join(
                    path_to_season, check[0], '.'.join(check[0].split('.')[:-1])+'.markup.xml')
                classes, data = parse_data(path_to_episode_data)

                files_in_episode = os.listdir(path_to_episode_frames)
                for i_file in data:
                    # первые count_test изображений это тестовые, остальные для тренировки
                    if count > count_test:
                        path_to_images = path_to_train_images
                        path_to_labels = path_to_train_labels
                    else:
                        path_to_images = path_to_val_images
                        path_to_labels = path_to_val_labels

                    re_frame = '\w+.\d{3}.\d{3}.\w+.' + \
                        f'{int(i_file):06d}'+'.\w+'
                    # находим нужный кадр
                    file = list(filter(lambda file: re.fullmatch(
                        re_frame, file), files_in_episode))[0]
                    file_format = file.split('.')[-1]
                    new_file_name = f'{count}.{file_format}'
                    path_to_frame = os.path.join(path_to_episode_frames, file)
 
                    # копируем фотографию
                    shutil.copy(path_to_frame, os.path.join(
                        path_to_images, new_file_name))
                    width, height = imagesize.get(path_to_frame)

                    label_text = []

                    for obj in data[i_file]:
                        
                        vertices = list(map(int, obj.get('vertices').split()))
                        if one_class is None:
                            class_id = classes_data.index(obj['subtype'])
                        else:
                            class_id = 0


                        #Абсолютные координаты -> относительные
                        for n, vert in enumerate(vertices):
                            if n % 2 == 0:
                                vertices[n] = str(round(vert/width, 4))
                            else:
                                vertices[n] = str(round(vert/height, 4))
                        label_text.append(f'{class_id} {" ".join(vertices)}')
                    # записываем данные
                    with open(os.path.join(path_to_labels, f'{count}.txt'), 'w') as f:
                        f.write('\n'.join(label_text))

                    count += 1

            else:
                ...


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SegmentMarker to YoloV5")
    parser.add_argument("-source", required=True,
                        help='Путь до датасета SegmentMarker')
    parser.add_argument("-result", default='result',
                        help='Путь, где будет находиться итоговый датасет')
    parser.add_argument("-count_test", type=int, default=0,
                        help='Количество кадров в test датасете')
    parser.add_argument("-one_class", default=None,
                        help='Название класса, который будет включать в себе все остальные')

    args = parser.parse_args()

    transfer(args.source, args.result, args.count_test, args.one_class)
