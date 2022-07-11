import os
import shutil
import numpy as np

source = r"C:\work\parse\photos"
result = 'blb_city'
serial_name = 'blb'

os.mkdir(result)

data = os.listdir(source)

n_photos = len(data)

max_frames = 100
max_episode = 999
mark = 'left'
n_seasons = int(np.ceil(n_photos/(max_frames*max_episode)))
season1 = 2
for season in range(n_seasons):
    path_to_season = os.path.join(result, f'{serial_name}.{season1+1:03d}')
    os.mkdir(path_to_season)
    n_episode = int(min(max_episode, np.ceil(
        n_photos/max_frames-max_episode*season)))
    for episode in range(n_episode):
        path_to_episode_frames = os.path.join(
            path_to_season, f'{serial_name}.{season1+1:03d}.{episode+1:03d}.{mark}')
        os.mkdir(path_to_episode_frames)
        n_frames = int(min(max_frames, np.ceil(
            n_photos-(max_episode*season+episode)*max_frames)))
        for frame in range(n_frames):
            file = data.pop()
            file_format = file.split('.')[-1]
            if file_format == 'jpeg':
                file_format = 'jpg'
            shutil.copy(os.path.join(source, file), os.path.join(
                path_to_episode_frames, f'{serial_name}.{season1+1:03d}.{episode+1:03d}.{mark}.{frame:06d}.{file_format}'))
