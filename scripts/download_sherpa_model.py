import os
import sys
import urllib.request
import tarfile
import shutil
from pathlib import Path

# UTF-8 출력 재설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent
    dest_dir = project_root / "server" / "models" / "sherpa-onnx"
    
    # 1. 이미 존재하는지 체크
    if (dest_dir / "model.onnx").exists() and (dest_dir / "lexicon.txt").exists():
        print("🎉 이미 k2-fsa 한국어 VITS 모델 파일들이 존재하므로 다운로드를 생략합니다.")
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # k2-fsa 공식 한국어 VITS 모델 다운로드 URL
    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-mimic3-ko_KO-kss_low.tar.bz2"
    archive_path = dest_dir / "vits-mimic3-ko_KO-kss_low.tar.bz2"
    
    print("==================================================")
    print(" 🔊 k2-fsa 공식 한국어 VITS 모델 다운로드 시작")
    print("==================================================")
    print(f"-> 다운로드 주소: {url}")
    print(f"-> 저장 임시 파일: {archive_path}\n")
    
    try:
        # 다운로드 진행률 콜백
        def progress_hook(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            sys.stdout.write(f"\r  - 다운로드 중: {percent}% ({count * block_size / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB)")
            sys.stdout.flush()

        urllib.request.urlretrieve(url, archive_path, progress_hook)
        print("\n[성공] 다운로드 완료.")
        
        # 압축 해제
        print("-> 압축 해제 중 (tar.bz2)...")
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(path=dest_dir)
        print("[성공] 압축 해제 완료.")
        
        # 압축 해제된 폴더 내부 내용물 정리
        extracted_folder = dest_dir / "vits-mimic3-ko_KO-kss_low"
        if extracted_folder.exists():
            print("-> 모델 구조 정리 중...")
            # model.onnx는 복사하고, 나머지 파일들도 복제
            # vits-mimic3-ko_KO-kss_low.onnx -> model.onnx
            onnx_src = extracted_folder / "vits-mimic3-ko_KO-kss_low.onnx"
            if onnx_src.exists():
                shutil.copy(str(onnx_src), str(dest_dir / "model.onnx"))
                
            lexicon_src = extracted_folder / "lexicon.txt"
            if lexicon_src.exists():
                shutil.copy(str(lexicon_src), str(dest_dir / "lexicon.txt"))
                
            tokens_src = extracted_folder / "tokens.txt"
            if tokens_src.exists():
                shutil.copy(str(tokens_src), str(dest_dir / "tokens.txt"))
                
            # 임시 폴더 삭제
            shutil.rmtree(str(extracted_folder))
            
        # 임시 아카이브 파일 제거
        if archive_path.exists():
            archive_path.unlink()
            
        print("\n==================================================")
        print(" 🎉 한국어 VITS 모델 가중치 파일 배치 완수!")
        print(f"  - 위치: {dest_dir}")
        print("==================================================")
        
    except Exception as e:
        print(f"\n[실패] 에러 발생: {e}")
        if archive_path.exists():
            archive_path.unlink()
        sys.exit(1)

if __name__ == "__main__":
    main()
