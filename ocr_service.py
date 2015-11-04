from vyked import Host, HTTPService, get, Response, Request
import requests
from io import BytesIO
from PIL import Image
import subprocess
import asyncio
import math

img = ''
MY_URL = '192.168.80.69'
GHOST_ADDRESS = 'http://192.168.80.100:8000/'


# Helper Function to find distance between 2 points.
def dist(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)


class TaggerService(HTTPService):
    def __init__(self, ip, port):
        super(TaggerService, self).__init__("Tagger_Service", "1", ip, port)
        self.ocrres = asyncio.Future()

    # Request which sends the URL of the Prescription Image
    @get(path='/image/{url}')
    def req1(self, request: Request):
        global img
        url = request.match_info.get('url')
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return Response(status=200, body='Uploaded'.encode())

    # Request which sends the diagonal (x,y) coordinates of the rectangular region of interest
    @get(path='/ocr/{x1}/{y1}/{x2}/{y2}')
    def req3(self, request: Request):
        global img
        x1, y1, x2, y2 = (request.match_info.get('x1'), request.match_info.get('y1'),
                          request.match_info.get('x2'), request.match_info.get('y2'))
        nimg = img.crop([int(x1), int(y1), int(x2), int(y2)])
        nimg.save('ztemp.png')
        subprocess.check_output(['python', 'onep.py'])
        f = open('ltrace.txt', 'r')
        f2 = []
        cnt = -1
        pen_up = [-2]
        to_exec = []
        for line in f:
            cnt += 1
            f2.append(line)
            to_exec.append(True)
            if line.strip()[0:5] == '1 1 0':
                pen_up.append(cnt)

        c_index = -2
        thresh = 10
        for v in pen_up:
            if v - c_index < thresh:
                for i in range(c_index+2, v+1):
                    to_exec[i] = False
            c_index = v
            to_exec[c_index] = False
            try:
                to_exec[c_index+1] = False
            except IndexError:
                pass

        cnt = -1
        ghost_data = ''
        pen_cords = (-1, -1)
        cur_cords = (0, 0)
        for line in f2:
            cnt += 1
            if to_exec[cnt]:
                if line[0:5] == '1 0 0' and pen_cords != (-1, -1):
                    cords = line.strip().split('*')[1].split(' ')
                    cur_cords = (int(cords[0]), int(cords[1]))
                    disp = (cur_cords[0]-pen_cords[0], cur_cords[1]-pen_cords[1])
                    for_ghost = '0 '+str(disp[0])+' '+str(disp[1])+'\n'
                    if dist(pen_cords, cur_cords) > 10:
                        for_ghost = '1 1 0\n' + for_ghost + '1 0 0\n'
                    ghost_data += for_ghost
                else:
                    if line[0:5] == '1 1 0':
                        continue
                    cords = line.strip().split('*')[1].split(' ')
                    pen_cords = (int(cords[0]), int(cords[1]))
                    ghost_data += line.split('*')[0] + '\n'
        ghost_data += '1 1 0\n'
        requests.post(GHOST_ADDRESS, ghost_data)
        f.close()
        self.ocrres = asyncio.Future()
        res = yield from self.ocrres
        return Response(status=200, body=res.encode())

    # Response from the Ghost Server which contains the recognized string.
    @get(path='/ocrres/{res}')
    def req5(self, request: Request):
        self.ocrres.set_result(request.match_info.get('res'))
        return Response(status=200, body='thanx'.encode())


if __name__ == '__main__':
    http = TaggerService(MY_URL, 4501)
    Host.configure('TaggerService')
    Host.attach_http_service(http)
    Host.ronin = True
    Host.run()
