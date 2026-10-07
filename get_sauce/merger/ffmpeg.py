import shutil
import subprocess

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def remux(source, destination):
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg was not found on PATH.")
    result=subprocess.run([ffmpeg,"-y","-i",str(source),"-c","copy",str(destination)],
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if result.returncode:
        raise RuntimeError("FFmpeg failed.")
