#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import time
from PIL import Image
import numpy as np


cached_avgs = []


class ProgressCounter:
    def __init__(self, total):
        self.total = total
        self.counter = 0

    def update(self):
        self.counter += 1
        sys.stdout.write(f'{100 * self.counter // self.total}%\r')
        sys.stdout.flush()


def get_target(image, tile_size, scale=1):
    img = Image.open(image)
    w = img.width * scale
    h = img.height * scale
    img_large = img.resize((w, h), Image.ANTIALIAS)

    w_rem = (w % tile_size[0]) // 2
    h_rem = (h % tile_size[0]) // 2
    if w_rem or h_rem:
        img_large = img_large.crop((w_rem, h_rem, w - w_rem, h - h_rem))
    return img_large


def process_tile(tile, tile_size):
    w, h = tile.size
    min_dim = min(w, h)
    w_crop = (w - min_dim) // 2
    h_crop = (h - min_dim) // 2
    box = (w_crop, h_crop, w - w_crop, h - h_crop)
    tile = tile.resize(tile_size, Image.ANTIALIAS, box=box)
    return tile


def get_tiles(tiles_path, tile_size, mode):
    tiles = []
    print('Getting tiles...')
    files = os.listdir(tiles_path)
    progress = ProgressCounter(len(files))
    for file in files:
        tile = Image.open(os.path.join(tiles_path, file)).convert(mode)
        tile = process_tile(tile, tile_size)
        tiles.append(tile)
        progress.update()
    print('Done.')
    return tiles


def avg_rgb(image):
    img = image.resize((1, 1), Image.ANTIALIAS)
    return img.getpixel((0, 0))


def gridify(image, tile_size):
    w, h = tile_size
    rows = image.height // h
    cols = image.width // w
    grid = []
    for i in range(rows):
        row_tiles = []
        for j in range(cols):
            grid_tile = image.crop((j * w, i * h, (j + 1) * w, (i + 1) * h))
            row_tiles.append(grid_tile)
        grid.append(row_tiles)
    return grid


def error(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return np.sum(np.subtract(x, y) ** 2)


def find_best_match(target, tiles, method):
    if method == 'avg':
        target_avg = avg_rgb(target)
        min_err = float('inf')
        best_match = None

        if not cached_avgs:
            for tile in tiles:
                tile_avg = avg_rgb(tile)
                cached_avgs.append(tile_avg)
                err = error(target_avg, tile_avg)
                if err < min_err:
                    min_err = err
                    best_match = tile
        else:
            for avg in cached_avgs:
                err = error(target_avg, avg)
                if err < min_err:
                    min_err = err
                    best_match = tiles[cached_avgs.index(avg)]
        return best_match

    elif method == 'diff':
        min_err = float('inf')
        best_match = None
        for tile in tiles:
            err = error(target, tile)
            if err < min_err:
                min_err = err
                best_match = tile
        return best_match

    else:
        print('Unknown method. Exiting...')
        sys.exit()


def mosaic(image, tiles, tile_size, out_file, mode, method):
    grid = gridify(image, tile_size)
    print('Finding best matches...')
    mosaic_tiles = []
    progress = ProgressCounter(len(grid))
    for i, row in enumerate(grid):
        mosaic_row = []
        for grid_tile in row:
            best_match = find_best_match(grid_tile, tiles, method)
            mosaic_row.append(best_match)
        mosaic_tiles.append(mosaic_row)
        progress.update()
    print('Done.')

    print('Creating mosaic...')
    tile_w, tile_h = tile_size
    output = Image.new(mode, image.size)
    for i, row in enumerate(mosaic_tiles):
        for j, tile in enumerate(row):
            output.paste(tile, (j * tile_w, i * tile_h))
    output.save(out_file)
    print('Done.')


def main(argv):
    start_time = time.perf_counter()

    if len(argv) != 7:
        print(f'Usage: {argv[0]} <image> <tiles directory> <output> '
              '<tile size> <scale> <method>')
        print('image - image from which the mosaic is created')
        print('tiles directory - directory containing the images to '
              'be used as tiles for the mosaic')
        print('output - name of the output image')
        print('tile size - size of the tiles in px')
        print('scale - positive integer used for scaling the image')
        print("method - the method used for finding the best matches: 'avg' or 'diff'")
        sys.exit()

    image = argv[1]
    tiles_path = argv[2]
    out_file = argv[3]
    size = int(argv[4])
    scale = int(argv[5])
    method = argv[6]

    tile_size = (size, size)
    scale = 1 if scale < 1 else scale
    if method != 'avg' and method != 'diff':
        print(f"Unknown method '{method}'. Available methods are 'avg' and 'diff'")
        sys.exit()
    target = get_target(image, tile_size, scale=scale)
    if size > min(target.size):
        print('Tiles cannot be larger than the image')
        sys.exit()
    mode = target.mode
    tiles = get_tiles(tiles_path, tile_size, mode)
    mosaic(target, tiles, tile_size, out_file, mode, method)

    run_time = time.perf_counter() - start_time
    print(f'Run time: {run_time:.2f} seconds')


if __name__ == '__main__':
    main(sys.argv)
