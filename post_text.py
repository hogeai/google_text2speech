# coding=utf-8
import argparse
import json
import os
import time
import re
from pathlib import Path

import httplib2
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
import base64

try:
    import wave
    import pyaudio
except:
    pass

try:
    import pygame.mixer
    from mutagen.mp3 import MP3
except:
    pass


class GoogleTextToSpeech:
    def __init__(self, **kwargs):
        self.DISCOVERY_URL = "https://{api}.googleapis.com/$discovery/rest?version={apiVersion}"

    def get_speech_service(self, proxy_info=None):
        credentials = GoogleCredentials.get_application_default().create_scoped(
            ["https://www.googleapis.com/auth/cloud-platform"]
        )

        if proxy_info is None:
            http = httplib2.Http()
        else:
            http = httplib2.Http(proxy_info=proxy_info)

        credentials.authorize(http)

        return discovery.build(
            "texttospeech", "v1beta1", http=http, discoveryServiceUrl=self.DISCOVERY_URL
        )

    def post_texttospeech(self, service, language="ja", text=""):
        if language == "ja":
            body = {
                "voice": {"languageCode": "ja-JP", "name": "ja-JP-Wavenet-A"},
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "pitch": "0.00",
                    "speakingRate": "1.00",
                },
                "input": {"text": text},
            }
        else:
            body = {
                "voice": {
                    "languageCode": "en-gb",
                    "name": "en-GB-Standard-A",
                    "ssmlGender": "FEMALE",
                },
                "audioConfig": {"audioEncoding": "MP3"},
                "input": {"text": text},
            }

        # POST https://texttospeech.googleapis.com/v1beta1/text:synthesize
        service_request = service.text().synthesize(body=body)
        response = service_request.execute()

        return response

    def set_key_json(self, key_json_file_path=None):
        if key_json_file_path is None:
            key_json_file_path = Path(".") / "key.json"

        prj_name = self.get_json_key(key_json_file_path)

        # Windows
        self.set_env(key_json_file_path, prj_name)

    def get_json_key(self, json_file):
        with open(json_file, "r",encoding="utf-8") as j:
            json_data = json.load(j)

        return json_data["project_id"]

    def set_env(self, json_file, prj_name):
        # Google OAuth簡略化
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(json_file)
        os.environ["GCLOUD_PROJECT"] = prj_name

    def convert_audio(self, in_text_file, out_audio_file="out.wav"):
        cmd = "Base64.exe -d " + in_text_file + " > " + out_audio_file
        os.system(cmd)

    def make_audio_file(self, response, out_audio_folder):
        out_file_txt = Path("base64audio.txt")
        out_file_audio = Path("texttospeech_audio.mp3")


        out_text = out_audio_folder / out_file_txt
        out_audio = out_audio_folder / out_file_audio
        if out_audio.exists():
            os.remove(str(out_audio))

        with open(out_text, "w", encoding="utf-8") as out:
            out.write(response["audioContent"])

        self.convert_audio(str(out_text), str(out_audio))
        return out_audio

    def make_direct_audio(self, response, out_audio_folder):
        out_file_txt = Path("base64audio.txt")
        out_file_audio = Path("texttospeech_audio.mp3")
        out_audio = out_audio_folder / out_file_audio
        if out_audio.exists():
            os.remove(str(out_audio))

        audio_data=base64.b64decode(response["audioContent"])
        with open(out_audio,'wb') as out:
            out.write(audio_data)

        return out_audio


def play_audio(audio_file):
    # 24000Hz ステレオ
    pygame.mixer.init(frequency=24000, channels=2)

    pygame.mixer.music.load(audio_file)

    # 1回再生
    pygame.mixer.music.play(1)

    # 再生時間
    mp3_length = MP3(audio_file).info.length
    time.sleep(mp3_length + 0.1)

    # 終了
    pygame.mixer.music.stop()


def zihou():
    from datetime import datetime

    tdatetime = datetime.now()
    return tdatetime.strftime("%Y/%m/%d %H:%M")

def norm(text):
    regx_url=re.compile(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+")
    text = re.sub(regx_url,"",text)
    return text

def get_text(args):
    text=""
    if args.cmd == "time":
        text = zihou()
    elif args.file is not None:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except:
            with open(args.file, "r", encoding="cp932") as f:
                text = f.read()

    elif args.text is not None:
        text = args.text

    text = norm(text)
    return text


def main(args):
    # 連携用処理:投げたいTextを決める
    text = get_text(args)
    if text == "":
        text = "すももももものもものうち"

    # 作業フォルダを指定(連携時を考慮し絶対PATHが無難)
    current = Path(".")
    # current = Path("your full Path")

    google_speech = GoogleTextToSpeech()

    # キーファイルJSONセット
    key_json_file_path = current / Path("auth_info") / "google_text_to_speech.json"
    google_speech.set_key_json(key_json_file_path)

    # proxy設定
    proxy="your proxy"
    port = 8080
    username ="your proxy user name"
    passwd="your proxy password"
    proxy_info = httplib2.ProxyInfo(
        httplib2.socks.PROXY_TYPE_HTTP,
        proxy,
        port,
        proxy_user=username,
        proxy_pass=passwd
    )
    # service = google_speech.get_speech_service()
    service = google_speech.get_speech_service(proxy_info)
    response = google_speech.post_texttospeech(service, "ja", text)

    # audioFile作成
    out_audio_folder = current / Path("audio")
    # audio_file = google_speech.make_audio_file(response, out_audio_folder)
    audio_file = google_speech.make_direct_audio(response, out_audio_folder)

    # audio再生(pyaudio)
    play_audio(str(audio_file))


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="POST Google Text to Speech")
    arg_parser.add_argument("-t", "--text", type=str, default=None, help="Direct Text Change Speech")
    arg_parser.add_argument("-f", "--file", type=str, default=None, help="File Chenge Speech input file path")
    arg_parser.add_argument("-c", "--cmd", type=str, default="", help="cmd:[time:時報,any....]")
    args = arg_parser.parse_args()
    main(args)
