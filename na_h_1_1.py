#핵심유형 문제풀이
#1.나이순 정렬 / 하 /정렬 / 15분
#(나이, 이름)의 정보를 입력받은뒤에 나이를 기준으로 정렬합니다.
#파이썬의 기본정렬 라이브러리를 이용하면 된다.
#나이가 동일경우 먼저입력된 나이순서
n = int(input())
datas = list()
for _ in range(n):
    a,name = input().split()
    datas.append((a,name))

datas.sort(key=lambda a: a[1]) #lambda x는 x[0]을 기준으로 키값을 잡고 정렬한다.
print(datas)