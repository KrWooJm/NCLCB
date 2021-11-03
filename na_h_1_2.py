#좌표정렬하기 / 하 / 정렬 / 15분 https://www.acmicpc.net/problem/11650
#x,y좌표 입력받은뒤 x좌표, y좌표 순서대로 차례대로 오름차순으로 정렬한다.
#파이썬의 기본정렬 라이브러리는 기본적으로 튜플의 인덱스 순서대로 오름차순 정렬한다.
#따라서 단순히 기본정렬 라이브러리를 이용하면 된다.key속성 설정없이.

n = int(input())
numList = []
for _ in range(n):
    x,y =map(int,(input().split()))
    numList.append((x,y))

numList.sort()
print(numList)