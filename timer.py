import time
import subprocess
import os

def play_alarm():
    sound_file = "/System/Library/Sounds/Glass.aiff"
    if os.path.exists(sound_file):
        for _ in range(3):
            subprocess.Popen(["afplay", sound_file])
            time.sleep(0.5)
    else:
        # サウンドファイルが見つからない場合、ターミナルのベル音を鳴らす
        for _ in range(3):
            print("\a", end="", flush=True)
            time.sleep(0.5)


def countdown_timer(seconds):
    print(f"\n⏱ {seconds}秒のタイマーを開始します！\n")
    
    while seconds > 0:
        mins, secs = divmod(seconds, 60)
        print(f"\r{mins:02d}:{secs:02d}", end="")
        time.sleep(1)
        seconds -= 1
    
    print("\r00:00")
    print("\n✅ 時間です！\n")
    play_alarm()

def main():
    print("=== カウントダウンタイマー ===")
    try:
        minutes = int(input("何分タイマーをセットしますか？: "))
        seconds = int(input("何秒タイマーをセットしますか？: "))
        total_seconds = minutes * 60 + seconds
        
        if total_seconds <= 0:
            print("0より大きい時間を入力してください")
            return
        
        countdown_timer(total_seconds)
        
    except KeyboardInterrupt:
        print("\n\nタイマーを中断しました")
    except ValueError:
        print("数字を入力してください")

if __name__ == "__main__":
    main()