#수정렬하기 3 / 하 / 정렬 /20분 https://www.acmicpc.net/problem/10989
#**** 10,000,000개정도의 데이터까지면 기본 정렬 사용시 안된다. 10,000보다 작다는 걸 알수 있다.
#1.데이터의 개수가 최대 천만개다. 2. 시간복잡도O(N)의 정렬 알고리즘 이용 3.수 범위 1~10,000이므로 계수정렬이용할수있다.
#계수정렬 알고리즘 - 훨씬 빠ㅏ름
#Counting Sort - 배열의 인덱스를 특정한 데이터 값으로 여기는 정렬 방법
# 배열의 크기는 데이터 범위를 포함할 수 있도록 설정 (1~10000), 데이터가 등항한 횟수를 센다.
#ex) 759031629148052 > 7 +1 5 +1~~~~
# sys lib sys.stdin.readline() - 사용할 숫자가 많으면 이게 더 빠르다.

import sys

n = int(sys.stdin.readline())
arr = [0]*10001 #0~10000
for i in range(n):
    data = int(sys.stdin.readline())
    arr[data]+=1

for i in range(len(arr)):
    if arr[i] != 0:
        for j in range(arr[i]):
            print(i)
