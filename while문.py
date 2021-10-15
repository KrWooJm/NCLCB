# #while문 1번
# #두 정수 A와 B를 입력받은 다음, A+B를 출력하는 프로그램을 작성하시오.
# while True:
#     N1, N2 = map(int, input().split())
#     if N1==0 and N2==0:
#         break
#     else:
#         print(N1+N2)
#
# #while문 2번
# while True:
#     try:
#         N1, N2 = map(int,input().split())
#         print(N1+N2)
#     except:
#         break

#while문 3번
N = input()
origin = N
tmp = 0
cnt = 0

while True:
    tmp = str(int(N[0]) + int(N[1]))
    if origin == N and cnt !=0:
        break
    else:
        N = N[1] + str(tmp)[-1:]
        cnt = cnt+1

print(cnt)