import cv2
import numpy as np
import pymorph


# Function for morphological 'thinning' of img with given elements e1 and e2
def skeletor(img, e1, e2):
    while True:
        pimg = img
        for r in range(4):
            img = img-pymorph.supgen(img, e1)
            e1 = pymorph.interot(e1, theta=90)
            img = img-pymorph.supgen(img, e2)
            e2 = pymorph.interot(e2, theta=90)
        if (pimg == img).all():
            break
    return img


# Function for pruning the thinned img with the element prune
def pruner(img, prune):
    while True:
        pimg = img
        img = img - pymorph.supgen(img, prune)
        if (pimg == img).all():
            break
    return img


# A helper function for Depth First Search which identifies if a pixel is safe to visit
def issafe(i, j, m, v):
    if (i >= 0) and (i < len(m[0])) and (j >= 0) and (j < len(m)):
        return (m[j][i]) and (not v[j][i])
    else:
        return False


# A convenience function which returns a priority-wise sorted list of the 8 neighbours of a pixel
def arr_to_adj(m):
    rn = [0, 0, 0, 0, 0, 0, 0, 0]
    cn = [0, 0, 0, 0, 0, 0, 0, 0]
    for i in range(len(m)):
        for j in range(len(m[0])):
            if m[i][j] == 'x':
                continue
            rn[7-m[i][j]] = i-1
            cn[7-m[i][j]] = j-1
    return rn, cn


# A function which defines the neighbours of a particular element of a (3x3) matrix
def nbors(x):
    if x == 0:
        return [1, 5]
    if x == 1:
        return [0, 2]
    if x == 2:
        return [1, 4]
    if x == 3:
        return [0, 5]
    if x == 4:
        return [2, 7]
    if x == 5:
        return [3, 6]
    if x == 6:
        return [7, 5]
    if x == 7:
        return [6, 4]
    return [x]


# Function which attempts to mimic the drawing order of the image using several heuristics on a DFS of the img
# The function writes the DFS order to a file (ltrace.txt) which is processed and sent to the Ghost server
def dfs(m):
    otpf = open('ltrace.txt', 'w')
    v = [[False for _ in range(len(m[1]))] for _ in range(len(m))]
    c = -1
    glob_bias = [3, 2, 0, 5, 1, 7, 6, 4]
    prevks = []
    cur_cords = (0, 0)
    block = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

    otpf.write('1 0 0*0 0\n')
    for i in range(1, len(m[1]), 1):
        for j in range(1, len(m), 1):
            if issafe(i, j, m, v):
                c += 1
                stack = [(i, j, 0)]
                while len(stack) > 0:
                    ix, jx, pk = stack.pop(0)
                    if len(prevks) == 0:
                        if cur_cords != (0, 0):
                            disp = (ix-cur_cords[0], jx-cur_cords[1])
                            otpf.write('0 '+str(disp[0]) + ' ' + str(disp[1]) + '*'+str(cur_cords[0]) + ' ' +
                                       str(cur_cords[1]) + '\n')
                            otpf.write('1 0 0*'+str(ix)+' '+str(jx)+'\n')

                    otpf.write('0 '+str(block[pk][0])+' '+str(block[pk][1])+'*'+str(ix)+' '+str(jx)+'\n')

                    prevks.insert(0, pk)
                    if len(prevks) > 10:
                        prevks.pop()
                    v[jx][ix] = True
                    neybor = False
                    # Recovering weights from the votes by prvks
                    accum_wts = [0, 0, 0, 0, 0, 0, 0, 0]
                    for x in prevks:
                        accum_wts[x] += 1
                        for n in nbors(x):
                            accum_wts[n] += 0.25
                    # Inertia sort^(TM) to generate neighbour order
                    inertia = [(x, accum_wts[x], 7-glob_bias[x]) for x in range(8)]
                    inertia.sort(reverse=True, key=lambda tup: (tup[1], tup[2]))
                    pos = 0
                    adj = [[3, 2, 0], [5, 'x', 1], [7, 6, 4]]
                    for (x, _, _) in inertia:
                        if x > 3:
                            x += 1
                        adj[x / 3][x % 3] = pos
                        pos += 1
                    rnbr, cnbr = arr_to_adj(adj)
                    for k in range(8):
                        if issafe(ix+cnbr[k], jx+rnbr[k], m, v):
                            stack.insert(0, (ix+cnbr[k], jx+rnbr[k], inertia[7-k][0]))
                            neybor = True
                    if not neybor:
                        prevks = []
                        # Mouse-up + Store co-ordinates
                        otpf.write('1 1 0'+'*'+str(ix)+' '+str(jx)+'\n')
                        cur_cords = (ix, jx)


# Converting the input image to binary based on Otsu's thresholding
im_gray = cv2.imread('ztemp.png', cv2.CV_LOAD_IMAGE_GRAYSCALE)
(thresh, im_bw) = cv2.threshold(im_gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

# Creating thinning elements
telem1 = pymorph.homothin()
telem2a = np.array([[False, False, False], [True, True, False], [False, True, False]])
telem2b = np.array([[False, True, True], [False, False, True], [False, False, False]])
telem2 = (telem2a, telem2b)

# Thinning the binary image
thin_img = skeletor(pymorph.binary(255-im_bw), telem1, telem2)

# Creating pruning elements
prunera = np.array([[False, True, False], [True, True, True], [False, True, False]])
prunerb = np.array([[False, False, False], [False, False, False], [False, False, False]])
prunere = (prunera, prunerb)

# Pruning the thinned image
thin_img2 = pruner(thin_img, prunere)

# Saving the final pruned and thinned image
cv2.imwrite('skeleton.png', thin_img2)

# Performing hybrid DFS of the image
dfs(thin_img2)
