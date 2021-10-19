# 2839 설탕 배달문제
"""
설탕 3kg , 5kg
최소한의 봉지를 가져가기 18kg일경우  5,5,5,3
"""
#
# N = int(input())
# sugar = [5,3]
# result = 0
# for sg in sugar:
#     result += N//sg
#     N %=sg
# print(result)

##2839 백준 - 설탕문제
N = int(input())

result = 0
##5로 나누어 떨어지지 않으면 5의 배수가 될 때까지 -3을 해준다.
while N >= 0:
   if N % 5== 0:
       result +=N//5 #몫을 저장
       break #5의배수로 나누어 떨어졌기 때문에 끝.
   N -=3 # 먼저 3부터 빼주면서 5의 배수를 만들어간다.
   result +=1 #3이 제외 되면서 카운트 1 증가
else : #N이 -3이 누적되면서 0보다 작아질 경우 -1이 된다.
    result = -1

print(result)


# 11399 ATM
"""
인하은행에는 ATM이 1대밖에 없다. 지금 이 ATM앞에 N명의 사람들이 줄을 서있다. 사람은 1번부터 N번까지 번호가 매겨져 있으며, i번 사람이 돈을 인출하는데 걸리는 시간은 Pi분이다.
사람들이 줄을 서는 순서에 따라서, 돈을 인출하는데 필요한 시간의 합이 달라지게 된다. 예를 들어, 총 5명이 있고, P1 = 3, P2 = 1, P3 = 4, P4 = 3, P5 = 2 인 경우를 생각해보자.
 [1, 2, 3, 4, 5] 순서로 줄을 선다면, 1번 사람은 3분만에 돈을 뽑을 수 있다. 2번 사람은 1번 사람이 돈을 뽑을 때 까지 기다려야 하기 때문에, 3+1 = 4분이 걸리게 된다. 3번 사람은 1번, 2번 사람이 돈을 뽑을 때까지 기다려야 하기 때문에,
총 3+1+4 = 8분이 필요하게 된다. 4번 사람은 3+1+4+3 = 11분, 5번 사람은 3+1+4+3+2 = 13분이 걸리게 된다. 이 경우에 각 사람이 돈을 인출하는데 필요한 시간의 합은 3+4+8+11+13 = 39분이 된다.
줄을 [2, 5, 1, 4, 3] 순서로 줄을 서면, 2번 사람은 1분만에, 5번 사람은 1+2 = 3분, 1번 사람은 1+2+3 = 6분, 4번 사람은 1+2+3+3 = 9분, 3번 사람은
1+2+3+3+4 = 13분이 걸리게 된다. 각 사람이 돈을 인출하는데 필요한 시간의 합은 1+3+6+9+13 = 32분이다. 이 방법보다 더 필요한 시간의 합을 최소로 만들 수는 없다.
줄을 서 있는 사람의 수 N과 각 사람이 돈을 인출하는데 걸리는 시간 Pi가 주어졌을 때, 각 사람이 돈을 인출하는데 필요한 시간의 합의 최솟값을 구하는 프로그램을 작성하시오.

*오타.. [2,5,1,4,3] (X) -> [2,3,1,4,3]
"""
#
N = int(input("대기자 N명 : "))

timeList = list(map(int,input().split()))
tmp = 0
result = 0
timeList = sorted(timeList)
for i in range(N):
    for j in range(i,i+1,1):
        tmp += timeList[j]
    result = result +tmp

print(result)



#11047 동전 0
# """
# 준규가 가지고 있는 동전은 총 N종류이고, 각각의 동전을 매우 많이 가지고 있다.
#
# 동전을 적절히 사용해서 그 가치의 합을 K로 만들려고 한다. 이때 필요한 동전 개수의 최솟값을 구하는 프로그램을 작성하시오.
# """
N, K = map(int,input().split())
coinList = [1,5,10,50,100,500,1000,5000,10000,50000]
result = 0
for i in range(N):
    print(coinList[i])
coinList.reverse()
for coin in coinList:
    if K / coin > 0:
        result+= K//coin
        K %= coin

print(result)

#1931번
#회의실 배정
N = int(input()) #회의실 이용 최대 개수
timeList = []
limit_time = 0 #시간이 겹치지 않게 하도록 하기 위해서.
order = 0 #첫번째 기준을 잡아주기 위해서 사용
result = 0 #회의실 배정 가능한 시간대 카운트
for i in range(N):
    timeData = tuple(map(int,input().split()))
    timeList.append(timeData)
    for j in range(1):
        if timeList[i][j] < timeList[i][j+1] and order == 0 :
            limit_time = timeList[i][j+1]
            print(timeList[i])
            result +=1
        if limit_time <= timeList[i][j] and order != 0:
            limit_time = timeList[i][j+1]
            print(timeList[i])
            result += 1
        order +=1
print(result)
#첫번째 데이터를 기준으로
