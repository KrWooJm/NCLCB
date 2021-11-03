import sys
print("숫자 두개를 입력 후 범 위 내의 숫자를 입력해주십시오.")
N,X = map(int, sys.stdin.readline().split())
result = list(map(int,sys.stdin.readline().split()))
for i in range(N):
    if result[i]<X:
        print(result[i], end=" ")