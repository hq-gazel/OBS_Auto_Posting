import glob
import os
import shutil
import subprocess

if __name__ == '__main__':
    # Pydanticが破損した際の修復プログラム
    try:
        import pydantic_core

    except Exception as e:
        print(f"pydanticでエラーが発生しました。修復作業に入ります。\n{e}")
        USERPROFILE = os.environ['USERPROFILE']
        remove_list = glob.glob(f"{USERPROFILE}\\AppData\\Local\\Programs\\Python\\Python310\\Lib\site-packages\\pydantic*")

        for i in remove_list:
            shutil.rmtree(i)

        subprocess.run("pip install pydantic==2.33.2",shell=True)
        import pydantic_core