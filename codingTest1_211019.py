# #Ex1 - 거스름돈
# #500 / 100 / 50 / 10 무한히 존재 거름돈 N을 거슬러 줘야할 때 동전의 최소 개수를 구하라. 단 거슬러 줘야 할 돈 N은 항상 10의 배수이다.
#
# N = int(input("거슬러 줘야 할 금액 : "))
# Obek = 0
# Bek = 0
# Osib = 0
# Sib = 0
# while N !=0:
#     if N // 500 >= 1:
#         Obek = N//500
#         N %=500
#     if N // 100 >= 1:
#         Bek = N // 100
#         N %= 100
#     if N // 50 >= 1:
#         Osib = N // 50
#         N %= 50
#     if N // 10 >= 1:
#         Sib = N// 10
#         N %= 10
#     if N == 0:
#         break
#
# print("500원 : {} , 100원 : {}, 50원 : {}, 10원 : {},".format(Obek,Bek,Osib,Sib))
#
# #해설지
# n = 1260
# count = 0
#
# #큰 단위의 화폐부터 차례대로 확인
# coinList = [500,100,50,10]
#
# for coin in coinList:
#     count += n//coin
#     n %= coin
# print(count)
#

# # 1번 문제
# #큰 수의 법칙
# #N = 5 M = 8  K = 3 [ 2 4 5 4 6]
# N,M,K = map(int,input().split())
# print(N, M, K)
# numList = list(map(int,input().split()))
# maxNum1 = max(numList) #첫번째 큰 수
# numList.pop(numList.index(maxNum1))  #큰 수 제외
# maxNum2 = max(numList) #두번째 큰 수
# numList.pop(numList.index(maxNum2))  #큰 수 제외
# result = 0
# if M > K and len(numList) < N:
#     while True:
#         #반복문
#         for i in range(K):
#                 if M == 0:
#                     break
#                 result += maxNum1
#                 M -=1
#         if M == 0:
#             break
#         result += maxNum2
#         M -=1
#     print("result : {}".format(result))
# else:
#     print("배열의 개수가 많거나 K가 M보다 큽니다.")

# 1-1 답안 해설
# N,M,K = map(int,input().split())
# data = list(map(int,input.split()))

# data.sort()
# frist = data[N-1] #maxNum1
# second = data[N-2] #maxNum2

# 가장 큰 수가 더해지는 횟수 계산
# count = int(m / (k+1)) * k  #m은 총 개수 k+1은 최대로 큰수의 k + 분기 하는 숫자 1개 *k는 총 큰 숫자의 갯수가 되고
# count += m%(k+1) #는 총 갯수에서 나머지 큰수의 개수를 더해준다.
# 총 first의 개수는 count에 second는 m-count가 된다.


# #2번문제
# #숫자 카드 게임 M개 N개
# N, M = map(int,input().split())
# resultList = []
# for i in range(N):
#     numList = list(map(int,input().split()))
#     resultList.append(min(numList))
#
# print(max(resultList))

# ##2번문제 해설 1
#
# N, M = map(int, input().split())
# result = 0
#
# for i in range(N):
#     data = list(map(int,input().split()))
#
#     min_value = min(data)
#
#     result = max(result, min_value)
#
# print(result)

# ## 2번문제 해설2
#
# N, M = map(int, input().split())
#
# result = 0
# # 한 줄씩 입력받아 확인
# for i in range(N):
#     data = list(map(int, input().split()))
#     #현재 줄에서 가장 작은 수 찾기
#     min_value = 10001
#     for a in data:
#         min_value = min(min_value,a)
#
#     result  =max(result,min_value)
#
# print(result) #최종 답안.

# # 3번 문제 1이 될 때까지
# # 어떠한 수 N이 1이 될 때까지 다음의 두 과정 중 하나를 반복적으로 선택하여 수행
# # N에서 1을 뺀다.
# # N을 K로 나눈후 N에 대입
#
# N, K = map(int,(input().split()))
# cnt = 0
# while N != 1:
#     if N % K !=0:
#         N -=1
#         cnt +=1
#     elif N % K ==0:
#         N //=K
#         cnt +=1
#
# print(N,cnt)

##3번 해석 내용###########################
# # 3-5.py 단순하게 푸는 답안 공부하기
# N, K = map(int,(input().split()))
# result = 0

# #N이 K이상이라면 K로 계속 나누기
# while N >= K :
#     # N이 K로 나누어 떨어지지 않는다면 N에서 1씩빼기
#     while N % K != 0:
#         N -=1
#         result +=1
#     # K로 나누기
#     N //= K
#     result += 1
#
# #마지막으로 남은 수에 대하여 1씩 빼기
# while N > 1:
#     N -= 1
#     result += 1
#
# print(result)

# # 3-6.py
# N, K = map(int, input().split())
# result = 0
#
# while True:
#     #(N == K로 나누어 떨어지는 수) 가 될 때까지 1씩 빼기
#     target = (N//K) * K
#     result += (N - target)
#
#     N = target
#
#     #N이 K보다 작을 때 (더 이상 나눌 수 없을 때) 반복문 탈출
#     if N < K :
#         break
#     #K로 나누기
#     result += 1
#     N //= K
#
# result += (N-1)
# print(result)


N = int(input())

result = 0
while N != 0:
    if N >= 5:
        result +=N//5
        N %=5
    elif N >= 3:
        result += N // 3
        N %= 3
    else:
        result = -1

print(result)