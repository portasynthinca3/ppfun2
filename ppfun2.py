#!/usr/bin/env python3

# PixelPlanet bot version 2 by portasynthinca3 (now using WebSocket!)
# Distributed under WTFPL


import sys, threading
import json, pickle
import time, datetime, math, random
import os.path as path, getpass


from io import BytesIO
from PIL import Image
import base64, time, threading, random, string, json, socket

not_inst_libs = []

try:
    from pdf2image import convert_from_bytes
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM, renderPDF
except ImportError:
    not_inst_libs.append('pdf2image')
    not_inst_libs.append('svglib')
   
try:
    import requests as killpedos
except ImportError:
    not_inst_libs.append('requests')

try:
    import pyaudio
    import wave
except ImportError:
    not_inst_libs.append('PyAudio')

try:
    import numpy as np
except ImportError:
    not_inst_libs.append('numpy')

try:
    import cv2
except ImportError:
    not_inst_libs.append('opencv-python')

try:
    import websocket
except ImportError:
    not_inst_libs.append('websocket_client')

try:
    from colorama import Fore, Back, Style, init
except ImportError:
    not_inst_libs.append('colorama')

# tell the user to install libraries
if len(not_inst_libs) > 0:
    print('Some libraries are not installed. Install them by running this command:\npython -m pip install ' + ' '.join(not_inst_libs))
    exit()

def random_string(string_length):
    input = string.ascii_lowercase + string.digits
    return ''.join(random.choice(input) for i in range(string_length))
	



# configuration
class PpfunConfigAuth(object):
    def __init__(self):
        self.login = ''
        self.password = ''
class PpfunConfigProxy(object):
    def __init__(self):
        self.host = ''
        self.port = 0
        self.user = ''
        self.passwd = ''
class PpfunConfigImage(object):
    def __init__(self):
        self.path = ''
        self.x = 0
        self.y = 0
        self.defend = False
        self.strategy = ''
        self.canv_id = 0
class PpfunConfig(object):
    def __init__(self):
        self.auth  = PpfunConfigAuth()
        self.proxy = PpfunConfigProxy()
        self.image = PpfunConfigImage()

config = None




# shows the image in a window
def show_image(img):
    print(f'{Fore.YELLOW}Scroll to zoom, drag to pan, press any key to close the window{Style.RESET_ALL}')
    cv2.imshow('image', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# # renders a chunk as a colored CV2 image
# def render_chunk(d, x, y):
#     data = get_chunk(d, x, y)
#     img = np.zeros((256, 256, 3), np.uint8)
#     colors = me['canvases'][str(d)]['colors']
#     # go through the data
#     for y in range(256):
#         for x in range(256):
#             r, g, b = colors[data[y, x]]
#             img[y, x] = (b, g, r)
#     return img

# renders map data as a colored CV2 image
# def render_map(d, data):
#     img = np.zeros((data.shape[0], data.shape[1], 4), np.uint8)
#     colors = me['canvases'][str(d)]['colors']
#     # go through the data
#     for y in range(data.shape[0]):
#         for x in range(data.shape[1]):
#             if data[y, x] != 255:
#                 r, g, b = colors[data[y, x]]
#                 img[y, x] = (b, g, r, 255)
#             else:
#                 # a checkerboard pattern in transparent parts of the image
#                 if y % 20 < 10:
#                     img[y, x] = (32, 32, 32, 255) if x % 20 < 10 else (64, 64, 64, 255)
#                 else:
#                     img[y, x] = (32, 32, 32, 255) if x % 20 > 10 else (64, 64, 64, 255)
#     return img

# selects a canvas for future use
def select_canvas(ws, d):
    data = bytearray(2)
    data[0] = 0xA0
    data[1] = d
    # send data
    ws.send_binary(data)

# register a chunk
def register_chunk(ws, d, x, y):
    data = bytearray(3)
    data[0] = 0xA1
    data[1] = x
    data[2] = y
    # send data
    ws.send_binary(data)



def hf_ai_captcha(s, image_data):
    image_data_bytes = BytesIO()
    image_data.save(image_data_bytes, format="PNG")
    # image_data_bytes.seek(0)
    base64_data = base64.b64encode(image_data_bytes.getvalue()).decode('utf-8')
    # base64_data = base64.b64encode(image_data).decode('utf-8')
    # print(base64_data)
    
    while True:
        ############################################
        session_hash=random_string(12)
        json_data = {
            'fn_index': 0,
            'data': [ f"data:image/png;base64,{base64_data}" ],
            'action': 'predict',
            'session_hash': session_hash,
        }

        # json_data['data'][0] = f"data:image/png;base64,{base64_data}"
        # print(json_data)
        ###############################################################################

        

        project_path=random.choice(["sneedium/captcha_pixelplanet"])
        # r = killpedos.post('http://17540.gradio.app/api/predict/', headers={
        # r = killpedos.post('http://127.0.0.1:7860/api/predict/', headers={
        r = killpedos.post(f'https://hf.space/embed/{ project_path }/api/predict/', headers={
            'User-Agent': "Mozilla/5.0 (X11; Windows x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
        }, data=json.dumps(json_data))

        # print( r.text  )
        average_duration = r.json()['avg_durations'][0]
        duration = r.json()['durations'][0]
        captcha = r.json()['data'][0]
        # print( r.json() )

        return captcha# break#Breaks because, we got a session! #Breaks to "break the while-loop", therefore it will stop the function. and continue with the bot. 

def get_captcha_as_pillow(s, user_agent):
    headers = {
        'upgrade-insecure-requests': '1',
        'user-agent': user_agent,
    }
    r = s.get("https://scb.pixelplanet.fun/captcha.svg", headers=headers)

    captcha_id = r.headers["captcha-id"]
    svg_data = BytesIO(r.content)

    # Makes a SVG drwawing
    drawing = svg2rlg(svg_data)

    sneed_buffer_pdf = (
        BytesIO()
    )  ##Fake memory buffer, so we can kindda - NOT SAVE INTO HOUR COPE-COMPUTERS SNEED DOPE DILATE
    renderPDF.drawToFile(drawing, sneed_buffer_pdf)
    sneed_buffer_pdf.seek(0)
    cope = sneed_buffer_pdf.read()

    data_bytes_pillow_raw = convert_from_bytes(
        cope,
        fmt="jpeg",
        # open('/home/belval/example.pdf', 'rb').read()
    )[0]

    return data_bytes_pillow_raw, captcha_id

class bot():
    me, thr, ws = {}, None, None

    # are we allowed to draw
    draw = True
    # was the last placement of a pixel successful
    succ = False

    # chunk data cache
    chunk_data = None

    # number of pixels drawn and the starting time
    pixels_drawn = 1
    start_time = None


    def do_captcha(self):
        captcha_image, captcha_id_pixel_planet = get_captcha_as_pillow(self.sess, self.user_agent)
        bytes_captcha_images = BytesIO()
        print("proxy end ip:",self.sess.get("https://api64.ipify.org?format=json").text)

        def downscale(captcha_image):
            half = 0.4  # Actually
            with captcha_image as im:
                captcha_image = captcha_image.resize(
                    [int(half * s) for s in captcha_image.size]
                )
            return captcha_image

        captcha_image = downscale(captcha_image)

        captcha_image.save(
            bytes_captcha_images, quality=20, format="JPEG"
        )  # compress images a bit

        captcha_image = Image.open(bytes_captcha_images)  # Reopens it in a bytes-manner
        # captcha_image.show()

        headers = {
            'authority': 'sca.pixelplanet.fun',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            # Already added when you pass json=
            'content-type': 'application/json',
            'origin': 'https://pixelplanet.fun',
            'pragma': 'no-cache',
            'referer': 'https://pixelplanet.fun/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': self.user_agent,
        }
        captcha_answer = hf_ai_captcha(
            self.sess, captcha_image
        )
        json_data = {
            "text": captcha_answer,
            "id": captcha_id_pixel_planet,
        }

        r = self.sess.post(
            "https://sca.pixelplanet.fun/api/captcha", headers=headers, json=json_data
        )
        r_json = r.json()
        if "success" in list(r_json.keys()):
            print("CAPTCHA SUCCESS")
            print("LO1G-1", r_json)
            # print("LOG-1", self.sess.proxies)
            # captcha_image.save(
            #   f"pixelplanet_captcha_dataset/{captcha_answer}.jpg",
            #   quality=20,
            #   format="JPEG",
            # )
        else:
            if "You failed your captcha" in r_json["errors"]:
                print("Failed a captcha, (((Blame india lol)))")
            else:
                print("Unhandled error ===", r_json["errors"])
    
    # gets raw chunk data from the server
    def get_chunk(self, d, x, y):
        # get data from the server
        data = self.sess.get(f'https://pixelplanet.fun/chunks/{d}/{x}/{y}.bmp').content
        # construct a numpy array from it
        arr = np.zeros((256, 256), np.uint8)
        if len(data) != 65536:
            return arr
        for i in range(65536):
            c = data[i]
            # protected pixels are shifted up by 128
            if c >= 128:
                c = c - 128
            arr[i // 256, i % 256] = c
        return arr

    # gets several map chunks from the server
    def get_chunks(self, d, xs, ys, w, h):
        # the final image
        data = np.zeros((0, w * 256), np.uint8)
        # go through the chunks
        for y in range(h):
            # the row
            row = np.zeros((256, 0), np.uint8)
            for x in range(w):
                # append the chunk to the row
                row = np.concatenate((row, self.get_chunk(d, x + xs, y + ys)), axis=1)
            # append the row to the image
            data = np.concatenate((data, row), axis=0)
        return data

    # draws the image
    def draw_function(self, ws, canv_id, draw_x, draw_y, c_start_x, c_start_y, img, defend, strategy):
        try:
            size = img.shape
            canv_sz = self.me['canvases'][str(canv_id)]['size']
            canv_clr = self.me['canvases'][str(canv_id)]['colors']

            # fill a list of coordinates based on the strategy
            coords = []
            if strategy == 'forward':
                for y in range(size[0]):
                    for x in range(size[1]):
                        coords.append((x, y))
            elif strategy == 'backward':
                for y in range(size[0] - 1, -1, -1):
                    for x in range(size[1] - 1, -1, -1):
                        coords.append((x, y))
            elif strategy == 'rtl':
                for x in range(size[1] - 1, -1, -1):
                    for y in range(size[0]):
                        coords.append((x, y))
            elif strategy == 'ltr':
                for x in range(size[1]):
                    for y in range(size[0]):
                        coords.append((x, y))
            elif strategy == 'random':
                for y in range(size[0]):
                    for x in range(size[1]):
                        coords.append((x, y))
                random.shuffle(coords)

            # calculate position in the chunk data array
            start_in_d_x = draw_x + ((canv_sz // 2) - (c_start_x * 256))
            start_in_d_y = draw_y + ((canv_sz // 2) - (c_start_y * 256))

            start_time = datetime.datetime.now()
            self.draw = True

            while len(coords) > 0:
                # get a coordinate
                # coord = coords[0]
                coord = random.choice(coords)
                x, y = (coord)
                coords.remove(coord)

                # check if the pixel is transparent
                if img[y, x] == 255:
                    continue

                self.succ = False
                while not self.succ:
                    # we need to compare actual color values and not indicies
                    # because water and land have seprate indicies, but the same color values
                    #  as regular colors

                    # coord = random.choice(coords)
                    # x, y = (coord)
                    # coords.remove(coord)
                    if canv_clr[self.chunk_data[start_in_d_y + y, start_in_d_x + x]] != canv_clr[img[y, x]]:
                        c_idx = img[y, x]
                        pixels_remaining = len(coords)
                        sec_per_px = (datetime.datetime.now() - start_time).total_seconds() / self.pixels_drawn
                        time_remaining = datetime.timedelta(seconds=(pixels_remaining * sec_per_px))
                        print(f'{Fore.YELLOW}Placing a pixel at {Fore.GREEN}({x + draw_x}, {y + draw_y})' + 
                            f'{Fore.YELLOW}, color index: {Fore.GREEN}{c_idx}', end="")
                        if strategy == "forward":
                            print(f'{Fore.YELLOW}, progress: {Fore.GREEN}{"{:2.4f}".format((y * size[0] + x) * 100 / (size[0] * size[1]))}%' +
                                f'{Fore.YELLOW}, {Fore.GREEN}{self.pixels_drawn}{Fore.YELLOW} pixels placed{Style.RESET_ALL}')
                        elif strategy == "backward":
                            print(f'{Fore.YELLOW}, progress: {Fore.GREEN}{"{:2.4f}".format(100 - (y * size[0] + x) * 100 / (size[0] * size[1]))}%' +
                                f'{Fore.YELLOW}, {Fore.GREEN}{self.pixels_drawn}{Fore.YELLOW} pixels placed{Style.RESET_ALL}')
                        elif strategy == "random":
                            print(f'{Fore.YELLOW}, {Fore.GREEN}{self.pixels_drawn}{Fore.YELLOW} pixels placed{Style.RESET_ALL}')
                            
                        # try to draw it
                        while not self.draw:
                            time.sleep(0.25)
                        self.draw = False
                        self.place_pixel(ws, canv_id, x + draw_x, y + draw_y, c_idx)
                        # this flag will be reset when the other thread receives a confirmation message
                        while not self.draw:
                            time.sleep(0.25)
                        if self.succ:
                            self.pixels_drawn += 1
                        # wait half a second
                        # (a little bit of artifical fluctuation
                        #  so the server doesn't think we're a bot)
                        time.sleep(0.5 + random.uniform(-0.25, 0.25))
                    else:
                        self.succ = True

            print(f'{Fore.GREEN}Done drawing{Style.RESET_ALL}')
            if not defend:
                return
            print(f'{Fore.GREEN}Entering defend mode{Style.RESET_ALL}')

            # do the same thing, but now in a loop that checks everything once per second
            while True:
                for y in range(size[0]):
                    for x in range(size[1]):
                        if img[y, x] == 255:
                            continue
                        if canv_clr[self.chunk_data[start_in_d_y + y, start_in_d_x + x]] != canv_clr[img[y, x]]:
                            print(f'{Fore.YELLOW}[DEFENDING] Placing a pixel at {Fore.GREEN}({x + draw_x}, {y + draw_y}){Style.RESET_ALL}')

                            c_idx = img[y, x]
                            while not self.draw:
                                time.sleep(0.25)
                            self.draw = False
                            self.place_pixel(ws, canv_id, x + draw_x, y + draw_y, c_idx)

                            while not self.draw:
                                time.sleep(0.25)
                            time.sleep(0.5 + random.uniform(-0.25, 0.25))
                time.sleep(1)
        except websocket.WebSocketConnectionClosedException:
            # BAIL
            # raise
            return

    # places a pixel
    def place_pixel(self, ws, d, x, y, c):
        # convert the X and Y coordinates to I, J and Offset
        csz = self.me['canvases'][str(d)]['size']
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
        ws.send_binary(data)

    def main(self):
        self.user_agent = random_string(20)
        self.sess = killpedos.Session()
        self.sess.headers['user-agent'] = self.user_agent
        print(self.sess.headers['user-agent'])
        # initialize colorama
        init()

        # # get the version on the server
        # print(f'{Fore.YELLOW}PixelPlanet bot by portasynthinca3 version {Fore.GREEN}{VERSION}{Fore.YELLOW}' +
        #     f' released on {Fore.GREEN}{VERSION_DATE}{Fore.YELLOW}' + 
        #     f'\nNew features in this version: \n{Fore.GREEN}{VERSION_FEATURES}{Fore.YELLOW}'
        #     f'\nChecking for updates{Style.RESET_ALL}')
        # server_verdef = sess.get(VERDEF_URL).text
        # if int(server_verdef.split('\n')[1]) > VERSION_NUM:
        #     # update
        #     server_ver = server_verdef.split('\n')[0]
        #     print(f'{Fore.YELLOW}There\'s a new version {Fore.GREEN}{server_ver}{Fore.YELLOW} on the server. Downloading{Style.RESET_ALL}')
        #     with open('ppfun2.py', 'wb') as bot_file:
        #         bot_file.write(sess.get(BOT_URL).content)
        #     print(f'{Fore.YELLOW}Please start the bot again{Style.RESET_ALL}')
        #     exit()
        # else:
        #     print(f'{Fore.YELLOW}You\'re running the latest version{Style.RESET_ALL}')

        def auto_update_me(do_break):
            while True:
                # get canvas info list and user identifier
                print(f'{Fore.YELLOW}Requesting initial data{Style.RESET_ALL}')
                self.me = self.sess.get('https://pixelplanet.fun/api/me').json()
                
                if do_break:
                    break
                
                # time.sleep(4)
        auto_update_me(True)
        # threading.Thread(target=auto_update_me, args=(False,)).start()#Auto update via a thread
        
        # try to load the config file
        try:
            config_path = ' '.join(sys.argv[1:])
            with open(config_path, 'rb') as cf:
                config = pickle.load(cf)
        except:
            config = PpfunConfig()

        if config.image.path == "":
            # ask for login and password
            print(f'{Fore.YELLOW}Enter your PixelPlanet username or e-mail (YOU CAN LEAVE EMPTY to skip authorization): {Style.RESET_ALL}', end='')
            config.auth.login = input()
            config.auth.passwd = ''
            auth_token = ''
            if config.auth.login != '':
                config.auth.passwd = getpass.getpass(f'{Fore.YELLOW}Enter your PixelPlanet password: {Style.RESET_ALL}')

            # # ask for proxy
            # print(f'{Fore.YELLOW}Enter your proxy (host:port), leave empty to not use a proxy: {Style.RESET_ALL}', end='')
            # config.proxy.host = input()
            # config.proxy.port = None
            # config.proxy.user = ''
            # config.proxy.passwd = ''
            # if config.proxy.host != '':
            #     config.proxy.port = int(config.proxy.host.split(':')[1])
            #     config.proxy.host = config.proxy.host.split(':')[0]

            #     print(f'{Fore.YELLOW}Enter your proxy username: {Style.RESET_ALL}', end='')
            #     config.proxy.user = input()
            #     config.proxy.passwd = getpass.getpass(f'{Fore.YELLOW}Enter your proxy password: {Style.RESET_ALL}')



            # request some info from the user
            print(f'{Fore.YELLOW}Enter a path to the image:{Style.RESET_ALL} ', end='')
            config.image.path = input()

            print(f'{Fore.YELLOW}Enter the X coordiante of the top-left corner:{Style.RESET_ALL} ', end='')
            config.image.x = int(input())
            print(f'{Fore.YELLOW}Enter the Y coordiante of the top-left corner:{Style.RESET_ALL} ', end='')
            config.image.y = int(input())

            # defend the image?
            config.image.defend = ''
            while config.image.defend not in ['y', 'n', 'yes', 'no']:
                print(f'{Fore.YELLOW}Defend [y, n]?{Style.RESET_ALL} ', end='')
                config.image.defend = input().lower()
            config.image.defend = config.image.defend if config.image.defend in ['y', 'yes'] else False

            config.image.strategy = "random"
            
            # choose the canvas
            config.image.canv_id = -1
            while str(config.image.canv_id) not in self.me['canvases']:
                print(Fore.YELLOW + '\n'.join(['[' + (Fore.GREEN if ("v" not in self.me["canvases"][k]) else Fore.RED) + f'{k}{Fore.YELLOW}] ' +
                                                self.me['canvases'][k]['title'] for k in self.me['canvases']]))
                print(f'Select the canvas [0-{len(self.me["canvases"]) - 1}]:{Style.RESET_ALL} ', end='')
                config.image.canv_id = input()
                if 0 <= int(config.image.canv_id) <= len(self.me['canvases']) - 1:
                    if 'v' in self.me['canvases'][config.image.canv_id]:
                        print(Fore.RED + 'Only 2D canvases are supported' + Style.RESET_ALL)
                        config.image.canv_id = -1
            config.image.canv_id = int(config.image.canv_id)

            # save the config
            print(f'{Fore.YELLOW}Enter the configuration preset name (leave empty to not save configuration):{Style.RESET_ALL} ', end='')
            config_path = input()
            if config_path != '':
                config_path = config_path + '.pickle'
                with open(config_path, 'wb') as cf:
                    pickle.dump(config, cf)
                for x in range(50):
                    print(f'{Fore.YELLOW}Configuration was saved. Run {Fore.GREEN}python ppfun2_ai_solver.py {config_path}{Fore.YELLOW} next time to load it{Style.RESET_ALL} ')
                    time.sleep(0.05)
        
        


        # config.image.x = 3621#d,3621,-8639,43
        # config.image.y = -8639
        # config.image.path = "pxArt.png"

        


        # load the image
        canv_desc = self.me['canvases'][str(config.image.canv_id)]
        print(f'{Fore.YELLOW}Loading the image{Style.RESET_ALL}')
        img = None
        img_size = (0, 0)
        try:
            config.image.path = path.expanduser(config.image.path)
            img = cv2.imread(config.image.path, cv2.IMREAD_UNCHANGED)
            img_size = img.shape[:2]
        except:
            print(f'{Fore.RED}Failed to load the image. Does it exist? Is it an obscure image format?{Style.RESET_ALL}')
            exit()
        # check if it's JPEG
        img_extension = path.splitext(config.image.path)[1]
        if img_extension in ['jpeg', 'jpg']:
            print(f'{Fore.RED}WARNING: you appear to have loaded a JPEG image. It uses lossy compression, so it\'s not good at all for pixel-art.{Style.RESET_ALL}')
        
        # transform the colors
        print(f'{Fore.YELLOW}Processing the image{Style.RESET_ALL}')
        color_idxs = np.zeros(img_size, np.uint8)
        for y in range(img_size[0]):
            for x in range(img_size[1]):
                # ignore the pixel if it's transparent
                transparent = None
                if img.shape[2] == 3: # the image doesn't have an alpha channel
                    transparent = False
                else: # the image has an alpha channel
                    transparent = img[y, x][3] <= 128
                if not transparent:
                    # fetch BGR color
                    bgr = img[y, x]
                    bgr = (int(bgr[0]), int(bgr[1]), int(bgr[2]))
                    # find the nearest one in the palette
                    best_diff = 100000000000000
                    best_no = 0
                    # ignore the first "cli" colors, they show key background and are not allowed in the request
                    for i in range(canv_desc['cli'], len(canv_desc['colors'])):
                        c_bgr = tuple(canv_desc['colors'][i])
                        diff = (c_bgr[2] - bgr[0]) ** 2 + (c_bgr[1] - bgr[1]) ** 2 + (c_bgr[0] - bgr[2]) ** 2
                        if diff < best_diff:
                            best_diff = diff
                            best_no = i
                    # store the color idx
                    color_idxs[y, x] = best_no
                else:
                    color_idxs[y, x] = 255
        
        # threading.Thread(target=show_image, args=(img,)).start()

        # authorize
        extra_ws_headers = []
        if config.auth.login != '':
            print(f'{Fore.YELLOW}Authorizing{Style.RESET_ALL}')
            response = self.sess.post('https://pixelplanet.fun/api/auth/local', json={
                'nameoremail':config.auth.login,
                'password':config.auth.passwd
            })
            resp_js = response.json()
            print(resp_js)
            if 'success' in resp_js and resp_js['success']:
                print(f'{Fore.YELLOW}Logged in as {Fore.GREEN}{resp_js["me"]["name"]}{Style.RESET_ALL}')
                # get the token and add it as a WebSocket cookie
                auth_token = response.cookies.get('ppfun.session')
                extra_ws_headers.append("Cookie: ppfun.session=" + auth_token)
            else:
                print(f'{Fore.RED}Authorization failed{Style.RESET_ALL}')
                exit()

        def run_client():

            print(f'{Fore.YELLOW}Connecting to the server{Style.RESET_ALL}')
            ws = websocket.create_connection('wss://pixelplanet.fun:443/ws', header=extra_ws_headers,
                http_proxy_host=config.proxy.host, http_proxy_port=config.proxy.port,
                http_proxy_auth=(config.proxy.user, config.proxy.passwd))
            select_canvas(ws, config.image.canv_id)
            
            # load and register chunks
            csz = canv_desc['size']
            c_start_y = ((csz // 2) + config.image.y) // 256
            c_start_x = ((csz // 2) + config.image.x) // 256
            c_end_y = ((csz // 2) + config.image.y + img.shape[0]) // 256
            c_end_x = ((csz // 2) + config.image.x + img.shape[1]) // 256
            c_occupied_y = c_end_y - c_start_y + 1
            c_occupied_x = c_end_x - c_start_x + 1
            self.chunk_data = self.get_chunks(config.image.canv_id, c_start_x, c_start_y, c_occupied_x, c_occupied_y)
            for c_y in range(c_occupied_y):
                for c_x in range(c_occupied_x):
                    register_chunk(ws, config.image.canv_id, c_x + c_start_x, c_y + c_start_y)
            

            # start drawing
            thr = threading.Thread(target=self.draw_function, args=(
                    ws, config.image.canv_id, config.image.x, config.image.y,
                    c_start_x, c_start_y, color_idxs, config.image.defend, config.image.strategy),
                name='Drawing thread')
            thr.start()

            # read server messages
            while True:
                time.sleep(0.25)#Computer anti-lag?
                data = ws.recv()
                # ws.send('["ddd",1]')
                # text data = chat message
                if type(data) == str:
                    # data comes as a JS(ON) array
                    msg = json.loads('{"msg":' + data + '}')
                    msg = msg['msg']
                    if isinstance(msg, list): # it also could be a string, in which case it's our nickname
                        print(f'{Fore.GREEN}{msg[0]}{Fore.YELLOW} (country: {Fore.GREEN}{msg[2]}{Fore.YELLOW}) ' + 
                            f'says: {Fore.GREEN}{msg[1]}{Fore.YELLOW} in chat {Fore.GREEN}{"int" if msg[2] == 2 else "en"}{Style.RESET_ALL}')

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
                        # CAPTCHA error
                        if rc == 10:
                            self.draw = False
                            print(Fore.RED + 'Place a pixel somewhere manually and enter CAPTCHA' + Style.RESET_ALL)

                            ###############MY EDIT
                            self.do_captcha()


                            ##################ENDED

                        # any error
                        if rc != 0:
                            time.sleep(2)
                            self.succ = False
                            self.draw = True
                        # success
                        else:
                            # if wait >= 59*1000::
                            if wait >= 58999:
                                print(f'{Fore.YELLOW}Cooling down{Style.RESET_ALL}')
                                # wait that many seconds plus 1 (to be sure)
                                time.sleep(cd_s + 1)
                            self.succ = True
                            self.draw = True

                    # pixel update
                    elif opcode == 0xC1:
                        # get raw data
                        i = data[1]
                        j = data[2]
                        offs = (data[3] << 16) | (data[4] << 8) | data[5]
                        clr = data[6]
                        # convert it to X and Y coords
                        csz = self.me['canvases'][str(config.image.canv_id)]['size']
                        x = ((i * 256) - (csz // 2)) + (offs & 0xFF)
                        y = ((j * 256) - (csz // 2)) + ((offs >> 8) & 0xFF)
                        print(f'{Fore.YELLOW}Pixel update at {Fore.GREEN}({str(x)}, {str(y)}){Style.RESET_ALL}')
                        # write that change
                        local_x = (i - c_start_x) * 256 + (offs & 0xFF)
                        local_y = (j - c_start_y) * 256 + ((offs >> 8) & 0xFF)
                        self.chunk_data[local_y, local_x] = clr
                    else:
                        print(f'{Fore.RED}Unreconized data opcode from the server. Raw data: {data}{Style.RESET_ALL}')

        while True:
            try:
                run_client()
            except websocket.WebSocketConnectionClosedException:
                print(f'{Fore.RED}Disconnected, trying to reconnect in 5s{Style.RESET_ALL}')
                time.sleep(5)
                self.succ = False
                self.draw = True
                # raise
            except KeyboardInterrupt:
                print(f'{Fore.RED}Interrupting{Style.RESET_ALL}')
                sys.exit()

def main():
    # while True:
    try:
        kek = bot()
        kek.main()
    except:
        raise
if __name__ == "__main__":
    main()
