import subprocess

x1 = subprocess.run("TEST=$(ls | wc -l)", shell=True)
print(x1)
y = subprocess.run("echo $TEST", shell=True)
print(y)
x2 = subprocess.run("ls | head -$TEST", shell=True)
print(x2)
x3 = subprocess.run("echo $TEST", shell=True)
print(x3)
z1 = subprocess.run(["export", "TEST=$(ls | wc -l)"])
print(z1)
z2 = subprocess.run(["echo", "${TEST}"])
print(z2)
