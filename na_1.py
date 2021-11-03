#기본정렬 알고리즘 * 기초 문제 풀이
#1.수 정렬하기 -정렬 /하/ 15분

#선택 정렬
#매번 가장 작은값을 찾아서 앞으로 보내는 식 75934 > 34975 > 34579
n = int(input())
numList = list()

#숫자넣기
for _ in range(n):
    numList.append(int(input()))

for i in range(n):
    min_idx = i #가장 작은 원소의 인덱스
    for j in range(i+1,n,1):
        if numList[min_idx] > numList[j]:
            min_idx =j

        numList[i],numList[min_idx] = numList[min_idx],numList[i] #i - min_idx / min_idx - i인덱스쪽으로 값을 옮김

for i in numList:
    print(i)

