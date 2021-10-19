#조건문 01
#난수 비교하기
import random

num1 = random.randint(0,10000)
num2 = random.randint(0,10000)
print("첫번 째 숫자 값 : {}".format(num1))
print("두번 째 숫자 값 : {}".format(num2))

if num1 > num2:
    print(">")
elif num1 < num2:
    print("<")
elif num1 == num2:
    print("==")


#조건문 02
#시험 점수를 입력받아 90 ~ 100점은 A, 80 ~ 89점은 B, 70 ~ 79점은 C, 60 ~ 69점은 D, 나머지 점수는 F를 출력하는 프로그램을 작성하시오.

Score = int(input("시험 점수 입력 : "))

if Score >=90 and Score <=100:
    print("A")
elif Score >=80 and Score <90:
    print("B")
elif Score >= 70 and Score < 80:
    print("C")
elif Score >=60 and Score <70:
    print("D")
else:
    print("F")


#조건문 03
#윤년을 구하는 if문

year = int(input("연도를 입력하세요 : "))
if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
    print("{}년도는 윤년입니다".format(year))
else:
    print("{}년도는 윤년이 아닙니다.".format(year))

#사분면 고르기
x=int(input("x축의 값 입력(-1000<= x <= 1000; x != 0) : "))
y=int(input("y축의 값 입력(-1000<= x <= 1000; x != 0) : "))


if x > 0 :
    if y > 0 :
        print("1")
    else:
        print("4")
else:
    if y > 0 :
        print("2")
    else:
        print("3")


hh= int(input("시간을 입력하세요(0-23) : "))
mm = int(input("분을 입력하세요 (0-59) : "))
tt=0
hh2=0
mm2=0
if hh > 0:
    hh=hh*60
    tt= hh+mm-45
    hh2= int(tt/60)
    mm2= int(tt%60)
elif hh == 0:
    hh=24*60
    tt = hh+mm-45
    hh2 = int(tt/60)
    mm2 = int(tt % 60)
print("{}:{}".format(hh2,mm2))