#sortInside / 하 / 정렬,배열 25분
#자릿수를 기준으로 정렬하므로 9부터 0까지 차례대로 확인한다.
#각 숫자에 대하여 해당 숫자의 개수를 계산하여 출력합니다.

nums = list(map(int,input()))

for i in range(9,-1,-1):
    for j in nums:
        if i == j:
            print(i,end='')