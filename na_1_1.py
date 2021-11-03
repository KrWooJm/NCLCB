#python lib사용하기

n = int(input())
numList = list()

for _ in range(n):
    numList.append(int(input()))

numList.sort() #정렬

for i in numList:
    print(i)