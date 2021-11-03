#문제 1
N = int(input())
Nlist = list(map(int,input().split()))
min = 1000000
max = -1000000
for i in range(N):
    #최소값
    if min >= Nlist[i]:
        min = Nlist[i]
    #최대값
    if max <= Nlist[i]:
        max= Nlist[i]

print("{} {}".format(min,max))


#문제2
arr = []
tmp = 0
for i in range(9):
    N = int(input())
    arr.append(N)
    print(arr)

    if len(arr) <= 1:
        pass
    else:
        for j in range(len(arr)- 1):
            if arr[j] <= arr[j + 1]:
                tmp = arr[j + 1]

print(tmp)
print(arr.index(tmp)+1)


#문제3
A = int(input())
B = int(input())
C = int(input())

result = A*B*C
result = str(result)
tmp = list(result)

for i in range(10):
    cnt = 0
    for j in range(len(tmp)):
        if i == int(tmp[j]):
           cnt +=1
    print(cnt)


#문제4 - 나머지
#두 자연수 A와 B가 있을 때, A%B는 A를 B로 나눈 나머지 이다. 예를 들어, 7, 14, 27, 38을 3으로 나눈 나머지는 1, 2, 0, 2이다.
#수 10개를 입력받은 뒤, 이를 42로 나눈 나머지를 구한다. 그 다음 서로 다른 값이 몇 개 있는지 출력하는 프로그램을 작성하시오.
list = [] #나머지 리스트
result = 0
#값 넣기
for i in range(10):
    num = int(input())
    list.append(num%42)
#나머지 다른 갯수 구하기
for i in range(len(list)):
    cnt = 0
    for j in range(i+1,len(list)):
        if list[i] == list[j]:
            cnt += 1
    if cnt == 0:
        result += 1

print(result)

#문제5 평균
#세준이의 시험 점수 조작
N = int(input())
scoreList = list(map(int,input().split()))
maxScore = max(scoreList)

newScore = []
for i in range(N): #또는 리스트의 길이만큼
    newScore.append(scoreList[i]/maxScore *100)
newAvg = sum(newScore)/N
print("{:.2f}".format(newAvg))


#문제6
#"OOXXOXXOOO"와 같은 OX퀴즈의 결과
N = int(input())
for i in range(N):
    S = list(input()) #OX리스트
    sum = 0 #총점
    b = 1 #배점
    for j in S:
        if j == "O":
            sum += b
            b +=1
        else:
            b = 1
    print(sum)

#7번 평균은 넘겠지
# 대학생 새내기들의 90%는 자신이 반에서 평균은 넘는다고 생각한다. 당신은 그들에게 슬픈 진실을 알려줘야 한다.

C = int(input())
for s in range(C):
    scoreList = list(map(int, input().split()))
    avg = (sum(scoreList)-scoreList[0]) / scoreList[0]
    cnt = 0 #평균 이상 카운트
    for i in range(1,len(scoreList)):
        if  scoreList[i]> avg:
            cnt +=1
    print("{:.3f} %".format(cnt/scoreList[0]*100))
