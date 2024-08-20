import subprocess

def run_test(code: str):
  with open("test/.temp.lua", "w") as f:
    f.write(code)
  return subprocess.run(["python", "main.py", "test/.temp.lua", "--debug"], capture_output=True).stdout.decode().strip()
