import subprocess
import os

class JadxWrapper:
    def __init__(self, jadx_path="jadx"):
        self.jadx_path = jadx_path

    def decompile(self, input_file, output_dir):
        """
        Decompiles an APK or JAR to the output directory.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        cmd = [
            self.jadx_path,
            "-d", output_dir,
            "--no-imports",
            "--no-debug-info",
            # "--no-replace-consts",
            input_file
        ]
        
        print(f"Running Jadx: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Jadx failed: {result.stderr}")
        return result.stdout
