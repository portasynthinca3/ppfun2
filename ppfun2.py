#!/usr/bin/env python3

# PixelPlanet bot version 2 by portasynthinca3 (now using WebSockets!)
# Distributed under WTFPL

import asyncio, threading
import websockets, requests
import json
import numpy as np, cv2
import time, datetime, math, random
import os.path as path
from playsound import playsound
from colorama import Fore, Back, Style, init

me = {}

# are we allowed to draw
draw = True

# chunk data cache
chunk_data = None

# number of pixels drawn and the starting time
pixels_drawn = 1
start_time = None

# play a notification sound
def play_notification():
    playsound('notif.mp3')

# shows the image in a window
def show_image(img):
    print(f'{Fore.YELLOW}Scroll to zoom, drag to pan, press any key to close the window{Style.RESET_ALL}')
    cv2.imshow('image', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# gets raw chunk data from the server
def get_chunk(d, x, y):
    # get data from the server
    data = requests.get(f'https://pixelplanet.fun/chunks/{d}/{x}/{y}.bmp').content
    # construct a numpy array from it
    arr = np.zeros((256, 256), np.uint8)
    for i in range(65536):
        arr[i // 256, i % 256] = data[i]
    return arr

# gets several map chunks from the server
def get_chunks(d, xs, ys, w, h):
    # the final image
    data = np.zeros((0, w * 256), np.uint8)
    # go through the chunks
    for y in range(h):
        # the row
        row = np.zeros((256, 0), np.uint8)
        for x in range(w):
            # append the chunk to the row
            row = np.concatenate((row, get_chunk(d, x + xs, y + ys)), axis=1)
        # append the row to the image
        data = np.concatenate((data, row), axis=0)
    return data

# renders chunk as colored CV2 image
def render_chunk(d, x, y):
    global me
    data = get_chunk(d, x, y)
    img = np.zeros((256, 256, 3), np.uint8)
    colors = me['canvases'][str(d)]['colors']
    # go through the data
    for y in range(256):
        for x in range(256):
            # convert color number to color
            c = data[y, x]
            # protected pixels are shifted up by 128
            if c >= 128:
                c = c - 128
            # the order in OpenCV images is BGR, not RGB
            r, g, b = colors[c]
            img[y, x] = (b, g, r)
    return img

# renders map data into a colored CV2 image
def render_map(d, data):
    global me
    img = np.zeros((data.shape[0], data.shape[1], 3), np.uint8)
    colors = me['canvases'][str(d)]['colors']
    # go through the data
    for y in range(data.shape[0]):
        for x in range(data.shape[1]):
            # convert color number to color
            c = data[y, x]
            # protected pixels are shifted up by 128
            if c >= 128:
                c = c - 128
            # the order in OpenCV images is BGR, not RGB
            r, g, b = colors[c]
            img[y, x] = (b, g, r)
    return img

# selects a canvas for future use
async def select_canvas(ws, d):
    # construct the data array
    data = bytearray(2)
    data[0] = 0xA0
    data[1] = d
    # send data
    await ws.send(data)

# register a chunk
async def register_chunk(ws, d, x, y):
    # construct the data array
    data = bytearray(3)
    data[0] = 0xA1
    data[1] = x
    data[2] = y
    # send data
    await ws.send(data)

# places a pixel
async def place_pixel(ws, d, x, y, c):
    # convert the X and Y coordinates to I, J and Offset
    csz = me['canvases'][str(d)]['size']
    modOffs = (csz // 2) % 256
    offs = (((y + modOffs) % 256) * 256) + ((x + modOffs) % 256)
    i = (x + csz // 2) // 256
    j = (y + csz // 2) // 256
    # construct the data array
    data = bytearray(7)
    data[0] = 0xC1
    data[1] = i
    data[2] = j
    data[3] = (offs >> 16) & 0xFF
    data[4] = (offs >>  8) & 0xFF
    data[5] = (offs >>  0) & 0xFF
    data[6] = c
    # send data
    await ws.send(data)

# draws the image
def draw_function(ws, canv_id, draw_x, draw_y, c_start_x, c_start_y, img, defend):
    global me, draw, chunk_data, pixels_drawn, start_time

    loop = asyncio.new_event_loop()
    size = img.shape
    canv_sz = me['canvases'][str(canv_id)]['size']
    canv_clr = me['canvases'][str(canv_id)]['colors']

    # calculate position in the chunk data array
    start_in_d_x = draw_x + ((canv_sz // 2) - (c_start_x * 256))
    start_in_d_y = draw_y + ((canv_sz // 2) - (c_start_y * 256))

    start_time = datetime.datetime.now()

    for y in range(size[0]):
        for x in range(size[1]):
            # we need to compare actual color values and not indicies
            # because water and land have seprate indicies, but the same color values
            #  as regular colors
            if canv_clr[chunk_data[start_in_d_y + y, start_in_d_x + x]] != canv_clr[img[y, x]]:
                pixels_remaining = (size[0] * size[1]) - (y * size[0] + x)
                sec_per_px = (datetime.datetime.now() - start_time).total_seconds() / pixels_drawn
                time_remaining = datetime.timedelta(seconds=(pixels_remaining * sec_per_px))
                print(f'{Fore.YELLOW}Placing a pixel at {Fore.GREEN}({x + draw_x}, {y + draw_y})' + 
                      f'{Fore.YELLOW}, progress: {Fore.GREEN}{"{:2.4f}".format((y * size[0] + x) * 100 / (size[0] * size[1]))}%' +
                      f'{Fore.YELLOW}, remaining: {Fore.GREEN}{"estimating..." if pixels_drawn < 20 else str(time_remaining)}{Style.RESET_ALL}')
                # get the color index
                c_idx = img[y, x]
                # try to draw it
                while not draw:
                    time.sleep(0.25)
                    pass
                draw = False
                loop.run_until_complete(place_pixel(ws, canv_id, x + draw_x, y + draw_y, c_idx))
                pixels_drawn += 1
                # this flag will be reset when the other thread receives a confirmation message
                while not draw:
                    time.sleep(0.25)
                    pass
                # wait half a second
                # (a little bit of artifical fluctuation
                #  so the server doesn't think we're a bot)
                time.sleep(0.5 + random.uniform(-0.25, 0.25))

    print(f'{Fore.GREEN}Done drawing{Style.RESET_ALL}')
    if not defend:
        return
    print(f'{Fore.GREEN}Entering defend mode{Style.RESET_ALL}')

    # do the same thing, but now in a loop that checks everything once per second
    while True:
        for y in range(size[0]):
            for x in range(size[1]):
                if canv_clr[chunk_data[start_in_d_y + y, start_in_d_x + x]] != canv_clr[img[y, x]]:
                    print(f'{Fore.YELLOW}[DEFENDING] Placing a pixel at {Fore.GREEN}({x + draw_x}, {y + draw_y}){Style.RESET_ALL}')
                    # get the color index
                    c_idx = img[y, x]
                    # try to draw it
                    while not draw:
                        time.sleep(0.25)
                        pass
                    draw = False
                    loop.run_until_complete(place_pixel(ws, canv_id, x + draw_x, y + draw_y, c_idx))
                    # this flag will be reset when the other thread receives a confirmation message
                    while not draw:
                        time.sleep(0.25)
                        pass
                    # wait half a second
                    # (a little bit of artifical fluctuation
                    #  so the server doesn't think we're a bot)
                    time.sleep(0.5 + random.uniform(-0.25, 0.25))
        time.sleep(1)

async def main():
    global me, draw, chunk_data
    # initialize colorama
    init()
    # get canvas info list and user identifier
    print(f'{Fore.YELLOW}Requesting info{Style.RESET_ALL}')
    me = requests.get('https://pixelplanet.fun/api/me').json()

    # request some info from the user
    print(f'{Fore.YELLOW}Enter a path to the image:{Style.RESET_ALL} ', end='')
    img_path = input()

    print(f'{Fore.YELLOW}Enter the X coordiante of the top-left corner:{Style.RESET_ALL} ', end='')
    draw_x = int(input())
    print(f'{Fore.YELLOW}Enter the Y coordiante of the top-left corner:{Style.RESET_ALL} ', end='')
    draw_y = int(input())

    defend = ''
    while defend not in ['y', 'n', 'yes', 'no']:
        print(f'{Fore.YELLOW}Defend [y, n]?{Style.RESET_ALL} ', end='')
        defend = input().lower()
    defend = True if defend in ['y', 'yes'] else False
    
    canv_id = -1
    while str(canv_id) not in me['canvases']:
        print(Fore.YELLOW + '\n'.join(['[' + (Fore.GREEN if ("v" not in me["canvases"][k]) else Fore.RED) + f'{k}{Fore.YELLOW}] ' +
                                           me['canvases'][k]['title'] for k in me['canvases']]))
        print(f'Select the canvas [0-{len(me["canvases"]) - 1}]:{Style.RESET_ALL} ', end='')
        canv_id = input()
        if 0 <= int(canv_id) <= len(me['canvases']) - 1:
            if 'v' in me['canvases'][canv_id]:
                print(Fore.RED + 'This canvas is not supported, only 2D canvases are supported' + Style.RESET_ALL)
                canv_id = -1

    canv_desc = me['canvases'][canv_id]
    canv_id = int(canv_id)

    # load the image
    print(f'{Fore.YELLOW}Loading the image{Style.RESET_ALL}')
    img = None
    img_size = (0, 0)
    try:
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        img_size = img.shape[:2]
    except:
        print(f'{Fore.RED}Failed to load the image. Does it exist? Is it an obscure image format?{Style.RESET_ALL}')
        exit()
    # check if it's JPEG
    img_extension = path.splitext(img_path)[1]
    if img_extension in ['jpeg', 'jpg']:
        print(f'{Fore.RED}WARNING: you appear to have loaded a JPEG image. It uses lossy compression, so it\'s not good at all for pixel-art.{Style.RESET_ALL}')
    
    # transform the colors
    print(f'{Fore.YELLOW}Processing the image{Style.RESET_ALL}')
    color_idxs = np.zeros(img_size, np.uint8)
    preview = np.zeros((img_size[0], img_size[1], 4), np.uint8)
    for y in range(img_size[0]):
        for x in range(img_size[1]):
            # ignore the pixel if it's transparent
            if img[y, x][3] > 128:
                # fetch BGR color
                bgr = img[y, x]
                bgr = (int(bgr[0]), int(bgr[1]), int(bgr[2]))
                # find the nearest one in the palette
                best_diff = 1000000000
                best_no = 0
                # ignore the first two colors, they show the land a water colors and are not allowed in the request
                for i in range(2, len(canv_desc['colors'])):
                    c_bgr = tuple(canv_desc['colors'][i])
                    diff = (c_bgr[2] - bgr[0]) ** 2 + (c_bgr[1] - bgr[1]) ** 2 + (c_bgr[0] - bgr[2]) ** 2
                    if diff < best_diff:
                        best_diff = diff
                        best_no = i
                # store the color idx
                color_idxs[y, x] = best_no
                # store the color for preview
                preview[y, x] = tuple(canv_desc['colors'][best_no] + [255])
                # PixelPlanet uses RGB, OpenCV uses BGR, need to swap
                temp = preview[y, x][2]
                preview[y, x][2] = preview[y, x][0]
                preview[y, x][0] = temp
            else:
                # checkerboard pattern in transparent parts of the image
                brightness = 0
                if y % 10 >= 5:
                    brightness = 128 if x % 10 >= 5 else  64
                else:
                    brightness = 64  if x % 10 >= 5 else 128
                preview[y, x] = (brightness, brightness, brightness, 255)
                color_idxs[y, x] = 255

    # show the preview
    show_preview = ''
    while show_preview not in ['y', 'n', 'yes', 'no']:
        print(f'{Fore.YELLOW}Show the preview [y/n]?{Style.RESET_ALL} ', end='')
        show_preview = input().lower()
    if show_preview in ['y', 'yes']:
        show_image(preview)

    start = ''
    while start not in ['y', 'n', 'yes', 'no']:
        print(f'{Fore.YELLOW}Draw {Fore.GREEN}{img_path}{Fore.YELLOW} ' +
              f'at {Fore.GREEN}({draw_x}, {draw_y}){Fore.YELLOW} ' + 
              f'on canvas {Fore.GREEN}{me["canvases"][str(canv_id)]["title"]} {Fore.YELLOW}[y/n]?{Style.RESET_ALL} ', end='')
        start = input().lower()
    # abort if user decided not to draw
    if start not in ['y', 'yes']:
        exit()

    # load the chunks in the region of the image
    print(f'{Fore.YELLOW}Loading chunk data around the destination{Style.RESET_ALL}')
    csz = me['canvases'][str(canv_id)]['size']
    c_occupied_y = math.ceil(img.shape[0] / 256)
    c_occupied_x = math.ceil(img.shape[1] / 256)
    c_start_y = ((csz // 2) + draw_y) // 256
    c_start_x = ((csz // 2) + draw_x) // 256
    chunk_data = get_chunks(canv_id, c_start_x, c_start_y, c_occupied_x, c_occupied_y)
    # show them
    show_chunks = ''
    while show_chunks not in ['y', 'n', 'yes', 'no']:
        print(f'{Fore.YELLOW}Show the area around the destination [y/n]?{Style.RESET_ALL} ', end='')
        show_chunks = input().lower()
    if show_chunks in ['y', 'yes']:
        print(f'{Fore.YELLOW}Processing...{Style.RESET_ALL}')
        show_image(render_map(canv_id, chunk_data))

    # start a WebSockets connection
    print(f'{Fore.YELLOW}Connecting to the server{Style.RESET_ALL}')
    async with websockets.connect('wss://pixelplanet.fun:443/ws') as ws:
        await select_canvas(ws, canv_id)
        # register the chunks
        for c_y in range(c_occupied_y):
            for c_x in range(c_occupied_x):
                await register_chunk(ws, canv_id, c_x + c_start_x, c_y + c_start_y)
        # start drawing
        thr = threading.Thread(target=draw_function, args=(ws, canv_id, draw_x, draw_y, c_start_x, c_start_y, color_idxs, defend), name='Drawing thread')
        thr.start()
        # read server messages
        while True:
            data = await ws.recv()
            # text data = chat message
            if type(data) == str:
                # data comes as a JS array
                msg = json.loads('{"msg":' + data + '}')
                msg = msg['msg']
                print(f'{Fore.GREEN}{msg[0]}{Fore.YELLOW} (country: {Fore.GREEN}{msg[2]}{Fore.YELLOW}) ' + 
                      f'says: {Fore.GREEN}{msg[1]}{Fore.YELLOW} in chat {Fore.GREEN}{"int" if msg[2] == 0 else "en"}{Style.RESET_ALL}')
            # binary data = event
            else:
                opcode = data[0]
                # online counter
                if opcode == 0xA7:
                    oc = (data[1] << 8) | data[2]
                    print(f'{Fore.YELLOW}Online counter: {Fore.GREEN}{oc}{Style.RESET_ALL}')

                # total cooldown packet
                elif opcode == 0xC2:
                    cd = (data[4] << 24) | (data[3] << 16) | (data[2] << 8) | data[1]
                    print(f'{Fore.YELLOW}Total cooldown: {Fore.GREEN}{cd} ms{Style.RESET_ALL}')

                # pixel return packet
                elif opcode == 0xC3:
                    rc = data[1]
                    wait = (data[2] << 24) | (data[3] << 16) | (data[4] << 8) | data[5]
                    cd_s = (data[6] << 8) | data[7]
                    print(f'{Fore.YELLOW}Pixel return{Fore.YELLOW} (code: {Fore.RED if rc != 0 else Fore.GREEN}{rc}{Fore.YELLOW}): ' + 
                          f'wait: {Fore.GREEN}{wait}{Fore.YELLOW} ms {Fore.GREEN}[+{cd_s} s]{Style.RESET_ALL}')
                    if rc == 10:
                        draw = False
                        print(Fore.RED + 'Place a pixel manually, enter captcha, return here and press enter' + Style.RESET_ALL, end='')
                        # ouch
                        play_notification()
                        # mash dat enter key
                        input()
                        draw = True
                    else:
                        if wait >= 30000:
                            print(f'{Fore.YELLOW}Cooling down{Style.RESET_ALL}')
                            # wait that many seconds plus 1 (to be sure)
                            time.sleep(cd_s + 1)
                        draw = True

                # pixel update
                elif opcode == 0xC1:
                    # get raw data
                    i = data[1]
                    j = data[2]
                    offs = (data[3] << 16) | (data[4] << 8) | data[5]
                    clr = data[6]
                    # convert it to X and Y coords
                    csz = me['canvases'][str(canv_id)]['size']
                    x = ((i * 256) - (csz // 2)) + (offs & 0xFF)
                    y = ((j * 256) - (csz // 2)) + ((offs >> 8) & 0xFF)
                    print(f'{Fore.YELLOW}Pixel update at {Fore.GREEN}({str(x)}, {str(y)}){Style.RESET_ALL}')
                    # write that change
                    local_x = (i - c_start_x) * 256 + (offs & 0xFF)
                    local_y = (j - c_start_y) * 256 + ((offs >> 8) & 0xFF)
                    chunk_data[local_y, local_x] = clr
                else:
                    print(f'{Fore.RED}Unreconized data opcode from the server. Raw data: {data}{Style.RESET_ALL}')

asyncio.get_event_loop().run_until_complete(main())