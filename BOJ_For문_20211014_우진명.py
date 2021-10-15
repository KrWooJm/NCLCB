#for문 1
#N을 입력받은 뒤, 구구단 N단을 출력하는 프로그램을 작성하시오. 출력 형식에 맞춰서 출력하면 된다.

num1 = int(input("구구단 숫자를 입력해주세요."))

for i in range(1,10):
    print("{} * {} = {}".format( num1, i, (num1*i) ))



#for문 2
import sys

"""
첫째 줄에 테스트 케이스의 개수 T가 주어진다.

각 테스트 케이스는 한 줄로 이루어져 있으며, 각 줄에 A와 B가 주어진다. (0 < A, B < 10)
"""

numT = int(input("테스트 케이스 개수를 입려하세요 : "))

for i in range(0,numT,1):
    num1 = int(input("num1 : "))
    num2 = int(input("num2 : "))
    print("{} + {} = {}".format(num1,num2,(num1+num2)))



#for문 3
#n이 주어졌을 때, 1부터 n까지 합을 구하는 프로그램을 작성하시오.

numN = int(input("N값을 입력하세요. : "))

print("N값 : {}".format(numN))
tmp = 0 #빈 값(임시 공간)
for i in range(1,numN+1):
    tmp +=i #누적 합 계산

print("총 합계 : {}".format(tmp))


#for문 4
# 빠른 A+B

import sys

numT = int(input("T값 : "))
for i in range(numT):
    num1,num2 = map(int, sys.stdin.readline().split())
    #sys.stdin.readline().split()은 숫자 (띄어쓰기) 숫자 를 입력해야한다.
    print(num1+num2)

#for문 5
#N이 주어질때 N부터 1까지 한 줄에 하나씩 출력하는 프로그램

num = int(input("자연수 N(N <= 100,000 작거나 같은)"))

for i in range(num ,0,-1):
    print(i)


#for문 6
# 두 정수 A와 B를 입력받은 다음, A+B를 출력하는 프로그램을 작성하시오.
import sys

numT = int(input("T값 : "))
for i in range(numT):
    num1,num2 = map(int, sys.stdin.readline().split())
    #sys.stdin.readline().split()은 숫자 (띄어쓰기) 숫자 를 입력해야한다.
    print("Case #{}: {}".format((i+1),(num1+num2)))

#for문 7
# 두 정수 A와 B를 입력받은 다음, A+B를 출력하는 프로그램을 작성하시오.
import sys

numT = int(input("T값 : "))
for i in range(numT):
    num1,num2 = map(int, sys.stdin.readline().split())
    #sys.stdin.readline().split()은 숫자 (띄어쓰기) 숫자 를 입력해야한다.
    print("Case #{}:{} + {} = {}".format((i+1),num1,num2,(num1+num2)))

#for문 8
# 첫째 줄에는 별 1개, 둘째 줄에는 별 2개, N번째 줄에는 별 N개를 찍는 문제
num1 = int(input("자연수 N 입력 : "))

for i in range(num1+1):
    print("*"*i)

#for문 9
#첫째 줄에는 별 1개, 둘째 줄에는 별 2개, N번째 줄에는 별 N개를 찍는 문제
#하지만, 오른쪽을 기준으로 정렬한 별(예제 참고)을 출력하시오.
num1 = int(input("자연수 N 입력 : "))
for i in range(1,num1+1):
     print(" "*(num1-i),"*"*i)

#for문 10
#정수 N개로 이루어진 수열 A와 정수 X가 주어진다. 이때, A에서 X보다 작은 수를 모두 출력하는 프로그램을 작성하시오.
import sys
print("숫자 두개를 입력 후 범 위 내의 숫자를 입력해주십시오.")
N,X = map(int, sys.stdin.readline().split())
result = list(map(int,sys.stdin.readline().split()))
for i in range(N):
    if result[i]<X:
        print(result[i], end=" ")

