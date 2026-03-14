from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp, os, tempfile, threading, uuid, socket, re

app = Flask(__name__, static_folder='.')
CORS(app)
TEMP_DIR = tempfile.mkdtemp()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'

def build_format(height, is_audio):
    if is_audio:
        return 'bestaudio/best'
    if height == 'best':
        return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
    return (
        f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/'
        f'bestvideo[height<={height}]+bestaudio/'
        f'best[height<={height}]/best'
    )

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = (data or {}).get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL gerekli'}), 400
    opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        fmts = []
        seen = set()
        for f in (info.get('formats') or []):
            h = f.get('height')
            if h and h not in seen:
                seen.add(h)
                fmts.append({'height': h, 'ext': f.get('ext', ''), 'filesize': f.get('filesize') or f.get('filesize_approx')})
        return jsonify({
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'extractor': info.get('extractor_key') or info.get('extractor'),
            'formats': sorted(fmts, key=lambda x: x['height'], reverse=True),
        })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 400

@app.route('/api/download', methods=['POST'])
def download():
    data = request.get_json()
    url = (data or {}).get('url', '').strip()
    fmt_raw = (data or {}).get('format', 'best')
    if not url:
        return jsonify({'error': 'URL gerekli'}), 400

    is_audio = fmt_raw in ('bestaudio', 'worstaudio')
    height = 'best'
    m = re.search(r'height<=(\d+)', fmt_raw)
    if m:
        height = m.group(1)

    fmt = build_format(height, is_audio)
    fid = str(uuid.uuid4())

    # Uzantıyı önceden sabitle
    if is_audio:
        fixed_ext = 'mp3'
        out = os.path.join(TEMP_DIR, f'{fid}.%(ext)s')
    else:
        fixed_ext = 'mp4'
        out = os.path.join(TEMP_DIR, f'{fid}.mp4')  # Direkt mp4 olarak kaydet

    opts = {
        'format': fmt,
        'outtmpl': out,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
    }

    if is_audio:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        opts.pop('merge_output_format', None)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')

        # Dosyayı bul
        downloaded = None
        for f in os.listdir(TEMP_DIR):
            if f.startswith(fid):
                downloaded = os.path.join(TEMP_DIR, f)
                break

        if not downloaded or not os.path.exists(downloaded):
            return jsonify({'error': 'Dosya bulunamadı'}), 500

        # Uzantıyı dosyadan al ama mp4'e zorla (ses değilse)
        real_ext = os.path.splitext(downloaded)[1].lower()
        if not is_audio and real_ext != '.mp4':
            # mp4'e yeniden adlandır
            new_path = downloaded.replace(real_ext, '.mp4')
            os.rename(downloaded, new_path)
            downloaded = new_path
            real_ext = '.mp4'

        safe = ''.join(c for c in title if c.isalnum() or c in ' -_').strip()[:60]
        filename = f'{safe}{real_ext}'
        mime = 'video/mp4' if real_ext == '.mp4' else 'audio/mpeg' if real_ext == '.mp3' else 'application/octet-stream'

        print(f'[VidDrop] Gönderiliyor: {filename} ({mime})')

        threading.Timer(120, lambda: os.path.exists(downloaded) and os.remove(downloaded)).start()
        return send_file(downloaded, mimetype=mime, as_attachment=True, download_name=filename)

    except yt_dlp.utils.DownloadError as e:
        return jsonify({'error': 'İndirme hatası: ' + str(e)[:150]}), 400
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500

if __name__ == '__main__':
    ip = get_local_ip()
    print(f'\n{"="*50}\n🎬  VidDrop Başladı!\n{"="*50}')
    print(f'💻  http://localhost:5000')
    print(f'📱  http://{ip}:5000')
    print(f'{"="*50}\nCtrl+C ile durdur\n')
   port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port, debug=False)
