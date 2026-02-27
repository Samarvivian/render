from flask import Flask, request, jsonify
from phe import paillier
import time

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'edge node running', 'time': time.time()})

@app.route('/blind_process', methods=['POST'])
def blind_process():
    data = request.json
    public_key = paillier.PaillierPublicKey(n=int(data['public_key_n']))
    operation  = data['operation']
    width      = data['width']
    height     = data['height']
    channels   = data.get('channels', 1)  # 1=灰度, 3=RGB

    # 服务器只看到密文大整数，完全不知道图片内容
    if channels == 3:
        # RGB三通道分别处理
        result_channels = []
        for ch in range(3):
            enc_ch = [
                paillier.EncryptedNumber(public_key, int(c))
                for c in data['encrypted_pixels'][ch]
            ]
            if operation == 'brighten':
                amount = data.get('amount', 50)
                processed = [p + amount for p in enc_ch]
                counts = [1] * len(processed)
            elif operation == 'blur':
                processed, counts = blind_blur(enc_ch, width, height)
            elif operation == 'darken':
                amount = data.get('amount', 50)
                processed = [p + (-amount) for p in enc_ch]
                counts = [1] * len(processed)

            result_channels.append({
                'pixels': [str(e.ciphertext()) for e in processed],
                'counts': counts
            })

        return jsonify({'channels': result_channels, 'status': 'ok'})

    else:
        # 灰度单通道
        enc_pixels = [
            paillier.EncryptedNumber(public_key, int(c))
            for c in data['encrypted_pixels']
        ]
        if operation == 'brighten':
            amount = data.get('amount', 50)
            result = [p + amount for p in enc_pixels]
            counts = [1] * len(result)
        elif operation == 'blur':
            result, counts = blind_blur(enc_pixels, width, height)

        return jsonify({
            'result': [str(e.ciphertext()) for e in result],
            'counts': counts,
            'status': 'ok'
        })


def blind_blur(enc_pixels, width, height):
    """均值模糊——服务器全程看不到任何像素值"""
    result = []
    counts = []
    for i in range(height):
        for j in range(width):
            neighbors = []
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < height and 0 <= nj < width:
                        neighbors.append(enc_pixels[ni * width + nj])
            total = neighbors[0]
            for n in neighbors[1:]:
                total = total + n
            result.append(total)
            counts.append(len(neighbors))
    return result, counts


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)